"""
Generates /app/docs/output/Defect_Validation_Response_2026-04-30_v2.xlsx —
response to "Parking App - Defect Validation 2026 04 30.xlsx".

7 rows: 5 already-Closed items spot-checked, 1 NEW item (PPA-72) was
already fixed by yesterday's PPA-70 abstraction-layer change.
"""
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = Path("/app/docs/output/Defect_Validation_Response_2026-04-30_v2.xlsx")
OUT.parent.mkdir(parents=True, exist_ok=True)

STATUS_COLORS = {
    "Resolved":          "27AE60",
    "Already Resolved":  "16A085",
    "Verified Closed":   "1ABC9C",
}
SEV_COLORS = {"High": "C0392B", "Medium": "E67E22", "Low": "F1C40F", "—": "BDC3C7"}
ASSESS_COLORS = {
    "Confirmed real (now fixed)": "C0392B",
    "Same root cause as PPA-70 (already fixed)": "C0392B",
    "Already fixed": "27AE60",
}

ITEMS = [
    ("PPA-1", "Login - Invalid credentials shows blank page",
     "High", "Closed",
     "Already fixed", "Verified Closed",
     "Live retest: POST /api/auth/login with wrong creds → HTTP 401 + JSON detail; LoginPage shows toast, no blank page. Stays Closed.",
     "/app/frontend/src/pages/LoginPage.js (handleLogin)",
     "POST a wrong-password login → expect 401 + on-page toast."),

    ("PPA-72", "Booking shows ONLY Main Building (not other buildings in user's zone)",
     "High", "New (Failed)",
     "Confirmed real (now fixed)",
     "Resolved",
     "REPRODUCED on production: a user with `main_building` set AND assigned to a multi-building zone only saw their main_building in the booking dropdown.\n"
     "FIRST RCA WAS WRONG. I initially attributed this to the same abstraction-layer bug as PPA-70 (array-membership). That fix was necessary BUT NOT sufficient — verifying with a test user whose `main_building=None` masked the real defect.\n"
     "TRUE ROOT CAUSE: `/api/buildings` endpoint (routes/buildings.py, regular-user branch) restricted the query to `main_building + assigned_buildings` ONLY — zone buildings were never added to the set. So even when the abstraction returned correct zone data, the backend's first SQL filter had already trimmed the result to {main_building} before the frontend ever saw it. The frontend then intersected zone_ids with that single-building set → only main_building shown.\n"
     "FIX: routes/buildings.py now reads the user's zones and unions their building_ids into the user_buildings set before filtering. Admin / attendant branches unchanged.\n"
     "VERIFIED LIVE on Couchbase + the customer's exact scenario (user with main_building set + Main Zone with 3 buildings): dropdown now shows 'Test Building 175514', 'Main Office', 'CL Tower Makati (Main)'. Admin still sees all 19 buildings; users with no main + no zones still see all (unchanged fallback).",
     "/app/backend/routes/buildings.py (get_buildings — regular-user branch)",
     "1) Set a non-admin user's main_building to building X; "
     "2) Add that user to a zone containing buildings X, Y, Z; "
     "3) Login as that user → /api/buildings should return [X, Y, Z]; "
     "4) Open BookingPage → dropdown should list all three. "
     "Edge: a user with NO main, NO assigned, NO zones still sees ALL buildings (graceful fallback)."),

    ("PPA-15", "Reservations by Buildings — graph name alignment",
     "Low", "Closed",
     "Already fixed", "Verified Closed",
     "AdminDashboard BarChart YAxis is width=180 with interval=0 + ellipsis tickFormatter; Tooltip shows the full name. Stays Closed.",
     "/app/frontend/src/pages/admin/AdminDashboard.js (BarChart YAxis)",
     "Reload Admin Dashboard with ≥ 4 buildings of varying name lengths — labels should not overlap or clip."),

    ("PPA-57", "Recent Reservations shows stale data",
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
     "BuildingManagement.js renders the label and 'Blocked' sublabel as a flex-column stack (no longer position:absolute overlay). Tooltip = '{label} — Blocked'. Stays Closed.",
     "/app/frontend/src/pages/admin/BuildingManagement.js (slot tile)",
     "Open Building Management, expand a floor with at least one blocked slot — verify label + 'BLOCKED' sublabel render stacked, no overlap, at all viewport widths ≥ 768 px."),
]


# ---------- Workbook ----------
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
    cell.fill = hdr_fill; cell.font = hdr_font
    cell.alignment = center; cell.border = border

for r, row in enumerate(ITEMS, 2):
    for c, val in enumerate(row, 1):
        cell = ws.cell(row=r, column=c, value=val)
        cell.alignment = left_wrap if c >= 7 else center
        cell.border = border
    for col_idx, key, palette in [(3, row[2], SEV_COLORS), (5, row[4], ASSESS_COLORS), (6, row[5], STATUS_COLORS)]:
        c = ws.cell(row=r, column=col_idx)
        c.fill = PatternFill("solid", fgColor=palette.get(key, "DDDDDD"))
        c.font = Font(color="FFFFFF", bold=True)
        c.alignment = center

WIDTHS = [16, 50, 11, 18, 32, 18, 80, 55, 55]
for i, w in enumerate(WIDTHS, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.row_dimensions[1].height = 36
for r in range(2, len(ITEMS) + 2):
    item = ITEMS[r - 2]
    ws.row_dimensions[r].height = 320 if item[0] == "PPA-72" else 130
ws.freeze_panes = "A2"

# ---- Summary tab ----
sm = wb.create_sheet("Summary")
sm["A1"] = "Defect Validation 2026-04-30 — Engineering Response"
sm["A1"].font = Font(size=16, bold=True, color="08263E")
sm["A2"] = (
    f"Source: 'Parking App - Defect Validation 2026 04 30.xlsx'   |   "
    f"Generated {datetime.now().strftime('%B %d, %Y')}"
)
sm["A2"].font = Font(italic=True, color="666666")

sm["A4"] = "Total rows assessed";          sm["B4"] = len(ITEMS); sm["A4"].font = Font(bold=True)
sm["A5"] = "  Already-Closed (spot-checked)"; sm["B5"] = sum(1 for x in ITEMS if x[5] == "Verified Closed")
sm["A6"] = "  NEW failures (Confirmed real)"; sm["B6"] = sum(1 for x in ITEMS if "Confirmed" in x[4] or "Same root" in x[4])
sm["A7"] = "  Resolved this cycle";        sm["B7"] = sum(1 for x in ITEMS if x[5] == "Resolved")

sm["A9"] = "Headline finding"
sm["A9"].font = Font(bold=True, color="C0392B")
sm["A10"] = (
    "PPA-72 was a SECOND, distinct backend bug that I initially mis-attributed "
    "to yesterday's abstraction-layer fix. /api/buildings (regular-user branch) "
    "was filtering its DB query to `main_building + assigned_buildings` only, "
    "completely ignoring the user's zone buildings. The abstraction fix from "
    "PPA-70 was necessary but not sufficient — the backend was already trimming "
    "the result before the frontend could intersect with zone_ids.\n"
    "The fix is now in routes/buildings.py: zone buildings are unioned into "
    "the query filter. Verified end-to-end on Couchbase: a user with "
    "main_building set + a 3-building zone now sees all 3 in the dropdown."
)
sm["A10"].alignment = Alignment(wrap_text=True, vertical="top")
sm.row_dimensions[10].height = 130

sm["A12"] = ("Two missed-symptoms in two days both relate to multi-tenant filtering. "
             "The pytest suite I keep proposing — running 12-15 critical query "
             "shapes against both DB_TYPE backends — would have caught BOTH PPA-70 "
             "and PPA-72 before customer testing.")
sm["A12"].font = Font(italic=True, color="888888")
sm["A12"].alignment = Alignment(wrap_text=True, vertical="top")
sm.row_dimensions[12].height = 80

sm["A14"] = "Live cross-feature smoke (after fix)"
sm["A14"].font = Font(bold=True)
SMOKE = [
    "GET /api/buildings → 200",
    "GET /api/users → 200",
    "GET /api/zones → 200",
    "GET /api/event-blocks → 200",
    "GET /api/admin/reservations → 200",
    "GET /api/reports/stats → 200",
    "GET /api/zones/user-buildings (non-admin) → 3 building_ids returned",
    "POST /api/reservations cross-zone (PPA-70 retest) → 403",
    "POST /api/event-blocks past-date (PPA-71 retest) → 400",
    "BookingPage dropdown (PPA-72): 3 buildings shown, not just main_building",
]
for i, line in enumerate(SMOKE, start=15):
    sm.cell(row=i, column=1, value="OK   " + line)

sm.column_dimensions["A"].width = 110
sm.column_dimensions["B"].width = 12

wb.save(OUT)
print(f"Wrote {OUT}")
print(f"Total rows: {len(ITEMS)}  resolved: {sum(1 for x in ITEMS if x[5] == 'Resolved')}  closed-confirmed: {sum(1 for x in ITEMS if x[5] == 'Verified Closed')}")
