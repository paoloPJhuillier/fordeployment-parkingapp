import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth.security import get_current_user, require_attendant
from models import (
    ReservationCreate, ReservationResponse, CreateReservationResult,
    ConfirmReservationRequest, ParkingSlotResponse,
    UserRole, ReservationStatus, SlotStatus,
)
from services.qr import generate_qr_token, generate_qr_code_image
from services.reservations import batch_enrich_reservations
import features as feature_flags

router = APIRouter()


@router.get("/reservations", response_model=List[ReservationResponse])
async def get_reservations(
    building_id: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {}

    if current_user["role"] == UserRole.USER:
        query["user_id"] = current_user["id"]
    elif current_user["role"] == UserRole.ATTENDANT:
        if current_user.get("assigned_buildings"):
            query["building_id"] = {"$in": current_user["assigned_buildings"]}

    if building_id:
        query["building_id"] = building_id
    if date:
        query["date"] = date
    if status:
        query["status"] = status

    reservations = await db.reservations.find(query, {"_id": 0}).to_list(1000)
    return await batch_enrich_reservations(reservations)


@router.post("/reservations")
async def create_reservation(reservation: ReservationCreate, current_user: dict = Depends(get_current_user)):
    if current_user.get("is_blocked"):
        raise HTTPException(status_code=403, detail="Your account has been blocked from making reservations. Please contact your administrator.")

    if not reservation.dates or len(reservation.dates) == 0:
        raise HTTPException(status_code=400, detail="At least one date is required")
    if len(reservation.dates) > 7:
        raise HTTPException(status_code=400, detail="Maximum 7 dates allowed per booking")

    slot = await db.parking_slots.find_one({"id": reservation.slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")

    booking_building_id = slot["building_id"]
    user_main_building = current_user.get("main_building")
    user_tags = current_user.get("tags", [])
    is_vip = "vip" in user_tags or "group_head" in user_tags
    is_external_booking = user_main_building and booking_building_id != user_main_building

    # Main Building Exclusivity check
    if current_user["role"] != UserRole.ADMIN:
        building_config = await db.parking_configs.find_one({"building_id": booking_building_id}, {"_id": 0})
        if building_config and building_config.get("main_building_exclusive"):
            if user_main_building != booking_building_id:
                raise HTTPException(
                    status_code=403,
                    detail="This building is restricted to employees whose main building is set to this location.",
                )

    if current_user["role"] != UserRole.ADMIN:
        user_zones = await db.zones.find({"user_ids": current_user["id"]}, {"_id": 0}).to_list(100)
        zone_building_ids = set()
        for z in user_zones:
            for bid in z.get("building_ids", []):
                zone_building_ids.add(bid)

        if user_main_building:
            zone_building_ids.add(user_main_building)

        if zone_building_ids and booking_building_id not in zone_building_ids:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this building's zone. Please contact your administrator.",
            )

        if is_external_booking and not is_vip:
            if len(reservation.dates) > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Booking outside your main building is limited to a single day only.",
                )
            if not reservation.reason or not reservation.reason.strip():
                raise HTTPException(
                    status_code=400,
                    detail="A reason is required when booking outside your main building.",
                )

    vehicle = await db.vehicles.find_one({"id": reservation.vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle["user_id"] != current_user["id"] and current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Vehicle does not belong to you")

    # --- Dedicated Slot Policy Check ---
    building_policy = await db.building_policies.find_one(
        {"building_id": booking_building_id, "enabled": True}, {"_id": 0}
    )
    if building_policy and building_policy.get("policy_type") == "dedicated_slot":
        floor_id = slot["floor_id"]
        is_open_floor = floor_id in building_policy.get("open_floor_ids", [])

        if building_policy.get("requires_sticker"):
            # Vehicle-level check: the specific vehicle must have an active registration in this building
            vehicle_reg = await db.slot_registrations.find_one({
                "vehicle_plate": vehicle["plate_number"],
                "building_id": booking_building_id,
                "status": "active",
            }, {"_id": 0})
            if not vehicle_reg and current_user["role"] != UserRole.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=f"Vehicle {vehicle['plate_number']} does not have a parking sticker/registration for this building. Only vehicles with an active sticker can park here.",
                )

        if not is_open_floor:
            # Strict slot assignment: vehicle must be registered to this specific slot
            vehicle_slot_reg = await db.slot_registrations.find_one({
                "slot_id": reservation.slot_id,
                "user_id": current_user["id"],
                "vehicle_plate": vehicle["plate_number"],
                "status": "active",
            }, {"_id": 0})
            if not vehicle_slot_reg and current_user["role"] != UserRole.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=f"Vehicle {vehicle['plate_number']} is not registered to this parking slot. Under the dedicated slot policy, only the vehicle assigned to this slot can book it.",
                )

    floor = await db.floors.find_one({"id": slot["floor_id"]}, {"_id": 0})
    building = await db.buildings.find_one({"id": slot["building_id"]}, {"_id": 0})

    def time_to_minutes(t):
        h, m = map(int, t.split(':'))
        return h * 60 + m

    new_start = time_to_minutes(reservation.start_time)
    new_end = time_to_minutes(reservation.end_time)

    if new_end <= new_start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    created_reservations = []

    for booking_date in reservation.dates:
        try:
            datetime.strptime(booking_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {booking_date}")

        existing_slot_reservations = await db.reservations.find({
            "slot_id": reservation.slot_id,
            "date": booking_date,
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
        }, {"_id": 0}).to_list(100)

        slot_has_overlap = False
        for existing_res in existing_slot_reservations:
            existing_start = time_to_minutes(existing_res["start_time"])
            existing_end = time_to_minutes(existing_res["end_time"])
            if new_start < existing_end and new_end > existing_start:
                slot_has_overlap = True
                break

        if slot_has_overlap:
            if len(reservation.dates) > 1:
                continue
            else:
                raise HTTPException(status_code=400, detail=f"Slot already reserved for the selected time on {booking_date}")

        user_bookings = await db.reservations.find({
            "user_id": current_user["id"],
            "date": booking_date,
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
        }, {"_id": 0}).to_list(100)

        has_overlap = False
        for booking in user_bookings:
            existing_start = time_to_minutes(booking["start_time"])
            existing_end = time_to_minutes(booking["end_time"])
            if new_start < existing_end and new_end > existing_start:
                has_overlap = True
                break

        if has_overlap:
            if len(reservation.dates) > 1:
                continue
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"You already have a booking that overlaps with this time on {booking_date}.",
                )

        reservation_id = str(uuid.uuid4())
        qr_token = generate_qr_token()

        res_doc = {
            "id": reservation_id,
            "user_id": current_user["id"],
            "slot_id": reservation.slot_id,
            "vehicle_id": reservation.vehicle_id,
            "building_id": slot["building_id"],
            "floor_id": slot["floor_id"],
            "date": booking_date,
            "start_time": reservation.start_time,
            "end_time": reservation.end_time,
            "status": ReservationStatus.PENDING,
            "booking_type": "daily",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "photo_url": None,
            "qr_token": qr_token,
            "no_show_reported": False,
            "reason": reservation.reason,
        }

        await db.reservations.insert_one(res_doc)

        created_reservations.append(ReservationResponse(
            id=reservation_id,
            user_id=current_user["id"],
            slot_id=reservation.slot_id,
            vehicle_id=reservation.vehicle_id,
            building_id=slot["building_id"],
            floor_id=slot["floor_id"],
            date=booking_date,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            status=ReservationStatus.PENDING,
            booking_type="daily",
            created_at=res_doc["created_at"],
            slot_label=slot["label"],
            floor_label=floor["label"] if floor else None,
            building_name=building["name"] if building else None,
            vehicle_plate=vehicle["plate_number"],
            user_name=f"{current_user['first_name']} {current_user['last_name']}",
            qr_token=qr_token,
            no_show_reported=False,
            reason=reservation.reason,
        ))

    if not created_reservations:
        raise HTTPException(status_code=400, detail="Could not create any reservations. All dates may be unavailable.")

    if len(created_reservations) == 1:
        return created_reservations[0]

    return CreateReservationResult(
        message=f"Created {len(created_reservations)} reservations",
        reservations=created_reservations,
        count=len(created_reservations),
    )


@router.get("/reservations/{reservation_id}/qr")
async def get_reservation_qr(reservation_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": reservation_id}
    if current_user["role"] == UserRole.USER:
        query["user_id"] = current_user["id"]

    reservation = await db.reservations.find_one(query, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    qr_token = reservation.get("qr_token")
    if not qr_token:
        qr_token = generate_qr_token()
        await db.reservations.update_one({"id": reservation_id}, {"$set": {"qr_token": qr_token}})

    qr_code_image = generate_qr_code_image(qr_token)
    return {"qr_code": qr_code_image, "qr_token": qr_token, "reservation_id": reservation_id}


@router.put("/reservations/{reservation_id}/cancel")
async def cancel_reservation(reservation_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": reservation_id}
    if current_user["role"] == UserRole.USER:
        query["user_id"] = current_user["id"]

    reservation = await db.reservations.find_one(query, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # PPA-62 fix: do not allow cancelling a reservation whose date is already in
    # the past. (Today is fine — user might have ended early; only strictly
    # past dates are blocked.)
    from datetime import date as date_cls
    res_date = reservation.get("date") or ""
    try:
        if res_date and res_date < date_cls.today().isoformat():
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel a past reservation",
            )
    except HTTPException:
        raise
    except Exception:
        # Malformed date — let the original code path handle it
        pass

    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"status": ReservationStatus.CANCELLED}},
    )

    # Trigger waitlist notification for the building/date
    from routes.waitlist import notify_next_waitlisted_user
    try:
        await notify_next_waitlisted_user(reservation["building_id"], reservation["date"])
    except Exception:
        pass  # Don't fail cancellation if waitlist notification fails

    return {"message": "Reservation cancelled"}


@router.put("/reservations/{reservation_id}/confirm")
async def confirm_reservation(
    reservation_id: str,
    photo: Optional[str] = None,
    current_user: dict = Depends(require_attendant),
):
    update_data = {"status": ReservationStatus.CONFIRMED}
    if photo:
        update_data["photo_url"] = photo

    result = await db.reservations.find_one_and_update(
        {"id": reservation_id},
        {"$set": update_data},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return {"message": "Reservation confirmed"}


@router.post("/reservations/{reservation_id}/confirm-with-photo")
async def confirm_reservation_with_photo(
    reservation_id: str,
    request: ConfirmReservationRequest,
    current_user: dict = Depends(require_attendant),
):
    update_data = {"status": ReservationStatus.CONFIRMED}
    if request.photo:
        update_data["photo_url"] = request.photo

    result = await db.reservations.find_one_and_update(
        {"id": reservation_id},
        {"$set": update_data},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return {"message": "Reservation confirmed"}


@router.post("/reservations/{reservation_id}/checkin")
async def self_checkin(
    reservation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Parker self-check-in. Only allowed when attendant mode is disabled.

    Window: from reservation ``start_time`` until ``start_time +
    SELF_CHECKIN_WINDOW_MINUTES``. Outside the window the request is
    rejected and the existing auto-no-show loop will mark it shortly.

    Idempotent: a second call on an already-confirmed reservation returns
    200 with ``already_checked_in: true`` rather than failing.
    """
    if feature_flags.attendant_mode_enabled():
        raise HTTPException(
            status_code=403,
            detail="Self check-in is disabled. An attendant will confirm your arrival.",
        )

    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Authorisation: only the parker (or an admin) may check themselves in.
    if reservation["user_id"] != current_user["id"] and current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You can only check in to your own reservation")

    # Idempotency — already confirmed (by self or by an admin override).
    if reservation["status"] == ReservationStatus.CONFIRMED:
        return {
            "message": "Already checked in",
            "already_checked_in": True,
            "checked_in_at": reservation.get("checked_in_at"),
        }

    if reservation["status"] != ReservationStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot check in to a reservation with status '{reservation['status']}'",
        )

    # Validate the time window: now must be between start_time and
    # start_time + window. We compare in UTC; reservation start/end times
    # are stored as local-civil strings ("YYYY-MM-DD" + "HH:MM") that the
    # rest of the codebase already treats as UTC for scheduling decisions
    # (see auto_mark_no_shows). Same convention here keeps behaviour
    # consistent.
    now = datetime.now(timezone.utc)
    try:
        start_dt = datetime.fromisoformat(f"{reservation['date']}T{reservation['start_time']}:00").replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Reservation has invalid start time")

    window = timedelta(minutes=feature_flags.self_checkin_window_minutes())
    if now < start_dt:
        wait_mins = int((start_dt - now).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=400,
            detail=f"Too early to check in. Your reservation starts in ~{wait_mins} minutes.",
        )
    if now > start_dt + window:
        raise HTTPException(
            status_code=410,  # 410 Gone — window has elapsed
            detail=f"Check-in window has expired ({feature_flags.self_checkin_window_minutes()} min after start). The slot will be released shortly.",
        )

    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {
            "status": ReservationStatus.CONFIRMED,
            "checked_in_at": now.isoformat(),
            "checked_in_by_self": True,
        }},
    )

    return {
        "message": "Checked in successfully",
        "checked_in_at": now.isoformat(),
    }


@router.get("/scan/{qr_token}")
async def scan_qr_lookup(qr_token: str, current_user: dict = Depends(require_attendant)):
    reservation = await db.reservations.find_one({"qr_token": qr_token}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    slot = await db.parking_slots.find_one({"id": reservation["slot_id"]}, {"_id": 0})
    floor = await db.floors.find_one({"id": reservation.get("floor_id")}, {"_id": 0})
    building = await db.buildings.find_one({"id": reservation["building_id"]}, {"_id": 0})
    vehicle = await db.vehicles.find_one({"id": reservation["vehicle_id"]}, {"_id": 0})
    user = await db.users.find_one({"id": reservation["user_id"]}, {"_id": 0, "password": 0})

    return {
        "reservation_id": reservation["id"],
        "date": reservation["date"],
        "start_time": reservation["start_time"],
        "end_time": reservation["end_time"],
        "status": reservation["status"],
        "slot_label": slot["label"] if slot else None,
        "floor_label": floor["label"] if floor else None,
        "building_name": building["name"] if building else None,
        "vehicle_plate": vehicle["plate_number"] if vehicle else None,
        "user_name": f"{user['first_name']} {user['last_name']}" if user else None,
        "no_show_reported": reservation.get("no_show_reported", False),
    }


@router.get("/reservations/stats")
async def get_user_booking_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    reservations = await db.reservations.find({"user_id": user_id}, {"_id": 0, "status": 1, "no_show_reported": 1}).to_list(10000)

    stats = {
        "total": len(reservations),
        "pending": 0,
        "confirmed": 0,
        "cancelled": 0,
        "completed": 0,
        "no_show": 0,
    }
    for r in reservations:
        s = r.get("status", "pending")
        if s in stats:
            stats[s] += 1

    return stats
