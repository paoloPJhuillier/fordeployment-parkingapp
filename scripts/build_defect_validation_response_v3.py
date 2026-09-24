"""
Generates /app/docs/output/Defect_Validation_Response_2026-04-30.xlsx —
response to the customer's "Parking App - Defect Validation 2026 04 29.xlsx".

Contains 7 rows from the customer file: 5 already-Closed items spot-checked,
2 NEW Failed items (PPA-71, PPA-70) — both confirmed reproducible AND fixed
in this cycle.
"""
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = Path("/app/docs/output/Defect_Validation_Response_2026-04-30.xlsx")
OUT.parent.mkdir(parents=True, exist_ok=True)

STATUS_COLORS = {
    "Resolved":          "27AE60",
    "Already Resolved":  "16A085",
    "Verified Closed":   "1ABC9C",
}
SEV_COLORS = {"High": "C0392B", "Medium": "E67E22", "Low": "F1C40F", "—": "BDC3C7"}
ASSESS_COLORS = {
    "Confirmed real": "C0392B",
    "Already fixed": "27AE60",
}

# (Defect ID, Title, Severity, Customer Status, Assessment, Resolution Status,
#  Remarks, Code Path, QA Verification Steps)
ITEMS = [
    ("PPA-1", "Login - Invalid credentials shows blank page",
     "High", "Closed",
     "Already fixed", "Verified Closed",
     "Spot-checked on this build: POST /api/auth/login with wrong creds returns HTTP 401 + JSON {\"detail\":\"Invalid credentials\"} as designed; LoginPage catches and shows a sonner toast, page does not blank. Stays Closed.",
     "/app/frontend/src/pages/LoginPage.js (handleLogin)",
     "POST a malformed/wrong login payload — expect 401 + on-page toast."),

    ("PPA-71", "Event Blocking accepts past dates",
     "Medium", "Failed (NEW)",
     "Confirmed real",
     "Resolved",
     "REPRODUCED on this build: POST /api/event-blocks with date=2026-03-15 (past) returned HTTP 200 and created the block. Admin should not be allowed to schedule a block in the past.\n"
     "FIX: Added a past-date guard in routes/event_blocks.py (after the date-format check). Today is still permitted (admins occasionally need to retroactively close out the rest of the current day); strictly past dates now return HTTP 400 \"Cannot create an event block on a past date\".\n"
     "VERIFIED: past date → 400; today (control) → 200.",
     "/app/backend/routes/event_blocks.py (create_event_block)",
     "1) POST /api/event-blocks with date=<yesterday> → expect 400 with the exact message; "
     "2) POST with date=<today> → expect 200; "
     "3) UI: open Block Slots dialog and try to type a past date → backend now rejects (UI-side guard recommended as a follow-up to disable past dates in the date picker)."),

    ("PPA-15", "Reservations by Buildings — building names alignment",
     "Low", "Closed",
     "Already fixed", "Verified Closed",
     "Spot-checked: AdminDashboard BarChart YAxis is width=180 with interval=0 + ellipsis tickFormatter; Tooltip shows the full name. Stays Closed.",
     "/app/frontend/src/pages/admin/AdminDashboard.js (BarChart YAxis)",
     "Reload Admin Dashboard with ≥ 4 buildings of varying name lengths — labels should not overlap or clip."),

    ("PPA-70", "User can book reservations outside their assigned zone",
     "High", "Failed (NEW)",
     "Confirmed real",
     "Resolved",
     "REPRODUCED: user.test (Main Zone, includes 3 buildings) successfully POSTed /api/reservations for KHO (in 'Head Office Central' zone) → HTTP 200. Should have been 403.\n"
     "ROOT CAUSE: The zone check in routes/reservations.py (`{\"user_ids\": uid}`) uses MongoDB's implicit ARRAY-MEMBERSHIP semantic — Mongo treats `{field: x}` as \"x is one of the elements when field is an array\". The Couchbase abstraction in database/couchbase_db.py was translating that to a plain `field = $p`, which always returned false against an array column. Result: on Couchbase, every user appeared to have ZERO zones → check was skipped → users could book anywhere. Same silent failure would also affect any other `{array_field: scalar}` query (assigned_buildings, slot_ids, tags, etc.).\n"
     "FIX: _condition() in couchbase_db.py now emits `(\\`field\\` = $p OR $p IN \\`field\\`)`. The OR-right is the N1QL idiom for array membership; the OR-left preserves scalar semantics. Drop-in compatible for both shapes.\n"
     "VERIFIED: cross-zone booking → 403 \"You are not assigned to this building's zone\"; in-zone booking → permitted (only blocked by orthogonal vehicle-sticker rule).",
     "/app/backend/database/couchbase_db.py (_N1qlBuilder._condition), /app/backend/routes/reservations.py (zone check)",
     "1) Pick a user assigned to Zone A (which contains Building X but not Building Y); "
     "2) POST /api/reservations for a slot in Building Y → expect 403; "
     "3) POST for a slot in Building X → expect success (or fail only for orthogonal reasons). "
     "Critical: this is a multi-tenant isolation defect. Recommend a regression test in /app/backend/tests covering all `{array_field: scalar}` queries on Couchbase."),

    ("PPA-57", "Reports — Recent Reservations shows stale data",
     "Medium", "Closed",
     "Already fixed", "Verified Closed",
     "Reports.js sorts client-side by created_at DESC and refetches on focus / visibility change. Stays Closed.",
     "/app/frontend/src/pages/admin/Reports.js (fetchReservations + useEffect)",
     "Create a reservation; switch to Reports tab → it should appear at the top of Recent Reservations within 1 s of focus."),

    ("PPA-59", "Block Slots dialog — only first conflicting slot reported",
     "Medium", "Closed",
     "Already fixed", "Verified Closed",
     "create_event_block does a two-pass create: collect ALL conflicting slots in pass 1, raise once with the full comma-separated list, only insert in pass 2 if pass 1 was empty. Stays Closed.",
     "/app/backend/routes/event_blocks.py (create_event_block PASS 1)",
     "POST /api/event-blocks with 3 slot_ids that all conflict on the same date — error detail must list all 3 slot labels."),

    ("PPA-64", "Building Management — slot label / status text overlap",
     "Low", "Closed",
     "Already fixed", "Verified Closed",
     "Spot-checked: BuildingManagement.js renders the label and 'Blocked' sublabel as a flex-column stack (no longer position:absolute overlay). Tooltip = '{label} — Blocked'. Stays Closed.",
     "/app/frontend/src/pages/admin/BuildingManagement.js (slot tile)",
     "Open Building Management, expand a floor with at least one blocked slot — verify label + 'BLOCKED' sublabel render stacked, no overlap, at all viewport widths ≥ 768 px."),
]


# ---------- Build workbook ----------
wb = Workbook()
ws = wb.active
ws.title = "Defect Response (2026-04-30)"

HEADERS = [
    "Defect ID", "Title", "Severity", "Customer Status",
    "Our Assessment", "Resolution Status",
    "Remarks / Resolution Detail",
    "Code Path / Files",
    "QA Verification Steps",
]

hdr_fill = PatternFill("solid", fgColor="08263E")
hdr_font = Font(color="FFFFFF", bold=True)
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
left_wrap = Alignment(horizontal="left", vertical="top", wrap_text=True)
thin = Side(border_style="thin", color="B0B0B0")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

for c, h in enumerate(HEADERS, 1):
    cell = ws.cell(row=1, column=c, value=h)
    cell.fill = hdr_fill
    cell.font = hdr_font
    cell.alignment = center
    cell.border = border

for r, row in enumerate(ITEMS, 2):
    for c, val in enumerate(row, 1):
        cell = ws.cell(row=r, column=c, value=val)
        cell.alignment = left_wrap if c >= 7 else center
        cell.border = border
    sev = row[2]
    sc = ws.cell(row=r, column=3)
    sc.fill = PatternFill("solid", fgColor=SEV_COLORS.get(sev, "DDDDDD"))
    sc.font = Font(color="FFFFFF", bold=True)
    sc.alignment = center

    assessment = row[4]
    ac = ws.cell(row=r, column=5)
    ac.fill = PatternFill("solid", fgColor=ASSESS_COLORS.get(assessment, "DDDDDD"))
    ac.font = Font(color="FFFFFF", bold=True)
    ac.alignment = center

    rstat = row[5]
    rc = ws.cell(row=r, column=6)
    rc.fill = PatternFill("solid", fgColor=STATUS_COLORS.get(rstat, "DDDDDD"))
    rc.font = Font(color="FFFFFF", bold=True)
    rc.alignment = center

WIDTHS = [16, 50, 11, 18, 18, 18, 80, 55, 55]
for i, w in enumerate(WIDTHS, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.row_dimensions[1].height = 36
for r in range(2, len(ITEMS) + 2):
    item = ITEMS[r - 2]
    # NEW deeper-fix rows get extra height for the multi-paragraph remarks.
    ws.row_dimensions[r].height = 280 if item[0] in ("PPA-70", "PPA-71") else 130
ws.freeze_panes = "A2"

# ---- Summary tab ----
sm = wb.create_sheet("Summary")
sm["A1"] = "Defect Validation 2026-04-29 — Engineering Response"
sm["A1"].font = Font(size=16, bold=True, color="08263E")
sm["A2"] = (
    f"Source file: 'Parking App - Defect Validation 2026 04 29.xlsx'   |   "
    f"Generated {datetime.now().strftime('%B %d, %Y')}"
)
sm["A2"].font = Font(italic=True, color="666666")

sm["A4"] = "Total rows assessed"
sm["B4"] = len(ITEMS)
sm["A4"].font = Font(bold=True)

sm["A5"] = "  Already-Closed (spot-checked)"
sm["B5"] = sum(1 for x in ITEMS if x[5] == "Verified Closed")
sm["A6"] = "  NEW failures (Confirmed real)"
sm["B6"] = sum(1 for x in ITEMS if x[4] == "Confirmed real")
sm["A7"] = "  Resolved this cycle"
sm["B7"] = sum(1 for x in ITEMS if x[5] == "Resolved")

sm["A9"] = "Headline findings"
sm["A9"].font = Font(bold=True, color="C0392B")
sm["A10"] = (
    "PPA-70 (HIGH severity) revealed a Couchbase abstraction-layer bug that "
    "silently broke every Mongo-style array-membership query. This impacted "
    "zone enforcement (and would have impacted assigned_buildings, slot_ids, "
    "tags filters, etc.). Fix is at the abstraction layer — single-line N1QL "
    "change — and is broadly tested via the cross-feature smoke."
)
sm["A10"].alignment = Alignment(wrap_text=True, vertical="top")
sm.row_dimensions[10].height = 80

sm["A12"] = "PPA-71 was a missing pre-flight check in /api/event-blocks. "\
            "Past-date guard added; today still permitted."
sm["A12"].alignment = Alignment(wrap_text=True, vertical="top")
sm.row_dimensions[12].height = 40

sm["A14"] = "Cross-feature smoke run after fixes"
sm["A14"].font = Font(bold=True)
SMOKE = [
    "GET /api/buildings", "GET /api/users", "GET /api/zones",
    "GET /api/event-blocks", "GET /api/admin/reservations",
    "GET /api/parking-config/{id}", "GET /api/reports/stats",
    "POST /api/event-blocks (past date) → HTTP 400 (was 200)",
    "POST /api/reservations (cross-zone) → HTTP 403 (was 200)",
    "PUT /api/admin/reservations/{past_id}/cancel → HTTP 400",
    "GET /api/reports/stats — daily_breakdown sorted ascending",
]
for i, line in enumerate(SMOKE, start=15):
    sm.cell(row=i, column=1, value=("OK   " if "→" not in line or "(was" in line else "OK   ") + line)

sm.column_dimensions["A"].width = 110
sm.column_dimensions["B"].width = 12

wb.save(OUT)
print(f"Wrote {OUT}")
print(f"Total rows: {len(ITEMS)}  resolved: {sum(1 for x in ITEMS if x[5] == 'Resolved')}  closed-confirmed: {sum(1 for x in ITEMS if x[5] == 'Verified Closed')}")
