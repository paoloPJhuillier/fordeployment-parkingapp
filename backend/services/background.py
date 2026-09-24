import asyncio
import logging
from datetime import datetime, timezone, timedelta

from database import db
from models.enums import ReservationStatus
from services.notifications import create_notification
import features as feature_flags

logger = logging.getLogger(__name__)


async def auto_mark_no_shows():
    while True:
        try:
            now = datetime.now(timezone.utc)
            today_str = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")

            past_date_query = {
                "status": ReservationStatus.PENDING,
                "date": {"$lt": today_str},
            }
            same_day_query = {
                "status": ReservationStatus.PENDING,
                "date": today_str,
                "end_time": {"$lte": current_time},
            }

            past_reservations = await db.reservations.find(past_date_query, {"_id": 0}).to_list(1000)
            today_reservations = await db.reservations.find(same_day_query, {"_id": 0}).to_list(1000)
            all_no_shows = past_reservations + today_reservations

            # Self-check-in mode: also flag today's reservations whose
            # check-in window (start_time + SELF_CHECKIN_WINDOW_MINUTES)
            # has elapsed without the parker tapping "Check in". This is
            # the mechanism that replaces the attendant marking no-shows.
            if not feature_flags.attendant_mode_enabled():
                window_min = feature_flags.self_checkin_window_minutes()
                deadline_clock = (now - timedelta(minutes=window_min)).strftime("%H:%M")
                expired_checkin_query = {
                    "status": ReservationStatus.PENDING,
                    "date": today_str,
                    "start_time": {"$lte": deadline_clock},
                    # exclude rows already captured by the end_time path
                    "end_time": {"$gt": current_time},
                }
                expired = await db.reservations.find(expired_checkin_query, {"_id": 0}).to_list(1000)
                # de-dup against all_no_shows (defensive — shouldn't overlap
                # given the end_time guard above, but cheap insurance).
                already = {r["id"] for r in all_no_shows}
                all_no_shows.extend(r for r in expired if r["id"] not in already)

            if all_no_shows:
                ids = [r["id"] for r in all_no_shows]
                no_show_at = now.isoformat()
                await db.reservations.update_many(
                    {"id": {"$in": ids}},
                    {"$set": {"status": ReservationStatus.NO_SHOW, "no_show_reported": True, "no_show_at": no_show_at}},
                )

                for res in all_no_shows:
                    building = await db.buildings.find_one({"id": res.get("building_id")}, {"_id": 0, "name": 1})
                    building_name = building["name"] if building else "Unknown"
                    await create_notification(
                        user_id=res["user_id"],
                        title="Reservation Marked as No-Show",
                        message=f"Your reservation at {building_name} on {res['date']} ({res.get('start_time', '')} - {res.get('end_time', '')}) was automatically marked as a no-show because it was not confirmed.",
                        notification_type="no_show",
                    )
                    await db.users.update_one({"id": res["user_id"]}, {"$inc": {"no_show_count": 1}})

                logger.info(f"Auto no-show: marked {len(all_no_shows)} reservations and sent notifications")

            # Slot release for no-show reservations based on config
            no_show_reservations = await db.reservations.find(
                {"status": ReservationStatus.NO_SHOW, "slot_released": {"$ne": True}, "date": {"$lte": today_str}},
                {"_id": 0},
            ).to_list(1000)

            for res in no_show_reservations:
                config = await db.parking_configs.find_one({"building_id": res.get("building_id")}, {"_id": 0})
                # Self-check-in mode short-circuits the standard release
                # logic: without attendants, the only way a slot frees up
                # for the waitlist is via this loop, so we release as
                # soon as we see the no-show row instead of waiting for
                # ``no_show_release_minutes``. The traditional
                # per-building knob (``no_show_release_enabled``) is
                # respected when attendants are in charge.
                if not feature_flags.attendant_mode_enabled():
                    should_release_now = True
                    release_reason = "self-checkin window expired"
                elif config and config.get("no_show_release_enabled"):
                    should_release_now = False  # respect the wait
                    release_reason = "no_show_release_minutes elapsed"
                else:
                    continue  # neither path enabled, leave the slot held

                if should_release_now:
                    if res.get("slot_id"):
                        await db.parking_slots.update_one(
                            {"id": res["slot_id"]},
                            {"$set": {"status": "available"}},
                        )
                    await db.reservations.update_one(
                        {"id": res["id"]},
                        {"$set": {"slot_released": True}},
                    )
                    logger.info(f"Auto-released slot {res.get('slot_id')} from no-show reservation {res['id']} ({release_reason})")
                    try:
                        from routes.waitlist import notify_next_waitlisted_user
                        await notify_next_waitlisted_user(res["building_id"], res["date"])
                    except Exception as wl_err:
                        logger.debug(f"Waitlist notify skipped for {res['id']}: {wl_err}")
                    continue

                if config and config.get("no_show_release_enabled"):
                    release_minutes = config.get("no_show_release_minutes", 30)
                    no_show_at_str = res.get("no_show_at")
                    if not no_show_at_str:
                        # Legacy: if no_show_at not set, set it to now and skip this cycle
                        await db.reservations.update_one(
                            {"id": res["id"]},
                            {"$set": {"no_show_at": now.isoformat()}},
                        )
                        continue
                    try:
                        no_show_dt = datetime.fromisoformat(no_show_at_str.replace("Z", "+00:00"))
                        if no_show_dt.tzinfo is None:
                            no_show_dt = no_show_dt.replace(tzinfo=timezone.utc)
                        if now >= no_show_dt + timedelta(minutes=release_minutes):
                            if res.get("slot_id"):
                                await db.parking_slots.update_one(
                                    {"id": res["slot_id"]},
                                    {"$set": {"status": "available"}},
                                )
                            await db.reservations.update_one(
                                {"id": res["id"]},
                                {"$set": {"slot_released": True}},
                            )
                            logger.info(f"Auto-released slot {res.get('slot_id')} from no-show reservation {res['id']} ({release_minutes}min after no-show tag)")

                            # Notify the next person on the waitlist for
                            # this building/date — same call the cancel
                            # endpoint uses. Wrapped in try/except because
                            # missing waitlist support must not break the
                            # release loop.
                            try:
                                from routes.waitlist import notify_next_waitlisted_user
                                await notify_next_waitlisted_user(res["building_id"], res["date"])
                            except Exception as wl_err:
                                logger.debug(f"Waitlist notify skipped for {res['id']}: {wl_err}")
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            logger.error(f"Auto no-show task error: {e}")

        # In self-check-in mode we run more often so a 15-min window
        # closes promptly and the waitlist is notified within a minute
        # instead of within five. In attendant mode the original 5-min
        # cadence is plenty (the attendant marks things in real time).
        await asyncio.sleep(60 if not feature_flags.attendant_mode_enabled() else 300)


async def check_waitlist_expiry():
    """Background task to expire waitlist notifications that have passed the window."""
    while True:
        try:
            now = datetime.now(timezone.utc)

            # Find all "notified" waitlist entries
            notified_entries = await db.waitlist_entries.find(
                {"status": "notified"}, {"_id": 0}
            ).to_list(500)

            for entry in notified_entries:
                notified_at_str = entry.get("notified_at")
                if not notified_at_str:
                    continue

                notified_at = datetime.fromisoformat(notified_at_str.replace("Z", "+00:00"))
                if notified_at.tzinfo is None:
                    notified_at = notified_at.replace(tzinfo=timezone.utc)

                # Get the building config for expiry window
                config = await db.parking_configs.find_one(
                    {"building_id": entry["building_id"]}, {"_id": 0}
                )
                window_minutes = 15
                if config:
                    window_minutes = config.get("waitlist_notification_window_minutes", 15)

                if now >= notified_at + timedelta(minutes=window_minutes):
                    # Expire this entry
                    await db.waitlist_entries.update_one(
                        {"id": entry["id"]},
                        {"$set": {"status": "expired"}},
                    )
                    logger.info(f"Waitlist entry {entry['id']} expired after {window_minutes}min window")

                    # Notify next user in line
                    from routes.waitlist import notify_next_waitlisted_user
                    await notify_next_waitlisted_user(entry["building_id"], entry["preferred_date"])

        except Exception as e:
            logger.error(f"Waitlist expiry check error: {e}")

        await asyncio.sleep(60)  # Check every minute



async def auto_release_slots():
    """QAT-PARKING-CONFIG-007 fix.

    Resets parking_slots.status from 'reserved' / 'blocked' back to 'available'
    once a building's configured `release_time` has passed. Runs every minute.

    Algorithm:
      1. For each building, read its parking_config.release_time (HH:MM).
      2. If `now >= release_time` (HH:MM compare, server local time), then
         take any slot in that building whose status != 'available' AND that
         is NOT under an ACTIVE reservation right now -> set status='available'.
      3. Slot statuses that should NEVER be auto-released: 'maintenance'.
    """
    while True:
        try:
            now = datetime.now(timezone.utc)
            today_str = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")

            buildings = await db.buildings.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
            for b in buildings:
                cfg = await db.parking_configs.find_one(
                    {"building_id": b["id"]}, {"_id": 0, "release_time": 1}
                )
                release_time = (cfg or {}).get("release_time", "06:00")

                # Only act when the release time has passed for today.
                if current_time < release_time:
                    continue

                # Find slots in this building still flagged as not-available.
                non_available = await db.parking_slots.find(
                    {
                        "building_id": b["id"],
                        "status": {"$nin": ["available", "maintenance"]},
                    },
                    {"_id": 0, "id": 1, "label": 1},
                ).to_list(5000)
                if not non_available:
                    continue

                slot_ids = [s["id"] for s in non_available]

                # Skip any slot that has an ACTIVE reservation right now (today, current hour).
                active = await db.reservations.find(
                    {
                        "slot_id": {"$in": slot_ids},
                        "date": today_str,
                        "status": {
                            "$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]
                        },
                        "start_time": {"$lte": current_time},
                        "end_time": {"$gt": current_time},
                    },
                    {"_id": 0, "slot_id": 1},
                ).to_list(5000)
                busy = {a["slot_id"] for a in active}

                releasable = [sid for sid in slot_ids if sid not in busy]
                if releasable:
                    result = await db.parking_slots.update_many(
                        {"id": {"$in": releasable}}, {"$set": {"status": "available"}}
                    )
                    logger.info(
                        f"Auto-release: {result.modified_count} slot(s) returned to "
                        f"available in building {b.get('name')}"
                    )
        except Exception as e:
            logger.error(f"Auto-release error: {e}")

        await asyncio.sleep(60)  # Check every minute
