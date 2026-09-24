import uuid
import jwt
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from database import db
from config import limiter, JWT_SECRET, JWT_ALGORITHM, COOKIE_NAME
from auth.security import (
    hash_password, verify_password, create_access_token,
    generate_device_fingerprint, set_auth_cookie, clear_auth_cookie,
    get_current_user,
)
from models import (
    UserLogin, UserResponse, AuthMeResponse,
    TokenResponse, ChangePasswordRequest,
)

router = APIRouter()


def normalize_role(role_value: str) -> str:
    """Normalize legacy role values to valid enum values."""
    if not role_value:
        return "user"
    role_lower = role_value.lower().strip()
    if role_lower in ("admin", "user", "attendant"):
        return role_lower
    if "admin" in role_lower:
        return "admin"
    if "attendant" in role_lower:
        return "attendant"
    return "user"


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.get("is_blocked", False):
        raise HTTPException(status_code=403, detail="Your account has been blocked. Please contact your administrator.")

    fingerprint = generate_device_fingerprint(request)
    session_id = str(uuid.uuid4())
    await db.sessions.insert_one({
        "id": session_id,
        "user_id": user["id"],
        "fingerprint": fingerprint,
        "user_agent": request.headers.get("user-agent", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "revoked": False,
    })

    normalized_role = normalize_role(user.get("role", "user"))
    token = create_access_token({"sub": user["id"], "role": normalized_role, "fp": fingerprint, "sid": session_id})
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        company=user.get("company"),
        role=normalized_role,
        assigned_buildings=user.get("assigned_buildings", []),
        main_building=user.get("main_building"),
        tags=user.get("tags", []),
        is_blocked=user.get("is_blocked", False),
        must_change_password=user.get("must_change_password", False),
        default_start_time=user.get("default_start_time"),
        default_end_time=user.get("default_end_time"),
        parking_sticker_number=user.get("parking_sticker_number"),
        job_family=user.get("job_family"),
        created_at=user.get("created_at", "2026-01-01T00:00:00+00:00"),
    )

    response = JSONResponse(content=TokenResponse(access_token=token, user=user_response).model_dump())
    set_auth_cookie(response, token)
    return response


@router.get("/auth/me", response_model=AuthMeResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return AuthMeResponse(
        id=current_user["id"],
        first_name=current_user["first_name"],
        last_name=current_user["last_name"],
        role=normalize_role(current_user.get("role", "user")),
        assigned_buildings=current_user.get("assigned_buildings", []),
        main_building=current_user.get("main_building"),
        tags=current_user.get("tags", []),
        is_blocked=current_user.get("is_blocked", False),
        must_change_password=current_user.get("must_change_password", False),
        default_start_time=current_user.get("default_start_time"),
        default_end_time=current_user.get("default_end_time"),
        parking_sticker_number=current_user.get("parking_sticker_number"),
        job_family=current_user.get("job_family"),
    )


@router.post("/auth/logout")
async def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            session_id = payload.get("sid")
            if session_id:
                await db.sessions.update_one({"id": session_id}, {"$set": {"revoked": True}})
        except (jwt.PyJWTError, KeyError):
            pass
    response = JSONResponse(content={"message": "Logged out"})
    clear_auth_cookie(response)
    return response


@router.post("/auth/change-password")
async def change_password(data: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    # If not a forced change, verify current password
    if not current_user.get("must_change_password"):
        if not data.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        user = await db.users.find_one({"id": current_user["id"]})
        if not verify_password(data.current_password, user["password"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        # Prevent reusing the same password
        if verify_password(data.new_password, user["password"]):
            raise HTTPException(status_code=400, detail="New password cannot be the same as your current password")
    else:
        # Forced change: also prevent reusing the same password
        user = await db.users.find_one({"id": current_user["id"]})
        if user and verify_password(data.new_password, user["password"]):
            raise HTTPException(status_code=400, detail="New password cannot be the same as your current password")
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"password": hash_password(data.new_password), "must_change_password": False}},
    )
    return {"message": "Password changed successfully"}


@router.post("/auth/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, email: str = None):
    """Creates a password reset request. Admin is notified to reset the user's password."""
    from pydantic import BaseModel

    class ForgotPasswordRequest(BaseModel):
        email: str

    body = await request.json()
    user_email = body.get("email", "")
    if not user_email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = await db.users.find_one({"email": user_email}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    # Always return success to prevent email enumeration
    if user:
        from services.notifications import create_notification
        admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(50)
        for admin in admins:
            await create_notification(
                admin["id"],
                "Password Reset Request",
                f"{user['first_name']} {user['last_name']} ({user_email}) has requested a password reset.",
                "warning",
            )
    return {"message": "If the email exists in our system, your administrator has been notified to reset your password."}



@router.put("/auth/booking-preferences")
async def update_booking_preferences(
    default_start_time: str = None,
    default_end_time: str = None,
    current_user: dict = Depends(get_current_user),
):
    update = {}
    if default_start_time is not None:
        update["default_start_time"] = default_start_time if default_start_time else None
    if default_end_time is not None:
        update["default_end_time"] = default_end_time if default_end_time else None
    if not update:
        return {"message": "No changes"}
    await db.users.update_one({"id": current_user["id"]}, {"$set": update})
    return {"message": "Booking preferences updated", **update}
