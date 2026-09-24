import uuid
import io
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
import pandas as pd

from database import db
from config import ALLOWED_TAGS
from auth.security import hash_password, get_current_user, require_admin
from models import (
    UserBase, UserCreate, UserResponse, AdminResetPasswordRequest,
    AssignMainBuildingRequest, UpdateTagsRequest, UserRole, ReservationStatus,
    BulkSetMainBuildingRequest, BulkAssignZoneRequest,
)
from services.reservations import batch_enrich_reservations

router = APIRouter()


def normalize_role(role_value: str) -> str:
    """Normalize legacy role values to valid enum values.
    
    Production DB may have legacy values like 'user (employee)', 'admin (super)', etc.
    This function maps them to valid UserRole enum values.
    """
    if not role_value:
        return "user"
    
    role_lower = role_value.lower().strip()
    
    # Direct matches
    if role_lower in ("admin", "user", "attendant"):
        return role_lower
    
    # Legacy mappings
    if "admin" in role_lower:
        return "admin"
    if "attendant" in role_lower:
        return "attendant"
    
    # Default to user for any other legacy values like "user (employee)"
    return "user"


@router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(
        id=u["id"],
        email=u["email"],
        first_name=u["first_name"],
        last_name=u["last_name"],
        company=u.get("company"),
        role=normalize_role(u.get("role", "user")),
        assigned_buildings=u.get("assigned_buildings", []),
        main_building=u.get("main_building"),
        tags=u.get("tags", []),
        is_blocked=u.get("is_blocked", False),
        must_change_password=u.get("must_change_password", False),
        default_start_time=u.get("default_start_time"),
        default_end_time=u.get("default_end_time"),
        parking_sticker_number=u.get("parking_sticker_number"),
        job_family=u.get("job_family"),
        created_at=u.get("created_at", "2026-01-01T00:00:00+00:00"),
        updated_at=u.get("updated_at"),
    ) for u in users]


@router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, current_user: dict = Depends(require_admin)):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # BUG FIX TCID-ATTENDANT-MANAGEMENT-007: Validate assigned_buildings for attendants
    if user_data.role == "attendant" and not user_data.assigned_buildings:
        raise HTTPException(status_code=400, detail="Attendants must be assigned to at least one building")

    # V-08 FIX: defense-in-depth CSV/Excel formula injection sanitization on every
    # text field that may be exported. Applies even on single-user create (not just bulk).
    safe_first_name        = sanitize_csv_field(user_data.first_name)
    safe_last_name         = sanitize_csv_field(user_data.last_name)
    safe_company           = sanitize_csv_field(user_data.company)
    safe_job_family        = sanitize_csv_field(user_data.job_family) if user_data.job_family else user_data.job_family
    safe_parking_sticker   = sanitize_csv_field(user_data.parking_sticker_number) if user_data.parking_sticker_number else user_data.parking_sticker_number

    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "first_name": safe_first_name,
        "last_name": safe_last_name,
        "company": safe_company,
        "role": user_data.role,
        "assigned_buildings": user_data.assigned_buildings,
        "main_building": user_data.main_building,
        "tags": user_data.tags,
        "default_start_time": user_data.default_start_time,
        "default_end_time": user_data.default_end_time,
        "parking_sticker_number": safe_parking_sticker,
        "job_family": safe_job_family,
        "is_blocked": False,
        "must_change_password": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.users.insert_one(user_doc)
    return UserResponse(
        id=user_id,
        email=user_data.email,
        first_name=safe_first_name,
        last_name=safe_last_name,
        company=safe_company,
        role=user_data.role,
        assigned_buildings=user_data.assigned_buildings,
        main_building=user_data.main_building,
        tags=user_data.tags,
        default_start_time=user_data.default_start_time,
        default_end_time=user_data.default_end_time,
        parking_sticker_number=safe_parking_sticker,
        job_family=safe_job_family,
        must_change_password=True,
        created_at=user_doc["created_at"],
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_data: UserBase, current_user: dict = Depends(require_admin)):
    # V-08 FIX: sanitize CSV/Excel-formula payloads on update path too
    update_data = {
        "email": user_data.email,
        "first_name": sanitize_csv_field(user_data.first_name),
        "last_name": sanitize_csv_field(user_data.last_name),
        "company": sanitize_csv_field(user_data.company),
        "role": user_data.role,
        "assigned_buildings": user_data.assigned_buildings,
        "main_building": user_data.main_building,
        "tags": user_data.tags,
        "default_start_time": user_data.default_start_time,
        "default_end_time": user_data.default_end_time,
        "parking_sticker_number": sanitize_csv_field(user_data.parking_sticker_number) if user_data.parking_sticker_number else user_data.parking_sticker_number,
        "job_family": sanitize_csv_field(user_data.job_family) if user_data.job_family else user_data.job_family,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.find_one_and_update(
        {"id": user_id},
        {"$set": update_data},
        return_document=True,
        projection={"_id": 0, "password": 0},
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=result["id"],
        email=result["email"],
        first_name=result["first_name"],
        last_name=result["last_name"],
        company=result.get("company"),
        role=normalize_role(result.get("role", "user")),
        assigned_buildings=result.get("assigned_buildings", []),
        main_building=result.get("main_building"),
        tags=result.get("tags", []),
        is_blocked=result.get("is_blocked", False),
        must_change_password=result.get("must_change_password", False),
        default_start_time=result.get("default_start_time"),
        default_end_time=result.get("default_end_time"),
        parking_sticker_number=result.get("parking_sticker_number"),
        job_family=result.get("job_family"),
        created_at=result.get("created_at", "2026-01-01T00:00:00+00:00"),
        updated_at=result.get("updated_at"),
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@router.put("/users/{user_id}/block")
async def block_user(user_id: str, current_user: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["role"] == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot block an admin user")
    await db.users.update_one({"id": user_id}, {"$set": {"is_blocked": True}})
    return {"message": "User blocked", "user_id": user_id}


@router.put("/users/{user_id}/unblock")
async def unblock_user(user_id: str, current_user: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"is_blocked": False}})
    return {"message": "User unblocked", "user_id": user_id}


@router.put("/users/{user_id}/main-building")
async def assign_main_building(user_id: str, data: AssignMainBuildingRequest, current_user: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.main_building:
        building = await db.buildings.find_one({"id": data.main_building}, {"_id": 0})
        if not building:
            raise HTTPException(status_code=404, detail="Building not found")
    await db.users.update_one({"id": user_id}, {"$set": {"main_building": data.main_building}})
    return {"message": "Main building assigned", "user_id": user_id, "main_building": data.main_building}


@router.put("/users/{user_id}/tags")
async def update_user_tags(user_id: str, data: UpdateTagsRequest, current_user: dict = Depends(require_admin)):
    invalid = set(data.tags) - ALLOWED_TAGS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid tags: {invalid}. Allowed: {ALLOWED_TAGS}")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"tags": data.tags}})
    return {"message": "Tags updated", "user_id": user_id, "tags": data.tags}


@router.put("/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, data: AdminResetPasswordRequest, current_user: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password": hash_password(data.password), "must_change_password": True}},
    )
    return {"message": "Password reset. User will be prompted to change on next login."}


@router.get("/admin/reservations")
async def get_admin_reservations(
    building_id: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    query = {}
    if building_id:
        query["building_id"] = building_id
    if date:
        query["date"] = date
    if status and status != "all":
        query["status"] = status
    if user_id:
        query["user_id"] = user_id

    reservations = await db.reservations.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return await batch_enrich_reservations(reservations)


@router.put("/admin/reservations/{reservation_id}/cancel")
async def admin_cancel_reservation(reservation_id: str, current_user: dict = Depends(require_admin)):
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation["status"] in [ReservationStatus.CANCELLED, ReservationStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {reservation['status']} reservation")

    # PPA-62 fix (admin path): block cancellation of strictly past-dated
    # reservations on the admin endpoint as well. The user-side endpoint
    # already enforced this; the admin path was missed.
    from datetime import date as _date_cls
    res_date = reservation.get("date") or ""
    try:
        if res_date and res_date < _date_cls.today().isoformat():
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel a past reservation",
            )
    except HTTPException:
        raise
    except Exception:
        pass

    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"status": ReservationStatus.CANCELLED}},
    )

    # Trigger waitlist notification (no user notification sent for admin cancels)
    from routes.waitlist import notify_next_waitlisted_user
    try:
        await notify_next_waitlisted_user(reservation["building_id"], reservation["date"])
    except Exception:
        pass

    return {"message": "Reservation cancelled by admin"}


def sanitize_csv_field(value: str) -> str:
    """Sanitize CSV field to prevent formula injection (V-08).
    
    Prepends a single quote to values starting with dangerous characters
    that could be interpreted as formulas in spreadsheet applications.
    """
    if not value:
        return value
    value = str(value).strip()
    # Characters that could trigger formula execution in Excel/Sheets
    dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r', '\n')
    if value.startswith(dangerous_prefixes):
        return "'" + value
    return value


@router.post("/users/bulk-upload")
async def bulk_upload_users(
    file: UploadFile = File(...),
    default_password: str = Form("changeme123"),
    current_user: dict = Depends(require_admin),
):
    try:
        content = await file.read()

        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="File must be CSV or Excel")

        required_columns = ['first_name', 'last_name', 'email']
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing required column: {col}")

        created = 0
        skipped = 0
        errors = []

        # Batch check existing emails to avoid N+1 queries
        all_emails = [str(row['email']).strip().lower() for _, row in df.iterrows()]
        existing_users = await db.users.find(
            {"email": {"$in": all_emails}}, {"_id": 0, "email": 1}
        ).to_list(len(all_emails))
        existing_emails = {u["email"] for u in existing_users}

        # Pre-load building and zone name maps for template columns
        all_buildings = await db.buildings.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
        building_name_to_id = {b["name"].strip().lower(): b["id"] for b in all_buildings}

        all_zones = await db.zones.find({}, {"_id": 0, "id": 1, "name": 1, "user_ids": 1}).to_list(100)
        zone_name_to_doc = {z["name"].strip().lower(): z for z in all_zones}

        # Track which users to add to which zones
        zone_user_additions = {}  # zone_id -> [user_id, ...]

        hashed_pw = hash_password(default_password)

        for idx, row in df.iterrows():
            try:
                email = str(row['email']).strip().lower()
                if email in existing_emails:
                    skipped += 1
                    continue

                # Resolve main_building name to ID
                main_building_id = None
                if 'main_building' in df.columns and pd.notna(row.get('main_building')):
                    bname = str(row['main_building']).strip().lower()
                    if bname:
                        main_building_id = building_name_to_id.get(bname)
                        if not main_building_id:
                            errors.append(f"Row {idx}: Building '{row['main_building']}' not found")

                # V-01 FIX: Only allow 'user' or 'attendant' roles via bulk upload
                # Admin accounts must be created through dedicated admin workflow
                requested_role = str(row.get('role', 'user')).strip().lower() if pd.notna(row.get('role')) else "user"
                if requested_role not in ('user', 'attendant'):
                    requested_role = 'user'  # Force to 'user' if admin or invalid role requested
                    errors.append(f"Row {idx}: Role '{row.get('role')}' not allowed in bulk upload. Set to 'user'.")

                user_id = str(uuid.uuid4())
                user_doc = {
                    "id": user_id,
                    "email": email,
                    "password": hashed_pw,
                    # V-08 FIX: Sanitize text fields to prevent CSV injection
                    "first_name": sanitize_csv_field(str(row['first_name'])),
                    "last_name": sanitize_csv_field(str(row['last_name'])),
                    "company": sanitize_csv_field(str(row.get('company', ''))) if pd.notna(row.get('company')) else None,
                    "role": requested_role,
                    "job_family": sanitize_csv_field(str(row.get('job_family', ''))) if pd.notna(row.get('job_family')) else None,
                    "assigned_buildings": [],
                    "main_building": main_building_id,
                    "tags": [],
                    "is_blocked": False,
                    "must_change_password": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.users.insert_one(user_doc)
                created += 1

                # Queue zone assignment
                if 'zone' in df.columns and pd.notna(row.get('zone')):
                    zname = str(row['zone']).strip().lower()
                    if zname and zname in zone_name_to_doc:
                        zone_doc = zone_name_to_doc[zname]
                        if zone_doc["id"] not in zone_user_additions:
                            zone_user_additions[zone_doc["id"]] = []
                        zone_user_additions[zone_doc["id"]].append(user_id)
                    elif zname:
                        errors.append(f"Row {idx}: Zone '{row['zone']}' not found")

            except (ValueError, KeyError, TypeError) as e:
                errors.append(f"Row {idx}: {str(e)}")

        # Batch update zones with new users
        zone_assignments = 0
        for zone_id, user_ids in zone_user_additions.items():
            await db.zones.update_one(
                {"id": zone_id},
                {"$addToSet": {"user_ids": {"$each": user_ids}}},
            )
            zone_assignments += len(user_ids)

        return {
            "message": "Bulk upload complete",
            "created": created,
            "skipped": skipped,
            "zone_assignments": zone_assignments,
            "errors": errors[:10],
        }
    except HTTPException:
        raise
    except (ValueError, pd.errors.ParserError, KeyError):
        raise HTTPException(status_code=400, detail="Failed to process upload file. Ensure it is a valid CSV or Excel file.")


@router.post("/users/bulk-set-building")
async def bulk_set_main_building(req: BulkSetMainBuildingRequest, current_user: dict = Depends(require_admin)):
    if not req.user_ids:
        raise HTTPException(status_code=400, detail="No users selected")

    now = datetime.now(timezone.utc).isoformat()
    result = await db.users.update_many(
        {"id": {"$in": req.user_ids}},
        {"$set": {"main_building": req.main_building, "updated_at": now}},
    )
    return {"message": f"Main building updated for {result.modified_count} users", "modified": result.modified_count}


@router.post("/users/bulk-assign-zone")
async def bulk_assign_zone(req: BulkAssignZoneRequest, current_user: dict = Depends(require_admin)):
    if not req.user_ids:
        raise HTTPException(status_code=400, detail="No users selected")

    zone = await db.zones.find_one({"id": req.zone_id}, {"_id": 0})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    await db.zones.update_one(
        {"id": req.zone_id},
        {"$addToSet": {"user_ids": {"$each": req.user_ids}}},
    )
    return {"message": f"Added {len(req.user_ids)} users to zone '{zone['name']}'", "zone_name": zone["name"]}
