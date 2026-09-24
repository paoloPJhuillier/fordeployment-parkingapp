import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth.security import get_current_user, require_admin
from models import (
    BuildingPolicyCreate, BuildingPolicyResponse, BuildingPolicyUpdate,
    SlotRegistrationCreate, SlotRegistrationResponse, SlotRegistrationUpdate,
    BulkSlotRegistrationCreate,
)

router = APIRouter()


# --- Building Policy CRUD ---

@router.get("/building-policies", response_model=List[BuildingPolicyResponse])
async def get_building_policies(current_user: dict = Depends(get_current_user)):
    policies = await db.building_policies.find({}, {"_id": 0}).to_list(100)
    return policies


@router.get("/building-policies/{building_id}")
async def get_building_policy(building_id: str, current_user: dict = Depends(get_current_user)):
    policy = await db.building_policies.find_one({"building_id": building_id}, {"_id": 0})
    if not policy:
        return {"building_id": building_id, "enabled": False, "policy_type": "dedicated_slot"}
    return policy


@router.post("/building-policies", response_model=BuildingPolicyResponse)
async def create_building_policy(policy: BuildingPolicyCreate, current_user: dict = Depends(require_admin)):
    building = await db.buildings.find_one({"id": policy.building_id}, {"_id": 0})
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    existing = await db.building_policies.find_one({"building_id": policy.building_id})
    if existing:
        raise HTTPException(status_code=400, detail="Policy already exists for this building. Use PUT to update.")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "building_id": policy.building_id,
        "policy_type": policy.policy_type,
        "enabled": policy.enabled,
        "max_users_per_slot": policy.max_users_per_slot,
        "open_floor_ids": policy.open_floor_ids,
        "requires_sticker": policy.requires_sticker,
        "created_at": now,
        "updated_at": now,
    }
    await db.building_policies.insert_one(doc)
    doc.pop("_id", None)
    return BuildingPolicyResponse(**doc)


@router.put("/building-policies/{building_id}", response_model=BuildingPolicyResponse)
async def update_building_policy(building_id: str, update: BuildingPolicyUpdate, current_user: dict = Depends(require_admin)):
    policy = await db.building_policies.find_one({"building_id": building_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="No policy found for this building")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.building_policies.update_one({"building_id": building_id}, {"$set": update_data})
    updated = await db.building_policies.find_one({"building_id": building_id}, {"_id": 0})
    return BuildingPolicyResponse(**updated)


@router.delete("/building-policies/{building_id}")
async def delete_building_policy(building_id: str, current_user: dict = Depends(require_admin)):
    result = await db.building_policies.delete_one({"building_id": building_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"message": "Building policy deleted"}


# --- Slot Registration CRUD ---

@router.get("/slot-registrations")
async def get_slot_registrations(
    building_id: Optional[str] = None,
    slot_id: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {"status": "active"}
    if building_id:
        query["building_id"] = building_id
    if slot_id:
        query["slot_id"] = slot_id
    if user_id:
        query["user_id"] = user_id

    # V-02 FIX: non-admins must only see their OWN active slot registrations.
    # Attendants are scoped to the buildings they're assigned to (operational visibility).
    role = current_user.get("role")
    if role == "user":
        query["user_id"] = current_user["id"]
    elif role == "attendant":
        assigned = current_user.get("assigned_buildings") or []
        if not assigned:
            return []
        # Don't override a more-specific building_id filter the caller asked for,
        # as long as it's within the attendant's assigned set.
        if building_id and building_id not in assigned:
            return []
        if not building_id:
            query["building_id"] = {"$in": assigned}

    regs = await db.slot_registrations.find(query, {"_id": 0}).to_list(1000)

    # Batch enrich with user names and slot labels
    user_ids = list({r["user_id"] for r in regs})
    slot_ids = list({r["slot_id"] for r in regs})

    users_map = {}
    if user_ids:
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}).to_list(1000)
        users_map = {u["id"]: f"{u['first_name']} {u['last_name']}" for u in users}

    slots_map = {}
    if slot_ids:
        slots = await db.parking_slots.find({"id": {"$in": slot_ids}}, {"_id": 0, "id": 1, "label": 1}).to_list(1000)
        slots_map = {s["id"]: s["label"] for s in slots}

    for r in regs:
        r["user_name"] = users_map.get(r["user_id"])
        r["slot_label"] = slots_map.get(r["slot_id"])

    return regs


@router.get("/slot-registrations/user/{user_id}")
async def get_user_slot_registrations(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get all active slot registrations for a specific user.

    V-02 FIX: a non-admin caller may only request their own user_id.
    """
    if current_user.get("role") != "admin" and current_user.get("id") != user_id:
        raise HTTPException(status_code=403, detail="Cannot view another user's slot registrations")

    regs = await db.slot_registrations.find(
        {"user_id": user_id, "status": "active"}, {"_id": 0}
    ).to_list(100)

    slot_ids = [r["slot_id"] for r in regs]
    if slot_ids:
        slots = await db.parking_slots.find({"id": {"$in": slot_ids}}, {"_id": 0, "id": 1, "label": 1}).to_list(100)
        slots_map = {s["id"]: s["label"] for s in slots}
        for r in regs:
            r["slot_label"] = slots_map.get(r["slot_id"])

    return regs


@router.post("/slot-registrations", response_model=SlotRegistrationResponse)
async def create_slot_registration(reg: SlotRegistrationCreate, current_user: dict = Depends(require_admin)):
    slot = await db.parking_slots.find_one({"id": reg.slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    user = await db.users.find_one({"id": reg.user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check policy exists and get max_users_per_slot
    policy = await db.building_policies.find_one({"building_id": slot["building_id"], "enabled": True}, {"_id": 0})
    max_per_slot = policy.get("max_users_per_slot", 5) if policy else 5

    # Check slot registration count
    active_count = await db.slot_registrations.count_documents({"slot_id": reg.slot_id, "status": "active"})
    if active_count >= max_per_slot:
        raise HTTPException(status_code=400, detail=f"This slot already has {active_count} registered users (max {max_per_slot})")

    # Check user not already registered to this slot
    existing = await db.slot_registrations.find_one({
        "slot_id": reg.slot_id, "user_id": reg.user_id, "status": "active"
    })
    if existing:
        raise HTTPException(status_code=400, detail="User is already registered to this slot")

    # BUG FIX TCID-BUILDING-POLICIES-009: User can only be registered to one slot per building
    existing_in_building = await db.slot_registrations.find_one({
        "building_id": slot["building_id"], "user_id": reg.user_id, "status": "active"
    })
    if existing_in_building:
        existing_slot = await db.parking_slots.find_one({"id": existing_in_building["slot_id"]}, {"_id": 0, "label": 1})
        slot_label = existing_slot.get("label", existing_in_building["slot_id"]) if existing_slot else existing_in_building["slot_id"]
        raise HTTPException(status_code=400, detail=f"User is already registered to slot {slot_label} in this building. A user can only be assigned to one slot per building.")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "slot_id": reg.slot_id,
        "building_id": slot["building_id"],
        "floor_id": slot["floor_id"],
        "user_id": reg.user_id,
        "vehicle_plate": reg.vehicle_plate,
        "sticker_number": reg.sticker_number,
        "status": "active",
        "registered_at": now,
    }
    await db.slot_registrations.insert_one(doc)
    doc.pop("_id", None)
    doc["user_name"] = f"{user['first_name']} {user['last_name']}"
    doc["slot_label"] = slot.get("label")
    return SlotRegistrationResponse(**doc)


@router.post("/slot-registrations/bulk")
async def bulk_create_slot_registrations(bulk: BulkSlotRegistrationCreate, current_user: dict = Depends(require_admin)):
    created = 0
    errors = []

    for reg in bulk.registrations:
        try:
            slot = await db.parking_slots.find_one({"id": reg.slot_id}, {"_id": 0})
            if not slot:
                errors.append(f"Slot {reg.slot_id} not found")
                continue

            user = await db.users.find_one({"id": reg.user_id}, {"_id": 0})
            if not user:
                errors.append(f"User {reg.user_id} not found")
                continue

            existing = await db.slot_registrations.find_one({
                "slot_id": reg.slot_id, "user_id": reg.user_id, "status": "active"
            })
            if existing:
                errors.append(f"User {user['first_name']} already registered to slot")
                continue

            policy = await db.building_policies.find_one({"building_id": slot["building_id"], "enabled": True}, {"_id": 0})
            max_per_slot = policy.get("max_users_per_slot", 5) if policy else 5
            active_count = await db.slot_registrations.count_documents({"slot_id": reg.slot_id, "status": "active"})
            if active_count >= max_per_slot:
                errors.append(f"Slot {slot.get('label', reg.slot_id)} is full ({active_count}/{max_per_slot})")
                continue

            now = datetime.now(timezone.utc).isoformat()
            doc = {
                "id": str(uuid.uuid4()),
                "slot_id": reg.slot_id,
                "building_id": slot["building_id"],
                "floor_id": slot["floor_id"],
                "user_id": reg.user_id,
                "vehicle_plate": reg.vehicle_plate,
                "sticker_number": reg.sticker_number,
                "status": "active",
                "registered_at": now,
            }
            await db.slot_registrations.insert_one(doc)
            created += 1
        except Exception as e:
            errors.append(str(e))

    return {"created": created, "errors": errors}


@router.put("/slot-registrations/{reg_id}", response_model=SlotRegistrationResponse)
async def update_slot_registration(reg_id: str, update: SlotRegistrationUpdate, current_user: dict = Depends(require_admin)):
    reg = await db.slot_registrations.find_one({"id": reg_id}, {"_id": 0})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.slot_registrations.update_one({"id": reg_id}, {"$set": update_data})
    updated = await db.slot_registrations.find_one({"id": reg_id}, {"_id": 0})
    return SlotRegistrationResponse(**updated)


@router.delete("/slot-registrations/{reg_id}")
async def delete_slot_registration(reg_id: str, current_user: dict = Depends(require_admin)):
    result = await db.slot_registrations.update_one(
        {"id": reg_id}, {"$set": {"status": "revoked"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Registration not found")
    return {"message": "Slot registration revoked"}


# --- Slot Ownership ---

@router.put("/slots/{slot_id}/ownership")
async def update_slot_ownership(slot_id: str, ownership_type: str, current_user: dict = Depends(require_admin)):
    """Update the ownership_type of a parking slot (e.g., company_owned, rented_clrb)."""
    slot = await db.parking_slots.find_one({"id": slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    await db.parking_slots.update_one({"id": slot_id}, {"$set": {"ownership_type": ownership_type}})
    return {"message": f"Slot ownership set to '{ownership_type}'"}
