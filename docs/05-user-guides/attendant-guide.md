# Parking Attendant Guide
**Cebuana Lhuillier Parking Reservation System**  
**Version:** 2.4 | **Last Updated:** May 5, 2026

---

## 1. Overview

As a Parking Attendant, your role is to manage the daily parking operations on-site. You are responsible for:
- Viewing daily reservations for your assigned building(s)
- Confirming arrivals when vehicles park
- Reporting no-shows for users who did not arrive
- Scanning QR codes to verify reservations

> **Your role at a glance**
> - ✅ Confirm arrivals (manually or by scanning the parker's QR code).
> - ✅ Mark no-shows when a reservation's window has elapsed and nobody arrived.
> - ✅ See only the buildings your admin has assigned to you.
> - ❌ Create, edit, or cancel reservations on behalf of users — that's an admin action.
> - ❌ Change building / floor / slot configuration.

> ⚠️ **If your site is in Self Check-In mode**, the parkers confirm themselves through their own app. Your dashboard remains available as a fallback (you can still confirm or mark no-shows manually), but the day-to-day flow happens without you. Ask your admin if you're unsure which mode your site is in.

---

## 2. Logging In

1. Open the Parking Reservation System in your browser (works on mobile and desktop).
2. Enter your **email** and **password**.
3. Click **Sign In**.
4. You will be redirected to the **Attendant Dashboard**.

> **First-time login:** You will be asked to change your temporary password before proceeding.

---

## 3. Attendant Dashboard

Your dashboard is the main workspace. It shows:

### 3.1 Summary Cards
Three cards at the top show counts for the selected date:

| Card | Description |
|------|-------------|
| **Reserved** | Reservations with status "Pending" (not yet confirmed) |
| **Confirmed** | Reservations confirmed by you (arrival verified) |
| **No Shows** | Reservations marked as no-show |

### 3.2 Building Filter
If you are assigned to multiple buildings, use the **building dropdown** to filter reservations by building.

### 3.3 Date Navigation
- Use the **left/right arrows** to move between dates.
- The current selected date is displayed prominently.
- A **"Today"** button appears when you navigate away from today's date. Click it to quickly return to the current date.

### 3.4 Reservation Cards
Each reservation card displays:
- **User name** and vehicle plate number
- **Parking slot** (building, floor, slot label)
- **Time** (start — end)
- **Status badge** (Pending, Confirmed, No Show, Cancelled)
- **Action buttons** (Confirm, No Show) — only visible for today or past dates

---

## 4. Confirming Arrivals

When a vehicle arrives at the parking area:

1. Find the reservation on the dashboard (search by name or plate number).
2. Click the **"Confirm"** button on the reservation card.
3. The status changes from **Pending** to **Confirmed**.

> **Tip:** You can also confirm by scanning the user's QR code (see Section 6).

---

## 5. Reporting No-Shows

If a user does not arrive by their scheduled time:

1. Find the reservation on the dashboard.
2. Click the **"No Show"** button.
3. The reservation status changes to **No Show**.

### 5.1 What Happens When You Report a No-Show
- The reservation status is set to "No Show".
- A **`no_show_at` timestamp** is recorded (the exact time the no-show was reported).
- The user's **no-show count** is incremented.
- A **notification** is automatically sent to the user informing them of the no-show.
- If the building has **auto-release** enabled, the slot is released back to "available" after a configured number of minutes **from the time of the no-show report** (not from the reservation end time).

### 5.2 Important Rules
- You can **only** report no-shows for reservations with **"Pending"** status.
- The "No Show" button is **hidden** for confirmed reservations — once confirmed, a no-show cannot be reported.
- The "No Show" and "Confirm" buttons are **hidden** for future dates — this prevents accidental no-show reports.
- You **cannot** report a no-show for a reservation that is already cancelled or completed.

---

## 6. QR Code Scanning

Each reservation has a unique QR code that the user can present at the parking entrance.

### 6.1 How to Initiate a QR Scan

The attendant dashboard has a **Scan QR** button in the top-right of the header.

1. Click the **Scan QR** button (QR icon) in the dashboard header.
2. A dialog appears prompting for a **QR Token**.
3. Ask the parker to show their QR code. The token is displayed below the QR image on their booking confirmation screen.
4. Enter the token and click **Look Up**.
5. The system loads the reservation detail page showing:
   - User name
   - Vehicle plate number
   - Building, floor, and slot
   - Date and time
   - Current status
6. If valid, click **"Confirm"** to mark the arrival.

> **Tip:** If the parker can show their phone, you can read the token directly from the QR confirmation page or ask them to read it aloud.

---

## 7. Auto No-Show System

The system has an automatic background process that helps manage no-shows:
- Every **5 minutes**, the system checks for **pending** reservations where:
  - The date has passed, OR
  - The reservation's end time has elapsed for today
- These are automatically marked as **no-show**, a `no_show_at` timestamp is recorded, and users are notified.
- If the building has **auto-release** enabled, the slot is released back after the configured release period **from when the no-show was tagged** (based on the `no_show_at` timestamp, not the reservation end time).
- When a slot is released and the building has **waitlist** enabled, the next user on the waitlist is automatically notified that a slot is available.

> As an attendant, you can still manually report no-shows during the day — the auto system handles the ones that slip through.

---

## 8. Daily Workflow

Here's a recommended workflow for a typical day:

| Time | Action |
|------|--------|
| **Start of shift** | Log in → Select your building → Check today's reservations |
| **Throughout the day** | Confirm arrivals as vehicles come in |
| **Mid-day check** | Review any pending reservations → Report no-shows for morning slots that weren't confirmed |
| **End of shift** | Final review → Report remaining no-shows → The auto system will catch anything you miss |

---

## 9. Tips & Best Practices

1. **Stay on today's view** — Use the "Today" button to quickly return if you've navigated to other dates.
2. **Use the building filter** — If you're assigned to one building, it will auto-filter for you.
3. **Confirm early** — Confirming arrivals promptly helps track real-time occupancy.
4. **Don't rush no-shows** — Wait until the reservation's start time before reporting a no-show. The user may be running late.
5. **Check the summary cards** — They give you a quick overview of how the day is going.

---

## 10. Troubleshooting

| Issue | Solution |
|-------|----------|
| No reservations showing | Check the date and building filter. Ensure you're looking at the correct date. |
| "Confirm" / "No Show" buttons not visible | Buttons only appear for today and past dates. Navigate to the correct date. |
| "Cannot report no-show for a future reservation" | This is a safety guard. You can only report no-shows for today or past dates. |
| Session expired | Sessions expire after 30 minutes. Log in again to continue. |
| QR code scan not working | Ensure the QR code is clear and the URL is correct. Try manual lookup if scanning fails. |

---

*Related: [End User Guide](end-user-guide.md) | [Admin Guide](admin-user-guide.md)*
