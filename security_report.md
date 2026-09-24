# Security Assessment Report
## Cebuana Lhuillier Parking Reservation App
**Date:** February 18, 2026  
**Scope:** Full-stack application (FastAPI backend, React frontend, MongoDB)

---

## Executive Summary

The application has a solid foundation with JWT authentication, bcrypt password hashing, role-based access control, and Pydantic input validation. However, **12 vulnerabilities** were identified across Critical, High, Medium, and Low severity levels. The most urgent issues involve the JWT secret key, CORS policy, file upload path traversal, and missing rate limiting.

---

## Findings

### CRITICAL (Immediate Action Required)

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| C1 | **Weak/Hardcoded JWT Secret** | `backend/.env` line 4 | A02: Cryptographic Failures |

**Detail:** The JWT secret `cebuana-parking-secret-key-2024-secure` is a guessable, hardcoded string. If an attacker obtains this key, they can forge JWT tokens for any user, including admins.

**Recommendation:**
- Generate a cryptographically random secret: `openssl rand -hex 64`
- Rotate the key periodically
- Never commit secrets to version control

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| C2 | **Wildcard CORS Policy** | `backend/.env` line 3: `CORS_ORIGINS="*"` | A05: Security Misconfiguration |

**Detail:** `allow_origins=["*"]` combined with `allow_credentials=True` allows any website to make authenticated cross-origin requests to the API, enabling CSRF-like attacks from malicious sites.

**Recommendation:**
- Restrict to the actual frontend domain: `CORS_ORIGINS="https://reserve-park-debug.preview.emergentagent.com"`
- In production, list only trusted origins

---

### HIGH

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| H1 | **Path Traversal in File Upload Serving** | `server.py` — `serve_upload()` endpoint | A01: Broken Access Control |

**Detail:** The `/api/uploads/{filename}` endpoint takes a user-supplied filename and resolves it against `UPLOAD_DIR`. A crafted filename like `../../.env` could potentially serve sensitive files.

**Current code:**
```python
filepath = UPLOAD_DIR / filename
```

**Recommendation:**
```python
# Sanitize filename to prevent directory traversal
import re
safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
if not safe_name or '..' in safe_name:
    raise HTTPException(status_code=400, detail="Invalid filename")
filepath = UPLOAD_DIR / safe_name
```

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| H2 | **No Rate Limiting on Authentication** | `server.py` — `/auth/login`, `/auth/register` | A07: Identification & Authentication Failures |

**Detail:** No rate limiting exists on login or registration endpoints. An attacker can perform unlimited brute-force password attempts.

**Recommendation:**
- Add `slowapi` rate limiting library
- Limit login to 5 attempts per minute per IP
- Limit registration to 3 per hour per IP
- Consider account lockout after 10 failed attempts

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| H3 | **No File Extension Whitelist on Upload** | `server.py` — `upload_floor_layout()` | A04: Insecure Design |

**Detail:** The upload endpoint checks `content_type.startswith("image/")` but this header is client-controlled and trivially spoofed. The file extension is taken directly from the user-supplied filename without validation. An attacker could upload a `.html` or `.svg` file containing JavaScript.

**Recommendation:**
```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(status_code=400, detail="Allowed formats: png, jpg, jpeg, gif, webp")
```

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| H4 | **Tag Injection — Unrestricted Tag Values** | `server.py` — `update_user_tags()` | A01: Broken Access Control |

**Detail:** The `/users/{user_id}/tags` endpoint accepts any list of strings. An attacker with admin access (or if the endpoint were ever exposed) could inject arbitrary tags like `"admin"` or `"superuser"` that might be interpreted by future business logic.

**Recommendation:**
```python
ALLOWED_TAGS = {"vip", "group_head"}

@api_router.put("/users/{user_id}/tags")
async def update_user_tags(user_id: str, data: UpdateTagsRequest, ...):
    invalid = set(data.tags) - ALLOWED_TAGS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid tags: {invalid}")
    ...
```

---

### MEDIUM

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| M1 | **No Password Complexity Enforcement** | `server.py` — `/auth/register` | A07: Identification & Authentication Failures |

**Detail:** The registration endpoint accepts any password string, including single-character passwords. There is no minimum length, complexity, or common-password check.

**Recommendation:**
```python
class UserCreate(BaseModel):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain an uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain a digit')
        return v
```

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| M2 | **JWT Token Stored in localStorage** | `frontend/src/context/AuthContext.js` | A07: Identification & Authentication Failures |

**Detail:** JWT tokens are stored in `localStorage`, which is accessible to any JavaScript running on the page. If an XSS vulnerability exists anywhere in the app, the token can be stolen.

**Recommendation:**
- For highest security: store JWT in an HttpOnly, Secure, SameSite cookie (requires backend changes)
- At minimum: use `sessionStorage` instead of `localStorage` (clears on tab close)
- Add Content Security Policy (CSP) headers to mitigate XSS

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| M3 | **Blocked User Can Use Existing Token** | `server.py` — `get_current_user()` | A01: Broken Access Control |

**Detail:** When an admin blocks a user, the user's existing JWT token remains valid until expiration (24 hours). The `get_current_user()` function does not check `is_blocked` status. Only the reservation creation endpoint checks for blocked status.

**Recommendation:**
```python
async def get_current_user(...):
    ...
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("is_blocked"):
        raise HTTPException(status_code=403, detail="Account blocked")
    return user
```

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| M4 | **Sensitive Data in QR Code** | `server.py` — `generate_qr_code()` | A04: Insecure Design |

**Detail:** QR codes contain reservation details (building, floor, slot, vehicle plate) in plain text and are also stored as full base64 images in the database. If a QR code is photographed or shared, it exposes PII. The base64 images also significantly increase database storage.

**Recommendation:**
- QR codes should contain only a reservation ID or a signed reference token
- Attendant scans QR → app looks up full details server-side
- Don't store base64 QR images in the database; generate on demand

---

### LOW

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| L1 | **No Security Headers** | Backend/Infrastructure | A05: Security Misconfiguration |

**Detail:** The API does not set security headers like `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, or `Content-Security-Policy`.

**Recommendation:**
```python
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

| # | Vulnerability | Location | OWASP Category |
|---|--------------|----------|----------------|
| L2 | **Verbose Error Messages** | Various endpoints | A09: Security Logging & Monitoring Failures |

**Detail:** Some error handlers return internal details (e.g., `str(e)` in bulk upload). Stack traces or internal errors could leak implementation details to attackers.

**Recommendation:**
- In production, return generic error messages to clients
- Log detailed errors server-side only
- Never expose raw exception messages in API responses

---

## Summary Matrix

| Severity | Count | Items |
|----------|-------|-------|
| **Critical** | 2 | C1 (JWT Secret), C2 (CORS Wildcard) |
| **High** | 4 | H1 (Path Traversal), H2 (No Rate Limit), H3 (Upload Extension), H4 (Tag Injection) |
| **Medium** | 4 | M1 (Password Complexity), M2 (localStorage JWT), M3 (Blocked User Token), M4 (QR Code PII) |
| **Low** | 2 | L1 (Security Headers), L2 (Verbose Errors) |

---

## Positive Security Controls Already in Place

- **bcrypt** password hashing (industry standard)
- **JWT-based** stateless authentication with expiration
- **Role-based access control** (admin, user, attendant) properly enforced on all admin/attendant endpoints
- **Pydantic models** for input validation (type safety, email format)
- **MongoDB `_id` exclusion** from all API responses
- **Owner-scoped queries** — users can only see their own vehicles/reservations
- **Vehicle ownership check** on reservation creation
- **Booking overlap detection** prevents double-booking
- **File size limit** (10MB) on uploads

---

## Recommended Priority Order for Fixes

1. **C1** — Generate strong JWT secret (5 min fix, highest impact)
2. **C2** — Restrict CORS origins (2 min fix)
3. **M3** — Check blocked status in `get_current_user` (5 min fix)
4. **H1** — Sanitize upload filenames (10 min fix)
5. **H3** — Whitelist file extensions (5 min fix)
6. **H4** — Validate allowed tags (5 min fix)
7. **H2** — Add rate limiting (30 min, requires new dependency)
8. **M1** — Password complexity (10 min fix)
9. **L1** — Security headers middleware (10 min fix)
10. **L2** — Sanitize error messages (15 min)
11. **M2** — HttpOnly cookie for JWT (1 hr, architecture change)
12. **M4** — QR code redesign (1 hr, architecture change)
