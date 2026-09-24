# Compliance & Traceability Matrix
**Related:** [System Design](system-design.md) | [SRS](../02-system-requirements/SRS.md) | [BRD](../01-business-requirements/BRD.md)

---

## 1. Requirements-to-Implementation Traceability

This matrix maps every Business Requirement (BR) and User Story (US) from the [BRD](../01-business-requirements/BRD.md) to its concrete implementation artifacts, ensuring full coverage.

### 1.1 Authentication & Account Management

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-AUTH-01 | User login | `routes/auth.py::login` | `LoginPage.js` | users, sessions | TC-AUTH-01 | Implemented |
| US-AUTH-02 | First-login password change | `routes/auth.py::change_password` | `ForcePasswordChange.js` | users | TC-AUTH-02 | Implemented |
| US-AUTH-03 | 30-min session timeout | `auth/security.py::create_access_token` | `AuthContext.js` (401 handler) | sessions | TC-AUTH-03 | Implemented |
| US-AUTH-04 | Secure logout | `routes/auth.py::logout` | `AuthContext.js::logout` | sessions | TC-AUTH-04 | Implemented |
| US-AUTH-05 | Admin password reset | `routes/users.py::admin_reset_password` | `UserManagement.js` | users | TC-AUTH-05 | Implemented |
| US-AUTH-06 | Self-service password change | `routes/auth.py::change_password` (verifies current password, not first-login) | `ProfilePage.js` (change password section) | users | TC-AUTH-11 | Implemented |
| US-AUTH-07 | Forgot password | `routes/auth.py::forgot_password` (notifies admins, prevents enumeration) | `ForgotPassword.jsx`, `LoginPage.js` | notifications | TC-AUTH-12, TC-AUTH-13 | Implemented |

### 1.2 Vehicle Management

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-VEH-01 | Register vehicle | `routes/vehicles.py::create_vehicle` (with plate uniqueness check, length validation 2-15 chars) | `VehiclesPage.js` | vehicles | TC-VEH-01, TC-VEH-07, TC-VEH-08 | Implemented |
| US-VEH-02 | Manage multiple vehicles | `routes/vehicles.py::get_vehicles, delete_vehicle` | `VehiclesPage.js` | vehicles | TC-VEH-02 | Implemented |
| US-VEH-03 | Dashboard vehicle display | — | `UserDashboard.js` | vehicles | TC-VEH-03 | Implemented |

### 1.3 Parking Reservation

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-RES-01 | Book parking slot | `routes/reservations.py::create_reservation` | `BookingPage.js` | reservations | TC-RES-01 | Implemented |
| US-RES-02 | Multi-date booking | `routes/reservations.py::create_reservation` (loop) | `BookingPage.js` (date picker) | reservations | TC-RES-02 | Implemented |
| US-RES-03 | View available slots | `routes/buildings.py::get_available_slots` | `BookingPage.js` (slot grid) | parking_slots, reservations | TC-RES-03 | Implemented |
| US-RES-04 | QR code | `routes/reservations.py::get_reservation_qr` | `ReservationsPage.js` | reservations | TC-RES-04 | Implemented |
| US-RES-05 | Cancel reservation | `routes/reservations.py::cancel_reservation` | `ReservationsPage.js`, `UserDashboard.js` | reservations | TC-RES-05 | Implemented |
| US-RES-06 | Active/History tabs | — | `UserDashboard.js` | reservations | TC-RES-06 | Implemented |
| US-RES-07 | Default booking times | `routes/parking_config.py` | `BookingPage.js` | parking_configs, users | TC-RES-07 | Implemented |
| US-RES-08 | Profile booking preferences | `routes/auth.py::update_booking_preferences` | `ProfilePage.js` | users | TC-RES-08 | Implemented |
| US-RES-09 | Zone building count | `routes/zones.py::get_user_building_assignments` | `UserDashboard.js` | zones | TC-RES-09 | Implemented |
| US-RES-10 | Notifications | `routes/notifications.py` | `NotificationBell.js` | notifications | TC-RES-10 | Implemented |
| US-RES-11 | Hourly slot timeline | `routes/waitlist.py::get_floor_timeline` | `BookingPage.js` (timeline grid) | parking_slots, reservations | TC-RES-11 | Implemented |
| US-RES-12 | Waitlist | `routes/waitlist.py` (join, leave, status, count) | `BookingPage.js` (waitlist button) | waitlist_entries, notifications | TC-RES-12 | Implemented |

### 1.4 Zone & Building Rules

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-ZONE-01 | Main building booking | `routes/reservations.py` (no extra validation) | `BookingPage.js` | users, reservations | TC-ZONE-01 | Implemented |
| US-ZONE-02 | Zone building access | `routes/zones.py::get_user_building_assignments` | `BookingPage.js` | zones | TC-ZONE-02 | Implemented |
| US-ZONE-03 | External building rules | `routes/reservations.py` (single-day + reason) | `BookingPage.js` | zones, reservations | TC-ZONE-03 | Implemented |

### 1.5 Admin — User Management

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-ADM-01 | Create user | `routes/users.py::create_user` | `UserManagement.js` | users | TC-ADM-01 | Implemented |
| US-ADM-02 | Bulk upload | `routes/users.py::bulk_upload_users` | `UserManagement.js` | users, zones | TC-ADM-02 | Implemented |
| US-ADM-03 | Block/unblock | `routes/users.py::block_user, unblock_user` | `UserManagement.js` | users | TC-ADM-03 | Implemented |
| US-ADM-04 | Main building assignment | `routes/users.py::assign_main_building` | `UserManagement.js` | users | TC-ADM-04 | Implemented |
| US-ADM-05 | VIP/Group Head tags | `routes/users.py::update_user_tags` | `UserManagement.js` | users | TC-ADM-05 | Implemented |
| US-ADM-06 | Default booking times | `routes/users.py::update_user` | `UserManagement.js` | users | TC-ADM-06 | Implemented |
| US-ADM-07 | Advanced filters | — | `UserManagement.js` | — | TC-ADM-07 | Implemented |
| US-ADM-08 | Bulk modify | `routes/users.py::bulk_set_main_building, bulk_assign_zone` | `UserManagement.js` | users, zones | TC-ADM-08 | Implemented |
| US-ADM-09 | Template download | `routes/templates.py::download_users_template` | `UserManagement.js` | — | TC-ADM-09 | Implemented |
| US-ADM-10 | Audit timestamps | `routes/users.py` (created_at/updated_at) | `UserManagement.js` | users | TC-ADM-10 | Implemented |
| US-ADM-11 | Waitlist configuration | `routes/parking_config.py` (waitlist_enabled, window) | `ParkingConfig.js` | parking_configs | TC-ADM-11 | Implemented |
| US-ADM-12 | Job Family field | `routes/users.py` (CRUD + bulk upload) | `UserManagement.js` | users | TC-ADM-12 | Implemented |

### 1.6 Admin — Building & Slot Management

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-BLD-01 | Create building | `routes/buildings.py::create_building` | `BuildingManagement.js` | buildings | TC-BLD-01 | Implemented |
| US-BLD-02 | Add floors with layout | `routes/buildings.py::add_floor, upload_floor_layout` | `BuildingManagement.js` | floors | TC-BLD-02 | Implemented |
| US-BLD-03 | Add slots | `routes/buildings.py::add_slots_to_floor` | `BuildingManagement.js` | parking_slots | TC-BLD-03 | Implemented |
| US-BLD-04 | Block/unblock slots | `routes/buildings.py::update_slot_status` | `BuildingManagement.js` | parking_slots | TC-BLD-04 | Implemented |
| US-BLD-05 | Delete slots | `routes/buildings.py::delete_slot` | `BuildingManagement.js` | parking_slots | TC-BLD-05 | Implemented |
| US-BLD-06 | Available slots | `routes/buildings.py::get_available_slots` | `BookingPage.js` | parking_slots, reservations | TC-BLD-06 | Implemented |

### 1.7 Admin — Zone Management

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-ZN-01 | Create zone | `routes/zones.py::create_zone` | `ZoneManagement.js` | zones | TC-ZN-01 | Implemented |
| US-ZN-02 | Assign users | `routes/zones.py::update_zone` | `ZoneManagement.js` | zones | TC-ZN-02 | Implemented |
| US-ZN-03 | Manage buildings | `routes/zones.py::update_zone` | `ZoneManagement.js` | zones | TC-ZN-03 | Implemented |

### 1.8 Admin — Parking Configuration

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-CFG-01 | Default parking hours | `routes/parking_config.py::save_parking_config` | `ParkingConfig.js` | parking_configs | TC-CFG-01 | Implemented |
| US-CFG-02 | Booking window | `routes/parking_config.py` | `ParkingConfig.js` | parking_configs | TC-CFG-02 | Implemented |
| US-CFG-03 | Release time | `routes/parking_config.py` | `ParkingConfig.js` | parking_configs | TC-CFG-03 | Implemented |
| US-CFG-04 | Auto no-show release | `services/background.py::auto_mark_no_shows` | `ParkingConfig.js` | parking_configs, reservations | TC-CFG-04 | Implemented |
| US-CFG-05 | Main building exclusivity | `routes/parking_config.py` (`main_building_exclusive` field); `routes/reservations.py::create_reservation` (exclusivity check) | `ParkingConfig.js` (toggle) | parking_configs | TC-CFG-05 | Implemented |

### 1.9 Admin — Reports & Analytics

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-RPT-01 | Dashboard stats | `routes/reports.py::get_stats` | `AdminDashboard.js`, `Reports.js` | reservations | TC-RPT-01 | Implemented |
| US-RPT-02 | Date/building filter | `routes/reports.py::get_stats` (query params) | `Reports.js` | reservations | TC-RPT-02 | Implemented |
| US-RPT-03 | AI insights | `routes/reports.py::generate_ai_insights` | `Reports.js` | ai_insights | TC-RPT-03 | Implemented |
| US-RPT-04 | Insights history | `routes/reports.py::get_insights_history` | `Reports.js` | ai_insights | TC-RPT-04 | Implemented |
| US-RPT-05 | Admin reservations + cancellation with reason | `routes/admin.py::get_admin_reservations, admin_cancel_reservation` (requires reason, sends notification) | `AdminReservations.jsx` | reservations, notifications | TC-RPT-05, TC-INT-05 | Implemented |

### 1.10 Admin — Event Blocking

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-EVT-01 | Block slots for event | `routes/event_blocks.py::create_event_block` | `EventBlocking.jsx` | event_blocks, reservations | TC-EVT-01 | Implemented |
| US-EVT-02 | List event blocks | `routes/event_blocks.py::get_event_blocks` | `EventBlocking.jsx` | event_blocks | TC-EVT-02 | Implemented |
| US-EVT-03 | Delete event block | `routes/event_blocks.py::delete_event_block` | `EventBlocking.jsx` | event_blocks, reservations | TC-EVT-03 | Implemented |

### 1.12 Admin — Site Customization

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-SITE-01 | Login page editor | `routes/site_content.py` | `AdminSettings.js` | site_content | TC-SITE-01 | Implemented |

### 1.13 Admin — Building Policies

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-POL-01 | Create building policy | `routes/building_policies.py::create_building_policy` | `BuildingPolicies.js` | building_policies | TC-POL-01 | Implemented |
| US-POL-02 | Sticker requirement | `routes/reservations.py::create_reservation` (vehicle plate check) | `BookingPage.js` | slot_registrations, vehicles | TC-POL-02 | Implemented |
| US-POL-03 | Slot registration | `routes/building_policies.py::create_slot_registration` | `BuildingPolicies.js` | slot_registrations | TC-POL-03 | Implemented |
| US-POL-04 | Open floors | `routes/reservations.py` (open_floor_ids bypass) | `BuildingPolicies.js` | building_policies | TC-POL-04 | Implemented |
| US-POL-05 | Zone-filtered user selection | `routes/building_policies.py` + frontend filtering | `BuildingPolicies.js` | zones, users | TC-POL-05 | Implemented |
| US-POL-06 | Vehicle dropdown | `routes/vehicles.py::get_vehicles` | `BuildingPolicies.js` | vehicles | TC-POL-06 | Implemented |

### 1.14 Parking Attendant

| Req ID | Requirement | Backend Artifact | Frontend Artifact | DB Collection | Test Coverage | Status |
|--------|------------|-----------------|-------------------|---------------|---------------|--------|
| US-ATT-01 | Daily reservations | `routes/attendant.py::get_attendant_daily_reservations` | `AttendantDashboard.js` | reservations | TC-ATT-01 | Implemented |
| US-ATT-02 | Confirm arrival | `routes/reservations.py::confirm_reservation` | `AttendantDashboard.js` | reservations | TC-ATT-02 | Implemented |
| US-ATT-03 | Report no-show | `routes/attendant.py::report_no_show` | `AttendantDashboard.js` | reservations, users, notifications | TC-ATT-03 | Implemented |
| US-ATT-04 | Today button | — | `AttendantDashboard.js` | — | TC-ATT-04 | Implemented |
| US-ATT-05 | QR scan | `routes/reservations.py::scan_qr_lookup` | `ScanPage.js` | reservations | TC-ATT-05 | Implemented |
| US-ATT-06 | Summary cards | — | `AttendantDashboard.js` | reservations | TC-ATT-06 | Implemented |

---

## 2. Business Rules Compliance

| Rule ID | Rule | Implementation | Enforcement Point | Verified |
|---------|------|---------------|-------------------|----------|
| BR-01 | Vehicle required for booking | `BookingPage.js` validates vehicle selection; `create_reservation` checks vehicle exists | Frontend + Backend | Yes |
| BR-02 | No double-booking | Compound index `(slot_id, date, status)`. Backend checks existing reservations before insert | Backend (atomic) | Yes |
| BR-03 | External booking: single-day + reason | `create_reservation` validates `is_external_booking` → enforces `len(dates) == 1` and `reason` | Backend | Yes |
| BR-04 | Blocked users cannot access | `login` rejects blocked users; `create_reservation` checks `is_blocked` | Backend (auth + business) | Yes |
| BR-05 | No-show only for today/past | `report_no_show` checks `reservation.date <= today`. Records `no_show_at` timestamp. Frontend hides buttons for future dates | Backend + Frontend | Yes |
| BR-06 | 30-min session expiry | `JWT_EXPIRATION_HOURS=0.5` in `.env`. Cookie `max-age=1800`. JWT `exp` claim validated | Backend (JWT) | Yes |
| BR-07 | VIP/Group Head privileges | `tags` field on users. `create_reservation` skips single-day restriction for VIP | Backend | Yes |
| BR-08 | Maintenance slots not bookable | `get_available_slots` excludes `status: maintenance`. Frontend marks as unavailable | Backend + Frontend | Yes |
| BR-09 | Booking window enforcement | `parking_configs.booking_window_days`. Frontend limits calendar max date | Frontend + Config | Yes |
| BR-10 | First-login password change | `must_change_password` flag. `AuthContext.js` shows `ForcePasswordChange` dialog | Backend + Frontend | Yes |
| BR-11 | Waitlist notification expiry | `check_waitlist_expiry()` background task. `notified_at` + window minutes | Backend | Yes |
| BR-12 | No-show release based on no_show_at | `auto_mark_no_shows()` sets `no_show_at`. Slot release = `no_show_at` + configured minutes | Backend | Yes |
| BR-13 | Plate number uniqueness | `create_vehicle` checks `vehicles` collection for existing plate before insert. Returns 400 if duplicate | Backend | Yes |
| BR-14 | Vehicle-level sticker validation | `create_reservation` checks `slot_registrations` for matching `vehicle_plate` + `building_id`. User registration alone is insufficient | Backend | Yes |
| BR-15 | Vehicle-to-slot registration for non-open floors | `create_reservation` checks `slot_registrations` for matching `slot_id` + `user_id` + `vehicle_plate` on non-open floors | Backend | Yes |
| BR-16 | Admin cancellation requires reason; parker notified | `routes/admin.py::admin_cancel_reservation` requires `reason` body field; creates in-app notification for parker containing reason; triggers waitlist | Backend + Notifications | Yes |
| BR-17 | Main building exclusivity (admins exempt) | `routes/reservations.py::create_reservation` checks `parking_configs.main_building_exclusive`; compares `user.main_building` vs `building_id`; admin role bypasses check | Backend | Yes |
| BR-18 | Event blocks create confirmed reservations | `routes/event_blocks.py::create_event_block` creates one reservation per slot with `booking_type: "event_block"`, `status: "confirmed"` to prevent double-booking | Backend | Yes |
| BR-19 | Self-service password change requires current password | `routes/auth.py::change_password` verifies `current_password` hash via bcrypt before updating. Returns 400 if incorrect | Backend | Yes |
| BR-20 | Forgot password notifies admins; prevents email enumeration | `routes/auth.py::forgot_password` looks up user, creates notification for all admins if found. Always returns 200 regardless of email existence | Backend | Yes |

---

## 3. Non-Functional Requirements Compliance

| NFR ID | Requirement | Target | Implementation | Verified |
|--------|------------|--------|---------------|----------|
| NFR-01 | Mobile responsive | 375px+ | TailwindCSS responsive classes, mobile bottom nav | Yes |
| NFR-02 | Page load < 3s | < 3 sec | React SPA, `Promise.allSettled` parallel fetching, retry logic | Yes |
| NFR-03 | API response < 500ms | < 500ms (p95) | 25 MongoDB indexes, Motor async driver, connection pooling (maxPool=50) | Yes |
| NFR-04 | 200+ concurrent users | 200+ | Stateless JWT, async I/O, DB connection pooling | Designed |
| NFR-05 | Data security | Multi-layer | HttpOnly cookies, bcrypt, CSP/HSTS/X-Frame headers, rate limiting, device fingerprinting, RBAC. Password inputs use uncontrolled components (`useRef`) to prevent plaintext credential exposure in the DOM (CWE-312 mitigation) | Yes |
| NFR-06 | 99.9% uptime | 99.9% | Container orchestration, health checks, graceful shutdown, supervisor auto-restart | Designed |
| NFR-07 | Browser support | Latest 2 versions | React 19, ES2020 target, no browser-specific APIs | Yes |

---

## 4. Security Controls Matrix

| Control | Category | Implementation | Layer |
|---------|----------|---------------|-------|
| Authentication | Access Control | JWT tokens with 30-min expiry | Backend |
| Session Management | Access Control | DB-backed sessions with device fingerprinting | Backend |
| Authorization (RBAC) | Access Control | `get_current_user`, `require_admin`, `require_attendant` guards | Backend |
| Password Hashing | Data Protection | bcrypt with auto-salting | Backend |
| HttpOnly Cookies | Transport Security | `httponly=True, secure=True, samesite=lax` | Backend |
| HTTPS Enforcement | Transport Security | HSTS header (`max-age=31536000; includeSubDomains`) | Middleware |
| Content Security Policy | Injection Prevention | CSP header restricting script/style/img sources | Middleware |
| Clickjacking Protection | Injection Prevention | `X-Frame-Options: DENY` | Middleware |
| XSS Protection | Injection Prevention | `X-XSS-Protection: 1; mode=block` | Middleware |
| Rate Limiting | Abuse Prevention | 5 requests/minute on login endpoint | Backend |
| Input Validation | Data Integrity | Pydantic models for all request bodies | Backend |
| File Upload Validation | Data Integrity | Extension whitelist, size limit (10MB), content-type check | Backend |
| Path Traversal Prevention | Data Integrity | Regex sanitization + `resolve().is_relative_to()` check | Backend |
| Permission Boundary | Privacy | Camera, microphone, geolocation disabled via Permissions-Policy | Middleware |
| Blocked Account Enforcement | Authentication | Login endpoint checks `is_blocked` flag before issuing session token. Blocked users receive 403 regardless of credential validity | Backend |
| DOM Password Exposure Prevention (CWE-312) | Data Protection | All password inputs use uncontrolled React components (`useRef`); password values are never stored in component state or accessible in the DOM | Frontend |
| Attendant Building Validation | Data Integrity | Attendants must have at least one assigned building; backend validation prevents creation without building | Backend |
| One Slot Per User Per Building | Data Integrity | Users can only be registered to one slot per building for policy-based buildings | Backend |
| Hour Selection Restrictions | Business Logic | Past hours and hours outside parking config are disabled on booking page | Frontend |
| Vehicle Plate Length Validation | Data Integrity | Plate numbers must be 2-15 characters (Pydantic validators) | Backend |

---

*Previous: [ERD](diagrams/erd.md) | Back to: [System Design](system-design.md) | Next: [Test Plan](../04-testing/test-plan.md)*
