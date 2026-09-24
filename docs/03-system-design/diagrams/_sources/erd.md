# Entity Relationship Diagram
**Related:** [System Design](../system-design.md) · Last Updated: May 12, 2026

> The ERD below is **database-agnostic**: the same entities exist in both MongoDB (collections) and Couchbase (collections inside the `_default` scope of bucket `db_parking`). The DB Abstraction Layer keeps the application code identical against either backend.

---

## ERD (Mermaid)

```mermaid
erDiagram
    USERS {
        string id PK
        string email UK
        string password
        string role
        string main_building FK
        array assigned_buildings
        array tags
        boolean is_blocked
        int no_show_count
    }
    SESSIONS {
        string id PK
        string user_id FK
        string fingerprint
        boolean revoked
    }
    BUILDINGS { string id PK string name int total_floors }
    FLOORS {
        string id PK
        string building_id FK
        string layout_image_url
    }
    PARKING_SLOTS {
        string id PK
        string label
        string floor_id FK
        string building_id FK
        string status
    }
    RESERVATIONS {
        string id PK
        string user_id FK
        string slot_id FK
        string vehicle_id FK
        string building_id FK
        string date
        string start_time
        string end_time
        string status
        string qr_token UK
        boolean slot_released
        string checked_in_at
        boolean checked_in_by_self
    }
    VEHICLES {
        string id PK
        string user_id FK
        string plate_number UK
    }
    ZONES { string id PK string name array building_ids array user_ids }
    PARKING_CONFIGS {
        string building_id PK
        int booking_window_days
        boolean no_show_release_enabled
        int no_show_release_minutes
        boolean waitlist_enabled
        int waitlist_notification_window_minutes
        boolean main_building_exclusive
    }
    BUILDING_POLICIES {
        string building_id PK
        boolean requires_sticker
        array open_floor_ids
    }
    SLOT_REGISTRATIONS {
        string id PK
        string slot_id FK
        string user_id FK
        string vehicle_plate FK
        string building_id FK
        string status
    }
    EVENT_BLOCKS {
        string id PK
        string building_id FK
        string floor_id FK
        array slot_ids
        string date
        string event_name
    }
    WAITLIST_ENTRIES {
        string id PK
        string user_id FK
        string building_id FK
        string preferred_date
        string status
        string expires_at
    }
    NOTIFICATIONS { string id PK string user_id FK string type boolean read }
    AI_INSIGHTS { string id PK string building_id string content string generated_at }
    SITE_CONTENT { string key PK string heading_line1 string heading_highlight }

    USERS ||--o{ SESSIONS : has
    USERS ||--o{ RESERVATIONS : books
    USERS ||--o{ VEHICLES : owns
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ WAITLIST_ENTRIES : queues
    USERS ||--o{ AI_INSIGHTS : generates
    USERS ||--o{ EVENT_BLOCKS : creates
    BUILDINGS ||--o{ FLOORS : contains
    BUILDINGS ||--o| PARKING_CONFIGS : configured
    BUILDINGS ||--o| BUILDING_POLICIES : policy
    BUILDINGS ||--o{ EVENT_BLOCKS : scoped
    BUILDINGS ||--o{ WAITLIST_ENTRIES : queued
    FLOORS ||--o{ PARKING_SLOTS : has
    PARKING_SLOTS ||--o{ RESERVATIONS : reserved
    PARKING_SLOTS ||--o{ SLOT_REGISTRATIONS : assigned
    VEHICLES ||--o{ RESERVATIONS : used
    VEHICLES ||--o{ SLOT_REGISTRATIONS : registered
    ZONES }o--o{ BUILDINGS : groups
    ZONES }o--o{ USERS : assigns
```

---

## Index Summary

The same logical indexes are present on both DB backends; the abstraction layer maps them to the appropriate primitive (MongoDB index spec / Couchbase GSI).

| Collection | Indexes |
|-----------|---------|
| users | `id` (unique), `email` (unique) |
| sessions | `id` (unique), `user_id` |
| reservations | `id` (unique), `user_id`, `building_id`, `slot_id`, `date`, `qr_token`, compound(`slot_id+date+status`), compound(`status+date+slot_released`) |
| buildings | `id` (unique) |
| floors | `id` (unique), `building_id` |
| parking_slots | `id` (unique), `floor_id` |
| vehicles | `id` (unique), `user_id`, `plate_number` (unique) |
| zones | `id` (unique) |
| notifications | `id` (unique), compound(`user_id+created_at`) |
| parking_configs | `building_id` (unique) |
| building_policies | `id` (unique), `building_id` (unique) |
| slot_registrations | `id` (unique), compound(`slot_id+user_id+status`), `vehicle_plate` |
| event_blocks | `id` (unique), compound(`building_id+date`), compound(`floor_id+date`) |
| waitlist_entries | `id` (unique), compound(`building_id+preferred_date+status`) |
| ai_insights | `id`, `generated_at` |
| site_content | `key` (unique) |

---

*Back to: [System Design](../system-design.md) | Next: [Sequence Diagrams](sequences.md)*
