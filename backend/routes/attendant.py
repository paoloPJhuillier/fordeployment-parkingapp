from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth.security import require_attendant
from models import UserRole, ReservationStatus
from services.reservations import batch_enrich_reservations
from services.notifications import create_notification

router = APIRouter()


@router.get("/attendant/daily-reservations")
async def get_attendant_daily_reservations(
    date: Optional[str] = None,
    building_id: Optional[str] = None,
    current_user: dict = Depends(require_attendant),
):
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    query = {"date": date}
    assigned = current_user.get("assigned_buildings", [])
    if current_user["role"] == UserRole.ATTENDANT and assigned:
        if building_id and building_id in assigned:
            query["building_id"] = building_id
        else:
            query["building_id"] = {"$in": assigned}
    elif building_id:
        query["building_id"] = building_id

    reservations = await db.reservations.find(query, {"_id": 0}).to_list(1000)
    return await batch_enrich_reservations(reservations)


@router.get("/attendant/buildings")
async def get_attendant_buildings(current_user: dict = Depends(require_attendant)):
    assigned = current_user.get("assigned_buildings", [])
    if assigned:
        buildings = await db.buildings.find({"id": {"$in": assigned}}, {"_id": 0}).to_list(100)
    else:
        buildings = await db.buildings.find({}, {"_id": 0}).to_list(100)
    return [{"id": b["id"], "name": b["name"]} for b in buildings]


@router.post("/attendant/reservations/{reservation_id}/report-no-show")
async def report_no_show(reservation_id: str, current_user: dict = Depends(require_attendant)):
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation["status"] not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
        raise HTTPException(status_code=400, detail=f"Cannot report no-show for a {reservation['status']} reservation")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if reservation.get("date", "") > today_str:
        raise HTTPException(status_code=400, detail="Cannot report no-show for a future reservation")

    no_show_at = datetime.now(timezone.utc).isoformat()
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"no_show_reported": True, "status": ReservationStatus.NO_SHOW, "no_show_at": no_show_at}},
    )

    await db.users.update_one({"id": reservation["user_id"]}, {"$inc": {"no_show_count": 1}})

    building = await db.buildings.find_one({"id": reservation.get("building_id")}, {"_id": 0, "name": 1})
    building_name = building["name"] if building else "Unknown"
    await create_notification(
        user_id=reservation["user_id"],
        title="No-Show Reported",
        message=f"Your reservation at {building_name} on {reservation['date']} ({reservation['start_time']} - {reservation['end_time']}) was marked as a no-show by the parking attendant.",
        notification_type="no_show",
    )

    return {"message": "No-show reported", "reservation_id": reservation_id}
