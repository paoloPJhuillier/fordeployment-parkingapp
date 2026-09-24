import uuid
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter, Request
from starlette.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

import os

from database import db, init_db, close_db
from config import limiter

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

# V-03 FIX: Parse CORS origins with validation
def get_allowed_origins():
    """Parse CORS_ORIGINS env var and validate.
    
    If no specific origins are set, use a restrictive default for production.
    Wildcard (*) is only allowed if explicitly set for development.
    """
    origins_str = os.environ.get("CORS_ORIGINS", "")
    if not origins_str or origins_str == "*":
        # In production, CORS_ORIGINS should be explicitly set
        # Fall back to same-origin only if not configured
        return []
    return [o.strip() for o in origins_str.split(",") if o.strip()]

ALLOWED_ORIGINS = get_allowed_origins()

from auth.security import hash_password
from services.background import auto_mark_no_shows, check_waitlist_expiry, auto_release_slots
from routes import (
    auth as auth_routes,
    users as user_routes,
    vehicles as vehicle_routes,
    buildings as building_routes,
    reservations as reservation_routes,
    zones as zone_routes,
    parking_config as parking_config_routes,
    reports as report_routes,
    attendant as attendant_routes,
    notifications as notification_routes,
    templates as template_routes,
    site_content as site_content_routes,
    building_policies as building_policy_routes,
    waitlist as waitlist_routes,
    event_blocks as event_block_routes,
    system as system_routes,
)

logger = logging.getLogger("parking_app")

# Create the main app
app = FastAPI(title="Cebuana Lhuillier Parking API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Health check - MUST be registered immediately after app creation
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Create a router with the /api prefix and include all sub-routers
api_router = APIRouter(prefix="/api")
api_router.include_router(auth_routes.router)
api_router.include_router(user_routes.router)
api_router.include_router(vehicle_routes.router)
api_router.include_router(building_routes.router)
api_router.include_router(reservation_routes.router)
api_router.include_router(zone_routes.router)
api_router.include_router(parking_config_routes.router)
api_router.include_router(report_routes.router)
api_router.include_router(attendant_routes.router)
api_router.include_router(notification_routes.router)
api_router.include_router(template_routes.router)
api_router.include_router(site_content_routes.router)
api_router.include_router(building_policy_routes.router)
api_router.include_router(waitlist_routes.router)
api_router.include_router(event_block_routes.router)
api_router.include_router(system_routes.router)


@api_router.get("/")
async def root():
    # V-07 FIX: Remove version information from public endpoint
    return {"message": "Parking API", "status": "running"}


app.include_router(api_router)

# V-03 FIX: explicit allowed origins (fail-closed). When CORS_ORIGINS is empty,
# we now register NO origins instead of "*". This is safe in two prod modes:
#   1) Same-origin: frontend nginx reverse-proxies /api -> backend (no CORS needed)
#   2) Cross-origin: operator MUST set CORS_ORIGINS env var with the exact origin(s)
# If you're running purely locally and need wildcard, set CORS_ORIGINS="*" explicitly.
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else [],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https:; connect-src 'self' https:; frame-ancestors 'none'"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.on_event("startup")
async def start_background_tasks():
    # Connect the active DB adapter (MongoDB or Couchbase, controlled by DB_TYPE env var)
    await init_db()

    # Background loops fire every 1-5 minutes against shared DB state. When
    # scaling the backend horizontally, only ONE replica should run them —
    # otherwise N replicas all try to flip the same row to no_show, send N
    # waitlist notifications, etc. Set RUN_BACKGROUND_TASKS=false on the
    # additional replicas (the "leader" replica keeps the default true).
    if os.environ.get("RUN_BACKGROUND_TASKS", "true").lower() != "false":
        asyncio.create_task(auto_mark_no_shows())
        asyncio.create_task(check_waitlist_expiry())
        asyncio.create_task(auto_release_slots())
        logger.info("Background maintenance loops started on this replica")
    else:
        logger.info("RUN_BACKGROUND_TASKS=false — skipping background loops on this replica")
    # Ensure database indexes (polymorphic: MongoDBDatabase / CouchbaseDatabase both implement this)
    try:
        await db.create_indexes()
        logger.info("Database indexes ensured")
    except Exception as e:
        logger.error(f"Index creation error: {e}")
    # One-time cleanup: fix no-show records on future dates
    try:
        ran = await db.migrations.find_one({"key": "cleanup_future_no_shows"}, {"_id": 0})
        if not ran:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            bad = await db.reservations.find(
                {"status": "no_show", "date": {"$gt": today_str}},
                {"_id": 0, "id": 1, "user_id": 1},
            ).to_list(10000)
            for r in bad:
                await db.reservations.update_one(
                    {"id": r["id"]},
                    {"$set": {"status": "pending", "no_show_reported": False}},
                )
                await db.users.update_one(
                    {"id": r["user_id"], "no_show_count": {"$gt": 0}},
                    {"$inc": {"no_show_count": -1}},
                )
            await db.migrations.insert_one({"key": "cleanup_future_no_shows", "ran_at": datetime.now(timezone.utc).isoformat(), "fixed": len(bad)})
            if bad:
                logger.info(f"One-time cleanup: reverted {len(bad)} future no-show records")
    except Exception as e:
        logger.error(f"Cleanup migration error: {e}")

    # Ensure default admin exists. Email/password are env-overridable so
    # production deployments can ship without the dev-test credentials.
    try:
        admin = await db.users.find_one({"role": "admin"}, {"_id": 0})
        if not admin:
            seed_email = os.environ.get("FIRST_ADMIN_EMAIL", "admin.test@cebuana.com").strip().lower()
            seed_password = os.environ.get("FIRST_ADMIN_PASSWORD", "Test123!")
            using_defaults = (
                seed_email == "admin.test@cebuana.com"
                and seed_password == "Test123!"
            )
            if using_defaults:
                logger.warning(
                    "Seeding admin with DEV defaults (admin.test@cebuana.com / Test123!). "
                    "Set FIRST_ADMIN_EMAIL and FIRST_ADMIN_PASSWORD in your .env "
                    "before running in production."
                )
            admin_doc = {
                "id": str(uuid.uuid4()),
                "email": seed_email,
                "password": hash_password(seed_password),
                "first_name": "Admin",
                "last_name": "User",
                "company": os.environ.get("FIRST_ADMIN_COMPANY", "Cebuana Lhuillier"),
                "role": "admin",
                "is_blocked": False,
                "assigned_buildings": [],
                "main_building": None,
                "tags": [],
                "must_change_password": False,
                "no_show_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.users.insert_one(admin_doc)
            logger.info(f"Default admin account created: {seed_email}")
    except Exception as e:
        logger.error(f"Failed to seed admin account: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    await close_db()
