# Admin User Guide
**Cebuana Lhuillier Parking Reservation System**  
**Version:** 2.4 | **Last Updated:** May 5, 2026

---

## 1. Overview

As an Admin, you have full control over the Parking Reservation System. Your responsibilities include:
- Managing users (create, edit, block, bulk upload, tag)
- Managing buildings, floors, and parking slots (with floor layout images)
- Configuring zones, parking rules, building policies, and event blocks
- Viewing reports, generating AI insights, exporting reservations
- Managing attendants, site branding, and (where enabled) the active database backend

> **What's new in v2.4** — comprehensive **Policy Capabilities Matrix** (§6), runtime feature flags including AI Insights enable/disable (§10.4) and **Attendant Mode / Self Check-In** (§6.3), database switcher (§14), and floor-layout images now persist on object storage in the production cluster.

---

## 2. Accessing the Admin Panel

1. Log in with your admin credentials.
2. You will be redirected to the **Admin Dashboard** at `/admin`.
3. Use the **sidebar navigation** to access all admin modules.

### Admin Navigation

| Menu Item | Page | Description |
|-----------|------|-------------|
| Dashboard | `/admin` | Overview stats and charts |
| Users | `/admin/users` | User management with bulk actions |
| Buildings | `/admin/buildings` | Building, floor, and slot management |
| Zones | `/admin/zones` | Zone grouping and user assignment |
| Parking Config | `/admin/parking-config` | Per-building booking rules and exclusivity |
| Attendants | `/admin/attendants` | Attendant management |
| Reservations | `/admin/reservations` | View/cancel all reservations (with reason) |
| Event Blocking | `/admin/event-blocking` | Block parking slots for events |
| Reports | `/admin/reports` | Analytics and AI insights |
| Settings | `/admin/settings` | Login page customization |

---

## 3. User Management

### 3.1 Viewing Users
Navigate to **Users** in the sidebar. The user table shows:
- Name, email, company, role
- **Job Family** (e.g., Department Head)
- Main building, tags (VIP/Group Head)
- Status (Active/Blocked)
- Created and updated timestamps

### 3.2 Filtering Users
Use the filter bar above the table:
- **Search** — Type to filter by name, email, or company
- **Role** — Filter by User, Admin, or Attendant
- **Company** — Filter by company name
- **Zone** — Filter by zone assignment (includes "No Zone" option)
- **Main Building** — Filter by building (includes "No Building" option)

The result count updates dynamically as you apply filters.

### 3.3 Creating a Single User
1. Click **"Add User"**.
2. Fill in the form:
   - Email (required, must be unique)
   - First Name, Last Name (required)
   - Company
   - Role (User, Admin, or Attendant)
   - Password
   - **Job Family** (optional — e.g., "Department Head", "Manager", "Staff")
   - Main Building (optional)
   - Assigned Buildings (for attendants)
   - Default Start/End Time (optional)
3. Click **Save**.

The user will be created with `must_change_password: true` and must change their password on first login.

### 3.4 Bulk Uploading Users
1. Click **"Bulk Upload"** in the User Management page.
2. Optionally click **"Download Template"** to get a CSV template with the correct columns.
3. Prepare your CSV with columns:
   - `email` (required)
   - `first_name` (required)
   - `last_name` (required)
   - `company` (optional)
   - `role` (optional, defaults to "user")
   - `job_family` (optional — e.g., "Department Head")
   - `main_building` (optional — use the **building name**, the system resolves it to the building ID)
   - `zone` (optional — use the **zone name**, the system automatically assigns users to the zone)
4. Set a **default password** for all new users.
5. Select the file and click **Upload**.
6. Review the upload summary showing created, skipped (duplicate emails), zone assignments, and any errors.

### 3.5 Bulk Actions (Multi-Select)
1. Use the **checkboxes** in the user table to select multiple users.
2. Or click **"Select all X filtered"** to select all users matching the current filter.
3. The **bulk action bar** appears with options:
   - **Set Main Building** — Assign a main building to all selected users
   - **Assign to Zone** — Add all selected users to a specific zone

### 3.6 Individual User Actions
Click the **actions dropdown** (three dots) on any user row to:
- **Edit** — Modify user details
- **Reset Password** — Set a new temporary password (user must change on next login)
- **Block / Unblock** — Prevent or restore user access
- **Set Tags** — Assign VIP or Group Head tags
- **Delete** — Permanently remove the user

### 3.7 Tags
Tags grant special privileges:
- **VIP** — Can book multi-day reservations in non-main buildings (within zone) without the single-day restriction
- **Group Head** — Same privileges as VIP

---

## 4. Building Management

### 4.1 Creating a Building
1. Navigate to **Buildings**.
2. Click **"Add Building"**.
3. Enter:
   - Building name
   - Address
   - Number of floors
   - Slots per floor (auto-generated with prefix)
   - Slot prefix (e.g., `F1-` for Floor 1 → slots `F1-1`, `F1-2`, etc.)
4. Click **Create**.

Floors and slots are automatically created.

### 4.2 Managing Floors
Each building card shows its floors. For each floor you can:
- **Add Floor** — Create a new floor with custom slot labels or auto-generated slots
- **Upload Layout** — Upload a floor plan image (PNG, JPG, JPEG, GIF, WebP; max 10MB)
- **Delete Layout** — Remove the floor plan image

### 4.3 Managing Slots
Within each floor, you can see all parking slots. For each slot:
- **Rename** — Change the slot label
- **Block (Maintenance)** — Mark as under maintenance; the slot becomes unavailable for booking
- **Unblock** — Restore the slot to active status
- **Delete** — Permanently remove the slot (only if no active reservations)

### 4.4 Adding Slots to an Existing Floor
1. Click **"Add Slots"** on the floor card.
2. Either:
   - Enter **custom labels** (comma-separated, e.g., `VIP-1, VIP-2, VIP-3`)
   - Or specify a **count** with an auto-prefix
3. Click **Add**.

### 4.5 Deleting a Building
Click **Delete** on the building card. This will **cascade delete** all floors and slots within the building.

> **Warning:** This operation is irreversible. Ensure no active reservations exist for the building's slots.

---

## 5. Zone Management

Zones group buildings together and control which users can book in which buildings.

### 5.1 Creating a Zone
1. Navigate to **Zones**.
2. Click **"Create Zone"**.
3. Enter a zone name (e.g., "Metro Manila Zone").
4. Select the **buildings** to include in the zone.
5. Select the **users** to assign to the zone.
6. Click **Create**.

### 5.2 Editing a Zone
Click **Edit** on a zone card to:
- Rename the zone
- Add or remove buildings
- Add or remove users

### 5.3 Zone Booking Rules
- Users assigned to a zone can book in **any building** within that zone.
- Booking in a building that is **not** the user's main building requires:
  - **Single-day** booking only
  - A **reason** for the visit
- VIP/Group Head users are exempt from the single-day restriction.
- Users **cannot** book in buildings outside their assigned zones.

### 5.4 Deleting a Zone
Click **Delete** on the zone card. This removes the zone but does not delete the buildings or users.

---

## 6. Policy Capabilities Matrix

The platform exposes **five layers of configurable policy**. Use this matrix to find the right place to enforce a rule before reaching for a workaround. Every cell links to the section that explains *how* to configure it.

| Layer | What it controls | Where to configure | Highlights |
|---|---|---|---|
| **System-wide** | Site branding, login content, optional features (AI Insights, Attendant Mode), active database | Settings (§11) · System badge (§14) · Feature flags (§6.3) | Tri-state feature flag for AI Insights · Attendant Mode toggle with configurable self-check-in window · live login-page content editor · multi-DB support (MongoDB / Couchbase Capella / Couchbase Enterprise) |
| **Zone** | Which users can book in which buildings; main-building rules | Zones (§5) | Group buildings into zones · zone-restricted bookings · "main building" assignment per user · single-day / reason-required cross-zone bookings |
| **Building (operational)** | Per-building booking knobs that change behaviour daily | Parking Config (§7) | Booking window, release time, default times, no-show auto-release, **waitlist on/off**, **main-building exclusivity**, notification windows |
| **Building (policy)** | Per-building access rules tied to vehicles & slots | Building Policies (§12) | **Sticker enforcement** · **slot-level vehicle binding** · **open floors** · **per-slot user assignment** · zone-filtered user picker |
| **Time-bound override** | Reserve N slots for a specific event window | Event Blocking (§13) | Block any combination of slots on a floor for a date/time range · stamped with name + reason · auto-frees on delete |

### 6.1 Quick reference — "I want to…"

| I want to… | Use this layer | Specific setting |
|---|---|---|
| Stop people from booking 30 days ahead | Building (operational) | `booking_window_days` — caps at 1–30, default 7 |
| Free a slot automatically when someone doesn't show up | Building (operational) | `no_show_release_enabled` + `no_show_release_minutes` |
| Let users queue up when a building is full | Building (operational) | `waitlist_enabled` + `waitlist_notification_window_minutes` |
| Restrict a building to "home base" employees only | Building (operational) | `main_building_exclusive: true` |
| Tie a parking sticker to one specific vehicle | Building (policy) | `requires_sticker: true` + slot registration with vehicle plate |
| Let one designated user own slot B1-03 with vehicle ABC1234 | Building (policy) | Slot registration (user + vehicle plate per slot) |
| Make floor 4 a free-for-all (no slot ownership) | Building (policy) | Add floor to `open_floor_ids` |
| Reserve 12 slots for the board meeting next Friday | Time-bound override | Event Blocking → pick slots → name + reason |
| Let only Manila employees book Manila buildings | Zone | Create Zone "Manila", assign buildings + users |
| Hide AI Insights from the admin UI in air-gapped deployments | System-wide | `AI_INSIGHTS_ENABLED=false` env var (§9.4) |

### 6.2 Validation order (so you can predict what happens)

Whenever a user tries to book, the system checks rules **in this order** and stops at the first failure with a clear error message:

1. **Auth & block status** — user is logged in and not blocked.
2. **Vehicle ownership** — the chosen vehicle belongs to the user; plate is globally unique.
3. **Time guards** — date is within `booking_window_days`; not in the past; not overlapping another reservation; not before `release_time`.
4. **Zone access** — the building lives in a zone the user is in.
5. **Main-building exclusivity** — if the building has `main_building_exclusive: true`, the user's `main_building` must equal this building (admins exempt).
6. **Cross-zone single-day rule** — booking in a non-main building → date range must be a single day, reason required (VIPs exempt).
7. **Building policy** — sticker required? Vehicle has a slot registration in this building? On a non-open floor, is the vehicle bound to *this specific slot*?
8. **Event block** — slot isn't already locked by an event block for the requested time window.
9. **Slot availability** — slot is `available` and not currently held by another reservation.

Knowing the order helps you give users accurate guidance: "you got error X, so checks 1–N already passed."

### 6.3 Attendant Mode vs. Self Check-In

The platform supports **two arrival-confirmation modes**, set via a single environment variable on the backend (`ATTENDANT_MODE_ENABLED`). The mode is read live by both backend and frontend through `GET /api/system/features`, so changes take effect on the next page load — no rebuild.

| Mode | Toggle | What happens when the parker arrives |
|---|---|---|
| **Attendant Mode** (default) | `ATTENDANT_MODE_ENABLED=true` (or unset) | On-site attendants log into the Attendant Dashboard, see today's reservations, scan/confirm arrivals, or report no-shows. The auto-no-show loop sweeps any reservation whose `end_time` has passed without confirmation. |
| **Self Check-In** | `ATTENDANT_MODE_ENABLED=false` | Attendants are not used at this site. The parker sees a **"Check in"** button on their reservation card that becomes active at `start_time` and stays active for `SELF_CHECKIN_WINDOW_MINUTES` (default **15**, configurable 5–240). Tapping it confirms the slot. If the window elapses with no tap, a background loop marks the reservation as no-show, **releases the slot immediately**, and notifies the next person on the waitlist. |

**Where the check-in button appears**

- User → **My Reservations** page → today's PENDING reservation card → green **"Check in"** button on the right of the row.
- Visible only when (a) the system is in Self Check-In mode, (b) the reservation is the parker's own, (c) current time is between `start_time` and `start_time + SELF_CHECKIN_WINDOW_MINUTES`.

**Error messages your parkers will see**

| Situation | HTTP | Message |
|---|---|---|
| Too early — start_time hasn't arrived | 400 | "Too early to check in. Your reservation starts in ~N minutes." |
| Inside the window, success | 200 | "Checked in — your slot is confirmed." |
| Tapped twice (idempotent) | 200 | "Already checked in" |
| Window has expired | 410 | "Check-in window has expired (N min after start). The slot will be released shortly." |
| Mode is currently in attendant mode | 403 | "Self check-in is disabled. An attendant will confirm your arrival." |

**Choosing the window length**

- 15 min (default) — typical for office buildings; gives drivers a buffer for traffic / finding the entrance.
- 5 min — high-demand sites where you want the slot to recycle fast.
- 30–60 min — sites with long approach roads or strict gate procedures.

**No-show behaviour**

Whichever mode you're in, a no-show:
1. Sets reservation status to `no_show`.
2. Increments the user's `no_show_count` (visible to admins on the Users page).
3. Sends an in-app notification to the parker.
4. Frees the slot — **immediately** in Self Check-In mode, or after `no_show_release_minutes` if attendant mode is on and the building has `no_show_release_enabled`.
5. Calls the waitlist notifier — the next person on the waitlist for that building/date gets an in-app notification that a slot is now available.

**Operational tip**: switching from attendant mode to self check-in is a configuration change, not a feature deployment — you can A/B different buildings by spinning up two backend pods with different env vars and routing traffic accordingly. Most customers won't need that; one flag for the whole estate is fine.

---

## 7. Parking Configuration

Configure booking policies per building.

### 7.1 Editing Configuration
1. Navigate to **Parking Config**.
2. Select a **Building**.
3. Configure:

| Setting | Description | Default |
|---------|-------------|---------|
| Default Start Time | Pre-filled start time for bookings | 08:00 |
| Default End Time | Pre-filled end time for bookings | 18:00 |
| Release Time | Time when slots become bookable each day | 06:00 |
| Booking Window (days) | How many days in advance users can book | 7 |
| Auto No-Show Release | Automatically release slots from no-show reservations | Off |
| No-Show Release Minutes | Minutes after being tagged as no-show before slot is released | 30 |
| **Waitlist Enabled** | Allow users to join a waitlist when all slots are booked | Off |
| **Waitlist Notification Window (min)** | Minutes a notified waitlist user has to book before the slot is offered to the next person | 15 |
| **Main Building Exclusive** | Restrict reservations in this building to only users for whom it is their assigned main building. Admins are always exempt. | Off |

4. Click **Save**.

### 7.2 Auto No-Show Behavior
When enabled, a background task runs every 5 minutes that:
1. Marks **pending** reservations as **no-show** if the date has passed or the end time has elapsed.
2. Records a **`no_show_at` timestamp** on the reservation (the moment it was tagged as no-show).
3. Sends a notification to the user about the no-show.
4. Increments the user's no-show count.
5. After the configured release minutes **from the `no_show_at` timestamp** (not from the reservation end time), releases the slot back to "available" status.

### 7.3 Waitlist Behavior
When waitlist is enabled for a building:
1. Users who find all slots booked can **join a waitlist** for a specific building and date.
2. When a slot becomes available (due to cancellation or no-show release), the system automatically **notifies the next person** on the waitlist via an in-app notification.
3. The notified user has a **configurable time window** (default 15 minutes) to book a slot.
4. If they don't book within the window, a background task marks their waitlist entry as **expired** and notifies the **next user** in line.
5. Admins can view the full waitlist for any building via the admin waitlist management panel.

---

## 8. Attendant Management

### 8.1 Managing Attendants
Navigate to **Attendants** to view and manage parking attendant accounts. Attendants can be assigned to specific buildings to limit their view.

### 8.2 Assigning Buildings to Attendants
When creating or editing an attendant user:
1. Click **Add Attendant** or the edit button on an existing attendant.
2. Fill in the required fields (name, email, password).
3. In the **Assigned Buildings** section, check one or more buildings from the list.
4. At least one building **must** be selected — the Create/Save button is disabled otherwise.
5. Selected buildings appear as badges below the checklist.
6. Click **Create** or **Update** to save.

> **Note:** Attendants can now be assigned to **multiple buildings** simultaneously. Use the checkbox list to select all buildings the attendant should have access to.

---

## 9. Reservations (Admin View)

### 9.1 Viewing All Reservations
Navigate to **Reservations** to see all reservations across all buildings.

### 9.2 Filtering
Filter by:
- **Building**
- **Date**
- **Status** (All, Pending, Confirmed, Cancelled, No Show)
- **Search** (user name, email)

### 9.3 Admin Cancellation

Click **Cancel** on any active reservation to cancel it on behalf of a user.

1. A **Cancellation Reason** dialog will appear. You **must** provide a reason before confirming.
2. Click **Confirm Cancellation**.
3. The reservation status changes to **Cancelled**.
4. The parker automatically receives an **in-app notification** containing your cancellation reason.
5. If waitlist is enabled for the building, the next person on the waitlist is notified that a slot has become available.

---

## 10. Reports & Analytics

### 10.1 Dashboard Stats
The Admin Dashboard shows:
- **Total Reservations, Confirmed, Cancelled, Pending, No-Shows**
- **Buildings Count, Total Slots, Active Users**
- **Occupancy Rate**
- **Daily Breakdown Chart** — Reservations over time
- **Building Breakdown** — Reservations per building

### 10.2 Filtering Reports
On the Reports page:
1. Set a **date range** (Start Date / End Date).
2. Optionally filter by **Building**.
3. Stats update automatically.

### 10.3 AI-Powered Insights
1. On the Reports page, click **"Generate AI Insight"**.
2. Optionally select a building for building-specific analysis.
3. The system sends parking data to an AI model and returns **3-5 actionable business insights**.
4. Insights are saved to history and displayed in markdown format.

> **Note:** AI Insights call out to a hosted LLM. The feature is governed by the `AI_INSIGHTS_ENABLED` runtime flag (§10.4).

### 10.4 Enable / Disable AI Insights

AI Insights is the **only** feature that requires public-internet egress. Ops can flip it without rebuilding images:

| Posture | Server config | UI behaviour |
|---|---|---|
| Force on | `AI_INSIGHTS_ENABLED=true` | "AI Insights" button visible · button works if LLM key is set, else returns a clear error at click time |
| Force off | `AI_INSIGHTS_ENABLED=false` | Button hidden on Dashboard · Insights card hidden on Reports · API returns `503 disabled` |
| Auto (default) | unset | Auto-enabled iff `EMERGENT_LLM_KEY` is non-empty |

The frontend reads the live state from `GET /api/system/features` on tab load — no rebuild required when Ops flips the flag.

### 10.5 Insights History
Click the **"History"** tab on Reports to view previously generated insights. You can delete old insights.

---

## 11. Site Customization (Settings)

### 11.1 Login Page Branding
Navigate to **Settings** to customize the login page:
- **Heading Line 1** — First line of the heading
- **Heading Highlight** — Highlighted (colored) word
- **Heading Line 3** — Third line of the heading
- **Description** — Subtitle text
- **Badge 1 Text** — First feature badge
- **Badge 2 Text** — Second feature badge
- **Announcement** — Optional announcement banner

Click **Save** to apply changes. The login page updates immediately.

---

## 12. Building Policies

Building policies allow admins to configure special parking rules for specific buildings (e.g., reserved spots for designated users and vehicles).

### 12.1 Policy Management
Navigate to **Building Policies** (or the building-specific policy page) to configure:
- **User Assignment** — Select users who are allowed to book specific slots. The user dropdown is **filtered by the building's zone**, showing only users assigned to the relevant zone.
- **Vehicle Selection** — Instead of typing a vehicle registration manually, use the **vehicle registration dropdown** to select from the user's registered vehicles.

### 12.2 Zone-Filtered User Selection
When assigning users to a building policy:
- The system automatically filters the user list to show only users who belong to the **same zone** as the building.
- This prevents assigning users from unrelated zones to building-specific policies.

### 12.3 Vehicle-Level Sticker Enforcement
For buildings with `requires_sticker` enabled:
- During booking, the system validates the **specific vehicle** selected — not just the user. The vehicle's plate number must have an active slot registration in the building.
- If a user has multiple vehicles but only one is registered, they can only book with the registered vehicle.
- Error message example: *"Vehicle ABC1234 does not have a parking sticker/registration for this building."*

### 12.4 Slot-Level Vehicle Enforcement
For non-open floors in policy buildings:
- The system validates that the **specific vehicle** is registered to the **specific slot** being booked.
- A user may be registered to slot B1-03 with vehicle ABC1234 — they can only book B1-03 with that vehicle, not B1-01.
- Error message example: *"Vehicle ABC1234 is not registered to this parking slot."*

### 12.5 Open Floors
Floors listed in the policy's `open_floor_ids` bypass the strict slot-assignment check. Any user with a valid building registration can book any available slot on an open floor.

### 12.6 Plate Number Uniqueness
The system enforces **global plate number uniqueness**: no two vehicles across any users can share the same plate number. If an admin or user tries to register a vehicle with a plate already in the system, it is rejected with a clear error message.

---

## 13. Event Blocking

The **Event Blocking** module allows you to reserve multiple parking slots for corporate events, preventing regular users from booking those slots during the event period.

### 13.1 Creating an Event Block

1. Navigate to **Event Blocking** in the admin sidebar.
2. Select a **Building** and **Floor**.
3. Set the **Event Date**, **Start Time**, and **End Time** for the event.
4. The **slot map** will appear, showing available (green) and already-booked (red) slots. Click one or more available slots to select them.
5. Enter an **Event Name** (e.g., "Board Meeting") and a **Reason** (e.g., "Reserved for executive parking").
6. Click **Block Slots**.

The selected slots are immediately blocked — they will appear as unavailable in the regular booking interface for that date and time.

### 13.2 Viewing Event Blocks

The page displays a list of all active event blocks with:
- Event name and reason
- Building, floor, and slot count
- Date and time range
- Number of slots blocked

### 13.3 Deleting an Event Block

1. Find the event block in the list.
2. Click the **Delete** button.
3. Confirm deletion.

All reservation records associated with the event block are removed, freeing the slots back to regular users.

> **Note:** Deleting an event block does **not** cancel individual user reservations. It only removes the event-block-type reservations that were created specifically for the event.

---

## 14. Database & System Health (multi-DB awareness)

The platform supports two database backends interchangeably; the active one is selected at deploy time. Every admin page shows a small **DB badge** in the sidebar:

- **Green / "MongoDB"** — local or in-cluster MongoDB. Typical for staging.
- **Red / "Couchbase Capella"** or **"Couchbase Enterprise"** — managed Capella cloud or self-hosted on-prem cluster. Typical for production / HCS.

### 14.1 Health card

The **Database Health Card** on the Dashboard shows live connection status, host, bucket/database name, and per-collection document counts. Use it to:
- Verify a fresh deployment connected to the right cluster.
- Spot a misrouted environment (e.g. UAT pod accidentally pointing at prod).
- Check post-migration row counts after a Mongo→Couchbase mirror.

### 14.2 Switching backend

In production this is an **infrastructure change** (edit ConfigMap → restart pods), not an in-app toggle — see the deployment runbook. The app itself simply reads `DB_TYPE` at startup.

> **Floor-layout images** are stored separately (Huawei OBS or local volume, depending on deployment). They survive pod restarts and replica scaling. No admin action needed.

---

## 15. Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot create user (email exists) | Email must be unique across the system. Check for existing users with the same email. |
| AI Insights button missing | The deployment has `AI_INSIGHTS_ENABLED=false` (see §10.4) or `EMERGENT_LLM_KEY` is empty in auto-mode. Ask Ops to flip the flag if business approves the LLM call. |
| Floor-layout image uploads correctly but doesn't appear after pod restart | In OBS-backed deployments, image is fetched via `/api/uploads/...`. Hard-refresh the browser. If 404 persists, the OBS bucket / credentials may be misconfigured — check pod logs. |
| Database badge says "MongoDB" but you expect Couchbase | Wrong `DB_TYPE` env var on the pod, or wrong ConfigMap applied. Compare with the deployment runbook. |
| Bulk upload skipping users | Users with emails already in the system are automatically skipped. Check the summary report. |
| Cannot block slot (active reservations) | Cancel active reservations for the slot before setting it to maintenance. |
| AI insights not working | Ensure the EMERGENT_LLM_KEY is configured and has sufficient balance. |
| Zone changes not reflected | Users may need to refresh their browser to see updated zone assignments. |
| Waitlist not available | Ensure waitlist is enabled in the building's Parking Config settings. |
| Duplicate plate number error | The plate is already registered to another vehicle. Check the existing vehicles list to resolve. |
| "Vehicle does not have sticker" error | The vehicle's plate must have an active slot registration in the building. Go to Building Policies to add the registration. |
| "Vehicle not registered to slot" error | For non-open floors, the vehicle must be assigned to the specific slot. Update the slot registration with the correct vehicle. |
| Users cannot book in exclusive building | Ensure their `main_building` is set correctly. Or disable Main Building Exclusive in Parking Config. |
| Event block slot not visible | Ensure the correct building, floor, and date are selected. Already-booked slots are shown in red and cannot be blocked. |
| Event block delete not releasing slots | Only event-block-type reservations are removed. Regular user reservations are not affected. |

---

*Related: [End User Guide](end-user-guide.md) | [Attendant Guide](attendant-guide.md)*
