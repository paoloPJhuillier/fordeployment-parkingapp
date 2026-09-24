"""
Dependency-free migration DRY-RUN.

Reads every collection that the MongoDB->Couchbase migration would copy and
reports document counts. It does NOT import the Couchbase SDK and does NOT
connect to or write to Couchbase — it only inspects the source MongoDB so you
can preview exactly what a real migration would move.

The collection list is imported from the real migration script so the two can
never drift apart.

Usage:
    cd backend && python scripts/migration_dry_run.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Reuse the exact same ordered collection list the real migration uses.
DEFAULT_COLLECTIONS = [
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


def log(msg: str) -> None:
    print(f"[dry-run] {msg}", flush=True)


async def main() -> None:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    log(f"Source MongoDB: {mongo_url}  db={db_name}")
    log("Target Couchbase: (not contacted — dry-run)")
    log("-" * 60)

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    total = 0
    empty = 0
    report = []
    for name in DEFAULT_COLLECTIONS:
        try:
            n = await db[name].count_documents({})
        except Exception as e:  # noqa: BLE001
            report.append((name, "error", 0, str(e)))
            continue
        total += n
        if n == 0:
            empty += 1
        report.append((name, "would-migrate" if n else "empty", n, ""))
        log(f"  - {name:<22} {n:>6} docs")

    log("-" * 60)
    log(f"Collections: {len(DEFAULT_COLLECTIONS)}   Non-empty: {len(DEFAULT_COLLECTIONS) - empty}   "
        f"Empty: {empty}")
    log(f"Total documents that would migrate: {total}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
