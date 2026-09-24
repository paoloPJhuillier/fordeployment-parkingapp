# End User Guide
**Cebuana Lhuillier Parking Reservation System**  
**Version:** 2.4 | **Last Updated:** May 5, 2026

---

## 1. Getting Started

### 1.1 Accessing the System
Open your web browser and navigate to the Parking Reservation System URL provided by your administrator. The system works on desktop and mobile browsers.

> **What you can and can't do here**
> - ✅ Book a slot in any building inside your zone (within the booking window your admin has set).
> - ✅ Join a waitlist when a building is full (if waitlist is turned on for that building).
> - ✅ Cancel an upcoming reservation. Past reservations are read-only.
> - ✅ Manage your own vehicles and default booking times.
> - ❌ Book on behalf of someone else, change another user's reservation, or book outside your zone — that's an admin action.

### 1.2 Logging In
1. Enter your **corporate email** and **password** on the login page.
2. Click **Sign In**.
3. You will be redirected to your **Dashboard**.

> **First-time login:** If this is your first login, you will be prompted to change your temporary password. Enter a new password and confirm it to proceed.

### 1.3 Session Timeout
Your session automatically expires after **30 minutes** of inactivity. You will be redirected to the login page and need to sign in again.

### 1.4 Logging Out
Click the **Logout** button in the sidebar or navigation menu. Your session will be securely terminated.

---

## 2. Dashboard

After logging in, your dashboard displays:

| Section | Description |
|---------|-------------|
| **Stats Cards** | Quick overview of your reservations (Active, Confirmed, Cancelled, No-Shows) |
| **Buildings Card** | Number of buildings available in your zone |
| **My Vehicles** | Your registered vehicle(s) with a link to manage them |
| **Active Reservations** | Upcoming and current reservations |
| **History** | Past and cancelled reservations |

### 2.1 Navigating the Dashboard
- Click **"Book Now"** to create a new parking reservation.
- Click **"Manage >"** on the vehicles card to go to vehicle management.
- Use the **Active** and **History** tabs to switch between current and past reservations.
- Click the **logo** at any time to return to the dashboard.

---

## 3. Vehicle Management

You must register at least one vehicle before making a parking reservation.

### 3.1 Adding a Vehicle
1. Navigate to **Vehicles** from the sidebar or dashboard.
2. Click **"Add Vehicle"**.
3. Fill in the details:
   - **Plate Number** (required) — e.g., `ABC-1234`. Must be unique across the system — no other user can have a vehicle with the same plate number.
   - **Make** — e.g., `Toyota`
   - **Model** — e.g., `Vios`
   - **Color** — e.g., `White`
4. Click **Save**.

> **Note:** If the plate number is already registered to another vehicle in the system, the registration will be rejected. Contact your administrator if you believe this is an error.

### 3.2 Deleting a Vehicle
1. Go to the **Vehicles** page.
2. Find the vehicle you want to remove.
3. Click the **Delete** button on the vehicle card.
4. Confirm the deletion.

> **Note:** You cannot delete a vehicle that has active reservations.

---

## 4. Booking a Parking Spot

### 4.1 Creating a Reservation
1. Click **"Book Now"** from the dashboard or navigate to the **Booking** page.
2. **Select a Building** — Choose from the buildings available in your zone.
3. **Select a Floor** — Pick the floor where you want to park.
4. **Select Date(s)** — Click on one or more dates on the calendar. You can select up to **7 individual dates** in a single booking.
5. **Select Time** — Set your **Start Time** and **End Time**. Default times may be pre-filled based on your preferences or building configuration.
6. **Select a Slot** — Available slots are shown in green. Taken slots are red. Maintenance slots are gray. Click an available slot.
7. **Review Hourly Timeline** — After selecting a slot, an **hourly timeline** (6AM–10PM) appears showing which hours are already booked and which are available. This helps you verify your chosen time range doesn't conflict with existing bookings.
8. **Select a Vehicle** — Choose which of your registered vehicles you'll use.
9. Click **"Confirm Booking"**.

### 4.2 Booking Rules

| Rule | Description |
|------|-------------|
| **Main Building** | You can book freely in your assigned main building with no restrictions. |
| **Other Buildings (within zone)** | You can book in other buildings within your zone, but only for **one day at a time** and you must provide a **reason**. |
| **Outside Zone** | You cannot book in buildings outside your assigned zone. Contact your admin if you need access. |
| **VIP/Group Head** | If you have VIP or Group Head status, the single-day restriction for non-main buildings is waived. |
| **Time Overlap** | You cannot have two bookings that overlap in time on the same date. |

### 4.3 QR Code
After booking, a **QR code** is generated for each reservation. The parking attendant will scan this to verify your reservation when you arrive.

To view your QR code:
1. Go to your **Reservations** page.
2. Find the reservation.
3. Click the **QR code icon** to view and present it.

### 4.4 Confirming Your Arrival — Self Check-In

How you confirm your arrival depends on what your administrator has turned on for your site.

#### Attendant Mode (default)
An on-site parking attendant scans your QR code (or confirms your name on the daily list) when you park. You don't need to do anything in the app.

#### Self Check-In Mode
If your site doesn't use attendants, **you check yourself in** through the app:

1. On the day of your reservation, open **My Reservations**.
2. As soon as your reservation start time arrives, a green **"Check in"** button appears on that reservation card.
3. Tap **Check in**. Your slot is now confirmed.
4. **Important — you have a limited window.** Your admin configures the window (default **15 minutes** after your start time). If you don't check in within that window:
   - Your reservation is automatically marked as a no-show.
   - Your slot is released for someone else (and the next person on the waitlist is notified).
   - Your no-show count increases.

> **Tip:** if you're going to be late beyond the check-in window, **cancel the reservation** before your start time. That gives someone else a fair shot at the slot and avoids the no-show on your record.

You can tell which mode is active because, in Self Check-In mode, the green **"Check in"** button appears next to your reservation. In Attendant Mode, only the QR-code icon shows.

### 4.5 Waitlist
If all slots are fully booked for your desired date, you may be able to **join a waitlist** (if the building's admin has enabled it).

1. On the Booking page, if no slots are available, a **"Join Waitlist"** option appears.
2. Click it to add yourself to the queue for that building and date.
3. When a slot becomes available (due to a cancellation or no-show), the **next person on the waitlist** is notified via the in-app notification bell.
4. You will have a **limited time window** (configured by your admin, default 15 minutes) to go to the Booking page and reserve the available slot.
5. If you don't book within the window, the opportunity passes to the next person on the waitlist.

To leave the waitlist, go to your waitlist entry and click **Cancel**.

### 4.6 Building Policy Restrictions
Some buildings have a **dedicated slot policy** that enforces stricter rules:

- **Sticker/Registration Required:** If a building requires parking stickers, the **specific vehicle** you select for your booking must have an active registration in that building. It is not enough for you as a user to be registered — your vehicle's plate number must match a slot registration.
- **Assigned Slots:** On non-open floors, you can only book the **specific slot** your vehicle is registered to. You cannot book someone else's assigned slot.
- **Open Floors:** Some floors within a policy building may be marked as "open," meaning any registered user can book any available slot on that floor.

If you see a 403 error when booking, check with your administrator that your vehicle is registered to the correct building and slot.

---

## 5. Managing Reservations

### 5.1 Viewing Reservations
Navigate to **Reservations** from the sidebar. You'll see two tabs:
- **Active** — Upcoming and current reservations (status: Pending or Confirmed).
- **History** — Past, cancelled, and no-show reservations.

Each reservation card shows:
- Building name, floor, and slot label
- Date and time range
- Vehicle plate number
- Status badge (Pending, Confirmed, Cancelled, No Show)

### 5.2 Cancelling a Reservation
1. Find the reservation on your dashboard or Reservations page.
2. Click the **Cancel (X)** button.
3. Confirm the cancellation.

The slot is immediately freed for other users.

### 5.3 Reservation Statuses

| Status | Meaning |
|--------|---------|
| **Pending** | Reservation created, awaiting your arrival |
| **Confirmed** | Parking attendant confirmed your arrival |
| **Cancelled** | You or an admin cancelled the reservation |
| **No Show** | You did not arrive and the attendant or system marked it as a no-show |

---

## 6. Notifications

The **notification bell** in the top-right of the header shows your unread notification count.

Click the bell to see recent notifications. You'll receive notifications for:
- Booking confirmations
- Reservation cancellations (including admin-initiated cancellations with the reason provided by the admin)
- No-show warnings
- Waitlist slot available alerts

### 6.2 Viewing Full Notification Content
Click on any notification in the dropdown to open a **detail dialog** showing:
- Full notification title and message
- Timestamp of when it was sent
- Action buttons (e.g., "Book Now" for waitlist notifications)

Click **"Mark all as read"** to clear the unread count.

---

## 7. Profile & Preferences

### 7.1 Viewing Your Profile
Navigate to **Profile** from the sidebar. Your profile shows your name, email, company, and role.

### 7.2 Setting Default Booking Times
1. Go to your **Profile** page.
2. Set your preferred **Default Start Time** and **Default End Time**.
3. Click **Save**.

These times will auto-fill when you create new bookings, saving you time.

### 7.3 Changing Your Password

You can change your password at any time from the Profile page.

1. Go to your **Profile** page.
2. Scroll to the **Change Password** section.
3. Enter your **Current Password**.
4. Enter your **New Password**.
5. Enter your new password again in **Confirm New Password**.
6. Click **Change Password**.

> **Note:** You must provide your current password to verify your identity before setting a new one. If you have forgotten your current password, use the **Forgot Password** option on the login page.

### 7.4 Forgot Password

If you cannot log in because you have forgotten your password:

1. Go to the **Login** page.
2. Click the **"Forgot Password?"** link below the login form.
3. Enter your **corporate email address**.
4. Click **Submit**.

A notification will be sent to your administrator. Your admin will reset your password and provide you with a temporary one. You will be prompted to change it again on your next login.

> **Note:** For security reasons, the system always shows a success message regardless of whether the email you entered exists in the system.

---

## 8. Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid credentials" on login | Double-check your email and password. Contact your admin to reset your password if needed. |
| "Your account has been blocked" | Your admin has blocked your account. Contact them to resolve. |
| "Slot already reserved" | Another user booked the slot first. Try a different slot or date. |
| "limited to a single day only" | You're booking outside your main building. Select only one date. |
| "A reason is required" | When booking outside your main building, you must provide a reason for the visit. |
| "This building is restricted to its assigned employees only" | Your main building is not set to this building. Contact your admin to update your assignment. |
| Session keeps expiring | Sessions expire after 30 minutes of inactivity. This is a security feature. |
| QR code not showing | Ensure you have a stable internet connection and try refreshing the page. |
| Cannot change password | Make sure you enter your current password correctly. If forgotten, use "Forgot Password?" on the login page. |

---

*Related: [Admin Guide](admin-user-guide.md) | [Attendant Guide](attendant-guide.md)*
