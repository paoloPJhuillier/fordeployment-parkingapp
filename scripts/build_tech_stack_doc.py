"""
Generates the Technology Stack document for the Cebuana Lhuillier Parking
Reservation System with EXACT (no '.x') version pins of every runtime and
build-time component.

Outputs:
  /app/docs/output/07_Technology_Stack.docx
"""
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = Path("/app/docs/output/07_Technology_Stack.docx")
OUT.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------
NAVY = RGBColor(0x08, 0x26, 0x3E)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREY = RGBColor(0x55, 0x55, 0x55)


def set_cell_bg(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def add_h(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for r in h.runs:
        r.font.color.rgb = NAVY
    return h


def add_p(doc, text, size=10.5, bold=False, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    if bold:
        r.bold = True
    if color is not None:
        r.font.color.rgb = color
    return p


def add_table(doc, headers, rows, widths=None, alt_shade=True):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.size = Pt(10)
        set_cell_bg(hdr[i], "08263E")
    for ri, row in enumerate(rows):
        cells = t.rows[ri + 1].cells
        for ci, val in enumerate(row):
            cells[ci].text = str(val)
            for p in cells[ci].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9.5)
        if alt_shade and ri % 2 == 0:
            for c in cells:
                set_cell_bg(c, "F4F6F8")
    if widths:
        for col, w in enumerate(widths):
            for row in t.rows:
                row.cells[col].width = Cm(w)
    return t


# ---------------------------------------------------------------------------
# Build document
# ---------------------------------------------------------------------------
doc = Document()
section = doc.sections[0]
section.left_margin = Cm(2.0)
section.right_margin = Cm(2.0)
section.top_margin = Cm(1.8)
section.bottom_margin = Cm(1.8)

# ---- Cover ----
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = title.add_run("Technology Stack & Technical Design")
tr.bold = True; tr.font.size = Pt(26); tr.font.color.rgb = NAVY

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sr = sub.add_run("Cebuana Lhuillier — Parking Reservation System")
sr.bold = True; sr.font.size = Pt(14); sr.font.color.rgb = GREY

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
mr = meta.add_run(
    f"Document version 2.0  •  Generated {datetime.now().strftime('%B %d, %Y')}\n"
    "Audience: engineering, security, infrastructure"
)
mr.font.size = Pt(10); mr.font.color.rgb = GREY

doc.add_paragraph()

# ============================================================
# 1. Executive Summary
# ============================================================
add_h(doc, "1. Executive Summary")
add_p(doc, (
    "The Parking Reservation System is a three-role corporate web application "
    "(End Users, Parking Attendants, Administrators) that manages reservations "
    "across multiple buildings, floors, and parking slots. It is built on a "
    "FastAPI backend and a React 19 single-page frontend, with a pluggable "
    "data layer that runs against either MongoDB 7.0 or Couchbase 7+ (Capella "
    "cloud or on-premise Enterprise) controlled by a single environment "
    "variable. The application is containerized for Docker / Kubernetes "
    "deployment and ships with a same-origin nginx reverse-proxy front end "
    "that eliminates browser CORS concerns and keeps HttpOnly auth cookies "
    "isolated to one origin."
), size=10.5)

add_p(doc, "Key architectural properties:", size=10.5, bold=True)
for b in [
    "Stateless backend (no in-process session affinity) — horizontally scalable",
    "All configuration via 12-factor environment variables; no hard-coded secrets",
    "Database abstraction layer with Motor-shaped API; switching DB engines requires zero call-site changes",
    "JWT (HS256) auth with HttpOnly Secure cookies and bcrypt password hashing",
    "Background coroutines for auto-no-show, waitlist expiry, and slot auto-release",
    "Rate limiting via SlowAPI (limits library) with per-IP buckets",
    "Persistent file uploads on a mounted volume (no GridFS dependency)",
    "Hardened CORS (fail-closed when CORS_ORIGINS env var is empty)",
    "VAPT-cleared and QAT-cleared on the most recent test cycles",
]:
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(b); r.font.size = Pt(10)

# ============================================================
# 2. High-Level Architecture
# ============================================================
add_h(doc, "2. High-Level Architecture")
add_p(doc, (
    "Three-tier architecture: a React 19 SPA in the browser; an asynchronous "
    "FastAPI 0.110.1 service tier mediating all business logic, authentication, "
    "and persistence; and a polyglot persistence tier where any deployment can "
    "choose between MongoDB 7.0 and Couchbase 7+ at boot."
), size=10.5)

add_p(doc, "Logical request flow", size=11, bold=True)
add_p(doc,
      "Browser  →  nginx 1.27 (TLS termination + same-origin /api proxy)  "
      "→  Uvicorn 0.25.0 (ASGI)  →  FastAPI 0.110.1 routers  "
      "→  Database Abstraction Layer  →  MongoDB 7.0 (via Motor 3.3.1) "
      "OR Couchbase 7+ (via couchbase 4.6.0).",
      size=10)

add_p(doc, "Background workers (asyncio tasks running in-process):", size=11, bold=True)
add_table(doc,
    ["Task", "Cadence", "Purpose"],
    [
        ("auto_mark_no_shows()", "Every 60 s",
         "Marks a reservation as no_show when its window has passed without check-in."),
        ("check_waitlist_expiry()", "Every 60 s",
         "Expires unresponded waitlist offers after the configured notification window."),
        ("auto_release_slots()", "Every 60 s",
         "Resets parking_slots.status to 'available' once a building's configured "
         "release_time has passed and no active reservation occupies the slot."),
    ],
    widths=[5.5, 3.0, 9.5]
)

# ============================================================
# 3. Backend stack — exact pinned versions
# ============================================================
add_h(doc, "3. Backend Stack (Python)")

add_p(doc, "Runtime & build", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Notes"],
    [
        ("Python", "3.11.15", "CPython, Linux x86_64 in production images"),
        ("Uvicorn", "0.25.0", "ASGI server. Started with --proxy-headers --forwarded-allow-ips='*' so X-Forwarded-Proto from the LB is honored"),
        ("Docker base image (backend)", "python:3.11.15-slim", "Multi-stage Dockerfile at /app/backend/Dockerfile; runs as non-root uid 10001"),
    ],
    widths=[5.0, 4.0, 9.0]
)

add_p(doc, "Core web framework & validation", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("FastAPI", "0.110.1", "ASGI web framework; declarative routing & DI"),
        ("Starlette", "0.37.2", "Underlying ASGI toolkit (transitive)"),
        ("Pydantic", "2.12.5", "Request/response models + Field validators"),
        ("pydantic_core", "2.41.5", "Rust-backed Pydantic engine"),
        ("email-validator", "2.3.0", "Backs EmailStr type"),
        ("python-multipart", "0.0.22", "Multipart form parsing for file uploads"),
        ("python-dotenv", "1.2.1", ".env loader for local dev"),
        ("aiofiles", "25.1.0", "Async file IO for upload handlers"),
    ],
    widths=[5.0, 3.5, 9.5]
)

add_p(doc, "Authentication & security", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("PyJWT", "2.11.0", "JWT issuance/verification (HS256)"),
        ("passlib", "1.7.4", "Password hash framework"),
        ("bcrypt", "4.1.3", "Password hashing primitive (passlib backend)"),
        ("python-jose", "3.5.0", "JWS/JWE alternative library (kept for compatibility)"),
        ("cryptography", "46.0.4", "TLS / signing primitives, transitive for couchbase + jose"),
        ("slowapi", "0.1.9", "Per-IP rate limiting middleware"),
        ("limits", "5.8.0", "Storage backend for slowapi"),
    ],
    widths=[5.0, 3.5, 9.5]
)

add_p(doc, "Data layer", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("Motor", "3.3.1", "Async MongoDB driver — used by MongoDBDatabase adapter"),
        ("PyMongo", "4.5.0", "Required by Motor"),
        ("dnspython", "2.8.0", "MongoDB SRV record resolution"),
        ("couchbase", "4.6.0", "Couchbase Python SDK — used by CouchbaseDatabase adapter"),
    ],
    widths=[5.0, 3.5, 9.5]
)

add_p(doc, "AI / LLM & integration", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("emergentintegrations", "0.1.0", "Universal LLM key client (OpenAI / Anthropic / Gemini)"),
        ("openai", "1.99.9", "OpenAI SDK (transitive via emergentintegrations)"),
        ("litellm", "1.80.0", "Multi-provider routing layer used internally"),
        ("google-genai", "1.62.0", "Gemini SDK"),
        ("google-generativeai", "0.8.6", "Gemini SDK (legacy entry)"),
        ("tiktoken", "0.12.0", "OpenAI token counting"),
        ("stripe", "14.3.0", "Payments SDK (used only if Stripe integration is enabled)"),
        ("boto3", "1.42.42", "AWS SDK (transitive)"),
        ("requests", "2.32.5", "Sync HTTP client"),
        ("httpx", "0.28.1", "Async HTTP client"),
    ],
    widths=[5.0, 3.5, 9.5]
)

add_p(doc, "Document generation & utilities", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("openpyxl", "3.1.5", "Excel (.xlsx) generation — VAPT/QAT trackers"),
        ("python-docx", "1.2.0", "Word (.docx) generation — this document"),
        ("weasyprint", "68.1", "PDF generation"),
        ("Jinja2", "3.1.6", "Template engine for emails & PDFs"),
        ("Pillow", "12.1.0", "Image handling"),
        ("qrcode", "8.2", "QR code generation for reservation check-in"),
        ("pandas", "3.0.0", "CSV bulk-upload parsing & report exports"),
        ("numpy", "2.4.2", "Pandas dependency"),
        ("rich", "14.3.2", "CLI logging niceties (dev only)"),
    ],
    widths=[5.0, 3.5, 9.5]
)

add_p(doc, "Testing & developer tooling", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("pytest", "9.0.2", "Unit & integration tests"),
        ("playwright", "1.58.0", "End-to-end browser automation"),
        ("black", "26.1.0", "Code formatter"),
        ("flake8", "7.3.0", "Linter"),
        ("isort", "7.0.0", "Import sorter"),
        ("mypy", "1.19.1", "Static type checker"),
    ],
    widths=[5.0, 3.5, 9.5]
)

# ============================================================
# 4. Frontend stack — exact pinned versions
# ============================================================
add_h(doc, "4. Frontend Stack (Node / React)")

add_p(doc, "Runtime & build", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Notes"],
    [
        ("Node.js", "20.20.2", "Build-time only; the served bundle is static"),
        ("Yarn", "1.22.22", "Package manager — yarn.lock is the source of truth"),
        ("Docker base (build stage)", "node:20.20.2-alpine", "Stage 1 of /app/frontend/Dockerfile"),
        ("Docker base (runtime stage)", "nginx:1.27.5-alpine", "Stage 2: serves static files + reverse-proxies /api"),
    ],
    widths=[5.0, 4.0, 9.0]
)

add_p(doc, "Core framework", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("react", "19.2.3", "UI library"),
        ("react-dom", "19.2.3", "DOM renderer"),
        ("react-router-dom", "7.13.1", "Client-side routing (CVE-2025-43865 cleared)"),
        ("react-scripts", "5.0.1", "CRA build pipeline"),
        ("@craco/craco", "7.1.0", "Override CRA config without ejecting"),
    ],
    widths=[5.0, 3.5, 9.5]
)

add_p(doc, "UI primitives — Radix UI (shadcn/ui foundation)", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version"],
    [
        ("@radix-ui/react-accordion", "1.2.12"),
        ("@radix-ui/react-alert-dialog", "1.1.15"),
        ("@radix-ui/react-aspect-ratio", "1.1.8"),
        ("@radix-ui/react-avatar", "1.1.11"),
        ("@radix-ui/react-checkbox", "1.3.3"),
        ("@radix-ui/react-collapsible", "1.1.12"),
        ("@radix-ui/react-context-menu", "2.2.16"),
        ("@radix-ui/react-dialog", "1.1.15"),
        ("@radix-ui/react-dropdown-menu", "2.1.16"),
        ("@radix-ui/react-hover-card", "1.1.15"),
        ("@radix-ui/react-label", "2.1.8"),
        ("@radix-ui/react-menubar", "1.1.16"),
        ("@radix-ui/react-navigation-menu", "1.2.14"),
        ("@radix-ui/react-popover", "1.1.15"),
        ("@radix-ui/react-progress", "1.1.8"),
        ("@radix-ui/react-radio-group", "1.3.8"),
        ("@radix-ui/react-scroll-area", "1.2.10"),
        ("@radix-ui/react-select", "2.2.6"),
        ("@radix-ui/react-separator", "1.1.8"),
        ("@radix-ui/react-slider", "1.3.6"),
        ("@radix-ui/react-slot", "1.2.4"),
        ("@radix-ui/react-switch", "1.2.6"),
        ("@radix-ui/react-tabs", "1.1.13"),
        ("@radix-ui/react-toast", "1.2.15"),
        ("@radix-ui/react-toggle", "1.1.10"),
        ("@radix-ui/react-toggle-group", "1.1.11"),
        ("@radix-ui/react-tooltip", "1.2.8"),
    ],
    widths=[10.0, 7.0]
)
add_p(doc, "All shadcn/ui components (Button, Card, Dialog, Tooltip, Sonner, etc.) sit on the above Radix primitives.", size=9.5, color=GREY)

add_p(doc, "Styling, forms, data viz, utilities", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version", "Purpose"],
    [
        ("tailwindcss", "3.4.19", "Utility-first CSS"),
        ("tailwind-merge", "3.4.0", "Class de-duplication helper"),
        ("tailwindcss-animate", "1.0.7", "Animation utilities"),
        ("class-variance-authority", "0.7.1", "shadcn variant system"),
        ("clsx", "2.1.1", "Conditional className builder"),
        ("postcss", "8.5.6", "CSS processor (build pipeline)"),
        ("autoprefixer", "10.4.23", "Auto vendor prefixing"),
        ("react-hook-form", "7.69.0", "Form state management"),
        ("@hookform/resolvers", "5.2.2", "Bridge between react-hook-form and zod"),
        ("zod", "3.25.76", "Schema validation"),
        ("recharts", "3.6.0", "Charts on Admin Dashboard / Reports"),
        ("axios", "1.13.2", "HTTP client"),
        ("sonner", "2.0.7", "Toast notifications"),
        ("date-fns", "4.1.0", "Date arithmetic / formatting"),
        ("react-day-picker", "8.10.1", "Date range picker"),
        ("react-markdown", "10.1.0", "Markdown renderer for AI insights"),
        ("react-resizable-panels", "3.0.6", "Resizable layout panels"),
        ("lucide-react", "0.507.0", "Icon set"),
        ("html5-qrcode", "2.3.8", "QR scan on attendant check-in"),
        ("input-otp", "1.4.2", "OTP input component"),
        ("embla-carousel-react", "8.6.0", "Carousel primitive"),
        ("vaul", "1.1.2", "Drawer / sheet for mobile"),
        ("cmdk", "1.1.1", "Command palette primitive"),
        ("next-themes", "0.4.6", "Dark/light theme switcher"),
    ],
    widths=[5.0, 3.5, 9.5]
)

add_p(doc, "Linting & dev tooling", size=11, bold=True)
add_table(doc,
    ["Component", "Exact Version"],
    [
        ("eslint", "9.23.0"),
        ("@eslint/js", "9.23.0"),
        ("eslint-plugin-import", "2.31.0"),
        ("eslint-plugin-jsx-a11y", "6.10.2"),
        ("eslint-plugin-react", "7.37.4"),
        ("eslint-plugin-react-hooks", "5.2.0"),
        ("globals", "15.15.0"),
    ],
    widths=[10.0, 7.0]
)

# ============================================================
# 5. Database Layer
# ============================================================
add_h(doc, "5. Database Layer")

add_p(doc,
      "Two interchangeable storage engines sit behind a shape-compatible "
      "Motor-style abstraction. Switching is controlled by the DB_TYPE "
      "environment variable; no application code needs to change.", size=10.5)

add_table(doc,
    ["Engine", "Exact Version", "Used When", "Notes"],
    [
        ("MongoDB Server (CE)", "7.0.31",
         "DB_TYPE=mongodb (default)",
         "Single-node Docker deployment uses official mongo:7 image; clusters use a managed service or replica set"),
        ("Couchbase Server (Enterprise) on Capella", "7.6.10-8025-enterprise",
         "DB_TYPE=couchbase",
         "18 native scopes-and-collections under the configured bucket; one Couchbase collection per logical entity"),
    ],
    widths=[3.6, 3.5, 3.0, 7.0]
)

add_p(doc, "Logical collections (identical names on both engines):", size=11, bold=True)
add_p(doc,
      "users, sessions, buildings, floors, parking_slots, vehicles, zones, "
      "parking_configs, building_policies, slot_registrations, reservations, "
      "waitlist_entries, event_blocks, notifications, site_content, templates, "
      "ai_insights, migrations.", size=10)

add_p(doc, "Indexes (Mongo and Couchbase parity):", size=11, bold=True)
for line in [
    "users.email (unique), users.id (unique), users.role",
    "reservations.id (unique), reservations.user_id, reservations.building_id, reservations.qr_token; compound (slot_id, date, status)",
    "buildings.id, floors.building_id, parking_slots.floor_id",
    "notifications compound (user_id, created_at DESC)",
    "waitlist_entries compound (building_id, preferred_date, status); compound (user_id, status)",
    "slot_registrations compound (slot_id, status); compound (user_id, status); compound (building_id, status)",
    "event_blocks compound (building_id, date)",
    "site_content.key (unique), parking_configs.building_id (unique), building_policies.building_id (unique)",
]:
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(line); r.font.size = Pt(9.5)

# ============================================================
# 6. Network & Infrastructure
# ============================================================
add_h(doc, "6. Network, Web Server, & Infrastructure")

add_table(doc,
    ["Component", "Exact Version", "Role"],
    [
        ("nginx", "1.27.5 (alpine)",
         "Frontend container web server. Serves static React bundle, gzips text assets, reverse-proxies /api/* to the backend service, sets X-Content-Type-Options nosniff / X-Frame-Options DENY / Referrer-Policy strict-origin-when-cross-origin"),
        ("Docker Compose CLI", "v2 (no version key required in compose file)",
         "/app/docker-compose.yml; profiles {default, couchbase}"),
        ("Kubernetes ingress", "Per-deployment (NGINX ingress, Traefik, or LB)",
         "Out-of-scope for this stack doc; TLS termination + edge caching live there"),
    ],
    widths=[4.5, 4.5, 8.5]
)

add_p(doc, "Container topology (docker-compose default profile):", size=11, bold=True)
add_table(doc,
    ["Service", "Image", "Internal Port", "Notes"],
    [
        ("frontend", "parking-frontend:latest (built from /app/frontend/Dockerfile)", "80",
         "Multi-stage: yarn build → nginx; healthcheck on /healthz"),
        ("backend", "parking-backend:latest (built from /app/backend/Dockerfile)", "8001",
         "Uvicorn ASGI; healthcheck on /health; non-root user"),
        ("mongo", "mongo:7.0.31", "27017",
         "Optional — only when DB_TYPE=mongodb; mongo_data volume"),
    ],
    widths=[3.0, 7.5, 3.0, 7.0]
)

# ============================================================
# 7. Security Posture
# ============================================================
add_h(doc, "7. Security Posture")

add_table(doc,
    ["Control", "Implementation"],
    [
        ("Transport security", "TLS terminated upstream (Caddy / Traefik / cloud LB). Backend honours X-Forwarded-Proto via uvicorn --proxy-headers."),
        ("Auth tokens", "JWT HS256, signed with a 64-byte JWT_SECRET, delivered via HttpOnly Secure cookies (Secure flag toggled by COOKIE_SECURE env var)."),
        ("Password storage", "bcrypt 4.1.3 via passlib 1.7.4. Cost factor default."),
        ("Brute force", "SlowAPI rate limiter on /api/auth/login (per IP)."),
        ("CORS", "Fail-closed: allow_origins defaults to []. Operators must opt in via CORS_ORIGINS env var. Recommended path is the same-origin nginx proxy → no CORS at all."),
        ("CSV/Excel formula injection", "All free-text user fields sanitized at write time (single-user POST/PUT and bulk upload). Backfill script available."),
        ("Source maps", "GENERATE_SOURCEMAP=false in frontend build. No production maps shipped."),
        ("API version disclosure", "/api/ root returns only {message, status}; no version string."),
        ("Build-info verification", "GET /api/system/build-info returns deploy timestamp + key package versions, unauthenticated, for cache-freshness retests."),
        ("CSV bulk upload privilege guard", "Bulk upload silently downgrades any 'admin' role from CSV to 'user'."),
        ("Field-level access control", "Non-admin reads of /api/parking-config and /api/slot-registrations are trimmed/scoped (V-02 fix)."),
        ("Logout & session invalidation", "Sessions persisted server-side; revoked on logout and on password change."),
    ],
    widths=[5.0, 12.5]
)

# ============================================================
# 8. CI/CD & Build Process
# ============================================================
add_h(doc, "8. Build & Deploy Process")

add_p(doc, "Backend image build (single-stage Dockerfile):", size=11, bold=True)
for line in [
    "Base: python:3.11.15-slim",
    "apt: build-essential, libssl-dev, ca-certificates, curl",
    "pip install -r requirements.txt",
    "pip install emergentintegrations==0.1.0 --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/",
    "Add non-root user uid=10001",
    "EXPOSE 8001  /  CMD uvicorn server:app --host 0.0.0.0 --port 8001 --proxy-headers --forwarded-allow-ips=*",
    "HEALTHCHECK GET /health every 30 s",
]:
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(line); r.font.size = Pt(9.5)

add_p(doc, "Frontend image build (multi-stage Dockerfile):", size=11, bold=True)
for line in [
    "Stage 1 (build): node:20.20.2-alpine, yarn install --frozen-lockfile, yarn build (REACT_APP_BACKEND_URL passed in as a build arg, may be empty for same-origin)",
    "Stage 2 (runtime): nginx:1.27.5-alpine, copies /app/build into /usr/share/nginx/html, custom /etc/nginx/conf.d/app.conf with the SPA fallback + /api reverse proxy",
    "EXPOSE 80",
    "HEALTHCHECK wget /healthz every 30 s",
]:
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(line); r.font.size = Pt(9.5)

# ============================================================
# 9. Environment Variables (canonical)
# ============================================================
add_h(doc, "9. Environment Variables — Canonical List")

add_table(doc,
    ["Variable", "Required?", "Used By", "Description / Default"],
    [
        ("DB_TYPE", "Yes", "Backend",
         "'mongodb' (default) or 'couchbase' — selects active adapter"),
        ("MONGO_URL", "Conditional", "Backend",
         "Required when DB_TYPE=mongodb. e.g. mongodb://mongo:27017"),
        ("DB_NAME", "Conditional", "Backend",
         "MongoDB database name. Default 'parking'"),
        ("COUCHBASE_CONNECTION_STRING", "Conditional", "Backend",
         "couchbases://... required when DB_TYPE=couchbase"),
        ("COUCHBASE_BUCKET", "Conditional", "Backend",
         "Capella/Enterprise bucket name"),
        ("COUCHBASE_USERNAME", "Conditional", "Backend",
         "DB user with bucket+collection mgmt permission"),
        ("COUCHBASE_PASSWORD", "Conditional", "Backend",
         "Paired credential"),
        ("JWT_SECRET", "Yes", "Backend",
         "64-byte hex string. Generate with: openssl rand -hex 64"),
        ("JWT_ALGORITHM", "No", "Backend",
         "Default HS256"),
        ("JWT_EXPIRATION_HOURS", "No", "Backend",
         "Default 0.5 (30 minutes)"),
        ("COOKIE_SECURE", "Yes (prod)", "Backend",
         "'true' = Secure flag set on auth cookie (production behind TLS); 'false' for local plain HTTP testing"),
        ("CORS_ORIGINS", "No", "Backend",
         "Comma-separated list of allowed origins. Empty = fail-closed (recommended when using same-origin nginx proxy)"),
        ("UPLOAD_DIR", "No", "Backend",
         "Path for uploaded layout images. Default /var/lib/parking/uploads in containers"),
        ("EMERGENT_LLM_KEY", "Optional", "Backend",
         "Universal LLM key for AI Insights. Disable AI routes if absent"),
        ("REACT_APP_BACKEND_URL", "Build-time", "Frontend",
         "Baked into JS bundle. Leave empty for same-origin proxy mode"),
        ("FRONTEND_PORT", "No", "docker-compose",
         "Host-side port mapping. Default 3000"),
    ],
    widths=[4.7, 2.5, 2.5, 7.8]
)

# ============================================================
# 10. Versioning & Upgrade Cadence
# ============================================================
add_h(doc, "10. Versioning & Upgrade Cadence")
add_p(doc,
      "All Python dependencies are pinned to exact versions in "
      "/app/backend/requirements.txt (no '~=' or '>=' constraints). All "
      "Node dependencies use exact resolved versions captured in "
      "/app/frontend/yarn.lock. Reproducible builds are guaranteed by these "
      "two files.", size=10.5)

add_p(doc, "Recommended upgrade cadence:", size=11, bold=True)
add_table(doc,
    ["Component", "Cadence", "Trigger / Notes"],
    [
        ("Security patches (any pinned dep)", "Within 7 days of CVE disclosure",
         "Subscribe to Pydantic, FastAPI, react-router-dom, bcrypt, cryptography advisories"),
        ("Minor updates (Pydantic, FastAPI, React Radix)", "Quarterly",
         "Run pytest + Playwright suites against staging before promoting"),
        ("Major upgrades (Python, Node, React, MongoDB, Couchbase)", "Annually",
         "Plan a 1-week stabilization window; verify both DB adapters"),
        ("Container base images", "Monthly rebuild",
         "Picks up patched apt + alpine packages even when application code is unchanged"),
    ],
    widths=[5.5, 4.0, 7.5]
)

# ============================================================
# 11. Reference Files in the Repository
# ============================================================
add_h(doc, "11. Repository Reference Map")

add_table(doc,
    ["File / Folder", "Purpose"],
    [
        ("/app/backend/requirements.txt", "Pinned Python dependencies"),
        ("/app/backend/Dockerfile", "Backend container build"),
        ("/app/backend/server.py", "FastAPI app, route mounting, CORS, startup tasks"),
        ("/app/backend/database/", "Abstraction layer (interface, mongodb, couchbase_db, __init__)"),
        ("/app/backend/routes/", "All API routers (auth, users, buildings, reservations, ...)"),
        ("/app/backend/services/background.py", "auto_mark_no_shows, check_waitlist_expiry, auto_release_slots"),
        ("/app/backend/scripts/provision_couchbase_collections.py", "Idempotent Couchbase scope+collection provisioning"),
        ("/app/backend/scripts/migrate_mongo_to_couchbase.py", "Mongo→Couchbase data migration"),
        ("/app/backend/scripts/backfill_csv_sanitization.py", "V-08 backfill"),
        ("/app/frontend/package.json + yarn.lock", "Frontend dependency manifest + lockfile"),
        ("/app/frontend/Dockerfile", "Multi-stage frontend build"),
        ("/app/frontend/nginx.conf", "Same-origin reverse proxy + SPA fallback"),
        ("/app/docker-compose.yml", "Three-service stack: backend + frontend + mongo (profile-gated)"),
        ("/app/.env.example", "Canonical env-var template"),
        ("/app/docs/DEPLOYMENT.md", "Step-by-step deployment guide"),
        ("/app/docs/output/VAPT_Tracker_2026-03-25.xlsx", "Latest VAPT remediation tracker"),
        ("/app/docs/output/QAT_Failed_Items_Tracker_2026-03-23.xlsx", "Latest QAT failed-items tracker"),
        ("/app/memory/PRD.md", "Living product requirements doc"),
    ],
    widths=[7.5, 9.5]
)

# Footer
foot = doc.add_paragraph()
foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = foot.add_run("— End of Technology Stack Document —")
fr.italic = True; fr.font.size = Pt(9); fr.font.color.rgb = GREY

doc.save(OUT)
print(f"Wrote {OUT}")
print(f"Pages (approx): {len(doc.paragraphs) // 25 + 1}")
