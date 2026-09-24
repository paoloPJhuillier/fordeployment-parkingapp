import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import db
from auth.security import get_current_user, require_admin
from models.enums import ReservationStatus

router = APIRouter()


class WaitlistJoin(BaseModel):
    building_id: str
    preferred_date: str
    preferred_start_time: str = "08:00"
    preferred_end_time: str = "18:00"


class WaitlistResponse(BaseModel):
    id: str
    user_id: str
    building_id: str
    preferred_date: str
    preferred_start_time: str
    preferred_end_time: str
    status: str
    position: int
    notified_at: Optional[str] = None
    created_at: str
    user_name: Optional[str] = None
    building_name: Optional[str] = None


# --- Slot Timeline ---

@router.get("/slots/timeline")
async def get_floor_timeline(
    building_id: str,
    floor_id: str,
    date: str,
    current_user: dict = Depends(get_current_user),
):
    """Get hourly availability timeline for all slots on a floor for a given date."""
    slots = await db.parking_slots.find(
        {"building_id": building_id, "floor_id": floor_id},
        {"_id": 0}
    ).to_list(500)

    slot_ids = [s["id"] for s in slots]

    reservations = await db.reservations.find({
        "building_id": building_id,
        "floor_id": floor_id,
        "date": date,
        "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
    }, {"_id": 0}).to_list(2000)

    # Build timeline per slot (6AM to 10PM = 16 hours)
    hours = list(range(6, 22))
    result = {}

    for slot in slots:
        slot_reservations = [r for r in reservations if r["slot_id"] == slot["id"]]
        timeline = []
        for hour in hours:
            hour_str = f"{hour:02d}:00"
            next_hour_str = f"{hour + 1:02d}:00"
            is_booked = False
            for res in slot_reservations:
                if res["start_time"] <= hour_str and res["end_time"] > hour_str:
                    is_booked = True
                    break
            timeline.append({
                "hour": hour,
                "time": hour_str,
                "booked": is_booked,
            })
        result[slot["id"]] = {
            "slot_id": slot["id"],
            "slot_label": slot["label"],
            "status": slot.get("status", "available"),
            "timeline": timeline,
            "total_booked_hours": sum(1 for t in timeline if t["booked"]),
            "total_available_hours": sum(1 for t in timeline if not t["booked"]),
        }

    return result


# --- Waitlist CRUD ---

@router.get("/waitlist/count")
async def get_waitlist_count(
    building_id: str,
    date: str,
    current_user: dict = Depends(get_current_user),
):
    """Get waitlist count for a building on a specific date."""
    count = await db.waitlist_entries.count_documents({
        "building_id": building_id,
        "preferred_date": date,
        "status": "waiting",
    })
    return {"count": count, "building_id": building_id, "date": date}


@router.get("/waitlist/status")
async def get_user_waitlist_status(
    building_id: str,
    date: str,
    current_user: dict = Depends(get_current_user),
):
    """Check if current user is on the waitlist for a building/date."""
    entry = await db.waitlist_entries.find_one({
        "user_id": current_user["id"],
        "building_id": building_id,
        "preferred_date": date,
        "status": {"$in": ["waiting", "notified"]},
    }, {"_id": 0})
    return {"on_waitlist": entry is not None, "entry": entry}


@router.post("/waitlist/join")
async def join_waitlist(
    data: WaitlistJoin,
    current_user: dict = Depends(get_current_user),
):
    """Join the waitlist for a building on a specific date."""
    # Check waitlist is enabled
    config = await db.parking_configs.find_one({"building_id": data.building_id}, {"_id": 0})
    if not config or not config.get("waitlist_enabled"):
        raise HTTPException(status_code=400, detail="Waitlist is not enabled for this building")

    # Check not already on waitlist
    existing = await db.waitlist_entries.find_one({
        "user_id": current_user["id"],
        "building_id": data.building_id,
        "preferred_date": data.preferred_date,
        "status": {"$in": ["waiting", "notified"]},
    })
    if existing:
        raise HTTPException(status_code=400, detail="You are already on the waitlist for this building and date")

    # Get next position
    last_entry = await db.waitlist_entries.find_one(
        {"building_id": data.building_id, "preferred_date": data.preferred_date},
        sort=[("position", -1)],
        projection={"_id": 0, "position": 1},
    )
    position = (last_entry["position"] + 1) if last_entry else 1

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "building_id": data.building_id,
        "preferred_date": data.preferred_date,
        "preferred_start_time": data.preferred_start_time,
        "preferred_end_time": data.preferred_end_time,
        "status": "waiting",
        "position": position,
        "notified_at": None,
        "created_at": now,
    }
    await db.waitlist_entries.insert_one(entry)
    entry.pop("_id", None)

    # Get building name for response
    building = await db.buildings.find_one({"id": data.building_id}, {"_id": 0, "name": 1})

    return {
        **entry,
        "user_name": f"{current_user['first_name']} {current_user['last_name']}",
        "building_name": building["name"] if building else None,
    }


@router.delete("/waitlist/{entry_id}")
async def leave_waitlist(entry_id: str, current_user: dict = Depends(get_current_user)):
    """Leave the waitlist."""
    query = {"id": entry_id}
    if current_user["role"] != "admin":
        query["user_id"] = current_user["id"]

    result = await db.waitlist_entries.update_one(query, {"$set": {"status": "cancelled"}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return {"message": "Removed from waitlist"}


@router.get("/waitlist/building/{building_id}")
async def get_building_waitlist(
    building_id: str,
    date: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    """Admin: Get full waitlist for a building."""
    query = {"building_id": building_id, "status": {"$in": ["waiting", "notified"]}}
    if date:
        query["preferred_date"] = date

    entries = await db.waitlist_entries.find(query, {"_id": 0}).sort("position", 1).to_list(500)

    # Enrich with user names
    user_ids = list({e["user_id"] for e in entries})
    if user_ids:
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}).to_list(500)
        users_map = {u["id"]: f"{u['first_name']} {u['last_name']}" for u in users}
        for e in entries:
            e["user_name"] = users_map.get(e["user_id"])

    return entries


# --- Waitlist Notification Trigger ---

async def notify_next_waitlisted_user(building_id: str, date: str):
    """Called when a slot becomes available (cancellation/no-show).
    Finds the next waitlisted user and sends a notification."""
    config = await db.parking_configs.find_one({"building_id": building_id}, {"_id": 0})
    if not config or not config.get("waitlist_enabled"):
        return

    # Find next waiting user (not already notified)
    next_entry = await db.waitlist_entries.find_one(
        {
            "building_id": building_id,
            "preferred_date": date,
            "status": "waiting",
        },
        sort=[("position", 1)],
        projection={"_id": 0},
    )

    if not next_entry:
        return

    now = datetime.now(timezone.utc).isoformat()

    # Update entry to notified
    await db.waitlist_entries.update_one(
        {"id": next_entry["id"]},
        {"$set": {"status": "notified", "notified_at": now}},
    )

    # Get building name
    building = await db.buildings.find_one({"id": building_id}, {"_id": 0, "name": 1})
    building_name = building["name"] if building else "the building"

    window = config.get("waitlist_notification_window_minutes", 15)

    # Send in-app notification
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": next_entry["user_id"],
        "title": "Parking Slot Available!",
        "message": f"A parking slot is now available at {building_name} on {date}. You have {window} minutes to book. Go to the booking page now!",
        "type": "waitlist_available",
        "read": False,
        "created_at": now,
    })

    return next_entry
