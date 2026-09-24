import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth.security import get_current_user, require_admin
from models import ZoneCreate, ZoneResponse, ZoneUpdate

router = APIRouter()


@router.get("/zones", response_model=List[ZoneResponse])
async def get_zones(current_user: dict = Depends(require_admin)):
    zones = await db.zones.find({}, {"_id": 0}).to_list(100)
    return [ZoneResponse(
        id=z["id"],
        name=z["name"],
        building_ids=z.get("building_ids", [z["building_id"]] if z.get("building_id") else []),
        user_ids=z.get("user_ids", z.get("assigned_users", [])),
        created_at=z["created_at"],
    ) for z in zones]


@router.post("/zones", response_model=ZoneResponse)
async def create_zone(zone: ZoneCreate, current_user: dict = Depends(require_admin)):
    zone_id = str(uuid.uuid4())
    zone_doc = {
        "id": zone_id,
        "name": zone.name,
        "building_ids": zone.building_ids,
        "user_ids": zone.user_ids,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.zones.insert_one(zone_doc)
    return ZoneResponse(**zone_doc)


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(zone_id: str, update: ZoneUpdate, current_user: dict = Depends(require_admin)):
    zone = await db.zones.find_one({"id": zone_id}, {"_id": 0})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    update_data = {}
    if update.name is not None:
        update_data["name"] = update.name
    if update.building_ids is not None:
        update_data["building_ids"] = update.building_ids
    if update.user_ids is not None:
        update_data["user_ids"] = update.user_ids

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.zones.update_one({"id": zone_id}, {"$set": update_data})
    updated = await db.zones.find_one({"id": zone_id}, {"_id": 0})
    return ZoneResponse(
        id=updated["id"],
        name=updated["name"],
        building_ids=updated.get("building_ids", []),
        user_ids=updated.get("user_ids", []),
        created_at=updated["created_at"],
    )


@router.delete("/zones/{zone_id}")
async def delete_zone(zone_id: str, current_user: dict = Depends(require_admin)):
    zone = await db.zones.find_one({"id": zone_id}, {"_id": 0})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    await db.zones.delete_one({"id": zone_id})
    return {"message": "Zone deleted"}


@router.get("/zones/user-buildings")
async def get_user_building_assignments(current_user: dict = Depends(get_current_user)):
    zones = await db.zones.find(
        {"user_ids": current_user["id"]},
        {"_id": 0},
    ).to_list(100)

    building_ids = set()
    for z in zones:
        for bid in z.get("building_ids", []):
            building_ids.add(bid)

    if current_user.get("main_building"):
        building_ids.add(current_user["main_building"])

    zone_responses = [ZoneResponse(
        id=z["id"],
        name=z["name"],
        building_ids=z.get("building_ids", []),
        user_ids=z.get("user_ids", []),
        created_at=z["created_at"],
    ) for z in zones]

    return {"building_ids": list(building_ids), "zones": zone_responses}
