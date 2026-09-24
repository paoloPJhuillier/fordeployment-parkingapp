# System Requirements Specification (SRS)
**Project:** Cebuana Lhuillier Parking Reservation System  
**Version:** 2.1  
**Date:** March 5, 2026  
**Related:** [Business Requirements Document](../01-business-requirements/BRD.md)

---

## 1. Purpose

This document maps each business requirement (user story) from the [BRD](../01-business-requirements/BRD.md) to its system-level implementation, detailing the API endpoints, database operations, UI components, and validation logic.

---

## 2. Functional Requirements Traceability

### 2.1 Authentication & Account Management

| User Story | System Implementation |
|------------|----------------------|
| **US-AUTH-01** Login | **API:** `POST /api/auth/login` — Validates email/password with bcrypt. Checks `is_blocked` flag — returns 403 `"Your account has been blocked. Please contact your administrator."` if true. Creates JWT token (30min TTL), issues HttpOnly secure cookie, creates DB session record with device fingerprint. **UI:** `/login` page with frontend validation for empty fields (toast error shown before API call); role-based redirect (user→`/dashboard`, admin→`/admin`, attendant→`/attendant`). **DB:** `users.password` (bcrypt hash), `sessions` collection. |
| **US-AUTH-02** First-login password change | **API:** `POST /api/auth/change-password` — Validates current password, hashes new one, clears `must_change_password` flag. **UI:** `ChangePassword` dialog triggered by `must_change_password=true` in auth context. **DB:** `users.must_change_password` boolean field. |
| **US-AUTH-03** Session timeout (30min) | **Config:** `JWT_EXPIRATION_HOURS=0.5` in `.env`. **Implementation:** JWT `exp` claim set to `now + 30min`. Cookie `max-age=1800`. Backend validates `exp` on every authenticated request via `get_current_user` dependency. Returns 401 on expiry. |
| **US-AUTH-04** Logout | **API:** `POST /api/auth/logout` — Revokes session in DB, clears auth cookie. **UI:** Logout button in sidebar/header calls API and redirects to `/login`. |
| **US-AUTH-05** Admin password reset | **API:** `PUT /api/users/{user_id}/reset-password` — Admin-only. Hashes new password, sets `must_change_password=true`. **UI:** Reset Password dialog in User Management actions dropdown. |
| **US-AUTH-06** Self-service password change | **API:** `POST /api/auth/change-password` — Authenticated user submits `current_password` + `new_password`. Backend verifies current password hash (bcrypt), rejects with 400 if incorrect. Also rejects with 400 if `new_password` matches the current password hash (same-password prevention). Hashes and saves new password. **UI:** "Change Password" section on `/profile` page with current/new/confirm fields. **DB:** `users.password` updated. |
| **US-AUTH-07** Forgot password | **API:** `POST /api/auth/forgot-password` — Accepts `email`. Looks up user; if found, creates an in-app notification for all admin users. Always returns 200 regardless of whether the email exists (prevents email enumeration). **UI:** "Forgot Password?" link on login page opens `ForgotPassword.jsx` form. **DB:** `notifications` collection (admin notification created). |

### 2.2 Vehicle Management

| User Story | System Implementation |
|------------|----------------------|
| **US-VEH-01** Register vehicle | **API:** `POST /api/vehicles` — Creates vehicle with `plate_number`, `make`, `model`, `color`, `building_id`. Auto-links to authenticated user via `user_id`. **Validation:** Plate number normalized to uppercase, checked for uniqueness across `vehicles` collection. **Length validation:** Minimum 2 characters, maximum 15 characters (Pydantic validators). Duplicate plates rejected with 400 error. **DB:** `vehicles` collection. |
| **US-VEH-02** Manage multiple vehicles | **API:** `GET /api/vehicles` (list), `DELETE /api/vehicles/{id}` (remove). Filtered by authenticated user's ID. **UI:** `/vehicles` page with vehicle cards, add/delete functionality. |
| **US-VEH-03** Dashboard vehicle display | **UI:** `UserDashboard.js` "My Vehicles" section shows first vehicle card with "Manage >" link. |

### 2.3 Parking Reservation

| User Story | System Implementation |
|------------|----------------------|
| **US-RES-01** Book parking slot | **API:** `POST /api/reservations` — Accepts `building_id`, `floor_id`, `slot_id`, `vehicle_id`, `dates[]`, `start_time`, `end_time`, `booking_type`, `reason`. Creates one reservation per date. Validates slot availability atomically (checks `slot_id+date+status` compound index). Generates QR token. **Policy enforcement:** For buildings with a `requires_sticker` policy, validates that the selected vehicle's plate has an active `slot_registration` in the building. For non-open floors, the vehicle must be registered to the specific slot being booked. **UI:** `/book` page with building→floor→date→slot→vehicle flow. **DB:** `reservations` collection with compound index on `(slot_id, date, status)`. |
| **US-RES-02** Multi-date booking | **API:** `POST /api/reservations` accepts `dates: List[str]`. Backend loops over each date, creates individual reservation documents. **UI:** Calendar picker allows selecting multiple discrete dates (not range). |
| **US-RES-03** View available slots | **API:** `GET /api/slots/available?floor_id=X&date=Y` — Returns slots not booked for that date (excludes maintenance status). **UI:** Slot grid on booking page, color-coded (available=green, taken=red, maintenance=gray). |
| **US-RES-04** QR code | **API:** `GET /api/reservations/{id}/qr` — Returns QR code image (base64 PNG). Generated using `qrcode` library with reservation `qr_token`. **API:** `GET /api/scan/{qr_token}` — Returns reservation details (attendant/admin only). |
| **US-RES-05** Cancel reservation | **API:** `PUT /api/reservations/{id}/cancel` — Sets status to `cancelled`. Sends notification to user. **UI:** Cancel (X) button on active reservation cards. |
| **US-RES-06** Active/History tabs | **UI:** `UserDashboard.js` Reservations section with "Active" (today + future, non-cancelled) and "History" (past + cancelled) tabs. Backend returns all user reservations; filtering is client-side. |
| **US-RES-07** Default booking times | **Priority:** User preference → Admin per-user setting → Building config → System default (08:00-18:00). **API:** `GET /api/auth/me` returns `default_start_time`/`default_end_time`. Building config from `GET /api/parking-config/{building_id}`. |
| **US-RES-08** Profile booking preferences | **API:** `PUT /api/auth/booking-preferences` — Updates `default_start_time`/`default_end_time` on user record. **UI:** `/profile` page with time inputs and Save/Reset buttons. |
| **US-RES-09** Zone building count | **UI:** `UserDashboard.js` "Buildings" stat card. Calls `GET /api/zones/user-buildings` to get zone-filtered building IDs, displays count. Falls back to total if no zone. |
| **US-RES-10** Notifications | **API:** `GET /api/notifications` (list), `GET /api/notifications/unread-count`, `PUT /api/notifications/{id}/read`, `PUT /api/notifications/read-all`. **UI:** `NotificationBell` component in header with badge count and dropdown panel. **Triggers:** Booking confirmation, cancellation, no-show notification, waitlist slot available. |
| **US-RES-11** Hourly slot timeline | **API:** `GET /api/slots/timeline?building_id=X&floor_id=Y&date=Z` — Returns per-slot hourly availability (6AM–10PM). Each hour marked as booked or available based on active reservations. **UI:** Interactive hourly timeline grid on `BookingPage.js`, color-coded cells, shows after slot selection. |
| **US-RES-12** Waitlist | **API:** `POST /api/waitlist/join` — Joins user to waitlist for building+date. `GET /api/waitlist/status` — Check if user is on waitlist. `GET /api/waitlist/count` — Count of waiting users. `DELETE /api/waitlist/{entry_id}` — Leave waitlist. **Background:** `check_waitlist_expiry()` runs every 60 seconds, expires notified entries past the configured window, and notifies the next user. **DB:** `waitlist_entries` collection with position-ordered queue. |

### 2.4 Zone & Building Rules

| User Story | System Implementation |
|------------|----------------------|
| **US-ZONE-01** Main building booking | **API:** `POST /api/reservations` — If `booking_type=main`, no additional validation. User's `main_building` compared to `building_id`. |
| **US-ZONE-02** Zone building booking | **API:** `GET /api/zones/user-buildings` — Returns all building IDs in user's assigned zones. Frontend filters visible buildings to this list. |
| **US-ZONE-03** External building (within zone) | **API:** `POST /api/reservations` — If `booking_type=external`: enforces single date only, requires `reason` field. Backend validates building is in user's zone but not their main building. |

### 2.5 Admin — User Management

| User Story | System Implementation |
|------------|----------------------|
| **US-ADM-01** Create user | **API:** `POST /api/users` — Admin-only. Creates user with bcrypt password, all profile fields, `must_change_password=true`. **DB:** `users` collection with unique `email` index. |
| **US-ADM-02** Bulk upload | **API:** `POST /api/users/bulk-upload` — Accepts CSV/Excel file + default password. Parses `email`, `first_name`, `last_name`, `company`, `role`, `main_building` (resolved by name), `zone` (resolved by name). Batch email check ($in query), batch zone assignment ($addToSet). Returns `created`, `skipped`, `zone_assignments`, `errors`. **Template:** `GET /api/templates/users`. |
| **US-ADM-03** Block/unblock | **API:** `PUT /api/users/{id}/block`, `PUT /api/users/{id}/unblock` — Toggles `is_blocked`. Blocked users rejected at login. |
| **US-ADM-04** Main building assignment | **API:** `PUT /api/users/{id}/main-building` — Sets `main_building` field. Also available via bulk: `POST /api/users/bulk-set-building`. |
| **US-ADM-05** VIP/Group Head tags | **API:** `PUT /api/users/{id}/tags` — Sets `tags[]` array (e.g., `["vip", "group_head"]`). Displayed as badges in user table. |
| **US-ADM-06** Default booking times per user | **API:** `PUT /api/users/{id}` — Admin update includes `default_start_time`/`default_end_time`. Shown in user edit dialog. |
| **US-ADM-07** Advanced filters | **UI:** `UserManagement.js` — Dropdown filters: Role, Company, Zone (with "No Zone"), Main Building (with "No Building"). Text search across name/email/company. Count badge shows filtered results. |
| **US-ADM-08** Bulk modify | **API:** `POST /api/users/bulk-set-building` (body: `user_ids[]`, `main_building`), `POST /api/users/bulk-assign-zone` (body: `user_ids[]`, `zone_id`). **UI:** Checkboxes in table, bulk action bar appears on selection with "Set Main Building" and "Assign to Zone" buttons. "Select all X filtered" link for quick batch selection. |
| **US-ADM-09** Template download | **API:** `GET /api/templates/users` — Returns CSV with columns: `email, first_name, last_name, company, role, job_family, main_building, zone` and example rows. |
| **US-ADM-10** Audit timestamps | **DB:** `users.created_at` (set on creation), `users.updated_at` (set on every update). **UI:** "Created" column in table, "edited MM/DD" sub-text when updated. |
| **US-ADM-11** Waitlist configuration | **API:** `POST /api/parking-config` — Fields: `waitlist_enabled` (boolean), `waitlist_notification_window_minutes` (default 15). **UI:** Toggle and input field in Parking Config page. **Background:** `check_waitlist_expiry()` task uses this config. |
| **US-ADM-12** Job Family field | **API:** `POST /api/users` and `PUT /api/users/{id}` — Accepts `job_family` field (e.g., "Department Head"). `POST /api/users/bulk-upload` — CSV column `job_family` supported. **DB:** `users.job_family` (optional string). **UI:** Job Family field in user create/edit form. Template CSV includes `job_family` column. |

### 2.6 Admin — Building & Slot Management

| User Story | System Implementation |
|------------|----------------------|
| **US-BLD-01** Create building | **API:** `POST /api/buildings` — Creates with name, address. **DB:** `buildings` collection. |
| **US-BLD-02** Add floors with layout | **API:** `POST /api/buildings/{id}/floors` (create floor), `POST /api/floors/{id}/layout` (upload image). Images stored on disk at `/app/backend/uploads/`. **UI:** Floor tab with upload button, image preview. |
| **US-BLD-03** Add slots | **API:** `POST /api/floors/{floor_id}/slots` — Accepts `slots[]` array with `label`, `row`, `column`. Supports bulk creation. **DB:** `parking_slots` collection linked to `floor_id` and `building_id`. |
| **US-BLD-04** Block/unblock slots | **API:** `PUT /api/slots/{id}/status` — Toggles between `active` and `maintenance`. Maintenance slots excluded from availability. |
| **US-BLD-05** Delete slots | **API:** `DELETE /api/slots/{id}` — Permanent removal. |
| **US-BLD-06** Available slots | **API:** `GET /api/slots/available?floor_id=X&date=Y` — Cross-references reservations to return only free, active slots. |

### 2.7 Admin — Zone Management

| User Story | System Implementation |
|------------|----------------------|
| **US-ZN-01** Create zone | **API:** `POST /api/zones` — Creates zone with `name`, `building_ids[]`, `user_ids[]`. |
| **US-ZN-02** Assign users | **API:** `PUT /api/zones/{id}` — Updates `user_ids[]`. Also via bulk: `POST /api/users/bulk-assign-zone`. |
| **US-ZN-03** Manage buildings | **API:** `PUT /api/zones/{id}` — Updates `building_ids[]`. |

### 2.8 Admin — Parking Configuration

| User Story | System Implementation |
|------------|----------------------|
| **US-CFG-01** Default parking hours | **API:** `POST /api/parking-config` — Sets `default_start_time`, `default_end_time` per building. **DB:** `parking_configs` collection with unique `building_id` index. |
| **US-CFG-02** Booking window | **API:** `POST /api/parking-config` — `booking_window_days` field (default 7). Frontend enforces max selectable date. |
| **US-CFG-03** Release time | **API:** `POST /api/parking-config` — `release_time` field. Slots available for booking after this time. |
| **US-CFG-04** Auto no-show release | **API:** `POST /api/parking-config` — `no_show_release_enabled` + `no_show_release_minutes`. **Background:** `auto_mark_no_shows()` async task runs every 5 minutes. Marks expired reservations as no-show and records a `no_show_at` timestamp. Slot release is calculated as X minutes after `no_show_at` (not after reservation end time). |
| **US-CFG-05** Main building exclusivity | **API:** `POST /api/parking-config` — `main_building_exclusive` (boolean, default `false`). When enabled, `POST /api/reservations` checks if the authenticated user's `main_building` matches the booking building. Admins are always exempt. **UI:** Toggle switch in Parking Config page labeled "Main Building Exclusive." **DB:** `parking_configs.main_building_exclusive` field. |

### 2.9 Admin — Reports & Analytics

| User Story | System Implementation |
|------------|----------------------|
| **US-RPT-01** Dashboard stats | **API:** `GET /api/reports/stats` — Returns `total_reservations`, `confirmed`, `cancelled`, `pending`, `no_show`, `active_users`, `occupancy_rate`, `building_breakdown[]`. |
| **US-RPT-02** Date/building filter | **API:** `GET /api/reports/stats?start_date=X&end_date=Y&building_id=Z`. Frontend date picker + building dropdown. |
| **US-RPT-03** AI insights | **API:** `POST /api/reports/ai-insights` — Sends parking stats to Emergent LLM (GPT), returns markdown analysis. Saved to `ai_insights` collection. **UI:** Markdown-rendered insights with `react-markdown` + `remark-gfm`. |
| **US-RPT-04** Insights history | **API:** `GET /api/reports/ai-insights/history` — Lists all saved insights with timestamps. `DELETE /api/reports/ai-insights/{id}` for cleanup. |
| **US-RPT-05** Admin reservations | **API:** `GET /api/admin/reservations?status=X&building_id=Y&date=Z` — Full reservation list with user details. `DELETE /api/admin/reservations/{id}` — Admin cancels reservation; requires `reason` body field; sends in-app notification to the parker containing the reason; then triggers waitlist notification for the freed slot. |

### 2.10 Admin — Site Customization

| User Story | System Implementation |
|------------|----------------------|
| **US-SITE-01** Login page editor | **API:** `GET /api/site-content` (public), `PUT /api/admin/site-content` (admin-only). Fields: `heading_line1`, `heading_highlight`, `heading_line3`, `description`, `badge1_text`, `badge2_text`, `announcement`. **UI:** Admin Settings page with live preview. |

### 2.11 Admin — Building Policies

| User Story | System Implementation |
|------------|----------------------|
| **US-POL-01** Create building policy | **API:** `POST /api/building-policies` — Creates policy with `building_id`, `policy_type` (e.g., `dedicated_slot`), `enabled`, `max_users_per_slot`, `open_floor_ids`, `requires_sticker`. **DB:** `building_policies` collection. |
| **US-POL-02** Sticker requirement | **API:** `requires_sticker` field on policy. During reservation creation (`POST /api/reservations`), if enabled, the selected vehicle's plate must match an active `slot_registration` in the building. Rejects with 403 if no matching vehicle registration found. |
| **US-POL-03** Slot registration | **API:** `POST /api/slot-registrations` — Registers a user + vehicle to a specific slot. Fields: `slot_id`, `user_id`, `vehicle_plate`, `sticker_number`. Checks `max_users_per_slot` limit. `GET /api/slot-registrations` — Lists registrations with user names and slot labels. `DELETE /api/slot-registrations/{id}` — Revokes registration. **DB:** `slot_registrations` collection. |
| **US-POL-04** Open floors | **API:** `open_floor_ids` array on policy. Floors in this list bypass the strict slot-assignment check, allowing any registered user to book any slot on those floors. |
| **US-POL-05** Zone-filtered user selection | **API:** `GET /api/slot-registrations` + frontend filtering. The user dropdown in the policy management UI is filtered to only show users assigned to the building's zone. |
| **US-POL-06** Vehicle dropdown | **Frontend:** When assigning a slot registration, the admin selects a vehicle from the user's registered vehicles (dropdown) instead of typing a plate number manually. Populated via `GET /api/vehicles?user_id=X`. |

### 2.12 Parking Attendant

| User Story | System Implementation |
|------------|----------------------|
| **US-ATT-01** Daily reservations | **API:** `GET /api/attendant/daily-reservations?date=X&building_id=Y` — Returns reservations with user details, vehicle, slot, floor info. Attendant role required. |
| **US-ATT-02** Confirm arrival | **API:** `PUT /api/reservations/{id}/confirm` — Sets status to `confirmed`. Optional: `POST /api/reservations/{id}/confirm-with-photo` for photo evidence. |
| **US-ATT-03** Report no-show | **API:** `POST /api/attendant/reservations/{id}/report-no-show` — **Date guard:** rejects if `reservation.date > today`. Sets status to `no_show`, records `no_show_at` timestamp, increments user's `no_show_count`, creates notification. Slot release timing is based on `no_show_at` + configured release minutes. **UI:** "No Show" button hidden for future dates. |
| **US-ATT-04** Today button | **UI:** `AttendantDashboard.js` — "Today" button appears between date display and next arrow when selected date != today. Clicking resets to current date. |
| **US-ATT-05** QR scan | **API:** `GET /api/scan/{qr_token}` — Returns reservation details (attendant/admin only). **UI:** `/scan/:qrToken` route. |
| **US-ATT-06** Summary cards | **UI:** Three cards showing count by status: Reserved (pending), Confirmed, No Shows for selected date. |

### 2.13 Admin — Event Blocking

| User Story | System Implementation |
|------------|----------------------|
| **US-EVT-01** Block slots for event | **API:** `POST /api/event-blocks/` — Admin-only. Accepts `event_name`, `reason`, `building_id`, `floor_id`, `slot_ids[]`, `date`, `start_time`, `end_time`. Creates an `event_block` document and one `reservation` record per slot with `booking_type: "event_block"` and `status: "confirmed"`. These reservations block the slots from being booked by regular users. **DB:** `event_blocks` collection + `reservations` collection. |
| **US-EVT-02** List event blocks | **API:** `GET /api/event-blocks/` — Returns all event blocks. Optional `building_id` filter. Returns enriched data including building name, floor label, slot labels. **UI:** Event Blocking admin page with a list of active blocks. |
| **US-EVT-03** Delete event block | **API:** `DELETE /api/event-blocks/{id}` — Removes the event block record and all associated reservation records (frees the slots). **UI:** Delete button on each event block card. |

---

## 3. Non-Functional Requirements Implementation

| NFR | Implementation |
|-----|----------------|
| **NFR-01** Mobile responsive | TailwindCSS responsive classes (`sm:`, `md:`, `lg:`). Mobile bottom navigation on user pages. Tested at 375px width. |
| **NFR-02** Page load < 3s | React SPA with code-splitting via `React.lazy`. API calls use `Promise.all` for parallel fetching. Auto-retry on failure. |
| **NFR-03** API < 500ms | MongoDB indexes on all queried fields (25 indexes). Motor async driver. Connection pooling (maxPool=50). |
| **NFR-04** 200+ users | Stateless JWT auth (no session affinity needed). Horizontal scaling via container replicas. DB connection pooling. |
| **NFR-05** Security | HttpOnly cookies, bcrypt hashing, JWT with no fallback secret, CSP/HSTS/X-Frame headers, rate limiting (5/min on login), device fingerprinting, role-based access control. Password inputs use uncontrolled components (`useRef`) to prevent plaintext credential exposure in the DOM (mitigates CWE-312). See [Compliance Matrix](../03-system-design/compliance-matrix.md). |
| **NFR-06** 99.9% uptime | Container orchestration (K8s/ECS), health checks, graceful shutdown, auto-restart via supervisor. |
| **NFR-07** Browser support | Standard React 19 + ES2020 target. No browser-specific APIs used. |

---

*Previous: [BRD](../01-business-requirements/BRD.md) | Next: [System Design](../03-system-design/system-design.md)*
