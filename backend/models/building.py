from pydantic import BaseModel, Field
from typing import List, Optional
from .enums import SlotStatus


class ParkingSlotCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=16)
    floor_id: str
    status: SlotStatus = SlotStatus.AVAILABLE


class ParkingSlotResponse(BaseModel):
    id: str
    label: str
    floor_id: str
    building_id: str
    status: SlotStatus
    row: int = 0
    column: int = 0
    ownership_type: Optional[str] = None


class FloorCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=16)
    building_id: str
    slot_count: int = 10
    slot_labels: Optional[List[str]] = None
    slot_prefix: Optional[str] = None


class FloorResponse(BaseModel):
    id: str
    label: str
    building_id: str
    layout_image_url: Optional[str] = None
    slots: List[ParkingSlotResponse] = []


class BuildingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)
    address: Optional[str] = Field(None, max_length=80)
    address_line_1: Optional[str] = Field(None, max_length=30)
    address_line_2: Optional[str] = Field(None, max_length=30)
    total_floors: int = 1
    slots_per_floor: int = 10
    slot_prefix: Optional[str] = None


class BuildingUpdate(BaseModel):
    # QAT-BUILDING-MANAGEMENT-010 fix: PUT/update is intentionally MORE permissive
    # than CREATE so legacy buildings with values exceeding the new char limits
    # (introduced in Phase 6 UX improvements) can still be edited and ultimately
    # deleted without hitting Pydantic 422 errors. The CREATE path remains strict.
    name: Optional[str] = Field(None, min_length=1)
    address: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None


class BuildingResponse(BaseModel):
    id: str
    name: str
    address: str
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    total_floors: int
    created_at: str
    floors: List[FloorResponse] = []


class SlotUpdate(BaseModel):
    label: str = Field(..., min_length=1, max_length=16)


class BulkSlotsCreate(BaseModel):
    slot_labels: Optional[List[str]] = None
    slot_count: Optional[int] = None
    slot_prefix: Optional[str] = None
