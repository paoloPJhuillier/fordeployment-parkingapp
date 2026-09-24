from pydantic import BaseModel
from typing import List, Optional
from .enums import ReservationStatus


class ReservationCreate(BaseModel):
    slot_id: str
    vehicle_id: str
    dates: List[str]
    start_time: str = "08:00"
    end_time: str = "18:00"
    reason: Optional[str] = None
    booking_type: Optional[str] = "daily"


class ReservationResponse(BaseModel):
    id: str
    user_id: str
    slot_id: str
    vehicle_id: Optional[str] = None
    building_id: str
    floor_id: str
    date: str
    start_time: str
    end_time: str
    status: ReservationStatus
    booking_type: str = "daily"
    created_at: str
    slot_label: Optional[str] = None
    floor_label: Optional[str] = None
    building_name: Optional[str] = None
    vehicle_plate: Optional[str] = None
    user_name: Optional[str] = None
    photo_url: Optional[str] = None
    qr_token: Optional[str] = None
    no_show_reported: bool = False
    reason: Optional[str] = None


class CreateReservationResult(BaseModel):
    message: str
    reservations: List[ReservationResponse]
    count: int


class ConfirmReservationRequest(BaseModel):
    photo: Optional[str] = None
