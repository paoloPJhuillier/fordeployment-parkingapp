# Architecture Diagrams
**Related:** [System Design](../system-design.md) · Last Updated: May 12, 2026

> All diagrams use Mermaid syntax, compatible with GitHub Markdown rendering.

---

## 1. Component Architecture (UML Component Diagram)

```mermaid
graph TB
    subgraph "Client Layer"
        Browser["Browser / Mobile"]
    end

    subgraph "Presentation Layer"
        React["React 19 SPA<br/>TailwindCSS + shadcn/ui<br/>useFeatures hook"]
    end

    subgraph "Edge / API Gateway"
        Ingress["K8s Ingress (Nginx) or HCS ELB<br/>TLS termination<br/>/api/* → backend:8001<br/>/* → frontend:80"]
    end

    subgraph "Application Layer (FastAPI)"
        Auth["Auth Module<br/>JWT + bcrypt + Sessions"]
        Routes["Route Modules<br/>15 route files"]
        Features["Feature Flags<br/>AI Insights · Attendant Mode<br/>Self Check-In Window"]
        DBI["DB Abstraction<br/>Motor or Couchbase SDK"]
        SI["Storage Abstraction<br/>Local FS or OBS / S3"]
        Services["Services<br/>Background loops<br/>Notifications · QR"]
    end

    subgraph "Data Layer"
        Mongo[("MongoDB 7.x<br/>staging default")]
        Couchbase[("Couchbase Capella<br/>or Enterprise<br/>production")]
        Storage["File Storage<br/>Local volume or<br/>Huawei OBS / S3"]
    end

    subgraph "External (optional)"
        LLM["Emergent LLM API<br/>AI Insights only"]
    end

    Browser --> React
    React --> Ingress
    Ingress --> Auth
    Ingress --> Routes
    Routes --> Features
    Routes --> Services
    Auth --> DBI
    Routes --> DBI
    Routes --> SI
    DBI --> Mongo
    DBI --> Couchbase
    SI --> Storage
    Routes -.optional.-> LLM
```

---

## 2. Deployment Architecture — Huawei CCE (Kubernetes) Production Target

```mermaid
graph TB
    User["End User Browser"]
    HCSDNS["HCS DNS"]
    User --> HCSDNS

    subgraph "Huawei Cloud Stack (on-prem)"
        ELB["HCS ELB / Nginx Ingress<br/>TLS termination"]

        subgraph "CCE Cluster — namespace parking-app"
            FE1["Frontend Pod 1<br/>nginx + React :80"]
            FE2["Frontend Pod 2<br/>HPA"]
            BL["Backend Leader<br/>:8001 replicas=1<br/>RUN_BACKGROUND_TASKS=true<br/>strategy Recreate"]
            BW1["Backend Worker 1<br/>:8001<br/>RUN_BACKGROUND_TASKS=false"]
            BW2["Backend Worker 2<br/>HPA 2 to 8"]
            BSVC["Service backend<br/>ClusterIP :8001<br/>fronts leader + workers"]
            FSVC["Service frontend<br/>ClusterIP :80"]
        end

        subgraph "Managed Services"
            Couch[("Couchbase Enterprise<br/>:11207 :18091 :18093")]
            OBS[("Huawei OBS<br/>S3-compatible<br/>floor-layout images")]
            SWR["SWR Registry<br/>cebuana-parking"]
        end
    end

    HCSDNS --> ELB
    ELB --> FSVC
    FSVC --> FE1
    FSVC --> FE2
    FE1 -.api.-> BSVC
    FE2 -.api.-> BSVC
    BSVC --> BL
    BSVC --> BW1
    BSVC --> BW2
    BL --> Couch
    BW1 --> Couch
    BW2 --> Couch
    BL --> OBS
    BW1 --> OBS
    BW2 --> OBS
    SWR -.pull.-> FE1
    SWR -.pull.-> BL
```

---

## 3. Application Layer Detail

```mermaid
graph LR
    subgraph "FastAPI Application"
        MW["Middleware Stack"]
        MW --> CORS["CORS"]
        MW --> SEC["Security Headers"]
        MW --> RL["Rate Limiter slowapi"]

        subgraph "Routes (15 modules)"
            R1["auth.py"]
            R2["users.py"]
            R3["buildings.py<br/>storage abstraction"]
            R4["reservations.py<br/>+ self check-in"]
            R5["zones.py"]
            R6["attendant.py"]
            R7["reports.py + AI insights"]
            R8["notifications.py"]
            R9["parking_config.py"]
            R10["templates.py"]
            R11["site_content.py"]
            R12["vehicles.py"]
            R13["waitlist.py"]
            R14["building_policy.py"]
            R15["system.py<br/>features db-info sync"]
        end

        subgraph "Auth Guards"
            G1["get_current_user"]
            G2["require_admin"]
            G3["require_attendant"]
        end

        subgraph "Cross-cutting"
            FF["features.py<br/>AI_INSIGHTS_ENABLED<br/>ATTENDANT_MODE_ENABLED<br/>SELF_CHECKIN_WINDOW_MINUTES"]
            DI["database<br/>interface.py<br/>mongodb.py<br/>couchbase_db.py"]
            SS["storage<br/>interface.py<br/>local.py<br/>obs.py"]
        end

        subgraph "Background (leader pod only)"
            S1["auto_mark_no_shows<br/>+ self-checkin window<br/>+ immediate slot release"]
            S2["check_waitlist_expiry"]
            S3["auto_release_slots"]
        end
    end
```

---

## 4. Frontend Component Tree

```mermaid
graph TD
    App["App.js<br/>Router + AuthProvider"]
    App --> Login["LoginPage"]
    App --> ProtectedRoute

    subgraph "Cross-cutting Hooks"
        UF["useFeatures<br/>GET /api/system/features<br/>ai_insights attendant_mode checkin_window"]
    end

    subgraph "User Routes"
        ProtectedRoute --> UD["UserDashboard"]
        ProtectedRoute --> BP["BookingPage"]
        ProtectedRoute --> VP["VehiclesPage"]
        ProtectedRoute --> RP["ReservationsPage<br/>+ self check-in button"]
        ProtectedRoute --> PP["ProfilePage"]
    end

    subgraph "Admin Routes"
        ProtectedRoute --> AL["AdminLayout<br/>Sidebar + DB Badge"]
        AL --> AD["AdminDashboard<br/>AI Insights btn gated"]
        AL --> UM["UserManagement"]
        AL --> BM["BuildingManagement"]
        AL --> ZM["ZoneManagement"]
        AL --> PC["ParkingConfig"]
        AL --> BPol["BuildingPolicy"]
        AL --> EB["EventBlocking"]
        AL --> RPT["Reports<br/>AI Insights card gated"]
        AL --> AM["AttendantManagement"]
        AL --> SET["Settings"]
    end

    subgraph "Attendant Routes"
        ProtectedRoute --> ATT["AttendantDashboard<br/>fallback if mode off"]
        ProtectedRoute --> SCAN["QRScanPage"]
    end

    UF -.flags.- AD
    UF -.flags.- RPT
    UF -.flags.- RP
```

---

*Back to: [System Design](../system-design.md) | Next: [ERD](erd.md)*
