# Business Requirements Document (BRD)
**Project:** Cebuana Lhuillier Parking Reservation System  
**Version:** 2.0  
**Date:** February 24, 2026  
**Stakeholders:** Corporate Facilities, IT, End Users (Employees), Parking Attendants

---

## 1. Executive Summary

Cebuana Lhuillier requires a corporate parking reservation system to manage limited parking spaces across multiple buildings. The system serves three user roles — End Users (employees/parkers), Administrators, and Parking Attendants — each with distinct workflows. The solution must support multi-building, multi-floor parking management with zone-based access control, VIP designations, and real-time occupancy tracking.

---

## 2. Business Objectives

| ID | Objective | Success Metric |
|----|-----------|----------------|
| BO-1 | Reduce parking conflicts and double-bookings | Zero double-booking incidents |
| BO-2 | Streamline parking slot allocation across buildings | 90%+ slot utilization rate |
| BO-3 | Enable self-service booking for employees | 80%+ adoption within 3 months |
| BO-4 | Provide management visibility into parking usage | Real-time dashboards and reports |
| BO-5 | Enforce corporate parking policies (zones, VIP) | 100% policy compliance |
| BO-6 | Track and reduce parking no-shows | No-show rate below 5% |

---

## 3. Stakeholder Roles

| Role | Description | Key Needs |
|------|-------------|-----------|
| **End User (Parker)** | Employee who books parking | Quick booking, vehicle management, mobile-friendly |
| **Admin** | Facilities/IT administrator | Full control, user management, reporting, configuration |
| **Attendant** | On-site parking staff | View daily reservations, confirm arrivals, report no-shows |

---

## 4. User Stories

### 4.1 Authentication & Account Management

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-AUTH-01 | As an employee, I want to log in with my corporate email and password so that I can access the system securely. | P0 | Login form with email/password, session cookie issued, redirect to role-appropriate dashboard |
| US-AUTH-02 | As a new user, I want to be prompted to change my temporary password on first login so that my account is secure. | P0 | `must_change_password` flag enforced, redirect to change-password screen |
| US-AUTH-03 | As a user, I want my session to expire after 30 minutes of inactivity so that unauthorized access is prevented. | P1 | JWT token expires after 30 minutes, automatic redirect to login |
| US-AUTH-04 | As a user, I want to log out securely so that my session is terminated. | P0 | Cookie cleared, session revoked in DB |
| US-AUTH-05 | As an admin, I want to reset a user's password so that I can help employees who are locked out. | P1 | Admin can set new password for any user |
| US-AUTH-06 | As a user, I want to change my own password from my profile page by verifying my current password first, so that my account remains secure. | P1 | Change password form with current/new/confirm fields; current password verified before update |
| US-AUTH-07 | As a user who forgot my password, I want to submit my email on the login page to notify an admin, so that I can regain access to my account. | P1 | "Forgot Password" link on login page; admin notified via in-app notification; email enumeration prevented (always returns success) |

### 4.2 End User — Vehicle Management

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-VEH-01 | As a user, I want to register my vehicle(s) with plate number, make, model, and color so that I can book parking. | P0 | Vehicle CRUD with all fields stored. Plate number must be unique across the system. |
| US-VEH-02 | As a user, I want to manage multiple vehicles so that I can book with any of my cars. | P1 | List, add, delete vehicles from profile |
| US-VEH-03 | As a user, I want to see my vehicles listed on my dashboard for quick access. | P2 | Dashboard shows vehicle cards |

### 4.3 End User — Parking Reservation

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-RES-01 | As a user, I want to book a parking slot by selecting a building, floor, date(s), time range, and vehicle so that I can reserve my spot. | P0 | Multi-step booking flow, slot confirmation |
| US-RES-02 | As a user, I want to book multiple individual dates (not weekly) in a single booking so that I can plan ahead. | P0 | Date picker allows multiple discrete dates |
| US-RES-03 | As a user, I want to see which slots are available for my selected date and floor so that I can choose a spot. | P0 | Real-time slot availability grid |
| US-RES-04 | As a user, I want to receive a QR code for my reservation so that I can present it at the parking gate. | P1 | QR code generated per reservation, viewable in app |
| US-RES-05 | As a user, I want to cancel my reservation so that the slot is released for others. | P0 | Cancel button on active reservations, slot immediately freed |
| US-RES-06 | As a user, I want to view my active and past reservations in separate tabs so that I can track my history. | P1 | "Active" tab shows today+future, "History" tab shows past/cancelled |
| US-RES-07 | As a user, I want my default booking times to auto-fill when I create a reservation so that booking is faster. | P2 | User preferences applied, admin defaults as fallback |
| US-RES-08 | As a user, I want to set my preferred default booking start/end times on my profile page. | P2 | Profile page with time inputs, saved to user record |
| US-RES-09 | As a user, I want to see how many buildings are in my zone on the dashboard so that I know my options. | P2 | Dashboard "Buildings" card shows zone-filtered count |
| US-RES-10 | As a user, I want to be notified about booking confirmations and no-show warnings so that I stay informed. | P1 | In-app notification bell with unread count |
| US-RES-11 | As a user, I want to see hourly slot availability on a visual timeline so that I can choose the best time to park. | P1 | Hourly timeline (6AM–10PM) per slot, color-coded booked vs. available hours |
| US-RES-12 | As a user, I want to join a waitlist when all slots are fully booked so that I am notified when a slot becomes available. | P1 | Waitlist join, position tracking, in-app notification when slot opens, configurable booking window |

### 4.4 End User — Zone & Building Rules

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-ZONE-01 | As a user, I want to book in my main building without restrictions so that my daily commute is simple. | P0 | Booking in main building: no extra validation |
| US-ZONE-02 | As a user, I want to book in any building within my assigned zone so that I have flexibility. | P0 | Zone buildings visible and bookable |
| US-ZONE-03 | As a user assigned to a zone, I want to book in a non-main building (within zone) for a single day with a reason so that external visits are tracked. | P1 | Single-day restriction + reason field for non-main buildings |

### 4.5 Admin — User Management

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-ADM-01 | As an admin, I want to create individual users with email, name, company, role, and building assignment. | P0 | User creation form with all fields |
| US-ADM-02 | As an admin, I want to bulk upload users via CSV/Excel with columns for name, email, company, role, main building, and zone. | P0 | File upload, auto-resolve building/zone names, success/error summary |
| US-ADM-03 | As an admin, I want to block/unblock users so that I can enforce access policies. | P1 | Block/unblock toggle, blocked users cannot log in |
| US-ADM-04 | As an admin, I want to assign a main building to a user so that their default booking location is set. | P0 | Main building field on user edit form |
| US-ADM-05 | As an admin, I want to tag users as VIP or Group Head so that they receive special privileges. | P1 | Tags (vip, group_head) on user records |
| US-ADM-06 | As an admin, I want to set default booking times per user so that corporate schedules are enforced. | P2 | Start/end time fields in user edit |
| US-ADM-07 | As an admin, I want to filter users by company, zone, main building, and role so that I can find users quickly. | P1 | Filter dropdowns with "No Zone" / "No Building" options |
| US-ADM-08 | As an admin, I want to select multiple users and bulk-assign them to a zone or set their main building so that onboarding is efficient. | P1 | Multi-select checkboxes, bulk action bar |
| US-ADM-09 | As an admin, I want to download a CSV template with example data including main_building and zone columns. | P2 | Template download with sample rows |
| US-ADM-10 | As an admin, I want to see when users were created and last updated so that I can track account activity. | P2 | created_at and updated_at columns in user table |
| US-ADM-11 | As an admin, I want to configure waitlist settings per building (enable/disable, notification window) so that I can manage parking demand. | P1 | Waitlist toggle and window minutes in parking config |
| US-ADM-12 | As an admin, I want to record and view a user's Job Family (e.g., Department Head) so that organizational context is captured. | P1 | Job Family field on user profile, bulk upload CSV, admin user form |

### 4.6 Admin — Building & Slot Management

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-BLD-01 | As an admin, I want to create buildings with name, address, and number of floors. | P0 | Building creation form |
| US-BLD-02 | As an admin, I want to add floors to a building and upload a floor layout image. | P0 | Floor creation with image upload |
| US-BLD-03 | As an admin, I want to add parking slots (alphanumeric labels) to a floor individually or in bulk. | P0 | Single and batch slot creation |
| US-BLD-04 | As an admin, I want to block/unblock individual parking slots (e.g., for maintenance) without deleting them. | P1 | Slot status toggle (active/maintenance) |
| US-BLD-05 | As an admin, I want to delete slots that are no longer in use. | P1 | Slot deletion |
| US-BLD-06 | As an admin, I want to view available slots filtered by building, floor, and date. | P0 | Available slots API with filters |

### 4.7 Admin — Zone Management

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-ZN-01 | As an admin, I want to create zones that group multiple buildings together. | P0 | Zone CRUD with building assignment |
| US-ZN-02 | As an admin, I want to assign users to zones so that their building access is controlled. | P0 | User assignment within zone management |
| US-ZN-03 | As an admin, I want to add/remove buildings from a zone. | P1 | Building multi-select in zone editor |

### 4.8 Admin — Parking Configuration

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-CFG-01 | As an admin, I want to set default parking hours (start/end time) per building. | P0 | Parking config form per building |
| US-CFG-02 | As an admin, I want to configure how many days in advance users can book. | P1 | Booking window days setting |
| US-CFG-03 | As an admin, I want to set a release time (when slots become bookable each day). | P1 | Release time field |
| US-CFG-04 | As an admin, I want to enable/disable automatic no-show slot release. | P2 | Toggle for auto-release with time offset |
| US-CFG-05 | As an admin, I want to enable main building exclusivity for a building so that only assigned employees can park there. | P1 | `main_building_exclusive` toggle in parking config |

### 4.9 Admin — Reports & Analytics

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-RPT-01 | As an admin, I want to view a dashboard with total reservations, active users, occupancy rate, and building breakdown. | P0 | Stats API with summary and per-building data |
| US-RPT-02 | As an admin, I want to filter reports by date range and building. | P1 | Date range and building filter on reports page |
| US-RPT-03 | As an admin, I want to generate AI-powered insights from parking data so that I can identify trends. | P2 | AI insights generation with markdown rendering |
| US-RPT-04 | As an admin, I want to view a history of previously generated insights. | P2 | Insights history tab with timestamps |
| US-RPT-05 | As an admin, I want to view all reservations across buildings with search and filter. | P1 | Admin reservations table with status filters |

### 4.10 Admin — Event Blocking

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-EVT-01 | As an admin, I want to block multiple parking slots for a specific date and time range for an event, so that those slots are unavailable to regular users during the event. | P0 | Visual slot map for selecting slots; blocked slots become confirmed reservations with `booking_type: event_block`; slots appear as taken in the booking grid |
| US-EVT-02 | As an admin, I want to name an event block and provide a reason, so that the purpose of the blocked slots is documented. | P0 | Event name and reason fields required |
| US-EVT-03 | As an admin, I want to view all active event blocks and delete them when no longer needed, so that slots are released back to users. | P1 | Event block list with name, date, time, slot count; delete action removes all associated reservation records |

### 4.11 Admin — Site Customization

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-SITE-01 | As an admin, I want to customize the login page heading, description, and badges so that the app reflects our brand. | P2 | Site content editor in admin settings |

### 4.12 Admin — Building Policies

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-POL-01 | As an admin, I want to create a dedicated-slot policy for a building so that certain slots are reserved for specific users and vehicles. | P0 | Policy CRUD per building, policy_type field |
| US-POL-02 | As an admin, I want to require parking stickers for a building so that only registered vehicles can park there. | P1 | `requires_sticker` toggle on policy |
| US-POL-03 | As an admin, I want to register users and their vehicles to specific slots so that assignments are enforced. | P0 | Slot registration CRUD with user, vehicle_plate, sticker_number |
| US-POL-04 | As an admin, I want to designate open floors within a policy building so that unregistered users can still park on those floors. | P1 | `open_floor_ids` list on policy |
| US-POL-05 | As an admin, I want the user selection dropdown to be filtered by the building's zone when assigning slot registrations. | P1 | Zone-filtered user list |
| US-POL-06 | As an admin, I want to select a vehicle from the user's registered vehicles (dropdown) when assigning a slot registration. | P1 | Vehicle dropdown populated from user's vehicles |

### 4.13 Parking Attendant

| ID | User Story | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| US-ATT-01 | As an attendant, I want to view all reservations for a specific date and building so that I can manage daily parking. | P0 | Daily reservation list with building filter |
| US-ATT-02 | As an attendant, I want to confirm a reservation when a car arrives so that occupancy is tracked. | P0 | Confirm button, status changes to "confirmed" |
| US-ATT-03 | As an attendant, I want to report a no-show for users who don't arrive by a certain time, only for today or past dates. | P0 | No-show button (hidden for future dates), backend date validation |
| US-ATT-04 | As an attendant, I want to quickly return to today's date from any viewed date. | P2 | "Today" button in date navigator |
| US-ATT-05 | As an attendant, I want to scan a QR code to verify a reservation. | P1 | QR scan endpoint returns reservation details |
| US-ATT-06 | As an attendant, I want to see summary cards (Reserved, Confirmed, No Shows) for the current day. | P1 | Status summary cards on attendant dashboard |

---

## 5. Business Rules

| Rule ID | Rule | Enforcement |
|---------|------|-------------|
| BR-01 | A user must have at least one registered vehicle to book a parking slot. | Frontend validation + backend check |
| BR-02 | A slot can only be booked by one user per date/time range — no double-booking. | Backend atomic check on slot+date+status |
| BR-03 | Booking in a non-main building (within zone) is limited to single-day and requires a reason. | Backend validation on booking type |
| BR-04 | Blocked users cannot log in or make reservations. | Auth check on login, booking endpoints |
| BR-05 | No-show can only be reported for reservations on today or past dates. A `no_show_at` timestamp is recorded when the no-show is tagged. | Backend date validation, frontend button hidden for future, `no_show_at` stored |
| BR-06 | Sessions expire after 30 minutes. | JWT expiration + cookie max-age |
| BR-07 | VIP/Group Head users have booking priority (tag-based). | Tags stored on user, available for priority logic |
| BR-08 | Slots in "maintenance" status cannot be booked. | Excluded from available slots query |
| BR-09 | Advance booking is limited by building-specific booking window (default 7 days). | Config-driven validation |
| BR-10 | Users must change their temporary password on first login. | `must_change_password` flag enforcement |
| BR-11 | Waitlist notifications expire after a configurable window (default 15 minutes). | Background task checks `notified_at` + window; next user notified on expiry |
| BR-12 | No-show auto-release timing is based on when the reservation is tagged as a no-show (`no_show_at`), not on the reservation end time. | `no_show_at` timestamp set on status change; background task checks elapsed time |
| BR-13 | A vehicle plate number must be unique across the entire system. No two vehicles can share the same plate. | Backend uniqueness check on `POST /api/vehicles` before insert |
| BR-14 | For buildings with a sticker policy, the specific vehicle used for booking must have an active slot registration in that building. User-level registration alone is not sufficient. | Backend checks `vehicle_plate` match in `slot_registrations` during reservation creation |
| BR-15 | For non-open floors in policy buildings, the vehicle must be registered to the specific slot being booked, not just any slot in the building. | Backend checks `slot_id + user_id + vehicle_plate` in `slot_registrations` |
| BR-16 | Admin-initiated cancellations require a mandatory cancellation reason. The parker receives an in-app notification containing the reason. The waitlist is then triggered for the freed slot. | Backend requires `reason` field on admin cancel endpoint; creates notification for parker with reason; then triggers waitlist notification |
| BR-17 | When main building exclusivity is enabled for a building, only users whose `main_building` matches can make reservations. Admins are exempt. | Backend checks `main_building_exclusive` config + user's `main_building` |
| BR-18 | Event blocks create actual reservation records with `booking_type: "event_block"` to prevent double-booking. | Backend creates confirmed reservations per blocked slot |
| BR-19 | Password changes require verification of the current password (except for forced first-login changes). | Backend verifies `current_password` hash match |
| BR-20 | Forgot password requests notify all admin users. Email enumeration is prevented by always returning a success message. | Backend creates notification for each admin, same response regardless of email existence |

---

## 6. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Mobile-responsive UI | Works on 375px+ screens |
| NFR-02 | Page load time | < 3 seconds |
| NFR-03 | API response time | < 500ms for 95th percentile |
| NFR-04 | Concurrent users | 200+ simultaneous |
| NFR-05 | Data security | HttpOnly cookies, bcrypt, CSP headers, password not exposed in DOM |
| NFR-06 | Availability | 99.9% uptime target |
| NFR-07 | Browser support | Chrome, Firefox, Safari, Edge (latest 2 versions) |

---

## 7. Assumptions & Constraints

### Assumptions
- Users are pre-provisioned by admin (no self-registration)
- All buildings and zones are configured by admin before users book
- Internet connectivity is available at all parking locations

### Constraints
- MongoDB as the sole database (no SQL)
- Single-tenant deployment per corporate group
- AI insights require Emergent LLM API key with balance

---

*Next: [System Requirements Specification](../02-system-requirements/SRS.md)*
