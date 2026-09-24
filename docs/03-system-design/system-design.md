# System Design Document
**Project:** Cebuana Lhuillier Parking Reservation System  
**Version:** 2.0  
**Date:** February 24, 2026  
**Related:** [SRS](../02-system-requirements/SRS.md) | [Architecture Diagrams](diagrams/architecture.md) | [ERD](diagrams/erd.md) | [Sequences](diagrams/sequences.md) | [Compliance](compliance-matrix.md)

---

## 1. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React | 19.0 | SPA framework |
| UI Components | shadcn/ui (Radix) | Latest | Accessible component library |
| Styling | TailwindCSS | 3.x | Utility-first CSS |
| Charts | Recharts | 3.6 | Dashboard visualizations |
| Routing | React Router | 7.5 | Client-side navigation |
| HTTP Client | Axios | 1.8 | API communication |
| Backend | FastAPI | 0.110 | Async Python API framework |
| ORM/Driver | Motor (Mongo) · couchbase-py | 3.x · 4.x | Async DB drivers, selected via `DB_TYPE` |
| Auth | PyJWT + bcrypt | Latest | Token generation + password hashing |
| Database | MongoDB **or** Couchbase | 7.x / Server 7 (Capella or Enterprise) | Pluggable via DB Abstraction Layer |
| Storage | Local FS **or** Huawei OBS (boto3 / S3) | 1.42 (boto3) | Pluggable via Storage Abstraction Layer |
| AI | Emergent LLM SDK (optional, behind `AI_INSIGHTS_ENABLED`) | 0.1 | AI insights generation |
| QR | qrcode + Pillow | Latest | QR code generation |
| Feature flags | features.py (env-driven, public `/api/system/features`) | – | AI Insights · Attendant Mode · Self Check-In Window |

---

## 2. High-Level Architecture

See [Architecture Diagrams](diagrams/architecture.md) for visual representation.

### 2.1 Component Architecture

```
[Browser/Mobile] → [Kubernetes Ingress / HCS ELB]
                        │
                ┌───────┴───────┐
                │ /api/* → :8001 │  (Backend - FastAPI · leader + worker pods)
                │ /*     → :80   │  (Frontend - nginx + React)
                └───────┬───────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
 [Couchbase :11207]  [MongoDB :27017]  [Huawei OBS / S3]
   (production)        (staging)       (floor-layout images)
        ▲                ▲
        └─── DB Abstraction Layer ──┘
            (DB_TYPE selects one)
```

### 2.2 Module Structure

**Backend (Python/FastAPI):**
```
backend/
├── server.py          # App orchestrator (middleware, startup, routes, RUN_BACKGROUND_TASKS guard)
├── config.py          # Environment config + logging
├── features.py        # Runtime feature flags (AI Insights, Attendant Mode, Self Check-In Window)
├── database/          # DB Abstraction Layer (DI selected by DB_TYPE)
│   ├── interface.py   # Async Mongo-like API surface
│   ├── mongodb.py     # Motor-backed adapter
│   └── couchbase_db.py # Couchbase SDK adapter (Capella + Enterprise)
├── storage/           # Storage Abstraction Layer (DI selected by STORAGE_TYPE)
│   ├── interface.py   # put/get/delete/exists
│   ├── local.py       # Local volume (UPLOAD_DIR)
│   └── obs.py         # Huawei OBS / S3 (boto3 path-style + s3v4)
├── auth/
│   └── security.py    # JWT, bcrypt, role guards, session fingerprint
├── models/            # Pydantic request/response models (incl. building_policy, parking_config)
├── routes/            # API endpoint handlers (15 modules — see system.py for /system/features)
│   ├── reservations.py  # Booking, cancel, confirm, QR, self check-in, sticker checks
│   ├── system.py        # /db-info, /features (public), /collection-stats, /sync
│   ├── waitlist.py      # Waitlist + notify_next_waitlisted_user
│   └── ... (others)
├── services/
│   ├── background.py  # Auto no-show + self-checkin window sweep + immediate slot release + waitlist notify
│   └── notifications.py
└── scripts/
    ├── db_cleanup.py
    ├── migrate_mongo_to_couchbase.py
    └── build_defect_validation_response.py
```

**Frontend (React):**
```
frontend/src/
├── App.js             # Routes, ProtectedRoute, layout (includes /admin/event-blocking)
├── context/
│   └── AuthContext.js  # Auth state, login/logout, session
├── services/
│   ├── api.js         # Axios instance, all API methods
│   └── eventBlocksAPI.js  # Event blocks API methods (NEW)
├── components/
│   ├── ui/            # shadcn/ui components
│   ├── NotificationBell.js
│   └── ForgotPassword.jsx  # Forgot password modal (NEW)
├── pages/
│   ├── LoginPage.js   # Login with forgot password link + uncontrolled password inputs
│   ├── UserDashboard.js
│   ├── BookingPage.js
│   ├── VehiclesPage.js
│   ├── ReservationsPage.js
│   ├── ProfilePage.js  # Includes change password section
│   ├── admin/
│   │   ├── AdminLayout.js
│   │   ├── AdminDashboard.jsx
│   │   ├── UserManagement.js
│   │   ├── BuildingManagement.jsx
│   │   ├── ZoneManagement.js
│   │   ├── ParkingConfig.js   # Includes main_building_exclusive toggle
│   │   ├── AdminReservations.jsx  # Includes cancellation reason dialog
│   │   ├── EventBlocking.jsx  # Event blocking management (NEW)
│   │   ├── AttendantManagement.js
│   │   ├── Reports.js
│   │   └── Settings.js
│   ├── auth/
│   │   └── ForcePasswordChange.jsx  # Uncontrolled password inputs (CWE-312 fix)
│   └── attendant/
│       └── AttendantDashboard.js
└── lib/
    └── utils.js       # cn() helper
```

---

## 3. Data Architecture

See [ERD](diagrams/erd.md) for entity-relationship diagram.

### 3.1 Collections Summary

| Collection | Records | Key Fields | Indexes |
|-----------|---------|------------|---------|
| users | 38 | id, email, password, role, main_building, tags, company, job_family | id (unique), email (unique) |
| sessions | 108 | id, user_id, fingerprint, revoked | id (unique), user_id |
| reservations | 45 | id, user_id, slot_id, building_id, date, status, qr_token, no_show_at, slot_released | id, user_id, building_id, (slot_id+date+status), qr_token |
| buildings | 6 | id, name, address | id (unique) |
| floors | 12 | id, label, building_id | id (unique), building_id |
| parking_slots | 121 | id, label, floor_id, building_id, status | id (unique), floor_id |
| vehicles | 10 | id, user_id, plate_number, make, model, color | id (unique), user_id, plate_number (unique) |
| zones | 3 | id, name, building_ids, user_ids | id (unique) |
| notifications | 10 | id, user_id, title, message, type, read | id (unique), (user_id+created_at) |
| parking_configs | 3 | id, building_id, release_time, booking_window_days, **main_building_exclusive** | building_id (unique) |
| ai_insights | 1 | id, content, generated_by, generated_at | id, generated_at |
| site_content | 1 | key, heading_line1, description, badges | key (unique) |
| building_policies | — | id, building_id, policy_type, enabled, max_users_per_slot, open_floor_ids, requires_sticker | id (unique), building_id (unique) |
| slot_registrations | — | id, slot_id, building_id, floor_id, user_id, vehicle_plate, sticker_number, status | id (unique), (slot_id+user_id+status) |
| waitlist_entries | — | id, user_id, building_id, preferred_date, preferred_start_time, preferred_end_time, status, position, notified_at | id (unique), (building_id+preferred_date+status) |
| **event_blocks** | — | id, event_name, reason, building_id, floor_id, slot_ids[], date, start_time, end_time, reservation_ids[], created_by, created_at | id (unique), building_id |
| migrations | 1 | key, ran_at | — |

### 3.2 Data Flow

```
User Action → React Component → Axios (withCredentials) 
    → K8s Ingress (/api prefix) → FastAPI Router 
    → Auth Middleware (JWT + Session + Fingerprint) 
    → Route Handler → DB Abstraction Layer (Motor OR Couchbase SDK) → DB
    → Pydantic Response Model → JSON → React State → UI Update
```

---

## 4. Integration Architecture

| Integration | Type | Purpose | Authentication |
|-------------|------|---------|----------------|
| MongoDB | Database (staging) | Document store via Motor | `MONGO_URL` connection string |
| Couchbase Capella / Enterprise | Database (production) | Document store via couchbase-py | `COUCHBASE_CONNECTION_STRING` + user/pass + Trust Store (TLS) |
| Huawei OBS / S3 | Object storage | Floor-layout images | AK/SK pair (`OBS_ACCESS_KEY`/`OBS_SECRET_KEY`) |
| Emergent LLM API | External AI (optional) | AI parking insights | API key (`EMERGENT_LLM_KEY`), gated by `AI_INSIGHTS_ENABLED` |
| File System | Storage (staging) | Floor plan images (local volume) | Local disk (`UPLOAD_DIR`) |

### 4.1 External API Integration

**AI Insights (Emergent LLM, optional):**
```
Admin triggers → POST /api/reports/ai-insights
    → features.ai_insights_enabled() guard
    → If disabled → 503 immediately (UI hides the surface entirely)
    → Else: build prompt with parking stats
    → emergentintegrations.llm.chat.LlmChat
    → Stream response → Save to ai_insights collection
    → Return markdown to frontend
```

### 4.2 Feature-Flag Surface

The public endpoint `GET /api/system/features` returns the live runtime state:

```json
{
  "ai_insights_enabled": true,
  "attendant_mode_enabled": true,
  "self_checkin_window_minutes": 15
}
```

Read by the React `useFeatures` hook once at SPA load and cached for the tab lifetime. Used to hide optional surfaces (AI Insights, Self Check-In button) so a deployment running with a feature off shows no traces of it in the UI.

---

## 5. Security Architecture

### 5.1 Authentication Flow

1. User submits credentials → `POST /api/auth/login`
2. Backend validates password (bcrypt) → creates JWT token (30min expiry)
3. JWT stored in HttpOnly secure cookie (not accessible via JS)
4. Session record created in DB with device fingerprint (User-Agent hash)
5. Every subsequent request: cookie sent automatically → JWT validated → session checked in DB → fingerprint verified
6. On failure: 401 response → frontend redirects to login

### 5.2 Authorization Model

| Guard | Implementation | Routes |
|-------|---------------|--------|
| `get_current_user` | JWT + session + fingerprint validation | All authenticated routes |
| `require_admin` | `get_current_user` + `role == 'admin'` check | User CRUD, reports, config, site content |
| `require_attendant` | `get_current_user` + `role in ['attendant', 'admin']` | Daily reservations, no-show, QR scan |

### 5.3 Security Headers

| Header | Value |
|--------|-------|
| Strict-Transport-Security | max-age=31536000; includeSubDomains |
| Content-Security-Policy | default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; ... |
| Permissions-Policy | camera=(), microphone=(), geolocation=() |
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| X-XSS-Protection | 1; mode=block |
| Referrer-Policy | strict-origin-when-cross-origin |

---

## 6. Business Architecture

### 6.1 Process Map

```
EMPLOYEE ONBOARDING:
  Admin bulk uploads CSV → Users created → Zone assigned → Main building set
  → Employee receives credentials → First login → Change password → Ready to book

DAILY BOOKING FLOW:
  Employee opens app → Dashboard → "Book Now" → Select building/floor/date/slot
  → View hourly timeline to verify availability → Confirm → QR code generated → Notification sent
  → (If fully booked: Join waitlist → Notified when slot opens → Book within window)

PARKING OPERATIONS:
  Attendant Mode (ATTENDANT_MODE_ENABLED=true, default):
    Attendant opens daily view → Sees reservations → Car arrives → Scans QR / Confirms
    → No-show after cutoff → Reports no-show → no_show_at timestamp recorded
    → User notified → Slot released X min after no_show_at (per config)
    → Waitlist triggered for the freed slot

  Self Check-In Mode (ATTENDANT_MODE_ENABLED=false):
    Parker arrives → opens "My Reservations" → green "Check in" button visible
    → Taps button (within start_time + SELF_CHECKIN_WINDOW_MINUTES, default 15)
    → Status flips to confirmed
    → If button NOT tapped within window → background loop flips to no_show
       → Slot released IMMEDIATELY → Waitlist triggered → no_show_count++ → in-app notice

EVENT BLOCKING:
  Admin navigates to Event Blocking → Selects building/floor/date/time/slots
  → Names the event + provides reason → Submits → System creates confirmed reservations
  → Blocked slots appear as unavailable to regular users during the event period
  → Admin can delete event block to release slots when event is over

ADMIN CANCELLATION:
  Admin views reservations → Clicks Cancel → Modal prompts for cancellation reason
  → Admin submits reason → Reservation cancelled → Parker notified with reason
  → Waitlist triggered for freed slot

PASSWORD MANAGEMENT:
  User forgets password → Clicks "Forgot Password?" on login → Enters email → Admin notified
  → Admin resets password → User logs in with new password → Prompted to change again
  OR
  User wants to change password → Profile page → Enters current + new password → Saved

REPORTING:
  Admin opens Reports → Views stats/charts → Filters by date/building
  → Generates AI insight → Saves for history → Shares with management
```

---

## 7. Diagrams Index

| Diagram | Type | Location |
|---------|------|----------|
| Component Architecture | UML Component | [architecture.md](diagrams/architecture.md) |
| Deployment Architecture (CCE) | UML Deployment | [architecture.md](diagrams/architecture.md) |
| Application Layer Detail | UML Component | [architecture.md](diagrams/architecture.md) |
| Frontend Component Tree | UML Component | [architecture.md](diagrams/architecture.md) |
| Entity Relationship | ERD | [erd.md](diagrams/erd.md) |
| Login Sequence | UML Sequence | [sequences.md](diagrams/sequences.md) |
| Booking Sequence | UML Sequence | [sequences.md](diagrams/sequences.md) |
| Attendant No-Show Sequence | UML Sequence | [sequences.md](diagrams/sequences.md) |
| Admin Bulk Upload Sequence | UML Sequence | [sequences.md](diagrams/sequences.md) |
| QR Scan Verification Sequence | UML Sequence | [sequences.md](diagrams/sequences.md) |
| **Self Check-In Sequence** | UML Sequence | [sequences.md](diagrams/sequences.md) |
| **Background No-Show + Waitlist Sequence** | UML Sequence | [sequences.md](diagrams/sequences.md) |
| Waitlist Notification & Claim Sequence | UML Sequence | [sequences.md](diagrams/sequences.md) |
| Session Validation Sequence | UML Sequence | [sequences.md](diagrams/sequences.md) |
| Compliance Matrix | Traceability | [compliance-matrix.md](compliance-matrix.md) |

---

*Previous: [SRS](../02-system-requirements/SRS.md) | Next: [Architecture Diagrams](diagrams/architecture.md)*
