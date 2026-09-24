"""
Database cleanup tool — operator entry point.

Routes through the active abstraction layer (DB_TYPE in .env), so it works
identically against MongoDB and Couchbase. The 18 collection names match
``provision_couchbase_collections.py``.

Subcommands
-----------
routine
    Idempotent maintenance you can run safely anytime (also runs as a
    background task; this is the manual / cron-friendly version):
      * Marks past pending reservations as no_show + releases slots.
      * Expires stale 'notified' waitlist entries past their window.
      * Resets parking_slot status to 'available' for buildings whose
        release_time has passed and have no active reservation.

purge-test-data
    Removes obvious test fixtures only (DESTRUCTIVE for tests, safe
    otherwise):
      * Users whose email matches *test*@* or starts with ratelimit_reg_*
      * Buildings whose name starts with 'Test '
      * All reservations / waitlist / vehicles / slots tied to the above.

reset-data
    DESTRUCTIVE. Truncates every DATA collection but keeps the schema and
    re-seeds the admin account from FIRST_ADMIN_* env vars (or dev defaults
    with a startup warning, same as server.py).

reset-all
    DESTRUCTIVE. Same as reset-data PLUS clears configs / templates /
    site_content. Use only when you want a totally blank cluster.

Usage
-----
    docker compose exec backend python -m scripts.db_cleanup routine
    docker compose exec backend python -m scripts.db_cleanup purge-test-data
    docker compose exec backend python -m scripts.db_cleanup reset-data --yes
    docker compose exec backend python -m scripts.db_cleanup reset-all --yes
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Make backend/ importable when running via `python -m scripts.db_cleanup`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db, init_db, close_db  # noqa: E402
from auth import hash_password  # noqa: E402

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("db_cleanup")


# Order matters here: data tables first, then config, then admin-managed.
DATA_COLLECTIONS = [
    "reservations",
    "waitlist_entries",
    "event_blocks",
    "notifications",
    "vehicles",
    "slot_registrations",
    "ai_insights",
    "sessions",
]
USER_COLLECTIONS = [
    "users",
]
INFRA_COLLECTIONS = [
    "buildings",
    "floors",
    "parking_slots",
    "zones",
]
CONFIG_COLLECTIONS = [
    "parking_configs",
    "building_policies",
    "site_content",
    "templates",
]
META_COLLECTIONS = [
    "migrations",
]


# ---------------------------------------------------------------------------
# routine
# ---------------------------------------------------------------------------

async def cmd_routine() -> None:
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    # 1) Past PENDING reservations -> NO_SHOW
    past = await db.reservations.find(
        {"status": "pending", "date": {"$lt": today}}, {"_id": 0}
    ).to_list(5000)
    same_day = await db.reservations.find(
        {"status": "pending", "date": today, "end_time": {"$lte": current_time}},
        {"_id": 0},
    ).to_list(5000)
    no_shows = past + same_day
    if no_shows:
        ids = [r["id"] for r in no_shows]
        await db.reservations.update_many(
            {"id": {"$in": ids}},
            {"$set": {"status": "no_show", "no_show_reported": True, "no_show_at": now.isoformat()}},
        )
        log.info("routine: %d reservation(s) flipped to no_show", len(ids))
    else:
        log.info("routine: no past pending reservations")

    # 2) Expire stale 'notified' waitlist entries
    notified = await db.waitlist_entries.find({"status": "notified"}, {"_id": 0}).to_list(5000)
    expired = 0
    for w in notified:
        notified_at = w.get("notified_at")
        if not notified_at:
            continue
        try:
            t = datetime.fromisoformat(notified_at.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        cfg = await db.parking_configs.find_one({"building_id": w["building_id"]}, {"_id": 0})
        window = (cfg or {}).get("waitlist_notification_window_minutes", 15)
        if now >= t + timedelta(minutes=window):
            await db.waitlist_entries.update_one(
                {"id": w["id"]}, {"$set": {"status": "expired"}}
            )
            expired += 1
    log.info("routine: %d waitlist entries expired", expired)

    # 3) Release slots whose building release_time has passed
    buildings = await db.buildings.find({}, {"_id": 0, "id": 1}).to_list(1000)
    released = 0
    for b in buildings:
        cfg = await db.parking_configs.find_one(
            {"building_id": b["id"]}, {"_id": 0, "release_time": 1}
        )
        rt = (cfg or {}).get("release_time", "06:00")
        if current_time < rt:
            continue
        bad = await db.parking_slots.find(
            {"building_id": b["id"], "status": {"$nin": ["available", "maintenance"]}},
            {"_id": 0, "id": 1},
        ).to_list(5000)
        if not bad:
            continue
        sids = [s["id"] for s in bad]
        active = await db.reservations.find(
            {
                "slot_id": {"$in": sids},
                "date": today,
                "status": {"$in": ["pending", "confirmed"]},
                "start_time": {"$lte": current_time},
                "end_time": {"$gt": current_time},
            },
            {"_id": 0, "slot_id": 1},
        ).to_list(5000)
        busy = {a["slot_id"] for a in active}
        free = [sid for sid in sids if sid not in busy]
        if free:
            res = await db.parking_slots.update_many(
                {"id": {"$in": free}}, {"$set": {"status": "available"}}
            )
            released += getattr(res, "modified_count", len(free))
    log.info("routine: %d slot(s) auto-released", released)


# ---------------------------------------------------------------------------
# purge-test-data
# ---------------------------------------------------------------------------

async def cmd_purge_test_data() -> None:
    # Test users: emails containing 'test' OR starting with 'ratelimit_reg_'
    test_users = await db.users.find(
        {
            "$or": [
                {"email": {"$regex": "test", "$options": "i"}},
                {"email": {"$regex": "^ratelimit_reg_"}},
                {"email": {"$regex": "^overlap.test"}},
            ]
        },
        {"_id": 0},
    ).to_list(5000)
    test_user_ids = {u["id"] for u in test_users if u.get("role") != "admin"}

    # Test buildings: names beginning with 'Test '
    test_bldgs = await db.buildings.find(
        {"name": {"$regex": "^Test ", "$options": "i"}}, {"_id": 0}
    ).to_list(5000)
    test_bldg_ids = {b["id"] for b in test_bldgs}

    # Reservations / waitlist / vehicles tied to either set
    if test_user_ids or test_bldg_ids:
        clauses = []
        if test_user_ids:
            clauses.append({"user_id": {"$in": list(test_user_ids)}})
        if test_bldg_ids:
            clauses.append({"building_id": {"$in": list(test_bldg_ids)}})
        match = {"$or": clauses}

        for col_name in ["reservations", "waitlist_entries", "vehicles", "event_blocks", "notifications"]:
            col = getattr(db, col_name)
            res = await col.delete_many(match)
            log.info("purge-test-data: removed %s from %s",
                     getattr(res, "deleted_count", "?"), col_name)

    # Floors / slots tied to test buildings
    if test_bldg_ids:
        await db.floors.delete_many({"building_id": {"$in": list(test_bldg_ids)}})
        await db.parking_slots.delete_many({"building_id": {"$in": list(test_bldg_ids)}})
        await db.parking_configs.delete_many({"building_id": {"$in": list(test_bldg_ids)}})
        await db.buildings.delete_many({"id": {"$in": list(test_bldg_ids)}})
        log.info("purge-test-data: removed %d test buildings + descendants", len(test_bldg_ids))

    if test_user_ids:
        await db.users.delete_many({"id": {"$in": list(test_user_ids)}})
        log.info("purge-test-data: removed %d test user(s)", len(test_user_ids))


# ---------------------------------------------------------------------------
# reset-data / reset-all
# ---------------------------------------------------------------------------

async def _truncate(collections):
    for name in collections:
        col = getattr(db, name)
        res = await col.delete_many({})
        log.info("truncate: %s -> deleted=%s", name, getattr(res, "deleted_count", "?"))


async def _seed_admin():
    seed_email = os.environ.get("FIRST_ADMIN_EMAIL", "admin.test@cebuana.com").strip().lower()
    seed_password = os.environ.get("FIRST_ADMIN_PASSWORD", "Test123!")
    company = os.environ.get("FIRST_ADMIN_COMPANY", "Cebuana Lhuillier")
    if seed_email == "admin.test@cebuana.com" and seed_password == "Test123!":
        log.warning(
            "Re-seeding admin with DEV defaults. Set FIRST_ADMIN_EMAIL / "
            "FIRST_ADMIN_PASSWORD before running this in production."
        )
    doc = {
        "id": str(uuid.uuid4()),
        "email": seed_email,
        "password": hash_password(seed_password),
        "first_name": "Admin",
        "last_name": "User",
        "company": company,
        "role": "admin",
        "is_blocked": False,
        "assigned_buildings": [],
        "main_building": None,
        "tags": [],
        "must_change_password": False,
        "no_show_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    log.info("admin re-seeded: %s", seed_email)


async def cmd_reset_data() -> None:
    await _truncate(DATA_COLLECTIONS + USER_COLLECTIONS)
    await _seed_admin()


async def cmd_reset_all() -> None:
    await _truncate(
        DATA_COLLECTIONS
        + USER_COLLECTIONS
        + INFRA_COLLECTIONS
        + CONFIG_COLLECTIONS
        + META_COLLECTIONS
    )
    await _seed_admin()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

DESTRUCTIVE = {"reset-data", "reset-all", "purge-test-data"}

async def _amain(args: argparse.Namespace) -> None:
    await init_db()
    try:
        log.info("DB_TYPE=%s", os.environ.get("DB_TYPE", "mongodb"))
        if args.cmd == "routine":
            await cmd_routine()
        elif args.cmd == "purge-test-data":
            await cmd_purge_test_data()
        elif args.cmd == "reset-data":
            await cmd_reset_data()
        elif args.cmd == "reset-all":
            await cmd_reset_all()
        else:
            raise SystemExit(f"unknown command {args.cmd!r}")
    finally:
        await close_db()


def main() -> None:
    p = argparse.ArgumentParser(prog="db_cleanup")
    p.add_argument(
        "cmd",
        choices=["routine", "purge-test-data", "reset-data", "reset-all"],
        help="cleanup action to run",
    )
    p.add_argument("--yes", action="store_true",
                   help="skip the destructive-action confirmation prompt")
    args = p.parse_args()

    if args.cmd in DESTRUCTIVE and not args.yes:
        warn = (
            "About to run a DESTRUCTIVE cleanup ('%s'). "
            "Type the command name to confirm: " % args.cmd
        )
        if input(warn).strip() != args.cmd:
            print("Aborted.")
            sys.exit(2)

    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
