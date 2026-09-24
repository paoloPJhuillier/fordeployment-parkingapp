import uuid
import re
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response

from database import db
from config import ALLOWED_IMAGE_EXTENSIONS
from storage import get_storage
from auth.security import get_current_user, require_admin
from models import (
    BuildingCreate, BuildingResponse, BuildingUpdate, FloorCreate, FloorResponse,
    ParkingSlotResponse, SlotUpdate, BulkSlotsCreate,
    SlotStatus, ReservationStatus,
)

router = APIRouter()


@router.get("/buildings", response_model=List[BuildingResponse])
async def get_buildings(current_user: dict = Depends(get_current_user)):
    """Get buildings accessible to the current user.
    
    V-02/V-06 FIX: Filter buildings based on user role and assignments.
    - Admins: See all buildings
    - Attendants: Only see assigned buildings
    - Users: Only see their main building and assigned buildings
    """
    user_role = current_user.get("role", "user")
    
    # Build query filter based on role
    query = {}
    if user_role == "admin":
        # Admins see all buildings
        pass
    elif user_role == "attendant":
        # Attendants only see their assigned buildings
        assigned = current_user.get("assigned_buildings", [])
        if assigned:
            query["id"] = {"$in": assigned}
        else:
            return []  # No assigned buildings
    else:
        # Regular users see: their main_building + assigned_buildings + any
        # buildings reachable via a zone they belong to.
        # PPA-72 fix: zone buildings were being dropped here, so users in a
        # multi-building zone only ever saw their main_building (one entry)
        # in the booking dropdown.
        user_buildings = set()
        if current_user.get("main_building"):
            user_buildings.add(current_user["main_building"])
        user_buildings.update(current_user.get("assigned_buildings", []) or [])
        # Pull in zone buildings (zones whose user_ids contain this user).
        user_zones = await db.zones.find(
            {"user_ids": current_user["id"]}, {"_id": 0, "building_ids": 1}
        ).to_list(100)
        for z in user_zones:
            for bid in z.get("building_ids", []) or []:
                user_buildings.add(bid)
        if user_buildings:
            query["id"] = {"$in": list(user_buildings)}
        # If still empty (no main, no assigned, no zones), return all so the
        # user can at least browse availability — same behaviour as before.
    
    buildings = await db.buildings.find(query, {"_id": 0}).to_list(100)
    if not buildings:
        return []

    building_ids = [b["id"] for b in buildings]

    # Batch fetch all floors and slots in 2 queries instead of N+1
    all_floors = await db.floors.find({"building_id": {"$in": building_ids}}, {"_id": 0}).to_list(1000)
    floor_ids = [f["id"] for f in all_floors]
    all_slots = await db.parking_slots.find({"floor_id": {"$in": floor_ids}}, {"_id": 0}).to_list(10000) if floor_ids else []

    # Index slots by floor_id
    slots_by_floor = {}
    for s in all_slots:
        slots_by_floor.setdefault(s["floor_id"], []).append(ParkingSlotResponse(**s))

    # Index floors by building_id
    floors_by_building = {}
    for f in all_floors:
        floor_resp = FloorResponse(
            id=f["id"],
            label=f["label"],
            building_id=f["building_id"],
            layout_image_url=f.get("layout_image_url"),
            slots=slots_by_floor.get(f["id"], []),
        )
        floors_by_building.setdefault(f["building_id"], []).append(floor_resp)

    return [BuildingResponse(
        id=b["id"],
        name=b["name"],
        address=b.get("address", ""),
        address_line_1=b.get("address_line_1"),
        address_line_2=b.get("address_line_2"),
        total_floors=b.get("total_floors", 1),
        created_at=b["created_at"],
        floors=floors_by_building.get(b["id"], []),
    ) for b in buildings]


@router.post("/buildings", response_model=BuildingResponse)
async def create_building(building: BuildingCreate, current_user: dict = Depends(require_admin)):
    building_id = str(uuid.uuid4())
    # Build address from line 1 and 2 if provided, else use address field
    full_address = building.address or ""
    if building.address_line_1:
        full_address = building.address_line_1
        if building.address_line_2:
            full_address += ", " + building.address_line_2
    
    building_doc = {
        "id": building_id,
        "name": building.name,
        "address": full_address,
        "address_line_1": building.address_line_1,
        "address_line_2": building.address_line_2,
        "total_floors": building.total_floors,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.buildings.insert_one(building_doc)

    floor_responses = []
    for floor_num in range(1, building.total_floors + 1):
        floor_id = str(uuid.uuid4())
        floor_doc = {
            "id": floor_id,
            "label": f"Floor {floor_num}",
            "building_id": building_id,
            "layout_image_url": None,
        }
        await db.floors.insert_one(floor_doc)

        slots = []
        prefix = building.slot_prefix or f"F{floor_num}-"
        for i in range(building.slots_per_floor):
            slot_id = str(uuid.uuid4())
            slot_label = f"{prefix}{i + 1}"
            slot_doc = {
                "id": slot_id,
                "label": slot_label,
                "floor_id": floor_id,
                "building_id": building_id,
                "status": SlotStatus.AVAILABLE,
                "row": i // 5,
                "column": i % 5,
            }
            await db.parking_slots.insert_one(slot_doc)
            slots.append(ParkingSlotResponse(**slot_doc))

        floor_responses.append(FloorResponse(
            id=floor_id,
            label=f"Floor {floor_num}",
            building_id=building_id,
            slots=slots,
        ))

    return BuildingResponse(
        id=building_id,
        name=building.name,
        address=full_address,
        address_line_1=building.address_line_1,
        address_line_2=building.address_line_2,
        total_floors=building.total_floors,
        created_at=building_doc["created_at"],
        floors=floor_responses,
    )


@router.put("/buildings/{building_id}", response_model=BuildingResponse)
async def update_building(building_id: str, data: BuildingUpdate, current_user: dict = Depends(require_admin)):
    building = await db.buildings.find_one({"id": building_id})
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.address is not None:
        update_data["address"] = data.address
    if data.address_line_1 is not None:
        update_data["address_line_1"] = data.address_line_1
    if data.address_line_2 is not None:
        update_data["address_line_2"] = data.address_line_2
    
    # Rebuild full address if line fields provided
    if data.address_line_1 is not None or data.address_line_2 is not None:
        line1 = data.address_line_1 if data.address_line_1 is not None else building.get("address_line_1", "")
        line2 = data.address_line_2 if data.address_line_2 is not None else building.get("address_line_2", "")
        full_address = line1
        if line2:
            full_address += ", " + line2
        update_data["address"] = full_address
    
    if update_data:
        await db.buildings.update_one({"id": building_id}, {"$set": update_data})
    
    updated = await db.buildings.find_one({"id": building_id}, {"_id": 0})
    floors = await db.floors.find({"building_id": building_id}, {"_id": 0}).to_list(100)
    floor_responses = []
    for f in floors:
        slots = await db.parking_slots.find({"floor_id": f["id"]}, {"_id": 0}).to_list(500)
        floor_responses.append(FloorResponse(
            id=f["id"],
            label=f["label"],
            building_id=f["building_id"],
            layout_image_url=f.get("layout_image_url"),
            slots=[ParkingSlotResponse(**s) for s in slots],
        ))
    
    return BuildingResponse(
        id=updated["id"],
        name=updated["name"],
        address=updated.get("address", ""),
        address_line_1=updated.get("address_line_1"),
        address_line_2=updated.get("address_line_2"),
        total_floors=updated.get("total_floors", 1),
        created_at=updated["created_at"],
        floors=floor_responses,
    )


@router.delete("/buildings/{building_id}")
async def delete_building(building_id: str, current_user: dict = Depends(require_admin)):
    await db.parking_slots.delete_many({"building_id": building_id})
    await db.floors.delete_many({"building_id": building_id})
    result = await db.buildings.delete_one({"id": building_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Building not found")
    return {"message": "Building and all related data deleted"}


@router.post("/buildings/{building_id}/floors", response_model=FloorResponse)
async def add_floor(building_id: str, floor: FloorCreate, current_user: dict = Depends(require_admin)):
    building = await db.buildings.find_one({"id": building_id})
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    floor_id = str(uuid.uuid4())
    floor_doc = {
        "id": floor_id,
        "label": floor.label,
        "building_id": building_id,
        "layout_image_url": None,
    }
    await db.floors.insert_one(floor_doc)

    slots = []
    if floor.slot_labels and len(floor.slot_labels) > 0:
        for i, label in enumerate(floor.slot_labels):
            slot_id = str(uuid.uuid4())
            slot_doc = {
                "id": slot_id,
                "label": label,
                "floor_id": floor_id,
                "building_id": building_id,
                "status": SlotStatus.AVAILABLE,
                "row": i // 5,
                "column": i % 5,
            }
            await db.parking_slots.insert_one(slot_doc)
            slots.append(ParkingSlotResponse(**slot_doc))
    else:
        prefix = floor.slot_prefix or f"{floor.label[:2].upper()}-"
        for i in range(floor.slot_count):
            slot_id = str(uuid.uuid4())
            slot_doc = {
                "id": slot_id,
                "label": f"{prefix}{i + 1}",
                "floor_id": floor_id,
                "building_id": building_id,
                "status": SlotStatus.AVAILABLE,
                "row": i // 5,
                "column": i % 5,
            }
            await db.parking_slots.insert_one(slot_doc)
            slots.append(ParkingSlotResponse(**slot_doc))

    await db.buildings.update_one({"id": building_id}, {"$inc": {"total_floors": 1}})

    return FloorResponse(id=floor_id, label=floor.label, building_id=building_id, slots=slots)


@router.post("/floors/{floor_id}/layout")
async def upload_floor_layout(floor_id: str, file: UploadFile = File(...), current_user: dict = Depends(require_admin)):
    floor = await db.floors.find_one({"id": floor_id}, {"_id": 0})
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    safe_filename = f"floor_{re.sub(r'[^a-zA-Z0-9_-]', '', floor_id)}.{ext}"

    layout_url = get_storage().put(
        safe_filename,
        content,
        content_type=file.content_type or f"image/{ext}",
    )
    await db.floors.update_one({"id": floor_id}, {"$set": {"layout_image_url": layout_url}})

    return {"message": "Layout image uploaded", "layout_image_url": layout_url}


@router.delete("/floors/{floor_id}/layout")
async def delete_floor_layout(floor_id: str, current_user: dict = Depends(require_admin)):
    floor = await db.floors.find_one({"id": floor_id}, {"_id": 0})
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    # Best-effort cleanup of the underlying object (no-op if storage already
    # cleared it). Filename is reconstructed from the floor_id sanitization
    # rule used at upload time; we don't know the original extension so we
    # try the common ones.
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', floor_id)
    storage = get_storage()
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        candidate = f"floor_{safe_id}.{ext}"
        if storage.exists(candidate):
            storage.delete(candidate)

    await db.floors.update_one({"id": floor_id}, {"$set": {"layout_image_url": None}})
    return {"message": "Layout image removed"}


@router.get("/uploads/{filename}")
async def serve_upload(filename: str, current_user: dict = Depends(get_current_user)):
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    if not safe_name or '..' in safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    try:
        content = get_storage().get(safe_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

    content_types = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
    content_type = content_types.get(ext, "application/octet-stream")

    return Response(content=content, media_type=content_type)


@router.put("/slots/{slot_id}")
async def rename_slot(slot_id: str, update: SlotUpdate, current_user: dict = Depends(require_admin)):
    slot = await db.parking_slots.find_one({"id": slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    await db.parking_slots.update_one({"id": slot_id}, {"$set": {"label": update.label}})
    return {"message": "Slot renamed", "slot_id": slot_id, "new_label": update.label}


@router.put("/slots/{slot_id}/status")
async def update_slot_status(slot_id: str, status: str, current_user: dict = Depends(require_admin)):
    slot = await db.parking_slots.find_one({"id": slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    valid_statuses = [s.value for s in SlotStatus]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    if status == SlotStatus.MAINTENANCE:
        active = await db.reservations.find_one({
            "slot_id": slot_id,
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
        })
        if active:
            raise HTTPException(status_code=400, detail="Cannot block a slot with active reservations. Cancel them first.")
    await db.parking_slots.update_one({"id": slot_id}, {"$set": {"status": status}})
    return {"message": f"Slot status updated to {status}", "slot_id": slot_id, "status": status}


@router.post("/floors/{floor_id}/slots")
async def add_slots_to_floor(floor_id: str, data: BulkSlotsCreate, current_user: dict = Depends(require_admin)):
    floor = await db.floors.find_one({"id": floor_id}, {"_id": 0})
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    building_id = floor["building_id"]
    existing_slots = await db.parking_slots.find({"floor_id": floor_id}, {"_id": 0}).to_list(1000)
    existing_count = len(existing_slots)

    new_slots = []
    if data.slot_labels and len(data.slot_labels) > 0:
        for i, label in enumerate(data.slot_labels):
            slot_id = str(uuid.uuid4())
            idx = existing_count + i
            slot_doc = {
                "id": slot_id,
                "label": label,
                "floor_id": floor_id,
                "building_id": building_id,
                "status": SlotStatus.AVAILABLE,
                "row": idx // 5,
                "column": idx % 5,
            }
            await db.parking_slots.insert_one(slot_doc)
            new_slots.append(ParkingSlotResponse(**slot_doc))
    elif data.slot_count and data.slot_count > 0:
        prefix = data.slot_prefix or f"{floor['label'][:2].upper()}-"
        start_num = existing_count + 1
        for i in range(data.slot_count):
            slot_id = str(uuid.uuid4())
            idx = existing_count + i
            slot_doc = {
                "id": slot_id,
                "label": f"{prefix}{start_num + i}",
                "floor_id": floor_id,
                "building_id": building_id,
                "status": SlotStatus.AVAILABLE,
                "row": idx // 5,
                "column": idx % 5,
            }
            await db.parking_slots.insert_one(slot_doc)
            new_slots.append(ParkingSlotResponse(**slot_doc))
    else:
        raise HTTPException(status_code=400, detail="Provide either slot_labels or slot_count")

    return {"message": f"Added {len(new_slots)} slots", "slots": new_slots}


@router.delete("/slots/{slot_id}")
async def delete_slot(slot_id: str, current_user: dict = Depends(require_admin)):
    slot = await db.parking_slots.find_one({"id": slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    active = await db.reservations.find_one({
        "slot_id": slot_id,
        "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
    })
    if active:
        raise HTTPException(status_code=400, detail="Cannot delete slot with active reservations")
    await db.parking_slots.delete_one({"id": slot_id})
    return {"message": "Slot deleted"}


@router.get("/slots/available")
async def get_available_slots(
    building_id: str,
    date: str,
    floor_id: str = None,
    current_user: dict = Depends(get_current_user),
):
    query = {"building_id": building_id}
    if floor_id:
        query["floor_id"] = floor_id

    slots = await db.parking_slots.find(query, {"_id": 0}).to_list(1000)

    reservations = await db.reservations.find({
        "building_id": building_id,
        "date": date,
        "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
    }, {"_id": 0}).to_list(1000)

    # PPA event-block visibility fix: also load active event blocks for this
    # building+date so the slot picker can flag slots already blocked off by
    # an event (admin couldn't see existing block-off status before).
    event_blocks = await db.event_blocks.find({
        "building_id": building_id,
        "date": date,
    }, {"_id": 0}).to_list(1000)

    # Map slot_id -> list of (start_time, end_time, reason) from event blocks
    blocks_by_slot = {}
    for blk in event_blocks:
        for sid in blk.get("slot_ids", []) or []:
            blocks_by_slot.setdefault(sid, []).append({
                "start_time": blk.get("start_time", "00:00"),
                "end_time": blk.get("end_time", "23:59"),
                "reason": blk.get("reason", ""),
            })

    # Build reservations-by-slot map
    res_by_slot = {}
    for res in reservations:
        res_by_slot.setdefault(res["slot_id"], []).append(res)

    # Check for dedicated slot policy
    policy = await db.building_policies.find_one(
        {"building_id": building_id, "enabled": True}, {"_id": 0}
    )
    is_dedicated = policy and policy.get("policy_type") == "dedicated_slot"

    user_registered_slots = set()
    slot_reg_counts = {}
    if is_dedicated:
        user_regs = await db.slot_registrations.find(
            {"user_id": current_user["id"], "building_id": building_id, "status": "active"},
            {"_id": 0}
        ).to_list(100)
        user_registered_slots = {r["slot_id"] for r in user_regs}

        all_regs = await db.slot_registrations.find(
            {"building_id": building_id, "status": "active"},
            {"_id": 0, "slot_id": 1}
        ).to_list(5000)
        for r in all_regs:
            slot_reg_counts[r["slot_id"]] = slot_reg_counts.get(r["slot_id"], 0) + 1

    # Build hourly timeline (0 to 23 = full 24 hours)
    hours = list(range(0, 24))

    def time_str_to_minutes(t):
        """Convert 'H:MM' or 'HH:MM' to minutes since midnight."""
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    result = []
    for slot in slots:
        slot_data = ParkingSlotResponse(**slot)
        slot_reservations = res_by_slot.get(slot["id"], [])
        slot_blocks = blocks_by_slot.get(slot["id"], [])

        # Build hourly timeline for this slot
        timeline = []
        booked_hours = 0
        for hour in hours:
            hour_start_min = hour * 60  # e.g., 9*60 = 540
            hour_end_min = (hour + 1) * 60  # e.g., 10*60 = 600
            is_booked = False
            for res in slot_reservations:
                res_start = time_str_to_minutes(res.get("start_time", "0:00"))
                res_end = time_str_to_minutes(res.get("end_time", "0:00"))
                # Overlap check: hour block [hour_start, hour_end) overlaps with reservation [res_start, res_end)
                if hour_start_min < res_end and hour_end_min > res_start:
                    is_booked = True
                    break
            # Event blocks also occupy hours
            if not is_booked:
                for blk in slot_blocks:
                    bs = time_str_to_minutes(blk.get("start_time", "0:00"))
                    be = time_str_to_minutes(blk.get("end_time", "0:00"))
                    if hour_start_min < be and hour_end_min > bs:
                        is_booked = True
                        break
            if is_booked:
                booked_hours += 1
            timeline.append({
                "hour": hour,
                "time": f"{hour:02d}:00",
                "booked": is_booked,
            })

        # Slot is fully unavailable only if ALL hours are booked or slot is in maintenance
        is_fully_booked = booked_hours == len(hours)
        is_event_blocked = len(slot_blocks) > 0
        is_available = not is_fully_booked and slot["status"] == SlotStatus.AVAILABLE and not is_event_blocked

        slot_dict = slot_data.model_dump()
        slot_dict["is_available"] = is_available
        slot_dict["ownership_type"] = slot.get("ownership_type")
        slot_dict["timeline"] = timeline
        slot_dict["booked_hours"] = booked_hours
        slot_dict["available_hours"] = len(hours) - booked_hours
        slot_dict["is_event_blocked"] = is_event_blocked
        if is_event_blocked:
            slot_dict["event_block_reason"] = slot_blocks[0].get("reason", "")

        if is_dedicated:
            current_floor = floor_id or slot.get("floor_id")
            is_open_floor = current_floor in policy.get("open_floor_ids", [])
            is_user_assigned = slot["id"] in user_registered_slots
            reg_count = slot_reg_counts.get(slot["id"], 0)

            slot_dict["is_dedicated_policy"] = True
            slot_dict["is_open_floor"] = is_open_floor
            slot_dict["is_user_assigned"] = is_user_assigned
            slot_dict["registered_users_count"] = reg_count
            slot_dict["max_users_per_slot"] = policy.get("max_users_per_slot", 5)

            if not is_open_floor and not is_user_assigned and current_user["role"] != "admin":
                slot_dict["is_available"] = False
                slot_dict["restriction_reason"] = "not_assigned"
        else:
            slot_dict["is_dedicated_policy"] = False

        result.append(slot_dict)

    return result
