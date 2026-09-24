"""
Cleanup Script: Fix No-Show Records on Future Dates

This script finds and reverts any reservation records that were incorrectly
marked as "no_show" on future dates. It:
1. Reverts the reservation status back to "pending"
2. Clears the no_show_reported flag
3. Decrements the affected user's no_show_count

Usage:
    python scripts/cleanup_future_no_shows.py
    python scripts/cleanup_future_no_shows.py --dry-run   # Preview only, no changes
"""

import asyncio
import argparse
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")


async def cleanup(dry_run: bool = False):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    bad_records = await db.reservations.find(
        {"status": "no_show", "date": {"$gt": today}},
        {"_id": 0, "id": 1, "date": 1, "user_id": 1, "building_id": 1, "slot_id": 1},
    ).to_list(10000)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Cleanup: found {len(bad_records)} no-show records on future dates (today={today})")

    if not bad_records:
        print("Nothing to clean up.")
        client.close()
        return

    for r in bad_records:
        print(f"  ID={r['id']}  date={r['date']}  user={r['user_id']}  building={r.get('building_id','?')}  slot={r.get('slot_id','?')}")

    if dry_run:
        print("\n[DRY RUN] No changes made. Remove --dry-run to apply fixes.")
        client.close()
        return

    reverted = 0
    for r in bad_records:
        await db.reservations.update_one(
            {"id": r["id"]},
            {"$set": {"status": "pending", "no_show_reported": False}},
        )
        await db.users.update_one(
            {"id": r["user_id"], "no_show_count": {"$gt": 0}},
            {"$inc": {"no_show_count": -1}},
        )
        reverted += 1

    print(f"\nReverted {reverted} records to 'pending' status and corrected user no_show_counts.")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix no-show records on future dates")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    args = parser.parse_args()
    asyncio.run(cleanup(dry_run=args.dry_run))
