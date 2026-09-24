"""
Builds /app/docs/output/07_Technology_Stack.pdf from the same content as the
.docx generator. Uses WeasyPrint to render an HTML template.
"""
from datetime import datetime
from pathlib import Path
from weasyprint import HTML, CSS

OUT = Path("/app/docs/output/07_Technology_Stack.pdf")

CSS_STYLES = """
@page {
    size: A4;
    margin: 18mm 16mm;
    @bottom-center {
        content: "Cebuana Lhuillier — Technology Stack & Technical Design   |   Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #555;
    }
}
body { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 10.5pt; color: #222; line-height: 1.45; }
h1 { color: #08263e; font-size: 24pt; text-align: center; margin: 30pt 0 8pt; border-bottom: 3px solid #C0392B; padding-bottom: 6pt; }
h2 { color: #08263e; font-size: 15pt; margin-top: 22pt; border-left: 4px solid #C0392B; padding-left: 10pt; }
h3 { color: #08263e; font-size: 12pt; margin-top: 16pt; }
.cover-sub { text-align:center; font-size:13pt; color:#555; font-weight:600; }
.cover-meta { text-align:center; font-size:9.5pt; color:#777; margin: 8pt 0 30pt; }
table { width: 100%; border-collapse: collapse; margin: 8pt 0 14pt; font-size: 9.5pt; page-break-inside: avoid; }
th { background: #08263e; color: white; text-align: left; padding: 6pt 8pt; font-weight: 600; }
td { padding: 5pt 8pt; border-bottom: 1px solid #ddd; vertical-align: top; }
tr:nth-child(even) td { background: #F4F6F8; }
ul { margin: 6pt 0; padding-left: 20pt; }
li { margin: 3pt 0; }
code { background: #F4F6F8; padding: 1pt 4pt; border-radius: 3px; font-size: 9.5pt; color: #C0392B; }
.tag { display: inline-block; background:#08263e; color:white; padding:2pt 6pt; border-radius:3pt; font-size:8.5pt; font-weight:600; }
.muted { color:#666; font-size:9.5pt; }
"""


def tbl(headers, rows):
    th = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


HTML_DOC = f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS_STYLES}</style></head><body>

<h1>Technology Stack &amp; Technical Design</h1>
<div class='cover-sub'>Cebuana Lhuillier — Parking Reservation System</div>
<div class='cover-meta'>Document version 2.0 &nbsp;•&nbsp; Generated {datetime.now().strftime('%B %d, %Y')}<br/>Audience: engineering, security, infrastructure</div>

<h2>1. Executive Summary</h2>
<p>The Parking Reservation System is a three-role corporate web application (End Users, Parking Attendants, Administrators) that manages reservations across multiple buildings, floors, and parking slots. It is built on a FastAPI backend and a React 19 single-page frontend, with a pluggable data layer that runs against either MongoDB 7.0 or Couchbase 7+ (Capella cloud or on-premise Enterprise) controlled by a single environment variable. The application is containerized for Docker / Kubernetes deployment and ships with a same-origin nginx reverse-proxy front end that eliminates browser CORS concerns and keeps HttpOnly auth cookies isolated to one origin.</p>
<p><strong>Key architectural properties:</strong></p>
<ul>
<li>Stateless backend (no in-process session affinity) — horizontally scalable</li>
<li>All configuration via 12-factor environment variables; no hard-coded secrets</li>
<li>Database abstraction layer with Motor-shaped API; switching DB engines requires zero call-site changes</li>
<li>JWT (HS256) auth with HttpOnly Secure cookies and bcrypt password hashing</li>
<li>Background coroutines for auto-no-show, waitlist expiry, and slot auto-release</li>
<li>Rate limiting via SlowAPI (limits library) with per-IP buckets</li>
<li>Persistent file uploads on a mounted volume (no GridFS dependency)</li>
<li>Hardened CORS (fail-closed when CORS_ORIGINS env var is empty)</li>
<li>VAPT-cleared and QAT-cleared on the most recent test cycles</li>
</ul>

<h2>2. High-Level Architecture</h2>
<p>Three-tier architecture: a React 19 SPA in the browser; an asynchronous FastAPI 0.110.1 service tier mediating all business logic, authentication, and persistence; and a polyglot persistence tier where any deployment can choose between MongoDB 7.0 and Couchbase 7+ at boot.</p>
<h3>Logical request flow</h3>
<p>Browser → nginx 1.27.5 (TLS termination + same-origin <code>/api</code> proxy) → Uvicorn 0.25.0 (ASGI) → FastAPI 0.110.1 routers → Database Abstraction Layer → MongoDB 7.0.31 (via Motor 3.3.1) <em>OR</em> Couchbase 7.6.10-8025-enterprise (via couchbase 4.6.0).</p>
<h3>Background workers (asyncio tasks)</h3>
{tbl(["Task","Cadence","Purpose"], [
    ("auto_mark_no_shows()","Every 60 s","Marks a reservation as no_show when its window has passed without check-in."),
    ("check_waitlist_expiry()","Every 60 s","Expires unresponded waitlist offers after the configured notification window."),
    ("auto_release_slots()","Every 60 s","Resets parking_slots.status to 'available' once the building's release_time has passed and no active reservation occupies the slot."),
])}

<h2>3. Backend Stack (Python)</h2>
<h3>Runtime &amp; build</h3>
{tbl(["Component","Exact Version","Notes"], [
    ("Python","3.11.15","CPython, Linux x86_64"),
    ("Uvicorn","0.25.0","ASGI server. Started with <code>--proxy-headers --forwarded-allow-ips='*'</code>"),
    ("Docker base image (backend)","python:3.11.15-slim","Multi-stage Dockerfile; runs as non-root uid 10001"),
])}

<h3>Core web framework &amp; validation</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("FastAPI","0.110.1","ASGI web framework"),
    ("Starlette","0.37.2","Underlying ASGI toolkit"),
    ("Pydantic","2.12.5","Request/response models"),
    ("pydantic_core","2.41.5","Rust-backed engine"),
    ("email-validator","2.3.0","Backs EmailStr"),
    ("python-multipart","0.0.22","Multipart form parsing"),
    ("python-dotenv","1.2.1",".env loader for dev"),
    ("aiofiles","25.1.0","Async file IO"),
])}

<h3>Authentication &amp; security</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("PyJWT","2.11.0","JWT HS256"),
    ("passlib","1.7.4","Password hash framework"),
    ("bcrypt","4.1.3","Hash primitive"),
    ("python-jose","3.5.0","JWS/JWE alt"),
    ("cryptography","46.0.4","TLS / signing primitives"),
    ("slowapi","0.1.9","Rate limiting middleware"),
    ("limits","5.8.0","SlowAPI storage"),
])}

<h3>Data layer</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("Motor","3.3.1","Async MongoDB driver"),
    ("PyMongo","4.5.0","Required by Motor"),
    ("dnspython","2.8.0","SRV record resolution"),
    ("couchbase","4.6.0","Couchbase Python SDK"),
])}

<h3>AI / LLM &amp; integration</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("emergentintegrations","0.1.0","Universal LLM key client"),
    ("openai","1.99.9","OpenAI SDK"),
    ("litellm","1.80.0","Multi-provider router"),
    ("google-genai","1.62.0","Gemini SDK"),
    ("google-generativeai","0.8.6","Gemini SDK (legacy)"),
    ("tiktoken","0.12.0","Token counting"),
    ("stripe","14.3.0","Payments SDK"),
    ("boto3","1.42.42","AWS SDK"),
    ("requests","2.32.5","Sync HTTP client"),
    ("httpx","0.28.1","Async HTTP client"),
])}

<h3>Document generation &amp; utilities</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("openpyxl","3.1.5","Excel generation"),
    ("python-docx","1.2.0","Word generation"),
    ("weasyprint","68.1","PDF generation (this document)"),
    ("Jinja2","3.1.6","Template engine"),
    ("Pillow","12.1.0","Image handling"),
    ("qrcode","8.2","QR codes for check-in"),
    ("pandas","3.0.0","CSV bulk-upload + report exports"),
    ("numpy","2.4.2","Pandas dependency"),
    ("rich","14.3.2","CLI logging (dev)"),
])}

<h3>Testing &amp; developer tooling</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("pytest","9.0.2","Unit + integration"),
    ("playwright","1.58.0","End-to-end browser automation"),
    ("black","26.1.0","Formatter"),
    ("flake8","7.3.0","Linter"),
    ("isort","7.0.0","Import sorter"),
    ("mypy","1.19.1","Static type checker"),
])}

<h2>4. Frontend Stack (Node / React)</h2>
<h3>Runtime &amp; build</h3>
{tbl(["Component","Exact Version","Notes"], [
    ("Node.js","20.20.2","Build-time only"),
    ("Yarn","1.22.22","Package manager (yarn.lock = source of truth)"),
    ("Docker base (build stage)","node:20.20.2-alpine","Stage 1 of Dockerfile"),
    ("Docker base (runtime stage)","nginx:1.27.5-alpine","Stage 2 — serves static + reverse-proxies /api"),
])}

<h3>Core framework</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("react","19.2.3","UI library"),
    ("react-dom","19.2.3","DOM renderer"),
    ("react-router-dom","7.13.1","Client-side routing (CVE-2025-43865 cleared)"),
    ("react-scripts","5.0.1","CRA build pipeline"),
    ("@craco/craco","7.1.0","Config override"),
])}

<h3>UI primitives — Radix UI (shadcn/ui foundation)</h3>
{tbl(["Component","Exact Version"], [
    ("@radix-ui/react-accordion","1.2.12"),
    ("@radix-ui/react-alert-dialog","1.1.15"),
    ("@radix-ui/react-aspect-ratio","1.1.8"),
    ("@radix-ui/react-avatar","1.1.11"),
    ("@radix-ui/react-checkbox","1.3.3"),
    ("@radix-ui/react-collapsible","1.1.12"),
    ("@radix-ui/react-context-menu","2.2.16"),
    ("@radix-ui/react-dialog","1.1.15"),
    ("@radix-ui/react-dropdown-menu","2.1.16"),
    ("@radix-ui/react-hover-card","1.1.15"),
    ("@radix-ui/react-label","2.1.8"),
    ("@radix-ui/react-menubar","1.1.16"),
    ("@radix-ui/react-navigation-menu","1.2.14"),
    ("@radix-ui/react-popover","1.1.15"),
    ("@radix-ui/react-progress","1.1.8"),
    ("@radix-ui/react-radio-group","1.3.8"),
    ("@radix-ui/react-scroll-area","1.2.10"),
    ("@radix-ui/react-select","2.2.6"),
    ("@radix-ui/react-separator","1.1.8"),
    ("@radix-ui/react-slider","1.3.6"),
    ("@radix-ui/react-slot","1.2.4"),
    ("@radix-ui/react-switch","1.2.6"),
    ("@radix-ui/react-tabs","1.1.13"),
    ("@radix-ui/react-toast","1.2.15"),
    ("@radix-ui/react-toggle","1.1.10"),
    ("@radix-ui/react-toggle-group","1.1.11"),
    ("@radix-ui/react-tooltip","1.2.8"),
])}
<p class='muted'>All shadcn/ui components (Button, Card, Dialog, Tooltip, Sonner, etc.) sit on the above Radix primitives.</p>

<h3>Styling, forms, data viz, utilities</h3>
{tbl(["Component","Exact Version","Purpose"], [
    ("tailwindcss","3.4.19","Utility-first CSS"),
    ("tailwind-merge","3.4.0","Class de-duplication"),
    ("tailwindcss-animate","1.0.7","Animation utilities"),
    ("class-variance-authority","0.7.1","shadcn variant system"),
    ("clsx","2.1.1","Conditional className"),
    ("postcss","8.5.6","CSS processor"),
    ("autoprefixer","10.4.23","Vendor prefixing"),
    ("react-hook-form","7.69.0","Form state"),
    ("@hookform/resolvers","5.2.2","RHF + zod bridge"),
    ("zod","3.25.76","Schema validation"),
    ("recharts","3.6.0","Charts"),
    ("axios","1.13.2","HTTP client"),
    ("sonner","2.0.7","Toasts"),
    ("date-fns","4.1.0","Date utilities"),
    ("react-day-picker","8.10.1","Date range picker"),
    ("react-markdown","10.1.0","Markdown renderer"),
    ("react-resizable-panels","3.0.6","Panels"),
    ("lucide-react","0.507.0","Icons"),
    ("html5-qrcode","2.3.8","QR scan"),
    ("input-otp","1.4.2","OTP input"),
    ("embla-carousel-react","8.6.0","Carousel"),
    ("vaul","1.1.2","Drawer/sheet"),
    ("cmdk","1.1.1","Command palette"),
    ("next-themes","0.4.6","Theme switcher"),
])}

<h3>Linting &amp; dev tooling</h3>
{tbl(["Component","Exact Version"], [
    ("eslint","9.23.0"),
    ("@eslint/js","9.23.0"),
    ("eslint-plugin-import","2.31.0"),
    ("eslint-plugin-jsx-a11y","6.10.2"),
    ("eslint-plugin-react","7.37.4"),
    ("eslint-plugin-react-hooks","5.2.0"),
    ("globals","15.15.0"),
])}

<h2>5. Database Layer</h2>
<p>Two interchangeable storage engines sit behind a shape-compatible Motor-style abstraction. Switching is controlled by the <code>DB_TYPE</code> environment variable; no application code needs to change.</p>
{tbl(["Engine","Exact Version","Used When","Notes"], [
    ("MongoDB Server (CE)","7.0.31","DB_TYPE=mongodb (default)","Single-node Docker deployment uses official mongo:7.0.31 image; clusters use a managed service or replica set"),
    ("Couchbase Server (Enterprise) on Capella","7.6.10-8025-enterprise","DB_TYPE=couchbase","18 native scopes-and-collections under the configured bucket; one Couchbase collection per logical entity"),
])}
<h3>Logical collections (identical names on both engines)</h3>
<p>users, sessions, buildings, floors, parking_slots, vehicles, zones, parking_configs, building_policies, slot_registrations, reservations, waitlist_entries, event_blocks, notifications, site_content, templates, ai_insights, migrations.</p>

<h3>Indexes (Mongo and Couchbase parity)</h3>
<ul>
<li>users.email (unique), users.id (unique), users.role</li>
<li>reservations.id (unique), reservations.user_id, reservations.building_id, reservations.qr_token; compound (slot_id, date, status)</li>
<li>buildings.id, floors.building_id, parking_slots.floor_id</li>
<li>notifications compound (user_id, created_at DESC)</li>
<li>waitlist_entries compound (building_id, preferred_date, status); compound (user_id, status)</li>
<li>slot_registrations compound (slot_id, status); compound (user_id, status); compound (building_id, status)</li>
<li>event_blocks compound (building_id, date)</li>
<li>site_content.key (unique), parking_configs.building_id (unique), building_policies.building_id (unique)</li>
</ul>

<h2>6. Network, Web Server, &amp; Infrastructure</h2>
{tbl(["Component","Exact Version","Role"], [
    ("nginx","1.27.5 (alpine)","Frontend container web server. Serves static React bundle, gzips text assets, reverse-proxies /api/*, sets X-Content-Type-Options/X-Frame-Options/Referrer-Policy"),
    ("Docker Compose CLI","v2 (no version key required in compose file)","/app/docker-compose.yml; profiles {default, couchbase}"),
    ("Kubernetes ingress","Per-deployment (NGINX ingress, Traefik, or LB)","Out-of-scope for this stack doc; TLS termination + edge caching live there"),
])}

<h3>Container topology (docker-compose default profile)</h3>
{tbl(["Service","Image","Internal Port","Notes"], [
    ("frontend","parking-frontend:latest (built from /app/frontend/Dockerfile)","80","Multi-stage: yarn build → nginx; healthcheck on /healthz"),
    ("backend","parking-backend:latest (built from /app/backend/Dockerfile)","8001","Uvicorn ASGI; healthcheck on /health; non-root user"),
    ("mongo","mongo:7.0.31","27017","Optional — only when DB_TYPE=mongodb; mongo_data volume"),
])}

<h2>7. Security Posture</h2>
{tbl(["Control","Implementation"], [
    ("Transport security","TLS terminated upstream (Caddy / Traefik / cloud LB). Backend honours X-Forwarded-Proto via uvicorn --proxy-headers."),
    ("Auth tokens","JWT HS256, signed with a 64-byte JWT_SECRET, delivered via HttpOnly Secure cookies (Secure flag toggled by COOKIE_SECURE env var)."),
    ("Password storage","bcrypt 4.1.3 via passlib 1.7.4."),
    ("Brute force","SlowAPI rate limiter on /api/auth/login (per IP)."),
    ("CORS","Fail-closed: <code>allow_origins</code> defaults to []. Operators must opt in via CORS_ORIGINS env var."),
    ("CSV/Excel formula injection","All free-text user fields sanitized at write time (single-user POST/PUT and bulk upload). Backfill script available."),
    ("Source maps","GENERATE_SOURCEMAP=false in frontend build."),
    ("API version disclosure","/api/ root returns only {message, status}; no version string."),
    ("Build-info verification","GET /api/system/build-info returns deploy timestamp + key package versions, unauthenticated, for cache-freshness retests."),
    ("CSV bulk upload privilege guard","Bulk upload silently downgrades any 'admin' role from CSV to 'user'."),
    ("Field-level access control","Non-admin reads of /api/parking-config and /api/slot-registrations are trimmed/scoped (V-02 fix)."),
    ("Logout & session invalidation","Sessions persisted server-side; revoked on logout and on password change."),
])}

<h2>8. Build &amp; Deploy Process</h2>
<h3>Backend image build</h3>
<ul>
<li>Base: <code>python:3.11.15-slim</code></li>
<li>apt: build-essential, libssl-dev, ca-certificates, curl</li>
<li><code>pip install -r requirements.txt</code></li>
<li><code>pip install emergentintegrations==0.1.0 --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/</code></li>
<li>Add non-root user uid=10001</li>
<li>EXPOSE 8001 / CMD <code>uvicorn server:app --host 0.0.0.0 --port 8001 --proxy-headers --forwarded-allow-ips=*</code></li>
<li>HEALTHCHECK GET /health every 30 s</li>
</ul>
<h3>Frontend image build</h3>
<ul>
<li>Stage 1 (build): <code>node:20.20.2-alpine</code>, <code>yarn install --frozen-lockfile</code>, <code>yarn build</code> (REACT_APP_BACKEND_URL passed in as a build arg, may be empty for same-origin)</li>
<li>Stage 2 (runtime): <code>nginx:1.27.5-alpine</code>, copies <code>/app/build</code> into <code>/usr/share/nginx/html</code>, custom <code>/etc/nginx/conf.d/app.conf</code> with the SPA fallback + /api reverse proxy</li>
<li>EXPOSE 80</li>
<li>HEALTHCHECK <code>wget /healthz</code> every 30 s</li>
</ul>

<h2>9. Environment Variables — Canonical List</h2>
{tbl(["Variable","Required?","Used By","Description / Default"], [
    ("DB_TYPE","Yes","Backend","'mongodb' (default) or 'couchbase' — selects active adapter"),
    ("MONGO_URL","Conditional","Backend","Required when DB_TYPE=mongodb."),
    ("DB_NAME","Conditional","Backend","MongoDB database name. Default 'parking'"),
    ("COUCHBASE_CONNECTION_STRING","Conditional","Backend","couchbases://... required when DB_TYPE=couchbase"),
    ("COUCHBASE_BUCKET","Conditional","Backend","Capella/Enterprise bucket name"),
    ("COUCHBASE_USERNAME","Conditional","Backend","DB user with bucket+collection mgmt permission"),
    ("COUCHBASE_PASSWORD","Conditional","Backend","Paired credential"),
    ("JWT_SECRET","Yes","Backend","64-byte hex string. Generate with: <code>openssl rand -hex 64</code>"),
    ("JWT_ALGORITHM","No","Backend","Default HS256"),
    ("JWT_EXPIRATION_HOURS","No","Backend","Default 0.5 (30 minutes)"),
    ("COOKIE_SECURE","Yes (prod)","Backend","'true' = Secure flag set on auth cookie; 'false' for local plain HTTP"),
    ("CORS_ORIGINS","No","Backend","Comma-separated list of allowed origins. Empty = fail-closed"),
    ("UPLOAD_DIR","No","Backend","Path for uploaded layout images. Default /var/lib/parking/uploads"),
    ("EMERGENT_LLM_KEY","Optional","Backend","Universal LLM key for AI Insights"),
    ("REACT_APP_BACKEND_URL","Build-time","Frontend","Baked into JS bundle. Empty = same-origin proxy"),
    ("FRONTEND_PORT","No","docker-compose","Host-side port mapping. Default 3000"),
])}

<h2>10. Versioning &amp; Upgrade Cadence</h2>
<p>All Python dependencies are pinned to exact versions in <code>/app/backend/requirements.txt</code>. All Node dependencies use exact resolved versions captured in <code>/app/frontend/yarn.lock</code>. Reproducible builds are guaranteed by these two files.</p>
{tbl(["Component","Cadence","Trigger / Notes"], [
    ("Security patches (any pinned dep)","Within 7 days of CVE disclosure","Subscribe to Pydantic, FastAPI, react-router-dom, bcrypt, cryptography advisories"),
    ("Minor updates (Pydantic, FastAPI, React Radix)","Quarterly","Run pytest + Playwright suites against staging before promoting"),
    ("Major upgrades (Python, Node, React, MongoDB, Couchbase)","Annually","Plan a 1-week stabilization window; verify both DB adapters"),
    ("Container base images","Monthly rebuild","Picks up patched apt + alpine packages even when application code is unchanged"),
])}

<h2>11. Repository Reference Map</h2>
{tbl(["File / Folder","Purpose"], [
    ("/app/backend/requirements.txt","Pinned Python dependencies"),
    ("/app/backend/Dockerfile","Backend container build"),
    ("/app/backend/server.py","FastAPI app, route mounting, CORS, startup tasks"),
    ("/app/backend/database/","Abstraction layer (interface, mongodb, couchbase_db, __init__)"),
    ("/app/backend/routes/","All API routers (auth, users, buildings, reservations, ...)"),
    ("/app/backend/services/background.py","auto_mark_no_shows, check_waitlist_expiry, auto_release_slots"),
    ("/app/backend/scripts/provision_couchbase_collections.py","Idempotent Couchbase scope+collection provisioning"),
    ("/app/backend/scripts/migrate_mongo_to_couchbase.py","Mongo→Couchbase data migration"),
    ("/app/backend/scripts/backfill_csv_sanitization.py","V-08 backfill"),
    ("/app/frontend/package.json + yarn.lock","Frontend dependency manifest + lockfile"),
    ("/app/frontend/Dockerfile","Multi-stage frontend build"),
    ("/app/frontend/nginx.conf","Same-origin reverse proxy + SPA fallback"),
    ("/app/docker-compose.yml","Three-service stack: backend + frontend + mongo (profile-gated)"),
    ("/app/.env.example","Canonical env-var template"),
    ("/app/docs/DEPLOYMENT.md","Step-by-step deployment guide"),
    ("/app/docs/output/VAPT_Tracker_2026-03-25.xlsx","Latest VAPT remediation tracker"),
    ("/app/docs/output/QAT_Failed_Items_Tracker_2026-03-23.xlsx","Latest QAT failed-items tracker"),
    ("/app/memory/PRD.md","Living product requirements doc"),
])}

</body></html>"""

HTML(string=HTML_DOC).write_pdf(str(OUT))
print(f"Wrote {OUT}")
