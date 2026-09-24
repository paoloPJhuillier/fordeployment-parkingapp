"""
Admin-only system information endpoints.

Exposes:
 - GET  /api/system/db-info           : which DB backend is active (MongoDB or Couchbase)
 - GET  /api/system/collection-stats  : per-collection document counts on the active DB
 - POST /api/system/sync-mongo-to-couchbase : one-click mirror of MongoDB -> Couchbase Capella
 - GET  /api/system/features          : public feature flags (used by the frontend to
                                        hide UI for disabled/optional features)

The sync endpoint is protected by an in-process lock to prevent concurrent runs.
"""

import asyncio
import os
import time
import uuid
from datetime import timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from database import db
from auth.security import require_admin
import features as feature_flags

router = APIRouter()

# Collections that this app uses. Keep in sync with server.py index list and
# the migration script. Order doesn't matter functionally.
KNOWN_COLLECTIONS: List[str] = [
    "users",
    "sessions",
    "buildings",
    "floors",
    "parking_slots",
    "vehicles",
    "zones",
    "parking_configs",
    "building_policies",
    "slot_registrations",
    "reservations",
    "waitlist_entries",
    "event_blocks",
    "notifications",
    "site_content",
    "templates",
    "ai_insights",
    "migrations",
]

# Single-flight lock so two admins can't trigger a migration simultaneously.
_sync_lock = asyncio.Lock()


def _describe_db() -> Dict[str, str]:
    """Build the {db_type, label, host, database_name, connected} payload."""
    db_type = os.environ.get("DB_TYPE", "mongodb").strip().lower()
    info: Dict[str, str] = {
        "db_type": db_type,
        "connected": bool(getattr(db, "is_connected", False)),
    }

    if db_type == "mongodb":
        info["label"] = "MongoDB"
        info["database_name"] = os.environ.get("DB_NAME", "")
        mongo_url = os.environ.get("MONGO_URL", "")
        if "@" in mongo_url:
            info["host"] = mongo_url.split("@", 1)[1].split("/", 1)[0]
        else:
            info["host"] = mongo_url.replace("mongodb://", "").split("/", 1)[0]
    elif db_type == "couchbase":
        info["label"] = "Couchbase Capella"
        info["database_name"] = os.environ.get("COUCHBASE_BUCKET", "")
        info["host"] = (
            os.environ.get("COUCHBASE_CONNECTION_STRING", "")
            .replace("couchbases://", "")
            .replace("couchbase://", "")
        )
    else:
        info["label"] = db_type

    return info


@router.get("/system/db-info")
async def get_db_info(_: dict = Depends(require_admin)):
    """Return active DB adapter metadata for the admin UI badge."""
    return _describe_db()


@router.get("/system/features")
async def get_features():
    """Public snapshot of optional feature flags. Used by the frontend to
    decide whether to render gated UI (AI Insights button, etc.).

    Public on purpose — no secrets, just booleans.
    """
    return feature_flags.all_flags()


@router.get("/system/build-info")
async def get_build_info():
    """V-10 FIX: cheap unauthenticated build-stamp endpoint so VAPT retests
    and CDN invalidation checks can verify the freshly-built bundle is being
    served. Returns the deploy timestamp and the current backend dependency
    versions of security-sensitive packages.

    Public on purpose — no secrets revealed; used to detect stale caches.
    """
    import importlib.metadata as md
    import time

    def _ver(pkg: str) -> str:
        try:
            return md.version(pkg)
        except Exception:
            return "unknown"

    return {
        "deployed_at": os.environ.get("DEPLOY_TIMESTAMP", "unknown"),
        "server_time": int(time.time()),
        "python_packages": {
            "fastapi": _ver("fastapi"),
            "motor": _ver("motor"),
            "couchbase": _ver("couchbase"),
            "pyjwt": _ver("PyJWT"),
            "bcrypt": _ver("bcrypt"),
        },
    }


@router.get("/system/collection-stats")
async def get_collection_stats(_: dict = Depends(require_admin)):
    """Return per-collection document counts on the currently active database."""
    async def _count_one(name: str):
        try:
            c = await db.get_collection(name).count_documents({})
        except Exception:
            c = -1
        return {"name": name, "count": c}

    # Run all count queries in parallel (important for Couchbase where each
    # N1QL COUNT takes 3-5s on Capella; serial would take 60s+).
    stats = await asyncio.gather(*[_count_one(n) for n in KNOWN_COLLECTIONS])
    total = sum(s["count"] for s in stats if s["count"] > 0)

    return {
        "db_type": os.environ.get("DB_TYPE", "mongodb").strip().lower(),
        "total_documents": total,
        "collections": stats,
    }


@router.post("/system/sync-mongo-to-couchbase")
async def sync_mongo_to_couchbase(_: dict = Depends(require_admin)):
    """Mirror all documents from MongoDB -> Couchbase Capella.

    Runs regardless of the currently active DB_TYPE. Always reads from MONGO_URL
    and writes to COUCHBASE_CONNECTION_STRING/COUCHBASE_BUCKET. Idempotent:
    uses `upsert_multi` so re-running is safe and will overwrite existing docs.
    """
    # Validate required env vars before doing any work
    required = [
        "MONGO_URL",
        "DB_NAME",
        "COUCHBASE_CONNECTION_STRING",
        "COUCHBASE_BUCKET",
        "COUCHBASE_USERNAME",
        "COUCHBASE_PASSWORD",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required env vars: {', '.join(missing)}",
        )

    if _sync_lock.locked():
        raise HTTPException(status_code=409, detail="A sync is already in progress")

    async with _sync_lock:
        started = time.time()

        # Lazy imports so the module doesn't force motor/couchbase loads at app startup.
        from motor.motor_asyncio import AsyncIOMotorClient
        from couchbase.auth import PasswordAuthenticator
        from couchbase.cluster import Cluster
        from couchbase.options import ClusterOptions

        motor_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        motor_db = motor_client[os.environ["DB_NAME"]]

        def _connect_cluster():
            auth = PasswordAuthenticator(
                os.environ["COUCHBASE_USERNAME"], os.environ["COUCHBASE_PASSWORD"]
            )
            options = ClusterOptions(auth)
            try:
                options.apply_profile("wan_development")
            except Exception:
                pass
            cluster = Cluster(os.environ["COUCHBASE_CONNECTION_STRING"], options)
            cluster.wait_until_ready(timedelta(seconds=30))
            return cluster

        cluster = await asyncio.to_thread(_connect_cluster)
        bucket_name = os.environ["COUCHBASE_BUCKET"]
        bucket = cluster.bucket(bucket_name)

        per_collection: List[Dict] = []
        total_written = 0
        errors = 0

        for name in KNOWN_COLLECTIONS:
            try:
                docs = await motor_db[name].find({}, {"_id": 0}).to_list(length=1000000)
            except Exception as e:
                per_collection.append({"name": name, "written": 0, "status": "read-error", "error": str(e)})
                errors += 1
                continue

            if not docs:
                per_collection.append({"name": name, "written": 0, "status": "empty"})
                continue

            # Bind directly to the real Couchbase collection: bucket._default.<name>
            kv = bucket.scope("_default").collection(name)

            def _upsert_all(collection_docs: List[Dict]) -> int:
                batch: Dict = {}
                written = 0
                for d in collection_docs:
                    doc_id = d.get("id") or str(uuid.uuid4())
                    body = {**d, "id": doc_id}
                    batch[str(doc_id)] = body
                    if len(batch) >= 200:
                        kv.upsert_multi(batch)
                        written += len(batch)
                        batch = {}
                if batch:
                    kv.upsert_multi(batch)
                    written += len(batch)
                return written

            try:
                written = await asyncio.to_thread(_upsert_all, docs)
                total_written += written
                per_collection.append({"name": name, "written": written, "status": "ok"})
            except Exception as e:
                errors += 1
                per_collection.append({"name": name, "written": 0, "status": "write-error", "error": str(e)})

        motor_client.close()
        elapsed_seconds = round(time.time() - started, 2)

        return {
            "total_written": total_written,
            "errors": errors,
            "elapsed_seconds": elapsed_seconds,
            "collections": per_collection,
        }
