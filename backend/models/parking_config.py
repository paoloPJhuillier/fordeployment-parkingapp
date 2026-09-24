from pydantic import BaseModel, Field
from typing import Optional


class ParkingConfigCreate(BaseModel):
    building_id: str
    release_time: str = "06:00"
    default_start_time: str = "08:00"
    default_end_time: str = "18:00"
    # QAT-PARKING-CONFIG-010 fix: enforce sane bounds on booking window so a
    # value of 0 or 999 is rejected with a clear error instead of being silently
    # coerced.
    booking_window_days: int = Field(7, ge=1, le=30)
    no_show_release_enabled: bool = False
    no_show_release_minutes: int = Field(30, ge=5, le=240)
    waitlist_enabled: bool = False
    waitlist_notification_window_minutes: int = Field(15, ge=5, le=240)
    main_building_exclusive: bool = False


class ParkingConfigResponse(BaseModel):
    id: str
    building_id: str
    release_time: str
    default_start_time: str
    default_end_time: str
    booking_window_days: int
    no_show_release_enabled: bool = False
    no_show_release_minutes: int = 30
    waitlist_enabled: bool = False
    waitlist_notification_window_minutes: int = 15
    main_building_exclusive: bool = False


class ParkingConfigPublicResponse(BaseModel):
    """Public view returned to non-admin users.

    Includes all UX-driving flags users need to render correct UI (waitlist
    CTA, no-show warnings, main-building filtering). Admin-only operational
    tuning (notification window minutes, release-minute thresholds) is kept
    in the full ParkingConfigResponse — V-02 boundary preserved.
    """
    id: str
    building_id: str
    release_time: str
    default_start_time: str
    default_end_time: str
    booking_window_days: int
    no_show_release_enabled: bool = False
    no_show_release_minutes: int = 30
    waitlist_enabled: bool = False
    main_building_exclusive: bool = False
