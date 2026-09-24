# Cebuana Lhuillier Parking App — User Guide

**Step-by-step instructions for every user type**

This guide covers all three roles in the parking system: **Employee (User)**, **Parking Attendant**, and **Administrator**. Find your role below and follow the steps.

---

## Getting Started (All Users)

### How to Log In

1. Open the parking app in your web browser.
2. On the **Login** screen, enter your **email address** and **password**.
3. Click **Sign In**.
4. If this is your first login (or an admin reset your password), you will be taken to the **Change Password** screen. Set a new password, then continue.

Password rules: at least 8 characters, with at least one uppercase letter, one lowercase letter, and one digit.

### If You Forgot Your Password

1. On the **Login** screen, click **Forgot Password**.
2. Enter your email address and submit.
3. Your administrator is notified to reset your password. They will provide you with a temporary password.
4. Log in with the temporary password; you will be prompted to set a new one.

### How to Log Out

1. Open the menu (top-right of the screen).
2. Click **Log Out**.

---

# Part 1 — Employee (User) Guide

As an employee, you can register your vehicles, book parking slots, manage your reservations, and join a waitlist when a building is full.

## 1.1 Register a Vehicle (do this first)

You must have at least one vehicle registered before you can book parking.

1. From the menu, go to **My Vehicles**.
2. Click **Add Vehicle**.
3. Enter the **plate number**, **make**, **model**, and **color**.
4. Click **Save**.

Notes:
- Each plate number can only be registered once across the whole system.
- You cannot delete a vehicle that has an active or upcoming reservation — cancel the reservation first.

## 1.2 Book a Parking Slot

1. From the menu, go to **Book Parking**.
2. Select the **building** where you want to park.
3. Select the **floor** — you will see a timeline of each slot's availability for the day.
4. Pick an **available slot**.
5. Choose the **date(s)**. You can select up to 7 dates in a single booking.
6. Set the **start time** and **end time** (end time must be after start time).
7. Choose the **vehicle** you will park.
8. Click **Confirm Booking**.

Your reservation is created with status **Pending** and a **QR code** is generated for check-in.

Important booking rules:
- You may only book buildings within your assigned zone or your main building.
- Booking outside your main building is limited to a **single day** and requires a **reason** (unless you are tagged VIP or Group Head).
- Some buildings are restricted to employees whose main building is set to that location.
- Some buildings use a **dedicated-slot policy**, which may require a parking sticker or a slot registered to your specific vehicle.

## 1.3 Check In to Your Reservation

Depending on the building's settings, check-in works one of two ways:

**Self check-in (when attendant mode is off):**
1. Go to **My Reservations**.
2. Open the reservation for today.
3. Click **Check In**. This is only allowed from your start time until the check-in window closes (a few minutes after start).

**Attendant check-in (when attendant mode is on):**
1. Go to **My Reservations** and open the reservation.
2. Show the **QR code** to the parking attendant on arrival. They will scan it to confirm you.

## 1.4 View and Manage Your Reservations

1. From the menu, go to **My Reservations**.
2. Review the list showing building, slot, date, time, and status.
3. To view the entry QR code, open a reservation and tap **Show QR Code**.
4. To cancel, open the reservation and click **Cancel**. You cannot cancel a reservation whose date is already in the past.

Reservation statuses: **Pending**, **Confirmed** (checked in), **Cancelled**, **Completed**, **No-Show**.

## 1.5 Join a Waitlist (when a building is full)

If a building has no slots for your date and the waitlist is enabled:

1. On the **Book Parking** screen, choose the full building and date.
2. Click **Join Waitlist** and confirm your preferred time window.
3. When a slot frees up (someone cancels or is a no-show), the next person on the waitlist is notified in-app.
4. When you get the "Parking Slot Available!" notification, go to **Book Parking** and book within the time window shown (typically 15 minutes).
5. To leave the waitlist, open the waitlist entry and click **Leave Waitlist**.

## 1.6 Set Your Profile and Booking Preferences

1. From the menu, go to **Profile**.
2. Set your **default start time** and **default end time** so bookings pre-fill automatically.
3. Save your changes.

---

# Part 2 — Parking Attendant Guide

As an attendant, you confirm arrivals, scan QR codes, view the day's reservations for your assigned buildings, and report no-shows.

## 2.1 View Today's Reservations

1. Log in and open the **Attendant** dashboard.
2. The **Daily Reservations** list shows today's bookings for your assigned building(s).
3. Use the **date** picker to view another day, and the **building** filter if you cover more than one building.

## 2.2 Confirm an Arrival by Scanning a QR Code

1. Open the **Scan** screen.
2. Ask the driver to show their reservation **QR code**.
3. Scan the code. The system shows the reservation details: driver name, plate number, slot, floor, building, date, and time.
4. Verify the details match the vehicle, then confirm.
5. Optionally, capture a **photo** during confirmation for the record.

The reservation status changes to **Confirmed**.

## 2.3 Confirm an Arrival Manually

1. On the **Daily Reservations** list, find the reservation.
2. Click **Confirm**. Optionally attach a photo.

## 2.4 Report a No-Show

Report a no-show when a driver does not arrive.

1. Find the reservation on the **Daily Reservations** list.
2. Click **Report No-Show**.
3. The reservation is marked **No-Show**, the driver is notified, and their no-show count increases.

Rules:
- You can only report a no-show for a **Pending** or **Confirmed** reservation.
- You cannot report a no-show for a **future** date.

---

# Part 3 — Administrator Guide

As an administrator, you manage users, buildings, zones, parking configuration, policies, attendants, reports, and site content.

## 3.1 Manage Users

1. Go to **Admin → User Management**.
2. To add a user, click **Add User** and enter email, name, company, role, and initial password. Assign buildings, a main building, and tags (e.g., VIP, Group Head) as needed.
3. To edit a user, open their record and update the fields.
4. To reset a password, open the user and click **Reset Password**; provide the temporary password to the user.
5. To block or unblock a user, toggle **Blocked**. Blocked users cannot log in or book.
6. Use bulk actions to set a **main building** or **assign a zone** for many users at once.

## 3.2 Manage Buildings and Floors

1. Go to **Admin → Building Management**.
2. Click **Add Building** and enter its name and details.
3. Within a building, add **floors** and define **parking slots** (labels and statuses).

## 3.3 Configure Parking for a Building

1. Go to **Admin → Parking Configuration**.
2. Select the building.
3. Set options such as **main-building exclusivity**, **waitlist enabled**, and the **waitlist notification window** (minutes).
4. Save.

## 3.4 Set Building Policies

1. Go to **Admin → Building Policies**.
2. Choose a building and enable a policy.
3. For a **dedicated-slot** policy, configure whether a **sticker** is required and which floors are **open** (no fixed slot assignment).
4. Save.

## 3.5 Manage Zones

1. Go to **Admin → Zone Management**.
2. Create a zone and assign one or more **buildings** to it.
3. Assign **users** to the zone. Users can only book buildings within their zone (plus their main building).

## 3.6 Manage Attendants

1. Go to **Admin → Attendant Management**.
2. Create or edit attendant accounts.
3. Assign each attendant the **building(s)** they are responsible for. Attendants only see reservations for their assigned buildings.

## 3.7 Event Blocking

1. Go to **Admin → Event Blocking**.
2. Block out slots, floors, or a building for a date range (e.g., for an event or maintenance) so they cannot be booked.

## 3.8 View Reports

1. Go to **Admin → Reports**.
2. Review usage, occupancy, no-show, and booking statistics.
3. Export data where available for offline analysis.

## 3.9 Manage Reservations (Admin View)

1. Go to **Admin → Reservations**.
2. View and filter all reservations across buildings by building, date, and status.

## 3.10 Site Content and Settings

1. Go to **Admin → Settings** to manage system-wide settings.
2. Use the site-content tools to update in-app text and the built-in **Documentation** page.

---

## Appendix — Reference

### Roles at a Glance

| Role | Can do |
|------|--------|
| Employee (User) | Register vehicles, book slots, check in, cancel, join waitlist, set preferences |
| Attendant | View daily reservations for assigned buildings, scan QR, confirm arrivals, report no-shows |
| Administrator | Manage users, buildings, floors, slots, zones, attendants, policies, config, event blocks, reports, settings |

### Reservation Status Meanings

| Status | Meaning |
|--------|---------|
| Pending | Booked but not yet checked in |
| Confirmed | Driver checked in / arrival confirmed |
| Cancelled | Reservation was cancelled |
| Completed | Reservation finished normally |
| No-Show | Driver did not arrive and was reported |

### Common Rules and Limits

- Up to **7 dates** per booking.
- Off–main-building bookings: **1 day** and a **reason** required (unless VIP/Group Head).
- Plate numbers are **unique** system-wide.
- Cannot delete a vehicle with an active/upcoming reservation.
- Cannot cancel a **past** reservation.
- Self check-in only works within the check-in window after the start time, and only when attendant mode is off.
