import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth.security import get_current_user
from models import VehicleCreate, VehicleResponse, UserRole
from models.reservation import ReservationStatus
from datetime import datetime, timezone, date as date_cls

router = APIRouter()


@router.get("/vehicles", response_model=List[VehicleResponse])
async def get_vehicles(current_user: dict = Depends(get_current_user)):
    query = {} if current_user["role"] == UserRole.ADMIN else {"user_id": current_user["id"]}
    vehicles = await db.vehicles.find(query, {"_id": 0}).to_list(1000)
    return [VehicleResponse(**v) for v in vehicles]


@router.post("/vehicles", response_model=VehicleResponse)
async def create_vehicle(vehicle: VehicleCreate, current_user: dict = Depends(get_current_user)):
    plate = vehicle.plate_number.upper().strip()
    # Plate number uniqueness: no other vehicle should have the same plate
    existing = await db.vehicles.find_one({"plate_number": plate}, {"_id": 0, "id": 1, "user_id": 1})
    if existing:
        raise HTTPException(status_code=400, detail=f"Plate number {plate} is already registered to another vehicle.")

    vehicle_id = str(uuid.uuid4())
    vehicle_doc = {
        "id": vehicle_id,
        "user_id": current_user["id"],
        "plate_number": plate,
        "make": vehicle.make,
        "model": vehicle.model,
        "color": vehicle.color,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.vehicles.insert_one(vehicle_doc)
    return VehicleResponse(**vehicle_doc)


@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": vehicle_id}
    if current_user["role"] != UserRole.ADMIN:
        query["user_id"] = current_user["id"]

    # PPA-14 fix: refuse to delete a vehicle that has any active future bookings.
    today = date_cls.today().isoformat()
    blocking = await db.reservations.find_one(
        {
            "vehicle_id": vehicle_id,
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
            "date": {"$gte": today},
        },
        {"_id": 0, "id": 1, "date": 1},
    )
    if blocking:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot delete vehicle — it has an active reservation on "
                f"{blocking.get('date')}. Cancel the reservation first."
            ),
        )

    result = await db.vehicles.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"message": "Vehicle deleted"}
