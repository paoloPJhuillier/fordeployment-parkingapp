"""
Database Abstraction Layer - entry point.

Selects the active database adapter at import time via the DB_TYPE env var,
and exposes a single, shared `db` instance used throughout the application.

Supported DB_TYPE values:
    - "mongodb"  (default) -> MongoDBDatabase
    - "couchbase"          -> CouchbaseDatabase

FastAPI DI pattern:
    from database import get_db

    @router.get("/things")
    async def list_things(db = Depends(get_db)):
        return await db.things.find({}, {"_id": 0}).to_list(100)

Legacy import (still supported for services / background tasks):
    from database import db
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .interface import CollectionInterface, CursorInterface, DatabaseInterface

# Load .env at package import time, consistent with previous behavior
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _build_database() -> DatabaseInterface:
    db_type = os.environ.get("DB_TYPE", "mongodb").strip().lower()

    if db_type == "mongodb":
        from .mongodb import MongoDBDatabase

        return MongoDBDatabase(
            connection_string=os.environ["MONGO_URL"],
            database_name=os.environ["DB_NAME"],
        )

    if db_type == "couchbase":
        from .couchbase_db import CouchbaseDatabase

        return CouchbaseDatabase(
            connection_string=os.environ["COUCHBASE_CONNECTION_STRING"],
            bucket_name=os.environ["COUCHBASE_BUCKET"],
            username=os.environ["COUCHBASE_USERNAME"],
            password=os.environ["COUCHBASE_PASSWORD"],
            # Optional Enterprise-vs-Capella tuning. Defaults preserve
            # current behaviour (Capella) so existing deployments are unaffected.
            deployment=os.environ.get("COUCHBASE_DEPLOYMENT", "capella"),
            trust_store_path=os.environ.get("COUCHBASE_TRUST_STORE_PATH") or None,
            cert_path=os.environ.get("COUCHBASE_CERT_PATH") or None,
            tls_verify=os.environ.get("COUCHBASE_TLS_VERIFY", "peer"),
        )

    raise ValueError(
        f"Unsupported DB_TYPE='{db_type}'. Expected 'mongodb' or 'couchbase'."
    )


# Singleton instance used by services, background tasks, and FastAPI deps.
db: DatabaseInterface = _build_database()


async def init_db() -> None:
    """Connect the active database. Call once during FastAPI startup."""
    await db.connect()


async def close_db() -> None:
    """Disconnect. Call once during FastAPI shutdown."""
    await db.disconnect()


def get_db() -> DatabaseInterface:
    """FastAPI dependency: inject the active database into endpoints.

    Usage:
        @router.get("/x")
        async def x(db = Depends(get_db)): ...
    """
    return db


__all__ = [
    "db",
    "get_db",
    "init_db",
    "close_db",
    "DatabaseInterface",
    "CollectionInterface",
    "CursorInterface",
]
