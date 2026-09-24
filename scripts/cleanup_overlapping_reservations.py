"""
One-time migration script: Clean up overlapping reservations.
For each user+date combination, if multiple active reservations have overlapping time ranges,
cancel the later-created ones (keep the earliest).
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


def time_to_minutes(t):
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and a_end > b_start


async def cleanup():
    # Find all active reservations
    active = await db.reservations.find(
        {"status": {"$in": ["pending", "confirmed"]}},
        {"_id": 0}
    ).to_list(10000)

    print(f"Total active reservations: {len(active)}")

    # Group by user_id + date
    groups = {}
    for r in active:
        key = (r["user_id"], r["date"])
        groups.setdefault(key, []).append(r)

    cancelled_ids = []
    cancelled_details = []

    for (user_id, date), reservations in groups.items():
        if len(reservations) < 2:
            continue

        # Sort by created_at (keep earliest)
        reservations.sort(key=lambda r: r.get("created_at", ""))

        kept = []
        for res in reservations:
            res_start = time_to_minutes(res.get("start_time", "0:00"))
            res_end = time_to_minutes(res.get("end_time", "0:00"))

            has_overlap = False
            for k in kept:
                k_start = time_to_minutes(k.get("start_time", "0:00"))
                k_end = time_to_minutes(k.get("end_time", "0:00"))
                if overlaps(res_start, res_end, k_start, k_end):
                    has_overlap = True
                    break

            if has_overlap:
                cancelled_ids.append(res["id"])
                cancelled_details.append(
                    f"  CANCEL: user={user_id[:8]}..., date={date}, "
                    f"slot_id={res.get('slot_id', '?')[:8]}..., "
                    f"time={res.get('start_time')}-{res.get('end_time')}, "
                    f"id={res['id'][:8]}..."
                )
            else:
                kept.append(res)

    if cancelled_ids:
        print(f"\nFound {len(cancelled_ids)} overlapping reservations to cancel:")
        for detail in cancelled_details:
            print(detail)

        result = await db.reservations.update_many(
            {"id": {"$in": cancelled_ids}},
            {"$set": {
                "status": "cancelled",
                "cancelled_reason": "auto_cleanup_duplicate_overlap",
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
            }}
        )
        print(f"\nCancelled {result.modified_count} reservations.")
    else:
        print("\nNo overlapping reservations found. Data is clean.")

    client.close()


if __name__ == "__main__":
    asyncio.run(cleanup())
