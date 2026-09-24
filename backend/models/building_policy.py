from pydantic import BaseModel
from typing import List, Optional


class BuildingPolicyCreate(BaseModel):
    building_id: str
    policy_type: str = "dedicated_slot"
    enabled: bool = True
    max_users_per_slot: int = 5
    open_floor_ids: List[str] = []
    requires_sticker: bool = True


class BuildingPolicyResponse(BaseModel):
    id: str
    building_id: str
    policy_type: str = "dedicated_slot"
    enabled: bool = True
    max_users_per_slot: int = 5
    open_floor_ids: List[str] = []
    requires_sticker: bool = True
    created_at: str
    updated_at: Optional[str] = None


class BuildingPolicyUpdate(BaseModel):
    enabled: Optional[bool] = None
    max_users_per_slot: Optional[int] = None
    open_floor_ids: Optional[List[str]] = None
    requires_sticker: Optional[bool] = None


class SlotRegistrationCreate(BaseModel):
    slot_id: str
    user_id: str
    vehicle_plate: str
    sticker_number: Optional[str] = None


class SlotRegistrationResponse(BaseModel):
    id: str
    slot_id: str
    building_id: str
    floor_id: str
    user_id: str
    vehicle_plate: str
    sticker_number: Optional[str] = None
    status: str = "active"
    registered_at: str
    user_name: Optional[str] = None
    slot_label: Optional[str] = None


class SlotRegistrationUpdate(BaseModel):
    vehicle_plate: Optional[str] = None
    sticker_number: Optional[str] = None
    status: Optional[str] = None


class BulkSlotRegistrationCreate(BaseModel):
    registrations: List[SlotRegistrationCreate]
