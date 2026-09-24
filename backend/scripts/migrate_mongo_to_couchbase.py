"""
Migrate data from MongoDB to Couchbase Capella.

This script is idempotent — you can re-run it safely. For each MongoDB
collection it copies all documents into Couchbase using the same
key strategy the CouchbaseDatabase adapter uses:

    Key:   "{collection}::{doc.id}"   (id auto-generated if missing)
    Body:  doc + {"type": "{collection}"}
    Op:    upsert  (replaces existing docs, guarantees idempotency)

Usage:
    cd /app/backend
    python scripts/migrate_mongo_to_couchbase.py              # migrate everything
    python scripts/migrate_mongo_to_couchbase.py --dry-run    # count only, no writes
    python scripts/migrate_mongo_to_couchbase.py users buildings   # specific collections
    python scripts/migrate_mongo_to_couchbase.py --wipe       # wipe Couchbase bucket first

Environment variables (loaded from /app/backend/.env automatically):
    MONGO_URL, DB_NAME
    COUCHBASE_CONNECTION_STRING, COUCHBASE_BUCKET, COUCHBASE_USERNAME, COUCHBASE_PASSWORD
"""

import argparse
import asyncio
import os
import sys
import time
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.exceptions import CouchbaseException
from couchbase.options import ClusterOptions, QueryOptions

# Load env from backend/.env (this script lives in backend/scripts/)
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


# ---------------------------------------------------------------------------
# Collections to migrate (in dependency-friendly order)
# ---------------------------------------------------------------------------
DEFAULT_COLLECTIONS: List[str] = [
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SCOPE_NAME = "_default"


def log(msg: str) -> None:
    print(f"[migrate] {msg}", flush=True)


def build_cb_cluster() -> Cluster:
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


async def fetch_all(motor_db, collection: str) -> List[dict]:
    cur = motor_db[collection].find({}, {"_id": 0})
    return await cur.to_list(length=1000000)


def upsert_batch(kv, collection: str, docs: Iterable[dict], batch_size: int = 200) -> int:
    """Upsert documents using upsert_multi for much better throughput on Capella.

    Note: `kv` here is a collection-scoped handle (bucket.scope(_default).collection(X)),
    so keys are just the bare doc id and no `type` field is added.
    """
    count = 0
    batch: dict = {}
    for doc in docs:
        doc_id = doc.get("id") or str(uuid.uuid4())
        body = {**doc, "id": doc_id}
        batch[str(doc_id)] = body
        if len(batch) >= batch_size:
            kv.upsert_multi(batch)
            count += len(batch)
            batch = {}
    if batch:
        kv.upsert_multi(batch)
        count += len(batch)
    return count


def wipe_bucket(cluster: Cluster, bucket_name: str) -> None:
    """Wipe every native collection under the `_default` scope (preserves collection definitions)."""
    log(f"Wiping all collections in `{bucket_name}`.`{SCOPE_NAME}` ...")
    for name in DEFAULT_COLLECTIONS:
        try:
            cluster.query(f"DELETE FROM `{bucket_name}`.`{SCOPE_NAME}`.`{name}`").execute()
        except CouchbaseException as e:
            log(f"  WARN: wipe {name}: {e}")
    log("Wipe complete.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(description="Migrate MongoDB -> Couchbase")
    parser.add_argument("collections", nargs="*", help="Specific collections to migrate; default = all")
    parser.add_argument("--dry-run", action="store_true", help="Only print counts, don't write")
    parser.add_argument("--wipe", action="store_true", help="Wipe Couchbase bucket before migrating")
    args = parser.parse_args()

    targets = args.collections or DEFAULT_COLLECTIONS

    # --- Mongo ---
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    log(f"Source MongoDB: {mongo_url}  db={db_name}")
    motor_client = AsyncIOMotorClient(mongo_url)
    motor_db = motor_client[db_name]

    # --- Couchbase (only if not dry-run) ---
    cluster = None
    bucket = None
    bucket_name = os.environ["COUCHBASE_BUCKET"]
    if not args.dry_run:
        log(f"Target Couchbase: {os.environ['COUCHBASE_CONNECTION_STRING']}  bucket={bucket_name}  scope={SCOPE_NAME}")
        cluster = build_cb_cluster()
        bucket = cluster.bucket(bucket_name)
        if args.wipe:
            wipe_bucket(cluster, bucket_name)

    # --- Migrate ---
    totals = {"read": 0, "written": 0, "skipped_empty": 0, "errors": 0}
    per_collection_report = []
    started = time.time()

    for collection in targets:
        try:
            docs = await fetch_all(motor_db, collection)
        except Exception as e:
            log(f"ERROR reading {collection}: {e}")
            totals["errors"] += 1
            per_collection_report.append((collection, "read-error", 0, str(e)))
            continue

        totals["read"] += len(docs)
        if not docs:
            log(f"  - {collection}: 0 docs (skip)")
            totals["skipped_empty"] += 1
            per_collection_report.append((collection, "empty", 0, ""))
            continue

        if args.dry_run:
            log(f"  - {collection}: {len(docs)} docs (dry-run)")
            per_collection_report.append((collection, "dry-run", len(docs), ""))
            continue

        try:
            # Bind KV handle to the target collection (real Couchbase 7+ collection)
            kv = bucket.scope(SCOPE_NAME).collection(collection)
            written = upsert_batch(kv, collection, docs)
            totals["written"] += written
            log(f"  - {collection}: {written} docs migrated")
            per_collection_report.append((collection, "ok", written, ""))
        except Exception as e:
            log(f"ERROR writing {collection}: {e}")
            totals["errors"] += 1
            per_collection_report.append((collection, "write-error", 0, str(e)))

    elapsed = time.time() - started
    log("-" * 60)
    log(f"Done in {elapsed:.1f}s")
    log(f"  read={totals['read']}  written={totals['written']}  "
        f"empty={totals['skipped_empty']}  errors={totals['errors']}")

    log("-" * 60)
    log("Per-collection summary:")
    for name, status, n, err in per_collection_report:
        tail = f"  [{err}]" if err else ""
        log(f"  {name:<22} {status:<12} {n:>6}{tail}")

    motor_client.close()
    if totals["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
