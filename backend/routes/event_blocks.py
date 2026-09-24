import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth.security import require_admin
from models import ReservationStatus

router = APIRouter()


class EventBlockCreate(BaseModel):
    building_id: str
    floor_id: str
    slot_ids: List[str]
    date: str
    start_time: str = "08:00"
    end_time: str = "18:00"
    reason: str
    vehicle_plates: Optional[List[Optional[str]]] = None


class EventBlockResponse(BaseModel):
    id: str
    building_id: str
    floor_id: str
    slot_ids: List[str]
    date: str
    start_time: str
    end_time: str
    reason: str
    vehicle_plates: Optional[List[Optional[str]]] = None
    reservation_ids: List[str]
    created_at: str
    created_by: str
    building_name: Optional[str] = None
    floor_label: Optional[str] = None
    slot_labels: Optional[List[str]] = None


@router.post("/event-blocks", response_model=EventBlockResponse)
async def create_event_block(data: EventBlockCreate, current_user: dict = Depends(require_admin)):
    if not data.reason or not data.reason.strip():
        raise HTTPException(status_code=400, detail="A reason for the event block is required")
    if not data.slot_ids:
        raise HTTPException(status_code=400, detail="At least one slot must be selected")

    try:
        datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # PPA-71 fix: refuse event blocks on past dates. Today is fine — admins
    # may still need to retroactively close out the rest of today.
    from datetime import date as _date_cls
    if data.date < _date_cls.today().isoformat():
        raise HTTPException(
            status_code=400,
            detail="Cannot create an event block on a past date",
        )

    building = await db.buildings.find_one({"id": data.building_id}, {"_id": 0, "name": 1})
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    floor = await db.floors.find_one({"id": data.floor_id}, {"_id": 0, "label": 1})

    def time_to_minutes(t):
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    new_start = time_to_minutes(data.start_time)
    new_end = time_to_minutes(data.end_time)
    if new_end <= new_start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    reservation_ids = []
    slot_labels = []
    now = datetime.now(timezone.utc).isoformat()

    # PASS 1: validate that NO slot has an overlapping reservation. We collect
    # ALL conflicts in a single pass so the error message lists every conflicting
    # slot at once (QAT-EVENT-BLOCKING-012 fix — was only reporting the first one).
    conflicts = []
    slots_by_id = {}
    for slot_id in data.slot_ids:
        slot = await db.parking_slots.find_one({"id": slot_id}, {"_id": 0})
        if not slot:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
        slots_by_id[slot_id] = slot

        existing = await db.reservations.find({
            "slot_id": slot_id,
            "date": data.date,
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
        }, {"_id": 0, "start_time": 1, "end_time": 1}).to_list(100)

        for ex in existing:
            ex_start = time_to_minutes(ex["start_time"])
            ex_end = time_to_minutes(ex["end_time"])
            if new_start < ex_end and new_end > ex_start:
                conflicts.append(slot["label"])
                break  # one conflict per slot is enough for the message

    if conflicts:
        if len(conflicts) == 1:
            detail = f"Slot {conflicts[0]} already has a reservation that overlaps with this time on {data.date}"
        else:
            detail = (
                f"Slots {', '.join(conflicts)} already have reservations that overlap "
                f"with this time on {data.date}"
            )
        raise HTTPException(status_code=400, detail=detail)

    # PASS 2: insert the event-block reservations now that we know there are no conflicts.
    for i, slot_id in enumerate(data.slot_ids):
        slot = slots_by_id[slot_id]

        plate = None
        if data.vehicle_plates and i < len(data.vehicle_plates):
            plate = data.vehicle_plates[i] if data.vehicle_plates[i] else None

        res_id = str(uuid.uuid4())
        res_doc = {
            "id": res_id,
            "user_id": current_user["id"],
            "slot_id": slot_id,
            "vehicle_id": None,
            "building_id": data.building_id,
            "floor_id": data.floor_id,
            "date": data.date,
            "start_time": data.start_time,
            "end_time": data.end_time,
            "status": ReservationStatus.CONFIRMED,
            "booking_type": "event_block",
            "created_at": now,
            "photo_url": None,
            "qr_token": None,
            "no_show_reported": False,
            "reason": data.reason,
            "event_vehicle_plate": plate,
        }
        await db.reservations.insert_one(res_doc)
        reservation_ids.append(res_id)
        slot_labels.append(slot["label"])

    event_id = str(uuid.uuid4())
    event_doc = {
        "id": event_id,
        "building_id": data.building_id,
        "floor_id": data.floor_id,
        "slot_ids": data.slot_ids,
        "date": data.date,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "reason": data.reason,
        "vehicle_plates": data.vehicle_plates,
        "reservation_ids": reservation_ids,
        "created_at": now,
        "created_by": current_user["id"],
    }
    await db.event_blocks.insert_one(event_doc)

    return EventBlockResponse(
        id=event_id,
        building_id=data.building_id,
        floor_id=data.floor_id,
        slot_ids=data.slot_ids,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason,
        vehicle_plates=data.vehicle_plates,
        reservation_ids=reservation_ids,
        created_at=now,
        created_by=current_user["id"],
        building_name=building["name"],
        floor_label=floor["label"] if floor else None,
        slot_labels=slot_labels,
    )


@router.get("/event-blocks")
async def list_event_blocks(
    building_id: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    query = {}
    if building_id:
        query["building_id"] = building_id

    events = await db.event_blocks.find(query, {"_id": 0}).sort("date", -1).to_list(200)

    # Enrich with building/floor/slot names
    for event in events:
        building = await db.buildings.find_one({"id": event["building_id"]}, {"_id": 0, "name": 1})
        event["building_name"] = building["name"] if building else None
        floor = await db.floors.find_one({"id": event["floor_id"]}, {"_id": 0, "label": 1})
        event["floor_label"] = floor["label"] if floor else None
        slots = await db.parking_slots.find({"id": {"$in": event["slot_ids"]}}, {"_id": 0, "label": 1}).to_list(100)
        event["slot_labels"] = [s["label"] for s in slots]
        creator = await db.users.find_one({"id": event["created_by"]}, {"_id": 0, "first_name": 1, "last_name": 1})
        event["created_by_name"] = f"{creator['first_name']} {creator['last_name']}" if creator else "Unknown"

    return events


@router.delete("/event-blocks/{event_id}")
async def delete_event_block(event_id: str, current_user: dict = Depends(require_admin)):
    event = await db.event_blocks.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event block not found")

    # Cancel all associated reservations
    for res_id in event.get("reservation_ids", []):
        await db.reservations.update_one(
            {"id": res_id},
            {"$set": {"status": ReservationStatus.CANCELLED}},
        )

    await db.event_blocks.delete_one({"id": event_id})
    return {"message": "Event block removed and slots released"}
