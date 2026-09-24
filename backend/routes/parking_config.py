import uuid
from fastapi import APIRouter, Depends

from database import db
from auth.security import get_current_user, require_admin
from models import ParkingConfigCreate, ParkingConfigResponse, ParkingConfigPublicResponse

router = APIRouter()


@router.get("/parking-config/{building_id}")
async def get_parking_config(building_id: str, current_user: dict = Depends(get_current_user)):
    """V-02 FIX: return the full config to admins; return a trimmed public view to
    everyone else (no_show_release_*, waitlist_*, main_building_exclusive are hidden)."""
    is_admin = current_user.get("role") == "admin"
    config = await db.parking_configs.find_one({"building_id": building_id}, {"_id": 0})
    if not config:
        if is_admin:
            return ParkingConfigResponse(
                id="default",
                building_id=building_id,
                release_time="06:00",
                default_start_time="08:00",
                default_end_time="18:00",
                booking_window_days=7,
                no_show_release_enabled=False,
                no_show_release_minutes=30,
            )
        return ParkingConfigPublicResponse(
            id="default",
            building_id=building_id,
            release_time="06:00",
            default_start_time="08:00",
            default_end_time="18:00",
            booking_window_days=7,
        )

    base = {
        "id": config.get("id", "default"),
        "building_id": config.get("building_id", building_id),
        "release_time": config.get("release_time", "06:00"),
        "default_start_time": config.get("default_start_time", "08:00"),
        "default_end_time": config.get("default_end_time", "18:00"),
        "booking_window_days": config.get("booking_window_days", 7),
    }
    if not is_admin:
        # V-02 boundary preserved: expose UX-driving flags users need to
        # render correct UI, but keep admin-only tuning (notification window
        # minutes) hidden.
        return ParkingConfigPublicResponse(**{
            **base,
            "no_show_release_enabled": config.get("no_show_release_enabled", False),
            "no_show_release_minutes": config.get("no_show_release_minutes", 30),
            "waitlist_enabled": config.get("waitlist_enabled", False),
            "main_building_exclusive": config.get("main_building_exclusive", False),
        })

    return ParkingConfigResponse(**{
        **base,
        "no_show_release_enabled": config.get("no_show_release_enabled", False),
        "no_show_release_minutes": config.get("no_show_release_minutes", 30),
        "waitlist_enabled": config.get("waitlist_enabled", False),
        "waitlist_notification_window_minutes": config.get("waitlist_notification_window_minutes", 15),
        "main_building_exclusive": config.get("main_building_exclusive", False),
    })


@router.post("/parking-config", response_model=ParkingConfigResponse)
async def save_parking_config(config: ParkingConfigCreate, current_user: dict = Depends(require_admin)):
    existing = await db.parking_configs.find_one({"building_id": config.building_id})

    config_doc = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "building_id": config.building_id,
        "release_time": config.release_time,
        "default_start_time": config.default_start_time,
        "default_end_time": config.default_end_time,
        "booking_window_days": config.booking_window_days,
        "no_show_release_enabled": config.no_show_release_enabled,
        "no_show_release_minutes": config.no_show_release_minutes,
        "waitlist_enabled": config.waitlist_enabled,
        "waitlist_notification_window_minutes": config.waitlist_notification_window_minutes,
        "main_building_exclusive": config.main_building_exclusive,
    }

    if existing:
        await db.parking_configs.update_one({"building_id": config.building_id}, {"$set": config_doc})
    else:
        await db.parking_configs.insert_one(config_doc)

    return ParkingConfigResponse(**config_doc)
