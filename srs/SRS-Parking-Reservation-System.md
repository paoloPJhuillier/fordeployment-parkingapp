# Systems Requirements Specifications (SRS)

## Cebuana Lhuillier Corporate Parking Reservation System

| Field | Detail |
|---|---|
| **Document Version** | 1.0 |
| **Date** | February 10, 2026 |
| **Prepared For** | Cebuana Lhuillier |
| **Status** | Approved for Development |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Architecture](#3-system-architecture)
4. [User Roles and Personas](#4-user-roles-and-personas)
5. [Functional Requirements](#5-functional-requirements)
6. [User Interface Design](#6-user-interface-design)
7. [Data Model](#7-data-model)
8. [API Specifications](#8-api-specifications)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Appendices](#10-appendices)

---

## 1. Introduction

### 1.1 Purpose

This document defines the Systems Requirements Specifications (SRS) for the **Cebuana Lhuillier Corporate Parking Reservation System** — a web-based application designed to digitize and streamline corporate parking management across multiple Cebuana Lhuillier buildings.

### 1.2 Scope

The system provides:

- **End Users (Employees):** Mobile-friendly parking spot reservation, vehicle registration, QR-code-based entry verification, and repeat weekly bookings.
- **Administrators:** Building/floor/slot management, user management with bulk upload, zone-based access control, reservation oversight, reporting, and analytics.
- **Parking Attendants:** Daily reservation verification, booking confirmation, and vehicle photo capture.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| **Slot** | A single parking space within a floor. Identified by an alphanumeric label (e.g., `A-01`, `VIP-03`). |
| **Floor** | A level within a building that contains parking slots. |
| **Building** | A physical Cebuana Lhuillier property with one or more parking floors. |
| **Zone** | An access control group that assigns specific users to specific buildings. |
| **Reservation** | A time-bounded booking of a parking slot by a user for a specific vehicle. |
| **QR Code** | A machine-readable code generated per reservation for attendant verification. |
| **JWT** | JSON Web Token — used for stateless user authentication. |
| **SPA** | Single Page Application — the frontend architecture. |

### 1.4 References

- Cebuana Lhuillier Brand Guidelines (Navy `#1a2b4a`, Red `#d63031`, White)
- IEEE 830-1998 SRS Standard

---

## 2. Overall Description

### 2.1 Product Perspective

The system is a standalone web application with no dependencies on existing Cebuana Lhuillier internal systems. It is designed as a mobile-first responsive SPA with a RESTful API backend and a document database.

### 2.2 Product Functions (High-Level)

```
+------------------------------------------------------+
|           PARKING RESERVATION SYSTEM                  |
+------------------------------------------------------+
|                                                      |
|  END USER         ADMIN              ATTENDANT       |
|  --------         -----              ---------       |
|  Register         User Mgmt          View Bookings   |
|  Login            Building Mgmt      Confirm Entry   |
|  Add Vehicle      Slot Mgmt          Photo Capture   |
|  Book Spot        Zone Mgmt                          |
|  View QR Code     Reservations                       |
|  Cancel           Reports                            |
|  Repeat Book      Block/Unblock                      |
|                   Parking Config                     |
+------------------------------------------------------+
```

### 2.3 User Classes and Characteristics

| User Class | Count | Tech Proficiency | Access |
|---|---|---|---|
| End User (Employee) | 100–5000 | Basic (mobile-first) | Mobile browser |
| Admin | 1–10 | Moderate | Desktop browser |
| Parking Attendant | 5–30 per building | Basic | Tablet/mobile |

### 2.4 Operating Environment

- **Client:** Modern web browsers (Chrome, Safari, Edge, Firefox). Mobile-responsive.
- **Server:** Cloud-hosted Linux container (Kubernetes).
- **Database:** MongoDB (NoSQL document store).

### 2.5 Constraints

- All UI must adhere to Cebuana Lhuillier brand guidelines.
- The system must be mobile-first for end users.
- QR codes must be generated server-side and stored persistently.
- Zone enforcement must be real-time (no caching of access rights).

---

## 3. System Architecture

### 3.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       CLIENT LAYER                          │
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────────┐         │
│   │  Mobile  │    │ Desktop  │    │   Tablet     │         │
│   │  (User)  │    │ (Admin)  │    │ (Attendant)  │         │
│   └────┬─────┘    └────┬─────┘    └──────┬───────┘         │
│        │               │                 │                  │
│        └───────────────┼─────────────────┘                  │
│                        │                                    │
│              React SPA + TailwindCSS                        │
│              Shadcn UI + React Router                       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS / REST API
                         │ (JWT Bearer Auth)
┌────────────────────────┼────────────────────────────────────┐
│                  API GATEWAY (Nginx)                         │
│                  /api/* → Backend:8001                       │
│                  /*    → Frontend:3000                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────┐
│                   BACKEND LAYER                              │
│                                                              │
│              FastAPI (Python 3.11)                            │
│              ┌─────────────────────┐                         │
│              │  Auth Middleware     │                         │
│              │  (JWT + Role-Based)  │                         │
│              ├─────────────────────┤                         │
│              │  Routes:            │                         │
│              │  - Auth             │                         │
│              │  - Users            │                         │
│              │  - Vehicles         │                         │
│              │  - Buildings/Slots  │                         │
│              │  - Reservations     │                         │
│              │  - Zones            │                         │
│              │  - Config           │                         │
│              │  - Reports          │                         │
│              │  - Attendant        │                         │
│              ├─────────────────────┤                         │
│              │  QR Code Generator  │                         │
│              │  (qrcode library)   │                         │
│              └────────┬────────────┘                         │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────────┐
│                 DATA LAYER                                    │
│                                                               │
│              MongoDB (Motor Async Driver)                      │
│              ┌──────────────────────┐                          │
│              │  Collections:        │                          │
│              │  - users             │                          │
│              │  - vehicles          │                          │
│              │  - buildings         │                          │
│              │  - floors            │                          │
│              │  - parking_slots     │                          │
│              │  - reservations      │                          │
│              │  - zones             │                          │
│              │  - parking_configs   │                          │
│              └──────────────────────┘                          │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | React | 19.x |
| UI Framework | TailwindCSS + Shadcn UI | 3.x / latest |
| Routing | React Router | 6.x |
| Charts | Recharts | 2.x |
| Backend | FastAPI (Python) | 0.100+ |
| Database | MongoDB | 7.x |
| Async Driver | Motor | 3.x |
| Authentication | PyJWT | 2.x |
| QR Generation | qrcode | 7.x |
| Password Hashing | passlib (bcrypt) | 1.7 |

---

## 4. User Roles and Personas

### 4.1 End User (Employee)

**Persona: Maria Santos** — Office employee, commutes by car daily.

- Needs to reserve parking in advance.
- Uses her phone exclusively.
- Wants to show a QR code at entry for fast verification.
- Sometimes books the same slot every week.

### 4.2 Administrator

**Persona: Carlos Reyes** — Facilities Manager for multiple buildings.

- Manages buildings, floors, and slot configurations.
- Onboards new employees and controls access via zones.
- Reviews occupancy reports and usage trends.
- Needs to block abusive users from the system.

### 4.3 Parking Attendant

**Persona: Juan Dela Cruz** — On-site parking guard.

- Verifies daily reservations at the entrance.
- Confirms vehicle arrival and takes a photo.
- Needs a simple, clear interface on a tablet.

---

## 5. Functional Requirements

### 5.1 Authentication Module (FR-AUTH)

| ID | Requirement | Priority |
|---|---|---|
| FR-AUTH-01 | The system shall allow users to register with email, password, name, and company. | P0 |
| FR-AUTH-02 | The system shall authenticate users via email/password and return a JWT token. | P0 |
| FR-AUTH-03 | The system shall support three roles: `user`, `admin`, `attendant`. | P0 |
| FR-AUTH-04 | The system shall restrict route access based on user role. | P0 |
| FR-AUTH-05 | Blocked users shall be able to log in but shall be prevented from creating reservations. | P0 |

### 5.2 Vehicle Management (FR-VEH)

| ID | Requirement | Priority |
|---|---|---|
| FR-VEH-01 | Users shall register vehicles with plate number (required), make, model, and color (optional). | P0 |
| FR-VEH-02 | Users shall view and delete their registered vehicles. | P0 |
| FR-VEH-03 | The system shall prompt first-time users to register a vehicle before booking. | P1 |
| FR-VEH-04 | Users shall be able to add vehicles inline from the booking page without navigating away. | P1 |

### 5.3 Building and Slot Management (FR-BLDG)

| ID | Requirement | Priority |
|---|---|---|
| FR-BLDG-01 | Admins shall create buildings with name, address, number of floors, and slots per floor. | P0 |
| FR-BLDG-02 | Admins shall add floors to existing buildings with custom slot naming. | P0 |
| FR-BLDG-03 | Slots shall support alphanumeric labels (e.g., `A-01`, `VIP-03`, `EV-01`). | P0 |
| FR-BLDG-04 | Admins shall create slots using either (a) prefix + count pattern or (b) explicit custom labels. | P1 |
| FR-BLDG-05 | Admins shall rename individual slots inline by clicking on them. | P1 |
| FR-BLDG-06 | Admins shall bulk-add more slots to an existing floor. | P1 |
| FR-BLDG-07 | Admins shall delete individual slots (blocked if active reservations exist). | P1 |
| FR-BLDG-08 | Admins shall delete entire buildings and all associated data. | P1 |
| FR-BLDG-09 | The system shall show a live preview of generated slot labels before creation. | P2 |

### 5.4 Reservation Management (FR-RES)

| ID | Requirement | Priority |
|---|---|---|
| FR-RES-01 | Users shall book a parking slot by selecting building, floor, date, time range, and vehicle. | P0 |
| FR-RES-02 | The system shall display a visual parking map showing available and reserved slots. | P0 |
| FR-RES-03 | The system shall prevent double-booking of the same slot on the same date. | P0 |
| FR-RES-04 | The system shall prevent a user from having overlapping time reservations on the same date. | P0 |
| FR-RES-05 | Users shall cancel their own pending or confirmed reservations. | P0 |
| FR-RES-06 | The system shall generate a unique QR code for each reservation. | P0 |
| FR-RES-07 | Users shall view their QR code in a modal dialog on the reservations page. | P1 |
| FR-RES-08 | Users shall create repeat weekly bookings (1–4 weeks) for the same slot and time. | P1 |
| FR-RES-09 | Repeat bookings shall skip dates where conflicts exist (rather than failing entirely). | P1 |
| FR-RES-10 | Admins shall view all reservations across buildings with filters (building, status, date, search). | P0 |
| FR-RES-11 | Admins shall cancel any reservation. | P0 |

### 5.5 Zone Management (FR-ZONE)

| ID | Requirement | Priority |
|---|---|---|
| FR-ZONE-01 | Admins shall create zones that link a group of users to a specific building. | P0 |
| FR-ZONE-02 | Admins shall assign multiple users to a zone using a searchable checkbox list. | P0 |
| FR-ZONE-03 | Admins shall edit zones after creation (change name, building, users). | P1 |
| FR-ZONE-04 | If a building has one or more zones, only users assigned to those zones may book there. | P0 |
| FR-ZONE-05 | Buildings without zones shall remain open to all users. | P0 |
| FR-ZONE-06 | Admin users shall bypass zone restrictions. | P0 |
| FR-ZONE-07 | The system shall display summary statistics (assigned users, unassigned users). | P2 |
| FR-ZONE-08 | The system shall warn admins about users not assigned to any zone. | P2 |

### 5.6 User Management (FR-USER)

| ID | Requirement | Priority |
|---|---|---|
| FR-USER-01 | Admins shall create, update, and delete user accounts. | P0 |
| FR-USER-02 | Admins shall bulk-upload users via CSV/Excel file. | P1 |
| FR-USER-03 | Admins shall block users from making reservations (with visual indicator). | P0 |
| FR-USER-04 | Admins shall unblock previously blocked users. | P0 |
| FR-USER-05 | The system shall prevent blocking admin users. | P0 |
| FR-USER-06 | The user list shall show name, email, company, role, status (Active/Blocked), and creation date. | P0 |

### 5.7 Parking Attendant Module (FR-ATT)

| ID | Requirement | Priority |
|---|---|---|
| FR-ATT-01 | Attendants shall view all reservations for their assigned building on a given date. | P0 |
| FR-ATT-02 | Attendants shall navigate between dates. | P0 |
| FR-ATT-03 | Attendants shall confirm a reservation upon vehicle arrival. | P0 |
| FR-ATT-04 | Attendants shall optionally capture a photo of the vehicle when confirming. | P2 |

### 5.8 Parking Configuration (FR-CFG)

| ID | Requirement | Priority |
|---|---|---|
| FR-CFG-01 | Admins shall configure per-building settings: release time, default start/end times, booking window (days). | P1 |

### 5.9 Reports and Analytics (FR-RPT)

| ID | Requirement | Priority |
|---|---|---|
| FR-RPT-01 | Admins shall view dashboard statistics: total users, buildings, slots, occupancy rate. | P0 |
| FR-RPT-02 | Admins shall view reservation status distribution (pie chart). | P1 |
| FR-RPT-03 | Admins shall view daily reservations trend (bar chart). | P1 |
| FR-RPT-04 | Admins shall view reservations by building (horizontal bar chart). | P1 |

---

## 6. User Interface Design

### 6.1 Design System

| Property | Value |
|---|---|
| Primary Color (Navy) | `#1a2b4a` |
| Accent Color (Red) | `#d63031` |
| Background | White / `#f9fafb` |
| Font | System (Inter-like stack) |
| Border Radius | `0.5rem` (cards), `9999px` (pill buttons) |
| Mobile Breakpoint | 768px |

### 6.2 Screen: Login Page

```
┌─────────────────────────────────────────────────────────────┐
│                    Navy Background (#1a2b4a)                │
│                                                             │
│   ┌─────────────────────┐    ┌───────────────────────────┐  │
│   │                     │    │       ╔═══════════════╗    │  │
│   │  CEBUANA LHUILLIER  │    │       ║   Welcome     ║    │  │
│   │       [Logo]        │    │       ╠═══════════════╣    │  │
│   │                     │    │       ║ [Sign In]│[Reg]║   │  │
│   │  Reserve Your       │    │       ║               ║    │  │
│   │  Parking Spot       │    │       ║  Email:       ║    │  │
│   │  with Ease          │    │       ║  [________]   ║    │  │
│   │                     │    │       ║               ║    │  │
│   │  Seamlessly book,   │    │       ║  Password:    ║    │  │
│   │  manage, and track  │    │       ║  [________]   ║    │  │
│   │  your parking.      │    │       ║               ║    │  │
│   │                     │    │       ║ [  Sign In  ] ║    │  │
│   │  o Buildings        │    │       ║  (Red btn)    ║    │  │
│   │  o Secure Access    │    │       ╚═══════════════╝    │  │
│   └─────────────────────┘    └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Tab toggle between Sign In and Register modes.
- Register form adds: First Name, Last Name, Company fields.
- Role selection available for admin/attendant registration.
- Redirects to role-appropriate dashboard on success.

### 6.3 Screen: User Dashboard (Mobile)

```
┌──────────────────────────┐
│ [Logo]  Welcome, Maria ▸│
├──────────────────────────┤
│ ┌─────────┐ ┌──────────┐│
│ │ Active  │ │   My     ││
│ │ Bookings│ │ Vehicles ││
│ │   0     │ │    1     ││
│ └─────────┘ └──────────┘│
│ ┌─────────┐ ┌──────────┐│
│ │Buildings│ │Quick Book ││
│ │   5     │ │Reserve ▸ ││
│ └─────────┘ └──────────┘│
│                          │
│ Active Reservations  ▸   │
│ ┌────────────────────┐   │
│ │ No active reserva- │   │
│ │ tions              │   │
│ │  [ Book a Spot ]   │   │
│ └────────────────────┘   │
│                          │
│ My Vehicles         ▸    │
│ ┌────────────────────┐   │
│ │ 🚗 ABC 1234        │   │
│ │    White Toyota    │   │
│ └────────────────────┘   │
│                          │
│ Available Buildings      │
│ ┌────────────────────┐   │
│ │ 🏢 CL Tower Makati │   │
│ │   123 Ayala Ave    │   │
│ │   2 floors 20 slots│   │
│ └────────────────────┘   │
├──────────────────────────┤
│ Home  Book  Bookings  ▸  │
└──────────────────────────┘
```

**Behavior:**
- **New User (No Vehicle):** Shows onboarding banner with 2-step guide → Step 1: Add Vehicle (active), Step 2: Book Parking (greyed out).
- **Vehicle Added, No Booking:** Shows green "You're all set!" banner with "Book Now" CTA.
- **Quick Book card:** Links to booking page (or opens add-vehicle dialog if no vehicles).
- **Building cards:** Click navigates to booking page pre-filtered by building.

### 6.4 Screen: Booking Page (Mobile)

```
┌──────────────────────────┐
│ ← [Logo]       New Booking│
├──────────────────────────┤
│                          │
│ Select Building          │
│ ┌──────────────────────┐ │
│ │ Choose a building  ▾ │ │
│ └──────────────────────┘ │
│                          │
│ Select Date              │
│ ┌──────────────────────┐ │
│ │ 📅 February 10, 2026 │ │
│ └──────────────────────┘ │
│                          │
│ Select Vehicle           │
│ ┌──────────────────────┐ │
│ │ ABC 1234 - Toyota  ▾ │ │
│ └──────────────────────┘ │
│ + Add another vehicle    │
│                          │
│ Booking Time             │
│ [Daily] [Weekly]         │
│ Start: [08:00] End:[18:00│
│ Duration: 10 hours       │
│                          │
│ Repeat Weekly            │
│ [No repeat ▾]            │
│ (1 week / 2 / 3 / 4)    │
│                          │
│ Select Parking Spot      │
│ Floor: [Floor 1 ▾]      │
│ ┌──────────────────────┐ │
│ │ ┌──┐ ┌──┐ ┌──┐ ┌──┐ │ │
│ │ │A1│ │A2│ │A3│ │A4│ │ │
│ │ └──┘ └──┘ └──┘ └──┘ │ │
│ │ ┌──┐ ┌──┐ ┌──┐ ┌──┐ │ │
│ │ │B1│ │▓▓│ │B3│ │B4│ │ │
│ │ └──┘ └──┘ └──┘ └──┘ │ │
│ │  ○ Available ▓ Taken │ │
│ └──────────────────────┘ │
│                          │
│ [ Confirm Reservation ]  │
│    (Navy button)         │
├──────────────────────────┤
│ Home  Book  Bookings  ▸  │
└──────────────────────────┘
```

**Behavior:**
- Cinema-style slot grid: green = available (clickable), red/grey = reserved.
- Selected slot highlights with navy border.
- If no vehicles: Shows "Add Vehicle" CTA instead of dropdown.
- Repeat Weekly dropdown: 0–4 weeks.
- Confirm creates reservation(s) and navigates to reservations page.

### 6.5 Screen: Reservations Page

```
┌──────────────────────────┐
│ ← [Logo]    [+ New Book] │
├──────────────────────────┤
│ [Active (3)] [History(2)]│
├──────────────────────────┤
│ ┌────────────────────────┐
│ │▌ PENDING               │
│ │ CL Tower Makati        │
│ │ 📍 Floor 1 - Slot A-01│
│ │ 📅 Feb 15, 2026       │
│ │ 🕐 08:00 - 18:00      │
│ │ 🚗 ABC 1234      [QR] │
│ │                        │
│ │ [ ✕ Cancel Booking ]   │
│ └────────────────────────┘
│                          │
│ ┌────────────────────────┐
│ │▌ CONFIRMED             │
│ │ Main Office            │
│ │ 📍 Level 2 - VIP-03   │
│ │ 📅 Feb 20, 2026       │
│ │ 🕐 09:00 - 17:00      │
│ │ 🚗 XYZ 5678      [QR] │
│ │                        │
│ │ [ ✕ Cancel Booking ]   │
│ └────────────────────────┘
├──────────────────────────┤
│ Home  Book  Bookings  ▸  │
└──────────────────────────┘
```

**QR Code Dialog (on [QR] tap):**

```
┌────────────────────────┐
│    Parking QR Code     │
│                        │
│   ┌────────────────┐   │
│   │                │   │
│   │   [QR IMAGE]   │   │
│   │   (base64 PNG) │   │
│   │                │   │
│   └────────────────┘   │
│                        │
│   CL Tower Makati      │
│   Floor 1 - Slot A-01  │
│   Feb 15, 2026         │
│   08:00 - 18:00        │
│   ABC 1234             │
│                        │
│   Show this to the     │
│   parking attendant    │
└────────────────────────┘
```

### 6.6 Screen: Admin Dashboard

```
┌──────────────────────────────────────────────────────────────┐
│ [Logo] Parking Admin Panel                                    │
├──────────────┬───────────────────────────────────────────────┤
│              │                                               │
│  Dashboard ▸ │  Dashboard                                    │
│  Reservations│  Overview of your parking system              │
│  User Mgmt   │                                               │
│  Buildings   │  ┌────────┐┌────────┐┌────────┐┌────────┐    │
│  Zone Mgmt   │  │ Users  ││ Bldgs  ││ Slots  ││Occupancy│   │
│  Parking Cfg │  │  11    ││   5    ││  126   ││ 1.59%  │    │
│  Reports     │  └────────┘└────────┘└────────┘└────────┘    │
│  Attendants  │                                               │
│              │  ┌──────────────────┐┌──────────────────┐     │
│              │  │  Status Dist.    ││ Daily Reservations│    │
│  Sign Out    │  │  [PIE CHART]     ││ [BAR CHART]      │    │
│              │  │  Cancelled: ■    ││                   │    │
│              │  │  Confirmed: ■    ││  █ █              │    │
│              │  │  Pending:   ■    ││  █ █ █ █          │    │
│              │  └──────────────────┘└──────────────────┘     │
│              │                                               │
│              │  Reservations by Building                      │
│              │  [HORIZONTAL BAR CHART]                        │
├──────────────┴───────────────────────────────────────────────┤
```

### 6.7 Screen: Admin — Building Management

```
┌──────────────────────────────────────────────────────────┐
│ Building Management           [ + Add Building ]         │
│ 4 buildings configured                                   │
├──────────────────────────────────────────────────────────┤
│ ╔═══════════════════════════════════════════════════════╗ │
│ ║ 🏢 CL Tower Makati              [+ Add Floor] [🗑]  ║ │
│ ║    📍 123 Ayala Avenue, Makati City                  ║ │
│ ╠═══════════════════════════════════════════════════════╣ │
│ ║  📑 Floor 1         10 available │ 10 total    ▾    ║ │
│ ║  ┌────────────────────────────────────────────┐      ║ │
│ ║  │┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐│      ║ │
│ ║  ││A-01││A-02││A-03││A-04││A-05││A-06││A-07││      ║ │
│ ║  │└────┘└────┘└────┘└────┘└────┘└────┘└────┘│      ║ │
│ ║  │┌────┐┌────┐┌────┐                        │      ║ │
│ ║  ││A-08││A-09││A-10│  ○ Available ▓ Reserved│      ║ │
│ ║  │└────┘└────┘└────┘  Click any slot to rename      ║ │
│ ║  │                              [Add Slots]  │      ║ │
│ ║  └────────────────────────────────────────────┘      ║ │
│ ╚═══════════════════════════════════════════════════════╝ │
```

**Add Building Dialog:**

```
┌──────────────────────────────┐
│ Add New Building             │
├──────────────────────────────┤
│ Building Name *              │
│ [_________________________]  │
│                              │
│ Address *                    │
│ [_________________________]  │
│                              │
│ Floors    Slots per Floor    │
│ [__2__]   [__10__]           │
│                              │
│ Slot Label Prefix            │
│ [__A-__]                     │
│ Slots: A-1, A-2, A-3...     │
│                              │
│ Preview (Floor 1):           │
│ ┌──┐┌──┐┌──┐┌──┐┌──┐       │
│ │A-1│A-2│A-3│A-4│A-5│       │
│ └──┘└──┘└──┘└──┘└──┘       │
│                              │
│ [Cancel]  [Create Building]  │
└──────────────────────────────┘
```

**Add Floor Dialog (Two Modes):**

```
┌──────────────────────────────┐
│ Add New Floor                │
├──────────────────────────────┤
│ Floor Label *                │
│ [__Basement 2__]             │
│                              │
│ Slot Naming                  │
│ [Prefix + Number│Custom Lbl] │
│                              │
│ ── Prefix Mode ──           │
│ Prefix: [__B2-__]           │
│ Count:  [__20__]            │
│ Preview: B2-1, B2-2, ...    │
│                              │
│ ── Custom Mode ──           │
│ Enter labels (comma/newline):│
│ ┌──────────────────────────┐ │
│ │ VIP-01, VIP-02, VIP-03  │ │
│ │ EV-01, EV-02             │ │
│ │ WHEELCHAIR-01            │ │
│ └──────────────────────────┘ │
│ Preview (6 slots):           │
│ VIP-01 VIP-02 VIP-03        │
│ EV-01  EV-02  WHEELCHAIR-01 │
│                              │
│ [Cancel]     [Add Floor]     │
└──────────────────────────────┘
```

### 6.8 Screen: Admin — User Management

```
┌──────────────────────────────────────────────────────────┐
│ User Management      [+ Add User] [📤 Bulk Upload]      │
│ 11 total users                                           │
├──────────────────────────────────────────────────────────┤
│ 🔍 [Search users...____]  Role: [All ▾]                 │
│                                                          │
│ ┌────────────────────────────────────────────────────┐   │
│ │ Name          │Email           │Role│Status │ ⋮    │   │
│ ├───────────────┼────────────────┼────┼───────┼──────┤   │
│ │ Maria Santos  │maria@ceb...   │user│✅ Active│  ⋮  │   │
│ │ Carlos Reyes  │carlos@ceb...  │admin│✅ Active│ ⋮  │   │
│ │ Juan Dela Cruz│juan@ceb...    │user│🚫 Blocked│ ⋮ │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│ Dropdown (⋮):                                            │
│  ┌───────────┐                                           │
│  │ ✏️ Edit    │                                           │
│  │ 🛡️ Block   │  (or Unblock if already blocked)         │
│  │ 🗑️ Delete  │                                           │
│  └───────────┘                                           │
```

### 6.9 Screen: Admin — Zone Management

```
┌──────────────────────────────────────────────────────────┐
│ Zone Management                     [+ Create Zone]      │
│ Assign users to buildings                                │
├──────────────────────────────────────────────────────────┤
│ ┌──────┐┌──────────┐┌──────────┐┌───────────┐           │
│ │Zones ││Bldgs w/  ││ Assigned ││Unassigned │           │
│ │  3   ││ Zones: 2 ││ Users: 8 ││ Users: 3  │           │
│ └──────┘└──────────┘└──────────┘└───────────┘           │
│                                                          │
│ ⚠️ 3 users not assigned to any zone                      │
│   [Maria S.] [Juan D.] [+1 more]                        │
│                                                          │
│ ┌─────────────────┐ ┌─────────────────┐                  │
│ │ Executive Zone  │ │ Ground Floor    │                  │
│ │ 🏢 CL Tower    │ │ 🏢 Main Office  │                  │
│ │ 📱 GATE-01     │ │                 │                  │
│ │ 👥 3 users     │ │ 👥 5 users      │                  │
│ │ [Ana R.][Bob T.]│ │ [May L.][Ed S.] │                  │
│ │ [✏️] [🗑️]      │ │ [✏️] [🗑️]       │                  │
│ └─────────────────┘ └─────────────────┘                  │
```

**Create/Edit Zone Dialog:**

```
┌──────────────────────────────┐
│ Create Zone                  │
├──────────────────────────────┤
│ Zone Name *                  │
│ [__Executive Parking__]      │
│                              │
│ Building *                   │
│ [CL Tower Makati ▾]         │
│                              │
│ Device ID (Optional)         │
│ [__BARRIER-001__]            │
│                              │
│ Assign Users (3 selected)    │
│             [Select All]     │
│ 🔍 [Search users..._____]   │
│                              │
│ Selected:                    │
│ [Ana R. ✕][Bob T. ✕][May ✕] │
│                              │
│ ┌──────────────────────────┐ │
│ │ ☑ Ana Rodriguez          │ │
│ │   ana@cebuana.com        │ │
│ │ ☑ Bob Torres             │ │
│ │   bob@cebuana.com        │ │
│ │ ☑ May Lopez              │ │
│ │   may@cebuana.com        │ │
│ │ ☐ Ed Santos              │ │
│ │   ed@cebuana.com         │ │
│ └──────────────────────────┘ │
│                              │
│ [Cancel]    [Create Zone]    │
└──────────────────────────────┘
```

### 6.10 Screen: Admin — Reservation Management

```
┌──────────────────────────────────────────────────────────┐
│ Reservation Management                                    │
│ View and manage all parking reservations                  │
├──────────────────────────────────────────────────────────┤
│ ┌──────┐ ┌────────┐ ┌─────────┐ ┌──────────┐            │
│ │Total ││Pending ││Confirmed││Cancelled│            │
│ │  14  ││   5    ││    3    ││   6     │            │
│ └──────┘ └────────┘ └─────────┘ └──────────┘            │
│                                                          │
│ 🔍 [Search user, plate...]  [Building ▾] [Status ▾] 📅  │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ User       │ Building/Slot  │ Date     │Status│ Act  │ │
│ ├────────────┼────────────────┼──────────┼──────┼──────┤ │
│ │ 👤 Maria S.│ CL Tower       │ Feb 15   │ ⏳   │[Canc]│ │
│ │            │ Floor 1 - A-01 │ 08-18:00 │      │      │ │
│ ├────────────┼────────────────┼──────────┼──────┼──────┤ │
│ │ 👤 Bob T.  │ Main Office    │ Feb 20   │ ✅   │[Canc]│ │
│ │            │ Level 2 - B-03 │ 09-17:00 │      │      │ │
│ └──────────────────────────────────────────────────────┘ │
```

### 6.11 Screen: Attendant Dashboard

```
┌──────────────────────────────────────────────────────────┐
│ [Logo]  Parking Attendant      Welcome, Juan     [Exit]  │
├──────────────────────────────────────────────────────────┤
│           ◀  February 10, 2026  ▶                        │
│                                                          │
│  Today's Reservations (3)                                │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │  Maria Santos         ABC 1234                  │     │
│  │  Floor 1 - Slot A-01  08:00 - 18:00            │     │
│  │  Status: ⏳ Pending                              │     │
│  │                                                  │     │
│  │  [  Confirm Arrival  ]  [ 📷 Photo ]            │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │  Bob Torres           XYZ 5678                  │     │
│  │  Floor 2 - Slot B-03  09:00 - 17:00            │     │
│  │  Status: ✅ Confirmed                            │     │
│  └─────────────────────────────────────────────────┘     │
```

---

## 7. Data Model

### 7.1 Entity Relationship Diagram

```
┌──────────┐       ┌──────────────┐       ┌───────────┐
│  USERS   │──1:N──│  VEHICLES    │       │ BUILDINGS │
│──────────│       │──────────────│       │───────────│
│ id (PK)  │       │ id (PK)      │       │ id (PK)   │
│ email    │       │ user_id (FK) │       │ name      │
│ password │       │ plate_number │       │ address   │
│ first_nm │       │ make/model   │       │ total_flrs│
│ last_nm  │       │ color        │       └─────┬─────┘
│ company  │       └──────────────┘             │
│ role     │                                1:N │
│ is_blocked│      ┌──────────────┐       ┌─────┴─────┐
│ assigned_│──N:M──│   ZONES      │       │  FLOORS   │
│ buildings│       │──────────────│       │───────────│
└────┬─────┘       │ id (PK)      │       │ id (PK)   │
     │             │ name         │       │ label     │
     │             │ building_id  │       │building_id│
     │             │ device_id    │       └─────┬─────┘
     │             │ assigned_usrs│             │
     │             └──────────────┘         1:N │
     │                                   ┌─────┴──────┐
     │                                   │PARKING_SLOT│
     │                                   │────────────│
     │       ┌──────────────┐            │ id (PK)    │
     └──1:N──│ RESERVATIONS │──N:1───────│ label      │
             │──────────────│            │ floor_id   │
             │ id (PK)      │            │ building_id│
             │ user_id (FK) │            │ status     │
             │ vehicle_id   │            │ row/column │
             │ slot_id (FK) │            └────────────┘
             │ building_id  │
             │ floor_id     │       ┌──────────────┐
             │ date         │       │PARKING_CONFIG│
             │ start_time   │       │──────────────│
             │ end_time     │       │ id (PK)      │
             │ status       │       │ building_id  │
             │ booking_type │       │ release_time │
             │ qr_code      │       │ default_start│
             │ photo_url    │       │ default_end  │
             │ created_at   │       │ booking_wndw │
             └──────────────┘       └──────────────┘
```

### 7.2 Collection Schemas

#### users

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| email | String | Yes | Unique, email format |
| password_hash | String | Yes | bcrypt-hashed |
| first_name | String | Yes | |
| last_name | String | Yes | |
| company | String | No | Company affiliation |
| role | Enum | Yes | `user`, `admin`, `attendant` |
| is_blocked | Boolean | Yes | Default: `false` |
| assigned_buildings | Array[String] | Yes | Building IDs from zone assignments |
| created_at | String (ISO) | Yes | Timestamp |

#### vehicles

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| user_id | String | Yes | FK → users.id |
| plate_number | String | Yes | Alphanumeric plate |
| make | String | No | e.g., Toyota |
| model | String | No | e.g., Vios |
| color | String | No | e.g., White |
| created_at | String (ISO) | Yes | Timestamp |

#### buildings

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| name | String | Yes | Building name |
| address | String | Yes | Physical address |
| total_floors | Integer | Yes | Number of floors |
| created_at | String (ISO) | Yes | Timestamp |

#### floors

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| label | String | Yes | e.g., "Floor 1", "Basement" |
| building_id | String | Yes | FK → buildings.id |

#### parking_slots

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| label | String | Yes | Alphanumeric (e.g., `A-01`, `VIP-03`) |
| floor_id | String | Yes | FK → floors.id |
| building_id | String | Yes | FK → buildings.id |
| status | Enum | Yes | `available`, `reserved`, `maintenance` |
| row | Integer | Yes | Grid position |
| column | Integer | Yes | Grid position |

#### reservations

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| user_id | String | Yes | FK → users.id |
| slot_id | String | Yes | FK → parking_slots.id |
| vehicle_id | String | Yes | FK → vehicles.id |
| building_id | String | Yes | FK → buildings.id |
| floor_id | String | Yes | FK → floors.id |
| date | String | Yes | YYYY-MM-DD |
| start_time | String | Yes | HH:MM |
| end_time | String | Yes | HH:MM |
| status | Enum | Yes | `pending`, `confirmed`, `cancelled`, `completed` |
| booking_type | String | Yes | `daily` or `weekly` |
| qr_code | String | No | Base64 PNG of QR code |
| photo_url | String | No | Vehicle photo URL |
| created_at | String (ISO) | Yes | Timestamp |

#### zones

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| name | String | Yes | Zone name |
| building_id | String | Yes | FK → buildings.id |
| device_id | String | No | Physical device identifier |
| assigned_users | Array[String] | Yes | User IDs assigned to this zone |
| created_at | String (ISO) | Yes | Timestamp |

#### parking_configs

| Field | Type | Required | Description |
|---|---|---|---|
| id | String (UUID) | Yes | Primary key |
| building_id | String | Yes | FK → buildings.id (unique) |
| release_time | String | Yes | HH:MM — when slots are released |
| default_start_time | String | Yes | HH:MM — default booking start |
| default_end_time | String | Yes | HH:MM — default booking end |
| booking_window_days | Integer | Yes | How many days in advance |

---

## 8. API Specifications

### 8.1 Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/register` | Register new user | None |
| POST | `/api/auth/login` | Login, returns JWT | None |
| GET | `/api/auth/me` | Get current user profile | JWT |

### 8.2 Users (Admin)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/users` | List all users | Admin |
| POST | `/api/users` | Create user | Admin |
| PUT | `/api/users/{id}` | Update user | Admin |
| DELETE | `/api/users/{id}` | Delete user | Admin |
| PUT | `/api/users/{id}/block` | Block user from reservations | Admin |
| PUT | `/api/users/{id}/unblock` | Unblock user | Admin |
| POST | `/api/users/bulk-upload` | Bulk upload via CSV/Excel | Admin |

### 8.3 Vehicles

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/vehicles` | List user's vehicles | JWT |
| POST | `/api/vehicles` | Register vehicle | JWT |
| DELETE | `/api/vehicles/{id}` | Delete vehicle | JWT |

### 8.4 Buildings & Slots

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/buildings` | List all buildings with floors/slots | JWT |
| POST | `/api/buildings` | Create building | Admin |
| DELETE | `/api/buildings/{id}` | Delete building and all data | Admin |
| POST | `/api/buildings/{id}/floors` | Add floor to building | Admin |
| PUT | `/api/slots/{id}` | Rename a slot | Admin |
| POST | `/api/floors/{id}/slots` | Bulk add slots to floor | Admin |
| DELETE | `/api/slots/{id}` | Delete a slot | Admin |
| GET | `/api/slots/available` | Get available slots for booking | JWT |

### 8.5 Reservations

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/reservations` | List user's reservations | JWT |
| POST | `/api/reservations` | Create reservation (with QR) | JWT |
| PUT | `/api/reservations/{id}/cancel` | Cancel own reservation | JWT |
| PUT | `/api/reservations/{id}/confirm` | Confirm reservation | Attendant |
| POST | `/api/reservations/{id}/confirm-with-photo` | Confirm with photo | Attendant |
| GET | `/api/reservations/{id}/qr` | Get reservation QR code | JWT |
| GET | `/api/admin/reservations` | List all reservations (filtered) | Admin |
| PUT | `/api/admin/reservations/{id}/cancel` | Admin cancel any reservation | Admin |

### 8.6 Zones

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/zones` | List all zones | Admin |
| POST | `/api/zones` | Create zone | Admin |
| PUT | `/api/zones/{id}` | Update zone | Admin |
| DELETE | `/api/zones/{id}` | Delete zone | Admin |
| GET | `/api/zones/user-buildings` | Get user's assigned buildings | JWT |

### 8.7 Configuration & Reports

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/parking-config/{building_id}` | Get parking configuration | Admin |
| POST | `/api/parking-config` | Save parking configuration | Admin |
| GET | `/api/reports/stats` | Get dashboard statistics | Admin |
| GET | `/api/reports/ai-insights` | Get AI-generated insights | Admin |
| GET | `/api/attendant/daily-reservations` | Get daily reservations | Attendant |

---

## 9. Non-Functional Requirements

### 9.1 Performance

| ID | Requirement |
|---|---|
| NFR-PERF-01 | API response time shall be < 500ms for 95th percentile under normal load. |
| NFR-PERF-02 | The system shall support at least 500 concurrent users. |
| NFR-PERF-03 | The parking slot map shall render in < 2 seconds. |

### 9.2 Security

| ID | Requirement |
|---|---|
| NFR-SEC-01 | All passwords shall be hashed using bcrypt. |
| NFR-SEC-02 | All API communication shall use HTTPS. |
| NFR-SEC-03 | JWT tokens shall expire after 24 hours. |
| NFR-SEC-04 | All admin endpoints shall require admin role validation. |
| NFR-SEC-05 | MongoDB `_id` fields shall never be exposed in API responses. |

### 9.3 Usability

| ID | Requirement |
|---|---|
| NFR-USE-01 | The user interface shall be mobile-first, supporting screens ≥ 375px width. |
| NFR-USE-02 | First-time users shall be guided through onboarding (vehicle registration → booking). |
| NFR-USE-03 | All interactive elements shall have visible hover/focus states. |
| NFR-USE-04 | Error messages shall be user-friendly (not raw technical errors). |

### 9.4 Reliability

| ID | Requirement |
|---|---|
| NFR-REL-01 | The system shall be available 99.5% of the time during business hours (6:00–22:00). |
| NFR-REL-02 | QR codes shall be stored persistently and regenerated if missing. |
| NFR-REL-03 | Repeat booking shall gracefully skip conflicting dates rather than failing entirely. |

### 9.5 Scalability

| ID | Requirement |
|---|---|
| NFR-SCL-01 | The database schema shall support up to 50 buildings, 500 floors, and 50,000 slots. |
| NFR-SCL-02 | The system shall support horizontal scaling via container orchestration (Kubernetes). |

### 9.6 Branding

| ID | Requirement |
|---|---|
| NFR-BRD-01 | All UI shall use the Cebuana Lhuillier color palette: Navy `#1a2b4a`, Red `#d63031`, White. |
| NFR-BRD-02 | The official Cebuana Lhuillier logo shall appear on the login page, headers, and as favicon. |
| NFR-BRD-03 | No third-party brand elements or default framework colors shall be visible. |

---

## 10. Appendices

### Appendix A: User Flow — End-to-End Booking

```
START
  │
  ▼
[Login / Register]
  │
  ▼
[Dashboard] ──── No Vehicle? ──── [Add Vehicle Dialog]
  │                                       │
  │◄──────────────────────────────────────┘
  │
  ▼
[Select "Book" or Building Card]
  │
  ▼
[Booking Page]
  ├── Select Building
  ├── Select Date
  ├── Select Vehicle (or Add Inline)
  ├── Set Time Range
  ├── Optionally Set Repeat (1-4 weeks)
  ├── Select Floor
  └── Select Slot from Grid
  │
  ▼
[Confirm Reservation]
  │
  ▼
[Reservation Created + QR Code Generated]
  │
  ▼
[View on Reservations Page]
  ├── View QR Code (Modal)
  └── Cancel Booking
  │
  ▼
[At Parking Entrance]
  └── Show QR to Attendant ──► [Attendant Confirms]
                                       │
                                       ▼
                                 [Status → Confirmed]
END
```

### Appendix B: User Flow — Admin Zone Enforcement

```
START
  │
  ▼
[Admin Creates Zone]
  ├── Selects Building
  ├── Assigns Users (Multi-Select)
  └── Saves
  │
  ▼
[System syncs assigned_buildings on user records]
  │
  ▼
[User tries to book in zoned building]
  │
  ├── User IS in zone ──► Booking proceeds normally
  │
  └── User NOT in zone ──► 403: "Not assigned to this building"
  │
  ▼
[Buildings WITHOUT zones] ──► All users can book (no restriction)

END
```

### Appendix C: Glossary of Status Values

| Entity | Status | Meaning |
|---|---|---|
| Reservation | `pending` | Booked, awaiting vehicle arrival |
| Reservation | `confirmed` | Attendant verified vehicle arrival |
| Reservation | `cancelled` | User or admin cancelled the booking |
| Reservation | `completed` | Booking period has ended |
| Parking Slot | `available` | Open for booking |
| Parking Slot | `reserved` | Currently booked |
| Parking Slot | `maintenance` | Temporarily out of service |
| User | `is_blocked: true` | Prevented from creating reservations |
| User | `is_blocked: false` | Normal access |

---

### Appendix D: Live UI Reference Screenshots

The following table provides a reference to the live application screens. Each screen corresponds to a mock UI wireframe documented in Section 6.

| # | Screen | Description | Reference Section |
|---|---|---|---|
| 1 | **Login Page** | Cebuana Lhuillier branded login with navy background, logo, Sign In/Register tabs, email/password form, red CTA button | Section 6.2 |
| 2 | **User Dashboard — New User Onboarding** | Welcome banner with 2-step guide (Add Vehicle → Book Parking). Step 2 greyed out until vehicle registered. Stats cards, building list. | Section 6.3 |
| 3 | **User Dashboard — Active User** | Stats cards (Active Bookings, Vehicles, Buildings, Quick Book). Active reservations list with cancel. My Vehicles section. Available Buildings grid. | Section 6.3 |
| 4 | **Booking Page** | Left panel: Building dropdown, date picker, vehicle selector with inline add, Daily/Weekly toggle, time pickers, Repeat Weekly dropdown. Right panel: cinema-style parking slot grid with Available/Occupied/Selected legend. | Section 6.4 |
| 5 | **Reservations Page** | Active/History tabs. Reservation cards with status bar, building/slot/date/time/vehicle info. QR code button. Cancel booking button. | Section 6.5 |
| 6 | **QR Code Modal** | Generated QR code image, reservation summary (building, slot, date, time, plate), "Show this to the parking attendant" instruction. | Section 6.5 |
| 7 | **Vehicles Page** | Vehicle cards with plate number (monospace), make/model/color. Add Vehicle button. Delete button per vehicle. | — |
| 8 | **Admin Dashboard** | Total Users/Buildings/Parking Slots/Occupancy Rate stat cards. Reservation Status pie chart. Daily Reservations bar chart. Reservations by Building horizontal bars. Quick links (Manage Users, Buildings, Reports). | Section 6.6 |
| 9 | **Admin — Reservation Management** | Stats row (Total/Pending/Confirmed/Cancelled). Search bar, Building filter, Status filter, Date filter. Sortable table with User, Building/Slot, Date, Time, Vehicle, Status columns. Cancel action on active reservations. | Section 6.10 |
| 10 | **Admin — User Management** | Search + role filter. Table with Name, Email, Company, Role (badge), Status (Active/Blocked badge), Created date. Dropdown menu: Edit, Block/Unblock, Delete. Bulk Upload and Add User buttons. | Section 6.8 |
| 11 | **Admin — Building Management** | Building cards with navy gradient header (name, address). Floor accordion with available/total badges. Slot grid (click to rename). Add Floor, Add Slots, Delete Building actions. | Section 6.7 |
| 12 | **Admin — Zone Management** | Stats (Total Zones, Buildings with Zones, Assigned/Unassigned Users). Unassigned users warning banner. Zone cards with building, device ID, assigned user badges. Create/Edit dialog with multi-user checkbox selector and search. | Section 6.9 |
| 13 | **Attendant Dashboard** | Date navigator (prev/next). Daily reservations list with user name, vehicle plate, slot info, time. Confirm Arrival and Photo capture buttons. | Section 6.11 |

### Appendix E: Change Log

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | February 10, 2026 | System Architecture Team | Initial SRS document covering full MVP scope |

---

*End of Document*
