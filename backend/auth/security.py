import hashlib
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response

from database import db
from config import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS,
    pwd_context, COOKIE_NAME, COOKIE_MAX_AGE, IS_SECURE,
)
from models.enums import UserRole

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_device_fingerprint(request: Request) -> str:
    ua = request.headers.get("user-agent", "unknown")
    return hashlib.sha256(ua.encode()).hexdigest()[:16]


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=IS_SECURE,
        samesite="none",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, secure=IS_SECURE, samesite="none")


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = None
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        token = cookie_token
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        token_fp = payload.get("fp")
        if token_fp:
            current_fp = generate_device_fingerprint(request)
            if token_fp != current_fp:
                raise HTTPException(status_code=401, detail="Session invalid: device mismatch")

        if session_id:
            session = await db.sessions.find_one({"id": session_id, "user_id": user_id, "revoked": {"$ne": True}})
            if not session:
                raise HTTPException(status_code=401, detail="Session has been revoked")

        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("is_blocked"):
            raise HTTPException(status_code=403, detail="Your account has been blocked. Please contact your administrator.")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_attendant(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in [UserRole.ATTENDANT, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Attendant access required")
    return current_user
