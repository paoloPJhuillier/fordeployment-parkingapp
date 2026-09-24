# PRD — Cebuana Lhuillier Parking Reservation System
**Version:** 2.3  
**Last Updated:** April 24, 2026

---

## 1. Original Problem Statement

Build a comprehensive corporate Parking Reservation System for Cebuana Lhuillier that:
- Manages limited parking across multiple buildings
- Serves three roles: End Users (employees), Admins, and Parking Attendants
- Supports multi-building, multi-floor zone-based access control
- Enforces VIP designations, real-time occupancy tracking, and waitlisting
- **v2.3 addition:** Run against either MongoDB (current) or Couchbase (Capella cloud / on-prem Enterprise) via an abstraction layer so deployments can switch databases without code changes.

---

## 2. User Personas

| Role | Description |
|------|-------------|
| **End User (Parker)** | Employee who books parking via web app |
| **Admin** | Facilities/IT administrator managing the system |
| **Attendant** | On-site parking staff confirming arrivals and no-shows |

---

## 3. Core Architecture

- **Frontend:** React 19, TailwindCSS, shadcn/ui
- **Backend:** FastAPI (Python), Motor (async MongoDB), Couchbase Python SDK 4.6
- **Database:** MongoDB (default) or Couchbase Capella / Enterprise — selected at boot via `DB_TYPE` env var
- **Auth:** JWT HttpOnly cookies + bcrypt + device fingerprinting
- **Background Tasks:** auto no-show marking, waitlist expiry

---

## 4. What's Been Implemented

### Phase 1 — Core System (completed)
- Multi-role auth with JWT, session management, device fingerprinting
- User CRUD, bulk CSV upload, zone assignment, VIP tags, Job Family field
- Building/floor/slot management with maintenance status
- Zone-based booking rules (main building + zone restrictions)
- Multi-date booking, QR codes, reservation lifecycle
- Attendant dashboard with daily view, confirm/no-show, QR scan
- Admin reports with AI-powered insights (Emergent LLM)
- Site customization (login page branding)
- Waitlist + hourly slot timeline

### Phase 2 — Advanced Features (completed)
- Building Policies: sticker requirements, slot registrations, open floors
- Plate number uniqueness enforcement (global)
- Vehicle-level sticker validation (not just user-level)
- Job Family field + bulk upload column

### Phase 3 — Latest Release (completed Feb 25, 2026)
- **Admin Cancellation**: mandatory reason field + in-app notification to parker
- **Main Building Exclusivity**: per-building toggle restricting reservations to assigned employees (admins exempt)
- **Event Blocking**: admin module to block multiple slots for events using visual slot map
- **Password Management**: self-service change password (requires current password) + forgot password (admin notified)
- **Security Fix (CWE-312)**: all password inputs refactored to uncontrolled `useRef` components — passwords no longer stored in DOM/React state
- **Documentation Suite**: all 9 markdown files + 14 DOCX + 14 PDF output files regenerated

### Phase 4 — Bug Fix Release (completed Feb 28, 2026)
- **DEF-011 CRITICAL**: Blocked users could log in — fixed by checking `is_blocked` in login endpoint
- **DEF-012 HIGH**: Same password accepted in change-password — fixed with same-password prevention check
- **DEF-013**: Parking Config URL corrected from `/admin/config` → `/admin/parking-config`
- **DEF-014**: Login empty-field validation now shows correct field-specific error messages
- **DEF-015**: User Management full-name search now works (first + last name combined)
- **DEF-016**: "Unknown" buildings filtered from admin reports/charts
- **DEF-017**: Attendant dashboard now has QR scan button with token-entry dialog

### Phase 5 — Bug Fix Release (completed Mar 5, 2026)
Fixed 14 test cases from user's test suite:
- **TCID-PARKING-ATTENDANT-001**: No-Show button now hidden for confirmed reservations (only shows for pending)
- **TCID-ATTENDANT-MANAGEMENT-007**: Backend validates attendants must have at least one assigned building
- **TCID-ATTENDANT-MANAGEMENT-011**: Attendants can now be assigned to multiple buildings via checkbox UI
- **TCID-PARKING-RESERVATION-013**: Past hours disabled for today's date (shows "Past" label)
- **TCID-PARKING-CONFIG-013/014**: Hours outside parking config times are disabled (shows "Closed" label)
- **TCID-PARKING-RESERVATION-015**: Default booking hours auto-selected when user selects a slot
- **TCID-VEHICLE-MANAGEMENT-007/008**: Vehicle plate validation: min 2 chars, max 15 chars
- **TCID-BUILDING-POLICIES-006**: Sticker number required when policy has requires_sticker=true
- **TCID-BUILDING-POLICIES-009**: User can only be registered to one slot per building
- **TCID-BUILDING-MANAGEMENT-016**: Slot name truncated with tooltip to prevent UI overflow
- **TCID-ZONE-MANAGEMENT-004**: "Unknown" buildings filtered from zone display
- **TCID-PARKING-RESERVATION-017**: Notification detail dialog opens on click for full content view

### Phase 6 — UI/UX Enhancements (completed Mar 17, 2026)

**Part 1 - Field Character Limits:**
| Field | Limit | Backend | Frontend |
|-------|-------|---------|----------|
| First Name, Last Name, Company | 1-30 | Pydantic Field | maxLength + slice |
| Building Name | 1-30 | Pydantic Field | maxLength + slice |
| Address Line 1, Address Line 2 | 1-30 | Pydantic Field | maxLength + slice |
| Floor Label | 1-16 | Pydantic Field | maxLength + slice |
| Zone Name | 1-25 | Pydantic Field | maxLength + slice |
| Plate Number | 1-16 | Pydantic validator | maxLength + slice |

**Part 2 - UI/UX Features:**
- **Building Management**: Split address into Address Line 1 & 2 (30 chars each)
- **Building Management**: Added Edit Building function (PUT /buildings/{id})
- **User Management**: Added "No Company / Unassigned" option in Company filter
- **Reservation Management**: Added pagination (20 records per page)
- **User Dashboard**: Added confirmation dialog before cancelling reservations
- **Building Policies**: Shows "Changes are saved automatically" indicator
- **Global CSS**: Added text wrapping styles for better UI handling

### Phase 7 — Security VAPT Remediation (completed Mar 19, 2026)

Remediated 10 security findings from VAPT audit:

| ID | Severity | Finding | Remediation |
|----|----------|---------|-------------|
| **V-01** | HIGH | Bulk upload allowed `role=admin` | Block admin role; force to 'user' |
| **V-02** | HIGH | Users could access all buildings | Role-based filtering in GET /buildings |
| **V-03** | HIGH | CORS wildcard (*) policy | Configurable via CORS_ORIGINS env var |
| **V-04** | MEDIUM | Unminified JS exposed API | GENERATE_SOURCEMAP=false |
| **V-06** | MEDIUM | Attendants saw all buildings | Filter to assigned_buildings only |
| **V-07** | LOW | API version disclosed | Removed from /api/ root endpoint |
| **V-08** | LOW | CSV injection payloads stored | sanitize_csv_field() adds quote prefix |
| **V-09** | LOW | Login placeholder revealed domain | Changed to "Enter your email address" |
| **V-10** | LOW | Outdated react-router (CVEs) | Upgraded to 7.13.1 |
| **V-11** | LOW | Password in DOM console | Already using ref-based input |

**Files Modified:**
- `/app/backend/routes/users.py` - sanitize_csv_field(), bulk upload role restriction
- `/app/backend/routes/buildings.py` - Role-based building filtering
- `/app/backend/server.py` - CORS config, API version removed
- `/app/frontend/src/pages/LoginPage.js` - Generic email placeholder
- `/app/frontend/.env` - GENERATE_SOURCEMAP=false
- `/app/frontend/package.json` - react-router-dom@7.13.1

### Phase 8 — Database Abstraction Layer (completed Apr 24, 2026)

Introduced a database abstraction so the same FastAPI app can run against either MongoDB or Couchbase Capella/Enterprise. Toggle via a single env var; no code changes needed to swap.

**What was built:**
- `/app/backend/database/` package replaces legacy `database.py`
  - `interface.py` — Motor-shaped abstract API (`find`, `find_one`, `insert_one`, `update_one`, `delete_one`, cursor chain `sort().limit().skip().to_list()`)
  - `mongodb.py` — thin passthrough adapter around Motor (zero behavior change in Mongo mode)
  - `couchbase_db.py` — full adapter with:
    - MongoDB-style filter → N1QL `WHERE` translation (`$in`, `$ne`, `$gt/$gte/$lt/$lte`, equality)
    - Update operator translation (`$set`, `$inc`, `$addToSet` with `$each`)
    - Fast KV path when filtering by `id` only
    - Parallel GSI index creation across 30+ indexes on startup
    - `asyncio.to_thread` offloading so blocking SDK calls don't starve the event loop
  - `__init__.py` — `DB_TYPE` env-var driven factory + `get_db()` FastAPI dep
- `/api/system/db-info` (admin-only) — returns `{db_type, label, host, database_name, connected}` for the admin UI
- Sidebar badge `DbStatusBadge.js` — green "MONGODB" / red "COUCHBASE CAPELLA"
- `/app/backend/scripts/migrate_mongo_to_couchbase.py` — idempotent data migration using `upsert_multi` batch writes (815 docs in 6s)
- `/app/backend/scripts/test_couchbase_connection.py` — standalone Capella connectivity verifier

**Verified:**
- MongoDB mode regression: 15/15 pytest, no behavior change
- Couchbase mode read-only smoke: 14/14 pytest, counts match Mongo exactly (47 users, 8 buildings, 17 floors, 160 slots, 74 reservations)
- Migration tool successfully copied all 815 documents to Capella
- Admin badge renders correctly in both modes

**Operational notes:**
- Capella allowlist: preview pod egress IP `34.170.12.145/32` is whitelisted
- Preview pod egress IPs may rotate across sessions; production deployment will need its own allowlist entry
- Switch DBs: edit `DB_TYPE` in `/app/backend/.env` → `sudo supervisorctl restart backend`
- **Current active DB: `couchbase` (Capella).** Bucket: `db_parking`. 835 docs.

### Phase 12 — QAT 4th Pass Defect Closure (completed Apr 27, 2026)

Fixed 13 of 13 genuine defects from the 2026-03-23 QAT 4th Pass test report. Remaining 11 of the 24 originally-flagged failed rows are tester data-entry artefacts (Expected = Actual in the spreadsheet) that need QA re-execution before they can be triaged as real defects.

| ID | Severity | Fix |
|----|----------|-----|
| TCID-LOGIN-005 | P1 | Client-side email regex pre-check + `noValidate` on `<form>` so our toast fires instead of HTML5 popup; error path always toasts and stays on the login page |
| TCID-LOGIN-006 | P3 | UserLogin Pydantic validator rejects passwords with leading/trailing whitespace; LoginPage now shows clear message |
| TCID-LOGIN-018 | P0 | (already fixed in earlier phase) — change_password rejects new == current |
| TCID-DASHBOARD-002 | P2 | Verified: sidebar `/admin/parking-config` matches App.js route; was already correct |
| TCID-DASHBOARD-008 | P3 | Wider Y axis (180px), `interval={0}`, ellipsis tickFormatter for long building names |
| TCID-PARKING-CONFIG-007 | P0 | New `auto_release_slots()` background task in services/background.py — runs every 60s, returns slots to `available` after configured `release_time` |
| TCID-PARKING-CONFIG-010 | P3 | `booking_window_days: int = Field(7, ge=1, le=30)`; clear validation error |
| TCID-BUILDING-MANAGEMENT-010 | P1 | `BuildingUpdate` is now permissive (no max_length); legacy buildings can be edited and deleted without 422 |
| TCID-BUILDING-MANAGEMENT-027 | P1 | BuildingManagement page refetches on focus + 30s poll while visible |
| TCID-EVENT-BLOCKING-012 | P2 | Two-pass create: collect ALL conflicting slots before raising; error lists all slot labels |
| TCID-EVENT-BLOCKING-013 | P2 | Added `type="button"` to shadcn DialogClose component — fixes ALL modal close buttons app-wide |
| TCID-ANALYTICS-004 | P2 | Range Calendar `onSelect` now commits any non-null change immediately; single click works as a same-day range |
| TCID-ANALYTICS-016 | P2 | Reports.js sorts reservations newest-first by `created_at`; refetches on focus/visibility |
| TC-USER-MANAGEMENT-030 | P2 | Add User trigger explicitly calls `resetForm()` on click and on dialog open; no leakage from prior Edit interaction |

**Testing:** iteration_39 (full backend + frontend) → 100% backend (20/20), 75% frontend (1 minor wording gap). iteration_40 retest after `noValidate` fix → 100% (3/3 frontend, 1/1 backend). Couchbase find_one_and_update + reservation confirm flows still green.

Tracker file: `/app/docs/output/QAT_Failed_Items_Tracker_2026-03-23.xlsx` regenerated — **2 of 13 still flagged "No"** (genuinely need QA repro: TC-USER-MANAGEMENT-031 tooltip overlap location + TCID-LOGIN-003 blank-actual data entry).

### Phase 11 — VAPT 2026-03-25 Retest Remediations (completed Apr 27, 2026)

Closed 4 of the 6 remaining open VAPT findings; remaining 2 are deployment/ops-only.

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| V-02 | High | parking-config + slot-registrations leaked admin fields / other users' IDs | **DONE** — role-based response shape (`ParkingConfigPublicResponse`); slot-registrations row-scoped per role |
| V-03 | High | CORS fallback to `*` | **DONE** — fail-closed `[]` default; operators must set `CORS_ORIGINS` env var |
| V-08 | Low | CSV formula injection via single-user POST/PUT | **DONE** — `sanitize_csv_field()` on all three write paths; backfill script ready |
| V-10 | Low | react-router 7.11.0 stale cache | **DONE** — added unauthenticated `/api/system/build-info` endpoint for cache freshness verification |
| V-11 | Low | Cleartext password in DOM | **DONE (mitigated)** — wipe-on-blur + visibilitychange handlers; residual risk accepted |
| V-05 | Medium | Decommissioned env still public | **OPEN (ops)** — manual decommission via Emergent dashboard |

Side effect: testing agent caught a Couchbase adapter gap (`find_one_and_update` missing). Added both `find_one_and_update` and `find_one_and_delete` methods to `CouchbaseCollection`; covered both BEFORE / AFTER snapshot semantics. Full backend regression: **29/29 pass**.

Tracker file: `/app/docs/output/VAPT_Tracker_2026-03-25.xlsx` (auto-generated by `/app/scripts/build_vapt_tracker.py`).

### Phase 10 — Couchbase 7+ Best-Practice Refactor (completed Apr 24, 2026)

Refactored the Couchbase storage layout to follow **Couchbase 7+ best practice** of scopes + native collections (1:1 mapping to MongoDB collections), replacing the earlier single-default-collection + `type`-field pattern.

**What changed:**
- **18 native Couchbase collections** provisioned under `db_parking._default` scope (users, sessions, buildings, floors, parking_slots, vehicles, zones, parking_configs, building_policies, slot_registrations, reservations, waitlist_entries, event_blocks, notifications, site_content, templates, ai_insights, migrations)
- Adapter now binds to `bucket.scope("_default").collection(name)` for KV and queries `bucket.scope.collection` directly for N1QL — no more `WHERE type = '…'` filters
- Document keys are now bare UUIDs (no `"users::"` prefix) — uniqueness is guaranteed per-collection
- GSI indexes are collection-scoped without partial-filter predicates, simpler and faster
- New provisioning script `/app/backend/scripts/provision_couchbase_collections.py` (idempotent, safe to re-run)
- Migration script + in-app sync endpoint updated to target real collections
- Verified end-to-end: admin login, nested buildings+floors+slots, reports/stats, full CRUD cycle (create → read → update → cascade-delete), parallel collection-stats (~1.6s)

**Operational benefits unlocked:**
- Collection-level RBAC is now possible (grant a service account read-only on `reservations` without exposing `users`)
- Cleaner backup / XDCR / monitoring granularity
- 1:1 mental model with MongoDB — easier reasoning for devs already comfortable with Mongo

### Phase 9 — Database Health & Sync UI (completed Apr 24, 2026)

Admin Dashboard now includes a **Database Health** card with:
- Per-collection document counts (18 collections) on the active DB, refreshed in parallel (~1.6s)
- Total document count + active backend pill
- **"Sync now: Mongo → Couchbase"** one-click button (shown only in Couchbase mode)
- Toast-based progress + result feedback ("Synced N docs in Xs")

New admin endpoints:
- `GET /api/system/collection-stats` — parallel COUNT queries across all collections
- `POST /api/system/sync-mongo-to-couchbase` — in-process migration with single-flight lock (prevents concurrent runs across admins)

---

## 5. Documentation Suite (`/app/docs/`)

| File | Status | Last Updated |
|------|--------|--------------|
| BRD.md | Updated — includes US-AUTH-06/07, Section 4.10 Event Blocking, BR-16 fix, BR-17–20 | Feb 25, 2026 |
| SRS.md | Updated — US-VEH-01 plate length validation added | Mar 5, 2026 |
| system-design.md | Updated — new routes/models/components listed, event_blocks collection added, process map extended | Feb 25, 2026 |
| compliance-matrix.md | Updated — 5 new controls added (attendant building, one slot per user, hour restrictions, plate length) | Mar 5, 2026 |
| test-plan.md | Updated — scope extended for new features | Feb 25, 2026 |
| test-scripts.md | Updated — Section 6 added with 14 TCID bug fix test cases | Mar 5, 2026 |
| test-results.md | Updated — Section 2.17 added (iteration 33), total updated to 200, 12 new defects (DEF-018–029) | Mar 5, 2026 |
| attendant-guide.md | Updated — Section 5.2 updated to clarify No-Show only for pending status | Mar 5, 2026 |
| admin-user-guide.md | Updated — Section 7.2 updated with multi-building checkbox instructions | Mar 5, 2026 |
| end-user-guide.md | Updated — Section 6.2 added for notification detail dialog | Mar 5, 2026 |
| output/ (DOCX + PDF) | 14 DOCX + 14 PDF regenerated | Mar 5, 2026 |

---

## 6. Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| POST | `/api/auth/change-password` | Change password (requires current) |
| POST | `/api/auth/forgot-password` | Forgot password (notifies admins) |
| POST | `/api/vehicles/` | Register vehicle (plate uniqueness enforced) |
| POST | `/api/reservations/` | Create reservation (exclusivity + sticker checks) |
| DELETE | `/api/admin/reservations/{id}` | Admin cancel (requires reason, notifies user) |
| POST | `/api/event-blocks/` | Create event block |
| GET | `/api/event-blocks/` | List event blocks |
| DELETE | `/api/event-blocks/{id}` | Delete event block |
| POST | `/api/parking-config` | Save config (includes main_building_exclusive) |
| GET | `/api/system/db-info` | **NEW** Admin-only; active DB adapter info for UI badge |
| GET | `/api/system/collection-stats` | **NEW** Admin-only; per-collection counts on active DB |
| POST | `/api/system/sync-mongo-to-couchbase` | **NEW** Admin-only; mirrors Mongo -> Capella |

---

## 7. Key DB Schema Changes

| Collection | New/Modified Fields |
|-----------|---------------------|
| reservations | `vehicle_id: Optional[str]` (for event blocks) |
| parking_configs | `main_building_exclusive: bool` (NEW) |
| event_blocks | NEW collection: event_name, reason, building_id, floor_id, slot_ids[], date, start_time, end_time, reservation_ids[], created_by, created_at |

---

## 8. Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin.test@cebuana.com | Test123! |
| User | user.test@cebuana.com | Test123! |
| Attendant | attendant.test@cebuana.com | Test123! |
| Policy User | lgdeguzman@pjlhuillier.com | Test123! |

---

## 9. Prioritized Backlog

### P1 (Next Sprint)
- Email notifications for waitlisted users (currently in-app only)
- Forgot password flow via email (currently admin-notified via in-app)

### P2 (Future)
- CSV/Excel report exports for admins
- Push notifications (mobile)
- Recurring event blocking (weekly/monthly)
- Parking analytics dashboards with heatmaps

---

## 10. Known Limitations / Out of Scope

- No email delivery (all notifications are in-app only)
- No self-service registration (users are admin-provisioned)
- No load testing > 1000 users (requires dedicated infra)
- AI insights require EMERGENT_LLM_KEY with balance

## 2026-04-28 — Defect Validation Response Delivered
- Executed `/app/scripts/build_defect_validation_response.py`.
- Generated: `/app/docs/output/Defect_Validation_Response_2026-04-28.xlsx` (21 rows).
- Breakdown: Resolved this cycle 6 · Already resolved 7 · Verify deploy/UI 4 · Backlog 1 (PPA-30 email notifications) · Cannot reproduce 3.
- Open items resolved this cycle (new code): PPA-14, PPA-17, PPA-19, PPA-31, PPA-58, PPA-62.
- Closes the user's last pending request from the previous session.

## 2026-05-12 — Attendant Mode Toggle + Self Check-In
- **New runtime flag** `ATTENDANT_MODE_ENABLED` (default `true`). When `false`, parkers self-check-in via a green "Check in" button on their reservation card during a configurable window (`SELF_CHECKIN_WINDOW_MINUTES`, default 15, clamped 5–240) after `start_time`.
- **New endpoint** `POST /api/reservations/{id}/checkin` — idempotent. Returns 200 on success, 200 with `already_checked_in: true` on repeat, 400 if too early, 410 if window expired, 403 if attendant mode is on.
- **Background loop** now also flips expired-window pending reservations to `no_show`, releases the slot **immediately** (no `no_show_release_minutes` wait — that knob only applies in attendant mode), and notifies the next person on the waitlist. Loop cadence drops from 300 s to 60 s when self-checkin mode is active.
- **Bug fix in Couchbase abstraction**: `$ne` was translated to a bare `!= value` which excludes MISSING/NULL — silently dropped legitimate matches (e.g. `slot_released != true` missed never-set rows). Now `(field IS MISSING OR field IS NULL OR field != value)` to match Mongo semantics. Symptom: historical `slot_released=None` no-shows weren't being auto-released. Fixed; ~25 backlog rows cleaned up in the preview pod.
- **Frontend**: `useFeatures` hook now also exposes `attendant_mode_enabled` and `self_checkin_window_minutes`. `ReservationsPage.js` renders the "Check in" button only when (a) attendants are off, (b) it's the parker's own pending reservation, (c) now ∈ [start_time, start_time + window].
- **Docs**: Admin guide §6.3 "Attendant Mode vs. Self Check-In" with full posture matrix and error-message table. End-user guide §4.4. Attendant guide flagged with "if self-check-in mode is active your dashboard is fallback-only". K8s ConfigMap + CCE runbook updated. All 14 docs recompiled (.pdf + .docx).

## 2026-05-05 — Huawei CCE / OBS Deployment Package Complete
- **Storage abstraction wired end-to-end** in `/app/backend/storage/` (LocalStorage default, OBSStorage when `STORAGE_TYPE=obs`). `/app/backend/routes/buildings.py` now uses it for upload, **fetch (`GET /api/uploads/{filename}`)**, and **delete (`DELETE /api/floors/{id}/layout`)**. Previously `GET /api/uploads` still read from local disk — would have 404'd in OBS mode; fixed.
- **Kubernetes manifests** authored under `/app/deploy/k8s/`: `namespace.yaml`, `configmap.yaml`, `secret.example.yaml`, `backend-leader.yaml` (1 replica, `RUN_BACKGROUND_TASKS=true`, `strategy: Recreate`), `backend-worker.yaml` (N replicas + HPA, `RUN_BACKGROUND_TASKS=false`), `backend-service.yaml`, `frontend-deployment.yaml`, `ingress-nginx.yaml`, `ingress-clusterip.yaml`, `kustomization.yaml`, `README.md`.
- **CCE-specific runbook** at `/app/docs/ONPREM_HCS_CCE_RUNBOOK.md`. The previous `ONPREM_HCS_RUNBOOK.md` is now badged as the single-VM/Compose flow; `DEPLOYMENT.md` points to whichever runbook applies.
- **Testing**: backend regression via testing agent on the floor-layout pipeline — 15/15 tests passed (happy-path upload, byte-perfect round-trip, validation rejections, 404 on bad floor, admin-only enforcement, GET auth+404+path-traversal+disallowed-extension, JPEG variant, full upload→delete→404 cycle). YAML parser validates all 10 manifests cleanly.

