# Test Scripts
**Project:** Cebuana Lhuillier Parking Reservation System  
**Version:** 2.1  
**Date:** March 5, 2026  
**Related:** [Test Plan](test-plan.md) | [Test Results](test-results.md)

---

## 1. Unit Test Cases

### 1.1 Authentication Module

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-AUTH-01 | Login with valid credentials | `email: admin.test@cebuana.com, password: Test123!` | 200 OK, JWT cookie set, user object returned with correct role | P0 |
| TC-AUTH-02 | Login with invalid password | `email: admin.test@cebuana.com, password: wrong` | 401 "Invalid credentials" | P0 |
| TC-AUTH-03 | Login with non-existent email | `email: none@test.com, password: any` | 401 "Invalid credentials" | P0 |
| TC-AUTH-04 | Login rate limiting (>5 attempts/min) | 6 rapid login attempts | 429 Rate limit exceeded on 6th attempt | P1 |
| TC-AUTH-05 | Get current user (/auth/me) | Valid auth cookie | 200 OK with user profile (id, role, main_building, tags) | P0 |
| TC-AUTH-06 | Get current user without auth | No cookie | 401 Unauthorized | P0 |
| TC-AUTH-07 | Logout | Valid auth cookie | 200 OK, cookie cleared, session revoked in DB | P0 |
| TC-AUTH-08 | Change password (with current password verification) | `current_password: Test123!, new_password: NewPass123!` | 200 OK, `must_change_password` cleared, new password hash stored | P0 |
| TC-AUTH-09 | Session expiry after 30 minutes | Token with expired `exp` claim | 401 Unauthorized | P1 |
| TC-AUTH-10 | Device fingerprint mismatch | Valid token but different User-Agent | 401 Session fingerprint mismatch | P1 |
| TC-AUTH-11 | Change password with wrong current password | `current_password: WrongPass!, new_password: NewPass123!` | 400 "Current password is incorrect" | P0 |
| TC-AUTH-12 | Forgot password (existing email) | `email: user.test@cebuana.com` | 200 OK (always), admin notification created | P1 |
| TC-AUTH-13 | Forgot password (non-existent email) | `email: noone@nowhere.com` | 200 OK (prevents email enumeration), no notification created | P1 |
| TC-AUTH-14 | Same-password prevention (self-service change) | `current_password: Test123!, new_password: Test123!` | 400 "New password cannot be the same as your current password" | P0 |
| TC-AUTH-15 | Blocked user login attempt | Block user via admin → attempt login with valid credentials | 403 "Your account has been blocked. Please contact your administrator." | P0 |
| TC-AUTH-16 | Empty email on login | Submit login form with blank email field | Browser field validation or toast "Please enter your email address"; form does not submit to API | P1 |
| TC-AUTH-17 | Empty password on login | Submit login form with blank password field | Browser field validation or toast "Please enter your password"; form does not submit to API | P1 |

### 1.2 Vehicle Management

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-VEH-01 | Create vehicle | `plate_number: ABC-1234, make: Toyota, model: Vios, color: White` | 200 OK, vehicle created with user_id | P0 |
| TC-VEH-02 | List user vehicles | Authenticated user | Array of vehicles belonging to user only | P0 |
| TC-VEH-03 | Delete vehicle | Valid vehicle_id owned by user | 200 OK, vehicle removed | P1 |
| TC-VEH-04 | Delete vehicle owned by another user | Vehicle ID of another user | 403 or 404 | P1 |
| TC-VEH-05 | Create vehicle with duplicate plate | Plate already registered to another vehicle | 400 "Plate number X is already registered to another vehicle" | P0 |
| TC-VEH-06 | Create vehicle with unique plate | New unique plate number | 200 OK, vehicle created | P0 |
| TC-VEH-07 | Create vehicle with plate < 2 chars | `plate_number: "A"` | 422 "Plate number must be at least 2 characters" | P0 |
| TC-VEH-08 | Create vehicle with plate > 15 chars | `plate_number: "ABCDEFGHIJKLMNOP"` | 422 "Plate number must not exceed 15 characters" | P0 |

### 1.3 Reservation Management

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-RES-01 | Create single-date reservation | `slot_id, vehicle_id, dates: ["2026-02-25"], start_time: "08:00", end_time: "18:00"` | 200 OK, reservation with QR token, status: pending | P0 |
| TC-RES-02 | Create multi-date reservation | `dates: ["2026-02-25", "2026-02-26", "2026-02-27"]` | 200 OK, 3 reservations created | P0 |
| TC-RES-03 | Book already-reserved slot | Same slot_id + date as existing active reservation | 400 "Slot already reserved for {date}" | P0 |
| TC-RES-04 | Book with overlapping time | Same date, overlapping start/end times | 400 "You already have a booking that overlaps" | P0 |
| TC-RES-05 | Book more than 7 dates | `dates: [8 dates]` | 400 "Maximum 7 dates allowed per booking" | P1 |
| TC-RES-06 | Book with no dates | `dates: []` | 400 "At least one date is required" | P1 |
| TC-RES-07 | Book as blocked user | Blocked user auth | 403 "Your account has been blocked" | P0 |
| TC-RES-08 | Cancel reservation | Valid reservation_id | 200 OK, status changed to "cancelled" | P0 |
| TC-RES-09 | Cancel another user's reservation | Reservation belonging to different user | 404 (user-scoped query) | P1 |
| TC-RES-10 | Get QR code | Valid reservation_id | 200 OK with base64 QR image and qr_token | P1 |
| TC-RES-11 | End time before start time | `start_time: "18:00", end_time: "08:00"` | 400 "End time must be after start time" | P1 |

### 1.4 Zone & Building Rules

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-ZONE-01 | Book in main building | User's main_building matches booking building | 200 OK, no extra validation | P0 |
| TC-ZONE-02 | Book in zone building (non-main), single day | Different building in user's zone, 1 date, with reason | 200 OK | P0 |
| TC-ZONE-03 | Book in zone building, multi-day (non-VIP) | Different building, 2+ dates | 400 "limited to a single day only" | P0 |
| TC-ZONE-04 | Book in zone building without reason | Different building, no reason | 400 "A reason is required" | P0 |
| TC-ZONE-05 | Book outside zone | Building not in user's zone | 403 "not assigned to this building's zone" | P0 |
| TC-ZONE-06 | VIP books multi-day in non-main building | VIP user, 2+ dates in zone building | 200 OK (VIP bypass) | P1 |

### 1.5 Admin — User Management

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-ADM-01 | Create user (admin only) | User data with all fields | 200 OK, user created with `must_change_password: true` | P0 |
| TC-ADM-02 | Create user with duplicate email | Existing email | 400 "Email already registered" | P0 |
| TC-ADM-03 | Non-admin create user | User role auth | 403 Forbidden | P0 |
| TC-ADM-04 | Block user | Valid user_id | 200 OK, user.is_blocked = true | P1 |
| TC-ADM-05 | Block admin user | Admin user_id | 400 "Cannot block an admin user" | P1 |
| TC-ADM-06 | Unblock user | Blocked user_id | 200 OK, user.is_blocked = false | P1 |
| TC-ADM-07 | Reset password | `user_id, password: NewTemp!` | 200 OK, `must_change_password: true` | P1 |
| TC-ADM-08 | Update user tags | `tags: ["vip", "group_head"]` | 200 OK, tags updated | P1 |
| TC-ADM-09 | Invalid tag | `tags: ["invalid_tag"]` | 400 "Invalid tags" | P1 |
| TC-ADM-10 | Bulk set main building | `user_ids: [...], main_building: building_id` | 200 OK with modified count | P1 |
| TC-ADM-11 | Bulk assign zone | `user_ids: [...], zone_id: zone_id` | 200 OK, users added to zone | P1 |

### 1.6 Admin — Bulk Upload

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-BULK-01 | Upload valid CSV | CSV with email, first_name, last_name | 200 OK, users created | P0 |
| TC-BULK-02 | Upload CSV with existing emails | CSV with duplicate emails | Skipped count > 0, no errors | P0 |
| TC-BULK-03 | Upload CSV with main_building column | CSV with building name | Building name resolved to ID | P1 |
| TC-BULK-04 | Upload CSV with zone column | CSV with zone name | Zone assignment performed ($addToSet) | P1 |
| TC-BULK-05 | Upload CSV with invalid building name | Nonexistent building name | Error reported in response | P1 |
| TC-BULK-06 | Upload CSV missing required column | CSV without email column | 400 "Missing required column: email" | P0 |
| TC-BULK-07 | Upload non-CSV file | .txt file | 400 "File must be CSV or Excel" | P1 |
| TC-BULK-08 | Download user template | GET /api/templates/users | CSV with correct columns (`email, first_name, last_name, company, role, job_family, main_building, zone`) and example rows | P2 |

### 1.7 Building & Slot Management

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-BLD-01 | Create building | `name, address, total_floors, slots_per_floor` | Building + floors + slots created | P0 |
| TC-BLD-02 | Delete building | Valid building_id | Building, floors, and slots all deleted | P1 |
| TC-BLD-03 | Add floor to building | `label, slot_count` | Floor created with slots | P0 |
| TC-BLD-04 | Upload floor layout | Image file (PNG/JPG) | 200 OK, layout_image_url set | P1 |
| TC-BLD-05 | Upload non-image file | .txt file | 400 "File must be an image" | P1 |
| TC-BLD-06 | Upload file >10MB | Large image | 400 "File too large" | P2 |
| TC-BLD-07 | Set slot to maintenance | `status: maintenance` | Slot excluded from availability | P1 |
| TC-BLD-08 | Maintenance slot with active reservation | Slot has pending reservation | 400 "Cannot block a slot with active reservations" | P1 |
| TC-BLD-09 | Delete slot with active reservation | Slot has pending reservation | 400 "Cannot delete slot with active reservations" | P1 |
| TC-BLD-10 | Get available slots | `building_id, date, floor_id` | Only available, non-maintenance, non-reserved slots | P0 |

### 1.8 Zone Management

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-ZN-01 | Create zone | `name, building_ids, user_ids` | 200 OK, zone created | P0 |
| TC-ZN-02 | Update zone buildings | New building_ids | 200 OK, buildings updated | P1 |
| TC-ZN-03 | Delete zone | Valid zone_id | 200 OK, zone removed | P1 |
| TC-ZN-04 | Get user building assignments | Authenticated user | Building IDs from all assigned zones | P0 |

### 1.9 Parking Configuration

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-CFG-01 | Save config (new) | `building_id, default_start_time, default_end_time, booking_window_days` | Config created | P0 |
| TC-CFG-02 | Update config (existing) | Same building_id with new values | Config updated (upsert) | P1 |
| TC-CFG-03 | Get config (default) | Building without config | Default values returned | P1 |
| TC-CFG-04 | Enable main building exclusivity | `main_building_exclusive: true` for building X | Config saved; non-assigned users get 403 on `POST /api/reservations` | P1 |
| TC-CFG-05 | Non-assigned user books exclusive building | User's `main_building` != building X (exclusivity enabled) | 403 "This building is restricted to its assigned employees only" | P1 |
| TC-CFG-06 | Admin books exclusive building | Admin user, building X (exclusivity enabled) | 200 OK (admins are exempt) | P1 |

### 1.10 Waitlist & Slot Timeline

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-WL-01 | Get floor timeline | `building_id, floor_id, date` | Hourly timeline (6AM–10PM) per slot, with booked/available flags | P1 |
| TC-WL-02 | Join waitlist | `building_id, preferred_date, start_time, end_time` | 200 OK, entry created with position | P1 |
| TC-WL-03 | Join waitlist (disabled) | Building without waitlist enabled | 400 "Waitlist is not enabled" | P1 |
| TC-WL-04 | Join waitlist (duplicate) | Already on waitlist for same building+date | 400 "already on the waitlist" | P1 |
| TC-WL-05 | Leave waitlist | Valid entry_id | 200 OK, status set to cancelled | P1 |
| TC-WL-06 | Get waitlist status | `building_id, date` for user on waitlist | `on_waitlist: true` with entry details | P1 |
| TC-WL-07 | Get waitlist count | `building_id, date` | Count of waiting entries | P1 |
| TC-WL-08 | Admin get building waitlist | Admin auth, building_id | List of waitlist entries with user names | P1 |

### 1.11 Reports & AI Insights

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-RPT-01 | Get stats (no filters) | Admin auth | Summary with totals, daily/building breakdown | P0 |
| TC-RPT-02 | Get stats with date filter | `start_date, end_date` | Filtered results | P1 |
| TC-RPT-03 | Get stats with building filter | `building_id` | Building-specific stats | P1 |
| TC-RPT-04 | Generate AI insight | Admin auth + valid API key | Markdown insight saved to DB | P2 |
| TC-RPT-05 | AI insight without API key | No EMERGENT_LLM_KEY | Graceful error message | P2 |
| TC-RPT-06 | Get insights history | Admin auth | Array of past insights, sorted by date desc | P2 |
| TC-RPT-07 | Delete insight | Valid insight_id | 200 OK, insight removed | P2 |

### 1.12 Attendant Operations

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-ATT-01 | Get daily reservations | `date=today, building_id=X` | Reservations for that date + building | P0 |
| TC-ATT-02 | Confirm reservation | Valid reservation_id | Status changed to "confirmed" | P0 |
| TC-ATT-03 | Report no-show (today) | Reservation for today | Status: no_show, `no_show_at` timestamp recorded, no_show_count incremented, notification sent | P0 |
| TC-ATT-04 | Report no-show (future date) | Reservation for tomorrow | 400 "Cannot report no-show for a future reservation" | P0 |
| TC-ATT-05 | Report no-show (already cancelled) | Cancelled reservation | 400 "Cannot report no-show for a cancelled reservation" | P1 |
| TC-ATT-06 | QR scan lookup | Valid qr_token | Reservation details with user, vehicle, slot, building | P1 |
| TC-ATT-07 | QR scan invalid token | Random string | 404 "Reservation not found" | P1 |

### 1.13 Notifications

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-NOTIF-01 | Get notifications | Authenticated user | User's notifications, sorted desc | P1 |
| TC-NOTIF-02 | Get unread count | Authenticated user | `{count: N}` | P1 |
| TC-NOTIF-03 | Mark single as read | Valid notification_id | Notification.read = true | P1 |
| TC-NOTIF-04 | Mark all as read | Authenticated user | All unread → read | P1 |

### 1.14 Site Content

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-SITE-01 | Get site content (public) | No auth required | Default or custom content | P2 |
| TC-SITE-02 | Update site content | Admin auth, new heading/description | Content updated (upserted) | P2 |

### 1.15 Building Policies

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-POL-01 | Create building policy | Admin auth, `building_id, policy_type, enabled, requires_sticker` | 200 OK, policy created | P0 |
| TC-POL-02 | Book with registered vehicle (sticker building) | Vehicle plate matches active slot registration | 200 OK, reservation created | P0 |
| TC-POL-03 | Book with unregistered vehicle (sticker building) | Vehicle plate has no registration in building | 403 "Vehicle X does not have a parking sticker/registration" | P0 |
| TC-POL-04 | Book assigned slot with registered vehicle | Vehicle+user registered to specific slot | 200 OK | P0 |
| TC-POL-05 | Book unassigned slot with registered vehicle (non-open floor) | Vehicle registered to different slot | 403 "Vehicle X is not registered to this parking slot" | P0 |
| TC-POL-06 | Book any slot on open floor | Floor is in `open_floor_ids` | 200 OK (no strict slot check) | P1 |
| TC-POL-07 | Create slot registration (max reached) | Slot already at max_users_per_slot | 400 "This slot already has N registered users" | P1 |
| TC-POL-08 | Duplicate slot registration | Same user+slot already active | 400 "User is already registered to this slot" | P1 |

---

## 2. Integration Test Cases

| TC ID | Test Case | Modules Involved | Steps | Expected Result | Priority |
|-------|-----------|-----------------|-------|-----------------|----------|
| TC-INT-01 | Full booking flow | Auth, Buildings, Vehicles, Reservations | Login → List buildings → Create vehicle → Get available slots → Book → Verify reservation | Reservation created with all enriched data | P0 |
| TC-INT-02 | No-show notification flow | Attendant, Reservations, Notifications | Create reservation → Report no-show → Check user notifications | Notification created with correct message | P0 |
| TC-INT-03 | Bulk upload with zone assignment | Users, Zones | Create zone → Upload CSV with zone column → Verify zone.user_ids updated | Users created and added to zone | P1 |
| TC-INT-04 | External booking with zone enforcement | Auth, Zones, Reservations | Assign user to zone → Book in non-main building → Verify single-day + reason enforced | Business rule enforced correctly | P0 |
| TC-INT-05 | Admin cancellation flow (with reason + notification) | Users (admin), Reservations, Notifications | Admin cancels reservation with reason field → Verify status change → Verify user receives notification with reason | Reservation cancelled, parker receives in-app notification containing cancellation reason | P0 |
| TC-INT-06 | Session lifecycle | Auth | Login → Use token → Logout → Reuse token | Token invalid after logout (session revoked) | P0 |
| TC-INT-07 | Slot maintenance lifecycle | Buildings, Reservations | Set slot to maintenance → Verify not available → Remove maintenance → Verify available | Slot availability reflects status | P1 |
| TC-INT-08 | Waitlist notification flow | Waitlist, Reservations, Notifications | Join waitlist → Cancel reservation (triggers slot available) → Verify waitlist user notified | Next waitlisted user receives notification with booking window | P1 |
| TC-INT-09 | No-show slot release timing | Attendant, Reservations, Config | Report no-show → Check no_show_at recorded → Wait for release_minutes → Verify slot released | Slot released based on no_show_at + config minutes | P1 |
| TC-INT-10 | Vehicle-level policy enforcement | Vehicles, Building Policies, Reservations | Register vehicle → Create slot registration → Book with registered vehicle (pass) → Book with different vehicle (fail) | Only the specific registered vehicle can book the slot | P0 |
| TC-INT-11 | Plate uniqueness across users | Vehicles, Auth | User A registers plate X → User B tries to register same plate X | 400 error for User B, plate uniqueness enforced | P0 |
| TC-INT-12 | Event block prevents double-booking | Event Blocks, Reservations | Admin creates event block for slot S → Regular user tries to book slot S for same time | Slot appears as unavailable; booking rejected | P0 |
| TC-INT-13 | Main building exclusivity enforcement | Parking Config, Users, Reservations | Enable exclusivity for building B → User without B as main_building tries to book → Verify rejection | 403 error for non-assigned user; admin can still book | P1 |

---

## 3. UI Test Cases

| TC ID | Test Case | Page | Steps | Expected Result | Priority |
|-------|-----------|------|-------|-----------------|----------|
| TC-UI-01 | Login page renders | `/login` | Navigate to login | Email/password form, submit button, branding visible | P0 |
| TC-UI-02 | Login success redirect | `/login` | Enter valid credentials → Submit | Redirect to role-appropriate dashboard | P0 |
| TC-UI-03 | User dashboard loads | `/dashboard` | Login as user | Stats cards, vehicles, reservations tabs visible | P0 |
| TC-UI-04 | Booking page flow | `/book` | Select building → floor → dates → slot → vehicle → submit | Reservation confirmed, QR shown | P0 |
| TC-UI-05 | Admin dashboard loads | `/admin` | Login as admin | Stats cards, charts, building breakdown visible | P0 |
| TC-UI-06 | User management table | `/admin/users` | Navigate to user management | User table with filters, checkboxes, action buttons | P0 |
| TC-UI-07 | Bulk upload dialog | `/admin/users` | Click bulk upload → Select file → Submit | Upload summary displayed | P1 |
| TC-UI-08 | Building management | `/admin/buildings` | Navigate to buildings | Building cards with floors and slots | P1 |
| TC-UI-09 | Attendant dashboard | `/attendant` | Login as attendant | Date picker, building filter, reservation cards, summary cards | P0 |
| TC-UI-10 | No-show button hidden for future | `/attendant` | Navigate to future date | "Confirm" and "No Show" buttons not visible | P0 |
| TC-UI-11 | Today button on attendant | `/attendant` | Navigate to different date | "Today" button appears; clicking returns to today | P1 |
| TC-UI-12 | Notification bell | Any authenticated page | Check header | Bell icon with unread count badge | P1 |
| TC-UI-13 | Mobile responsive layout | `/dashboard` | Set viewport to 375px width | Layout adapts, bottom navigation visible | P1 |
| TC-UI-14 | Force password change | `/login` | Login with `must_change_password: true` | Password change dialog appears, blocks navigation | P0 |
| TC-UI-15 | Hourly timeline on booking | `/book` | Select building → floor → date → slot | Hourly timeline grid appears showing booked/available hours | P1 |
| TC-UI-16 | Waitlist join button | `/book` | Navigate to fully booked building+date | "Join Waitlist" option visible | P1 |
| TC-UI-17 | Job Family in user form | `/admin/users` | Click "Add User" or edit user | Job Family field visible in the form | P1 |
| TC-UI-18 | Change password on profile | `/profile` | Login → Navigate to Profile → Fill change password form with current + new password → Submit | Password updated, success toast shown | P1 |
| TC-UI-19 | Forgot password link on login | `/login` | Click "Forgot Password?" | ForgotPassword modal/form appears; submit email | P1 |
| TC-UI-20 | Event blocking admin page | `/admin/event-blocking` | Login as admin → Navigate to Event Blocking | Slot map and event block form visible; existing blocks listed | P0 |
| TC-UI-21 | Admin cancellation reason dialog | `/admin/reservations` | Click Cancel on a reservation | Modal prompts for cancellation reason; reason required before submit | P0 |
| TC-UI-22 | Main building exclusivity toggle | `/admin/parking-config` | Select building with exclusivity → Toggle on | Toggle saved; info text about restriction appears | P1 |

---

### 1.16 Event Blocking

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-EVT-01 | Create event block | Admin auth, `event_name, reason, building_id, floor_id, slot_ids: [slot1, slot2], date, start_time, end_time` | 200 OK, event_block created with reservation_ids for each slot; reservations have `booking_type: event_block` | P0 |
| TC-EVT-02 | List event blocks | Admin auth | Array of event blocks with enriched slot/building/floor info | P1 |
| TC-EVT-03 | Delete event block | Valid event_block_id | 200 OK; event block removed; all associated reservations deleted; slots freed | P0 |
| TC-EVT-04 | Create event block for already-booked slot | Slot with active reservation | 400 "Slot X is already reserved for the selected date/time" | P1 |
| TC-EVT-05 | Non-admin creates event block | User role auth | 403 Forbidden | P0 |

### 1.17 User Management Filters & Search

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-USR-FLT-01 | Filter by Role | Select "user" from Role dropdown | Only users with role=user displayed; admins and attendants hidden | P1 |
| TC-USR-FLT-02 | Filter by Company | Select a company from Company dropdown | Only users belonging to selected company displayed | P1 |
| TC-USR-FLT-03 | Filter by Zone | Select a zone from Zone dropdown | Only users in the selected zone displayed | P1 |
| TC-USR-FLT-04 | Filter by Main Building | Select a building from Main Building dropdown | Only users with matching main_building displayed | P1 |
| TC-USR-FLT-05 | Multiple filters simultaneously | Role=user + Company=Cebuana | Results satisfy all selected filter criteria | P1 |
| TC-USR-FLT-06 | Search by full name | Enter "Juan Dela Cruz" | Returns all users whose combined first + last name contains the search term | P0 |
| TC-USR-FLT-07 | Search by partial name | Enter "Juan" | Returns all users with "Juan" in first name, last name, or full name | P1 |

### 1.18 Admin Dashboard Counts

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TC-DASH-01 | Total users count accuracy | Compare dashboard stat vs `GET /api/users` count | Dashboard total_users equals actual count in users collection | P1 |
| TC-DASH-02 | Total buildings count accuracy | Compare dashboard stat vs `GET /api/buildings` count | Dashboard buildings_count equals actual count in buildings collection | P1 |
| TC-DASH-03 | Dashboard loads without auth error | Login as admin, navigate to `/admin` | Dashboard page loads; all stat cards visible; no "Invalid credentials" shown | P0 |
| TC-DASH-04 | No unknown buildings in chart | `GET /api/reports/stats` building_breakdown | No entries with `building_name == "Unknown"` in the breakdown array | P1 |

---

## 4. Performance Test Cases

| TC ID | Test Case | Metric | Target | Method | Priority |
|-------|-----------|--------|--------|--------|----------|
| TC-PERF-01 | Login API response time | Latency | < 300ms | `curl -w "%{time_total}"` | P1 |
| TC-PERF-02 | Get buildings response time | Latency | < 500ms | Timed API call | P1 |
| TC-PERF-03 | Available slots response time | Latency | < 300ms | Timed API call with filters | P1 |
| TC-PERF-04 | Admin stats response time | Latency | < 500ms | Timed API call | P1 |
| TC-PERF-05 | Create reservation response time | Latency | < 500ms | Timed API call | P1 |
| TC-PERF-06 | Frontend initial load | Page load | < 3s | Playwright timing | P1 |
| TC-PERF-07 | Dashboard data fetch | Total fetch | < 2s | `Promise.allSettled` timing | P2 |

---

## 5. Security Test Cases

| TC ID | Test Case | Category | Steps | Expected Result | Priority |
|-------|-----------|----------|-------|-----------------|----------|
| TC-SEC-01 | Access admin endpoint as user | Authorization | Login as user → Call `GET /api/users` | 403 Forbidden | P0 |
| TC-SEC-02 | Access admin endpoint as attendant | Authorization | Login as attendant → Call `POST /api/users` | 403 Forbidden | P0 |
| TC-SEC-03 | Access without authentication | Authentication | Call any protected endpoint without cookie | 401 Unauthorized | P0 |
| TC-SEC-04 | Expired JWT token | Authentication | Use token older than 30 minutes | 401 Unauthorized | P0 |
| TC-SEC-05 | Revoked session | Authentication | Logout → Reuse old token | 401 Session expired | P1 |
| TC-SEC-06 | Security headers present | Transport | Check response headers on any request | CSP, HSTS, X-Frame-Options, X-Content-Type-Options all present | P0 |
| TC-SEC-07 | HttpOnly cookie flag | Transport | Inspect Set-Cookie header | `HttpOnly; Secure; SameSite=Lax` | P0 |
| TC-SEC-08 | Rate limiting on login | Abuse Prevention | 6 rapid login attempts | 429 on 6th attempt | P1 |
| TC-SEC-09 | Path traversal on file upload | Injection | Upload file with `../../` in name | Filename sanitized, no traversal | P1 |
| TC-SEC-10 | XSS in user input | Injection | Create user with `<script>` in name | Stored as plain text, not executed | P1 |
| TC-SEC-11 | SQL/NoSQL injection in query | Injection | Pass `{"$gt":""}` in query params | Validated by Pydantic, no injection | P1 |
| TC-SEC-12 | Blocked user login attempt | Access Control | Block user → Attempt login | Login rejected | P0 |

---

## 6. March 2026 Bug Fix Test Cases

### 6.1 Attendant Management

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TCID-PARKING-ATTENDANT-001 | No-Show button hidden for confirmed bookings | Booking with `status: confirmed` | No-Show button not visible/clickable | P0 |
| TCID-ATTENDANT-MANAGEMENT-007 | Cannot create attendant without building | `role: attendant, assigned_buildings: []` | 400 "Attendants must be assigned to at least one building" | P0 |
| TCID-ATTENDANT-MANAGEMENT-011 | Attendant with multiple buildings | `assigned_buildings: [bldg1, bldg2]` | 200 OK, attendant created with both buildings | P1 |

### 6.2 Booking Time Restrictions

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TCID-PARKING-RESERVATION-013 | Past hours disabled for today | Select today's date on booking page | Hours before current time show "Past" label and are unclickable | P0 |
| TCID-PARKING-CONFIG-013 | Hours before config start disabled | Parking config `default_start_time: "08:00"` | Hours 00:00-07:00 show "Closed" label | P1 |
| TCID-PARKING-CONFIG-014 | Hours after config end disabled | Parking config `default_end_time: "18:00"` | Hours 18:00-23:00 show "Closed" label | P1 |
| TCID-PARKING-RESERVATION-015 | Default hours auto-selected | User with `default_start_time: "09:00", default_end_time: "17:00"` | When slot clicked, hours 09:00-16:00 pre-selected | P1 |

### 6.3 Building Policies

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TCID-BUILDING-POLICIES-006 | Sticker required validation | Policy with `requires_sticker: true`, empty sticker field | Submit button disabled, warning shown | P0 |
| TCID-BUILDING-POLICIES-009 | One slot per user per building | User already registered to slot A, try register to slot B | 400 "User is already registered to slot A in this building" | P0 |

### 6.4 UI/UX Fixes

| TC ID | Test Case | Input | Expected Result | Priority |
|-------|-----------|-------|-----------------|----------|
| TCID-BUILDING-MANAGEMENT-016 | Long slot name truncation | Slot label "VERY-LONG-SLOT-NAME-123456" | Text truncated with "..." and full name on hover tooltip | P2 |
| TCID-ZONE-MANAGEMENT-004 | Unknown buildings hidden | Zone with deleted building_id | Building not shown in zone card; "No buildings assigned" if all deleted | P2 |
| TCID-PARKING-RESERVATION-017 | Notification detail dialog | Click notification in bell dropdown | Detail dialog opens with full message and timestamp | P1 |

---

*Previous: [Test Plan](test-plan.md) | Next: [Test Results](test-results.md)*
