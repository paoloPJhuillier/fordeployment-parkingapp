# Sequence Diagrams
**Related:** [System Design](../system-design.md) · Last Updated: May 12, 2026

> All diagrams use Mermaid syntax, compatible with GitHub Markdown rendering. The participant `DB` represents the **DB Abstraction Layer** which speaks to MongoDB or Couchbase depending on `DB_TYPE`.

---

## 1. User Login Sequence

```mermaid
sequenceDiagram
    actor User
    participant Browser as React SPA
    participant Ingress as K8s Ingress
    participant API as FastAPI
    participant Auth as Auth Module
    participant DB as DB Abstraction

    User->>Browser: Enter email & password
    Browser->>Ingress: POST /api/auth/login
    Ingress->>API: Route to backend:8001
    API->>Auth: Rate limit check (5/min)
    alt Rate limit exceeded
        Auth-->>Browser: 429 Too Many Requests
    end
    API->>DB: find_one({email})
    DB-->>API: User document
    API->>Auth: verify_password(input, bcrypt_hash)
    alt Invalid credentials
        Auth-->>Browser: 401 Invalid credentials
    end
    alt User is blocked
        Auth-->>Browser: 403 Account blocked
    end
    API->>Auth: generate_device_fingerprint(User-Agent)
    API->>DB: Insert session {id, user_id, fingerprint, revoked: false}
    API->>Auth: create_access_token sub role fp sid exp=30min
    Auth-->>API: JWT token
    API-->>Browser: 200 user + access_token + Set-Cookie HttpOnly Secure
    Browser->>Browser: Store user in AuthContext
    Browser->>API: GET /api/system/features (fire-and-forget)
    API-->>Browser: ai_insights · attendant_mode · checkin_window
    alt must_change_password = true
        Browser->>User: Redirect to Change Password dialog
    else Role-based redirect
        Browser->>User: Redirect to /dashboard /admin /attendant
    end
```

---

## 2. Parking Reservation Booking Sequence

```mermaid
sequenceDiagram
    actor User
    participant Browser as React SPA
    participant API as FastAPI
    participant Auth as Auth Guard
    participant DB as DB Abstraction

    User->>Browser: Navigate to /book
    Browser->>API: GET /api/buildings (cookie auth)
    API->>Auth: Validate JWT + session + fingerprint
    Auth-->>API: current_user
    API->>DB: Find all buildings with floors and slots
    DB-->>Browser: Building list (zone-filtered)

    User->>Browser: Select building floor dates
    Browser->>API: GET /api/slots/available
    API->>DB: Find slots for floor
    API->>DB: Find reservations for date pending and confirmed
    API->>DB: Find event_blocks overlapping window
    DB-->>API: Reserved and blocked slot IDs
    API-->>Browser: Slots with is_available flag

    User->>Browser: Select available slot and vehicle
    Browser->>API: POST /api/reservations
    API->>Auth: Validate current_user
    Note over API: 9-step validation order

    alt External booking (non-main building)
        API->>DB: Find user zones - get zone_building_ids
        API->>API: Validate building is in user zone
        API->>API: Enforce single-day plus reason required
    end

    alt main_building_exclusive = true
        API->>API: Verify user.main_building equals building_id
    end

    alt requires_sticker = true
        API->>DB: Find slot_registration vehicle_plate building_id
        alt Non-open floor
            API->>API: Verify registration.slot_id equals this slot_id
        end
    end

    loop For each date
        API->>DB: Check slot not already reserved
        API->>DB: Check user has no overlapping booking
        API->>API: Generate UUID + QR token
        API->>DB: Insert reservation document
    end

    API-->>Browser: 200 reservations with QR token
    Browser->>User: Show confirmation with QR code

    alt Slot fully booked - waitlist enabled
        API-->>Browser: 409 + Join Waitlist option
        User->>Browser: Tap Join Waitlist
        Browser->>API: POST /api/waitlist
        API->>DB: Insert waitlist_entry status=active
    end
```

---

## 3. Attendant No-Show Reporting Sequence

```mermaid
sequenceDiagram
    actor Attendant
    participant Browser as React SPA
    participant API as FastAPI
    participant Auth as Auth Guard
    participant DB as DB Abstraction
    participant Notif as Notification Service

    Note over Attendant: Only used when ATTENDANT_MODE_ENABLED = true. In self-checkin mode the dashboard is fallback-only.

    Attendant->>Browser: Open Attendant Dashboard
    Browser->>API: GET /api/attendant/daily-reservations
    API->>Auth: Validate JWT role attendant or admin
    API->>DB: Find reservations for date + building
    API->>DB: Batch enrich user names vehicle plates slot labels
    DB-->>Browser: Enriched reservation list

    Attendant->>Browser: Click No Show on a reservation
    Browser->>API: POST /api/attendant/reservations/{id}/report-no-show
    API->>Auth: require_attendant guard
    API->>DB: Find reservation by ID

    alt Reservation not found
        API-->>Browser: 404
    end
    alt Status is cancelled or completed
        API-->>Browser: 400
    end
    alt Reservation date is in the future
        API-->>Browser: 400
    end

    API->>DB: Update reservation status=no_show no_show_reported=true no_show_at=now
    API->>DB: Increment user.no_show_count
    API->>DB: Find building name
    API->>Notif: create_notification user_id No-Show Reported message
    Notif->>DB: Insert notification document
    API-->>Browser: 200 No-show reported
    Browser->>Attendant: Update UI status badge changes
```

---

## 4. Admin Bulk User Upload Sequence

```mermaid
sequenceDiagram
    actor Admin
    participant Browser as React SPA
    participant API as FastAPI
    participant Auth as Auth Guard
    participant DB as DB Abstraction

    Admin->>Browser: Click Bulk Upload in User Management
    Admin->>Browser: Select CSV file and set default password
    Browser->>API: POST /api/users/bulk-upload multipart form-data
    API->>Auth: require_admin guard

    API->>API: Parse CSV with pandas
    alt Missing required columns
        API-->>Browser: 400 Missing required column
    end

    API->>DB: Batch fetch existing emails
    API->>DB: Batch fetch all buildings name to ID map
    API->>DB: Batch fetch all zones name to doc map
    API->>API: Hash default password once reuse for all

    loop For each CSV row
        alt Email already exists
            API->>API: Skip increment skipped count
        else New user
            API->>API: Resolve main_building name to ID
            API->>API: Queue zone assignment if zone column present
            API->>DB: Insert user document
        end
    end

    loop For each zone with queued users
        API->>DB: addToSet user_ids to zone
    end

    API-->>Browser: 200 created skipped zone_assignments errors
    Browser->>Admin: Show upload summary dialog
```

---

## 5. QR Code Scan Verification Sequence

```mermaid
sequenceDiagram
    actor Attendant
    participant Browser as React SPA
    participant API as FastAPI
    participant Auth as Auth Guard
    participant DB as DB Abstraction

    Attendant->>Browser: Navigate to /scan/qrToken
    Browser->>API: GET /api/scan/{qr_token}
    API->>Auth: require_attendant guard
    API->>DB: Find reservation by qr_token

    alt Not found
        API-->>Browser: 404 Reservation not found
    end

    API->>DB: Find slot label
    API->>DB: Find floor label
    API->>DB: Find building name
    API->>DB: Find vehicle plate_number
    API->>DB: Find user first_name last_name

    API-->>Browser: 200 reservation details
    Browser->>Attendant: Display reservation verification card

    opt Confirm arrival
        Attendant->>Browser: Click Confirm
        Browser->>API: PUT /api/reservations/{id}/confirm
        API->>DB: Update status confirmed checked_in_at=now
        API-->>Browser: 200 Reservation confirmed
    end
```

---

## 6. Self Check-In Sequence (Attendant Mode OFF)

```mermaid
sequenceDiagram
    actor Parker
    participant Browser as React SPA
    participant API as FastAPI
    participant FF as features.py
    participant DB as DB Abstraction

    Note over Browser: useFeatures at SPA load fetched attendant_mode_enabled=false self_checkin_window_minutes=15

    Parker->>Browser: Open My Reservations
    Browser->>API: GET /api/reservations cookie auth
    API->>DB: Find user reservations
    DB-->>Browser: Reservation list
    Browser->>Browser: Render Check in button when start_time <= now <= start_time + window

    Parker->>Browser: Tap Check in
    Browser->>API: POST /api/reservations/{id}/checkin
    API->>FF: attendant_mode_enabled
    alt Mode is ON
        FF-->>API: true
        API-->>Browser: 403 Self check-in is disabled
    end

    API->>DB: Find reservation
    alt Not own reservation and not admin
        API-->>Browser: 403
    end
    alt Status already confirmed
        API-->>Browser: 200 already_checked_in true
    end
    alt Status not pending
        API-->>Browser: 400
    end

    API->>FF: self_checkin_window_minutes
    FF-->>API: 15
    API->>API: Compute start_dt compare with now

    alt now before start_dt
        API-->>Browser: 400 Too early
    end
    alt now after start_dt + window
        API-->>Browser: 410 Window expired
    end

    API->>DB: Update status=confirmed checked_in_at=now checked_in_by_self=true
    API-->>Browser: 200 Checked in successfully
    Browser->>Parker: Status flips to Confirmed in the UI
```

---

## 7. Background No-Show + Waitlist Notification Sequence

```mermaid
sequenceDiagram
    participant Task as Background Loop
    participant FF as features.py
    participant DB as DB Abstraction
    participant Notif as Notification Service
    participant WL as waitlist.notify_next

    Note over Task: Sleep 60s when attendant_mode=false. Sleep 300s when attendant_mode=true.

    loop Each tick
        Task->>Task: now=utcnow today=now.date
        Task->>DB: Find PENDING where date less than today
        Task->>DB: Find PENDING where date equals today and end_time less or equal now

        Task->>FF: attendant_mode_enabled
        alt mode is OFF self check-in
            FF-->>Task: false
            Task->>FF: self_checkin_window_minutes
            Task->>DB: Find PENDING where date=today and start_time less or equal now minus window
            DB-->>Task: Expired-checkin candidates
        end

        Task->>DB: update_many status=no_show no_show_at=now
        loop For each newly flagged no-show
            Task->>Notif: create_notification user_id Marked as No-Show
            Task->>DB: Increment user.no_show_count
        end

        Note over Task: Slot Release Phase
        Task->>DB: Find NO_SHOW where slot_released not true and date less or equal today

        loop For each no-show
            Task->>DB: Find parking_configs for building_id

            alt attendant_mode_enabled false
                Task->>DB: parking_slots status=available
                Task->>DB: reservation slot_released=true
                Task->>WL: notify_next building_id date
            else config no_show_release_enabled true
                alt release_minutes elapsed since no_show_at
                    Task->>DB: parking_slots status=available
                    Task->>DB: reservation slot_released=true
                    Task->>WL: notify_next building_id date
                end
            end
        end
    end
```

---

## 8. Waitlist Notification & Claim Sequence

```mermaid
sequenceDiagram
    participant Trigger as Cancel or No-show release
    participant API as FastAPI
    participant DB as DB Abstraction
    participant Notif as Notification Service
    actor Parker as Next Waitlisted User
    participant Browser as React SPA

    Trigger->>API: Slot just freed building_id date
    API->>DB: Find waitlist_entries where building_id preferred_date status=active order by created_at
    DB-->>API: oldest active entry

    alt No active entries
        API->>API: No-op
    end

    API->>DB: Update oldest status=notified notified_at=now expires_at=now plus window
    API->>Notif: create_notification user_id Slot Available
    Notif->>DB: Insert notification

    Parker->>Browser: Sees in-app notification
    Parker->>Browser: Navigates to Booking page
    Browser->>API: POST /api/reservations

    alt Booked within window
        API->>DB: Insert reservation
        API->>DB: waitlist_entry status=fulfilled
        API-->>Browser: 200
    else Window expired background sweep
        Note over API,DB: services background check_waitlist_expiry
        API->>DB: waitlist_entry status=expired
        API->>API: Recursively notify next active entry
    end
```

---

## 9. Session Validation Sequence (Every Authenticated Request)

```mermaid
sequenceDiagram
    participant Browser as React SPA
    participant API as FastAPI
    participant Auth as get_current_user
    participant DB as DB Abstraction

    Browser->>API: Any authenticated request cookie auth_token=JWT
    API->>Auth: Extract token from cookie or Authorization header
    Auth->>Auth: jwt.decode token JWT_SECRET

    alt Token expired over 30min
        Auth-->>Browser: 401 Unauthorized
        Browser->>Browser: Redirect to /login
    end

    Auth->>Auth: Extract sub role fp sid
    Auth->>DB: Find session by session_id

    alt Session revoked or not found
        Auth-->>Browser: 401 Session expired
    end

    Auth->>Auth: Compare fingerprint with request User-Agent hash
    alt Fingerprint mismatch
        Auth-->>Browser: 401 Session fingerprint mismatch
    end

    Auth->>DB: Find user by user_id
    alt User blocked
        Auth-->>Browser: 403 Account blocked
    end

    Auth-->>API: current_user dict
    API->>API: Process request with user context
```

---

*Back to: [System Design](../system-design.md) | Next: [Compliance Matrix](../compliance-matrix.md)*
