"""
V-08 backfill — sanitize already-stored user fields against CSV/Excel formula
injection. Walks the `users` collection and, for any row whose first_name,
last_name, company, job_family, or parking_sticker_number starts with one of
the dangerous CSV/Excel formula prefixes (= + - @ tab CR), prepends a single
quote so spreadsheets treat the value as text on export.

Idempotent — re-runnable safely (sanitize_csv_field is a no-op on already-safe values).

Usage:
    cd /app/backend
    python scripts/backfill_csv_sanitization.py            # dry-run by default
    python scripts/backfill_csv_sanitization.py --apply    # actually write
"""
import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from database import db, init_db, close_db  # noqa: E402
from routes.users import sanitize_csv_field  # noqa: E402


FIELDS = ["first_name", "last_name", "company", "job_family", "parking_sticker_number"]
DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


async def run(apply_changes: bool):
    await init_db()
    cursor = db.users.find({}, {"_id": 0})
    users = await cursor.to_list(length=1000000)

    tainted = []
    for u in users:
        changes = {}
        for f in FIELDS:
            v = u.get(f)
            if isinstance(v, str) and v and v[:1] in DANGEROUS_PREFIXES:
                clean = sanitize_csv_field(v)
                if clean != v:
                    changes[f] = clean
        if changes:
            tainted.append((u["id"], u.get("email"), changes))

    print(f"Scanned {len(users)} users")
    print(f"Tainted rows: {len(tainted)}")
    for uid, email, changes in tainted[:50]:
        print(f"  {email or uid[:8]}: " + ", ".join(f"{k}={v[:40]!r}" for k, v in changes.items()))
    if len(tainted) > 50:
        print(f"  ... and {len(tainted) - 50} more")

    if not apply_changes:
        print("\nDRY RUN — no changes written. Re-run with --apply to commit.")
    else:
        for uid, _email, changes in tainted:
            await db.users.update_one({"id": uid}, {"$set": changes})
        print(f"\nApplied to {len(tainted)} rows.")

    await close_db()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default is dry-run)")
    args = parser.parse_args()
    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()
