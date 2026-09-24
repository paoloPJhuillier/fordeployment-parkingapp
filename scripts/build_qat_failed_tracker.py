"""
Generates /app/docs/output/QAT_Failed_Items_Tracker_2026-03-23.xlsx from the
4th-Pass QAT report findings.

Each row carries:
  ID | Module | Title | Severity | Defect | Status | Expected | Actual |
  Suspected Root Cause | Recommended Solution | Likely Already Fixed? | Owner | Effort | Files
"""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = Path("/app/docs/output/QAT_Failed_Items_Tracker_2026-03-23.xlsx")
OUT.parent.mkdir(parents=True, exist_ok=True)

STATUS_COLORS = {
    "Failed":  "C0392B",
    "Blocked": "8E44AD",
}
PRIORITY_COLORS = {
    "P0": "C0392B",
    "P1": "E67E22",
    "P2": "F1C40F",
    "P3": "95A5A6",
}
FIXED_COLORS = {
    "Yes (verify deploy)":  "27AE60",
    "Likely Yes":           "16A085",
    "Partial":              "E67E22",
    "No":                   "C0392B",
    "QA-data error":        "7F8C8D",
}

# Each tuple = (ID, Module, Title, Defect, Status, Priority, Expected, Actual,
#               RootCause, Solution, AlreadyFixed, Owner, Effort, Files)
ITEMS = [
    # ============ User Management ============
    (
        "TC-USER-MANAGEMENT-030", "User Management",
        "Add User and Edit User modals appear swapped",
        "PPA-56", "Failed", "P2",
        "Clicking 'Add User' opens the Add modal; clicking an existing user opens the Edit modal.",
        "Clicking 'Add User' opens the Edit modal page instead.",
        "UI router/state confusion: shared modal component reuses the same `selectedUser` ref between Add and Edit, so previously-edited user state leaks into the Add flow.",
        "In AdminUsers.js: ensure Add-flow explicitly resets `selectedUser` to null AND `formMode` to 'create' before opening the modal. Add a regression Cypress/Playwright test that opens Add right after Edit and asserts the modal title reads 'Add New User' and inputs are empty.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/frontend/src/pages/admin/AdminUsers.js",
    ),
    (
        "TC-USER-MANAGEMENT-031", "User Management",
        "Tooltip overlaps with the page title",
        "PPA-58", "Failed", "P3",
        "Tooltip displays the description on hover, properly positioned.",
        "Tooltip overlaps the page title at the top of the screen.",
        "Tooltip's `side='top'` placement collides with the sticky header. Radix Tooltip needs collision detection or explicit `align`/`avoidCollisions` props.",
        "In the Users list info-icon Tooltip, set `side='right'` (or `bottom`) and add `collisionPadding={16}`. If the icon sits in a CardHeader, anchor to the icon container, not the row, so it can flip to 'bottom' when near the page top.",
        "No",
        "Frontend dev", "0.25 day",
        "/app/frontend/src/pages/admin/AdminUsers.js (info Tooltip)",
    ),

    # ============ Login ============
    (
        "TCID-LOGIN-003", "Login",
        "Wrong password — Actual Result column blank in QAT (data entry gap)",
        "", "Failed", "P3",
        "'Invalid credentials' popup; admin not signed in.",
        "(blank — tester didn't fill in the actual result)",
        "Behavior is correct in code: backend returns 401 with 'Invalid credentials' on wrong password and the LoginPage.js shows a sonner toast. The QAT row is most likely a data-entry omission, not a real defect.",
        "Re-execute the test and capture the actual result. If toast still doesn't appear, check that `toast.error(error.response?.data?.detail || 'Login failed')` runs (LoginPage.js line ~53). Also verify rate-limit middleware isn't swallowing the body.",
        "QA-data error",
        "QA / Frontend dev", "0.25 day to re-run",
        "/app/backend/routes/auth.py (login endpoint), /app/frontend/src/pages/LoginPage.js",
    ),
    (
        "TCID-LOGIN-005", "Login",
        "Invalid email format — blank page displayed",
        "PPA-1", "Failed", "P1",
        "Validation message OR 'Invalid credentials' popup. Admin should NOT see a blank screen.",
        "Blank page is displayed after clicking Sign In with an invalid email.",
        "The backend returns 422 (Pydantic EmailStr validation) and the frontend AuthContext / axios interceptor likely throws an unhandled error that unmounts the form.",
        "DONE — added client-side email regex pre-check + noValidate on the <form> so our sonner toast 'Please enter a valid email address' fires instead of the HTML5 popup. handleLogin's catch always toasts and stays on the page (no navigation on error).",
        "No",
        "Frontend dev", "DONE",
        "/app/frontend/src/pages/LoginPage.js (handleLogin + noValidate)",
    ),
    (
        "TCID-LOGIN-006", "Login",
        "Password with leading/trailing spaces — error message wording wrong",
        "", "Failed", "P3",
        "Password should be rejected because spaces are not allowed (specific message).",
        "Generic 'Please fill in this field' error shows even though the field has content.",
        "HTML5 `required` triggers 'Please fill in this field' when Chrome auto-trims the value to empty in some locales. Backend doesn't currently validate trimmed-vs-raw passwords.",
        "(1) Frontend: trim password client-side BEFORE submit; if result is empty, show 'Password cannot be only spaces'. Otherwise send the raw value. "
        "(2) Backend: in LoginRequest pydantic model, add validator that rejects passwords starting/ending with whitespace and returns a meaningful message. "
        "(3) Update test expected result to match the new message.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/backend/routes/auth.py (LoginRequest), /app/frontend/src/pages/LoginPage.js",
    ),
    (
        "TCID-LOGIN-018", "Login",
        "Old password accepted during change-password workflow",
        "", "Failed", "P0",
        "User cannot reuse the OLD password when changing.",
        "System allowed user to set new_password = old_password.",
        "Backend change-password handler doesn't compare new_password against the current hash before saving.",
        "In auth.py change_password: BEFORE hashing/updating, do `if verify_password(req.new_password, current_hash): raise 400 'New password must differ from current password'`. Add pytest case in test_password_features.py.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE (already fixed in prior phase)",
        "/app/backend/routes/auth.py (change_password)",
    ),

    # ============ Dashboard ============
    (
        "TCID-DASHBOARD-002", "Dashboard",
        "Sidebar 'Parking Config' link goes to wrong URL",
        "", "Failed", "P2",
        "Each sidebar entry navigates to its corresponding URL.",
        "Parking Config link points to an incorrect URL.",
        "AdminLayout.js sidebar entry probably reads `/admin/config` while the route in App.js is registered as `/admin/parking-config` (or vice versa).",
        "Open AdminLayout.js sidebar `nav` array, locate Parking Config entry. Compare its `to=` against App.js route. Pick one canonical path (recommend `/admin/parking-config`) and update both. Add a smoke Playwright that walks every sidebar item and asserts the URL matches a registered route.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE (already correct in code)",
        "/app/frontend/src/pages/admin/AdminLayout.js, /app/frontend/src/App.js",
    ),
    (
        "TCID-DASHBOARD-008", "Dashboard",
        "Building names misaligned in 'Reservations by Buildings' graph",
        "", "Failed", "P3",
        "Building names render correctly under each bar.",
        "Names overlap or are clipped on the X axis.",
        "Recharts BarChart with long building names wraps awkwardly; default `tick` is single-line and gets clipped at chart bottom.",
        "On the AdminDashboard BarChart XAxis, set `interval={0}` plus a custom `tick` component that rotates labels (`angle={-30}`) or use a tooltip-only axis with shortened labels (3-letter codes) and full names in the tooltip. Bumping the chart's bottom margin to ~60px also helps.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/frontend/src/pages/admin/AdminDashboard.js (BarChart XAxis)",
    ),

    # ============ Vehicle Management ============
    (
        "TCID-VEHICLE-MANAGEMENT-004", "Vehicle Management",
        "Empty plate-number accepted (Actual = Expected; QAT data error suspected)",
        "", "Failed", "P2",
        "Empty plate field is rejected with 'Please fill in this field'.",
        "(QAT shows the SAME success message as expected — likely a data-entry copy-paste error)",
        "Either tester pasted Expected into Actual, OR validation is missing. The form already uses `<Input required>` HTML5 validation.",
        "Re-run the test with browser dev tools open. If it does pass through, add server-side validation in vehicles.py POST: reject empty `plate_number.strip()`. Also enforce regex `^[A-Z0-9-]{4,12}$` to prevent garbage data.",
        "QA-data error",
        "QA + Backend dev", "0.5 day",
        "/app/backend/routes/vehicles.py (create), /app/frontend/src/pages/VehiclesPage.js",
    ),
    (
        "TCID-VEHICLE-MANAGEMENT-006", "Vehicle Management",
        "Special characters accepted in plate number (Actual = Expected; QAT data error suspected)",
        "", "Failed", "P2",
        "Field validation rejects non-alphanumeric input.",
        "(QAT row shows the same wording in both columns)",
        "If genuinely failing: backend doesn't enforce plate-format regex; only client `required` is in place.",
        "Add Pydantic validator on VehicleCreate: `plate_number` must match `^[A-Z0-9-]{4,12}$`. Add corresponding pytest. Add toast on frontend if regex fails.",
        "QA-data error",
        "Backend dev", "0.25 day",
        "/app/backend/models/vehicle.py, /app/backend/routes/vehicles.py",
    ),

    # ============ Building Management ============
    (
        "TCID-BUILDING-MANAGEMENT-010", "Building Management",
        "Cannot delete building when its details exceed character limit",
        "PPA-65", "Failed", "P1",
        "Building deletes successfully.",
        "Delete fails because the building's existing details exceed the new char limit imposed in Phase 6.",
        "Phase 6 added max-length validators to BuildingUpdate (and possibly BuildingDelete). Existing legacy rows with values > limit fail Pydantic validation on the response model when the API tries to return the deleted record.",
        "Two-part fix: "
        "(1) DELETE handler should NOT validate the deleted body against the strict create/update schema. Either return `{ deleted: true, id }` (no full response model), OR explicitly use a relaxed response shape on DELETE. "
        "(2) Add a `legacy=True` mode on the Building model so over-length legacy values pass Pydantic on read paths.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/backend/routes/buildings.py (delete_building), /app/backend/models/building.py",
    ),
    (
        "TCID-BUILDING-MANAGEMENT-027", "Building Management",
        "Slot color does NOT change to gray when reservation is created",
        "PPA-22", "Blocked", "P1",
        "On creating a reservation, the slot in Building Management changes from green to gray (Available -> Reserved).",
        "Slot stays green; status doesn't refresh.",
        "Building Management page renders parking_slots.status from a one-time GET on mount. Reservation creation doesn't push an update via WebSocket/SSE, and there's no polling.",
        "Pick one: "
        "(a) Cheap: add a 30-second polling refresh on the Building Management slots view, OR refetch when the page regains focus (window 'focus' listener). "
        "(b) Robust: emit an event from POST /api/reservations and have the frontend subscribe via Server-Sent Events. "
        "Recommended: (a) for now, schedule (b) as a follow-up.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/frontend/src/pages/admin/AdminBuildings.js, /app/backend/routes/reservations.py",
    ),
    (
        "TCID-BUILDING-MANAGEMENT-028", "Building Management",
        "Cannot exceed character limit when adding a building (Actual = Expected; QAT data error)",
        "", "Failed", "P3",
        "Char limit blocks input.",
        "(QAT row identical)",
        "Phase 6 added explicit maxLength to all building inputs. Most likely a tester data-entry artefact.",
        "Re-execute. If genuinely failing, double-check the address line 1/2 inputs have `maxLength` props.",
        "QA-data error",
        "QA / Frontend dev", "0.25 day",
        "/app/frontend/src/pages/admin/AdminBuildings.js",
    ),

    # ============ Parking Config ============
    (
        "TCID-PARKING-CONFIG-007", "Parking Config",
        "Slots not auto-released at the configured release time",
        "", "Failed", "P0",
        "At release_time, slots blocked by previous-day reservations flip from Blocked → Available.",
        "Slot status doesn't change at the configured time.",
        "auto_mark_no_shows() background task in server.py runs every N minutes and only marks no-shows; there's no separate task that resets the slot.status back to 'Available' at config.release_time.",
        "Add a new background coroutine `auto_release_slots()` that wakes every minute, reads each building's parking_config.release_time, and for any reservation whose date<today AND status in ['confirmed','no_show'], sets the parking_slots.status='Available'. Wire it into the @app.on_event('startup') alongside the no-show task. Add a pytest with a frozen clock.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/backend/server.py (startup tasks), new /app/backend/services/auto_release.py",
    ),
    (
        "TCID-PARKING-CONFIG-010", "Parking Config",
        "Booking-window invalid value: only HTML5 'fill in this field' shown",
        "", "Failed", "P3",
        "Value validation should explain what's wrong (must be > 0 and ≤ 30 days).",
        "Browser default 'Please fill in this field' shows even when user typed a value.",
        "Empty value triggers HTML5 'required'; a typed-but-invalid value (e.g., 0 or 999) is silently coerced to default by parking_config.py.",
        "(1) Frontend: Add explicit min/max constraints to the input AND show inline error 'Booking window must be 1–30 days'. "
        "(2) Backend: ParkingConfigCreate Pydantic validator: `1 <= booking_window_days <= 30`.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/backend/models/parking_config.py, /app/frontend/src/pages/admin/AdminSettings.js",
    ),
    (
        "TCID-PARKING-CONFIG-016", "Parking Config",
        "Booking during default hours — Actual = Expected (QAT data error)",
        "", "Failed", "P3",
        "User can book within the default parking-hour window.",
        "(QAT row identical)",
        "Likely tester data-entry artefact, since the entire reservation flow is otherwise tested as PASS.",
        "Re-run the test case and capture the real actual result. If genuinely failing, log a new defect with reproduction steps.",
        "QA-data error",
        "QA / Backend dev", "0.25 day",
        "/app/backend/routes/reservations.py, /app/backend/services/reservations.py",
    ),
    (
        "TCID-PARKING-CONFIG-019", "Parking Config",
        "Exit Parking Config without saving — Actual = Expected (QAT data error)",
        "", "Failed", "P3",
        "No changes were saved.",
        "(QAT row identical)",
        "Behavior is correct (no save = no persistence). Likely tester data-entry artefact.",
        "Re-run; if genuinely failing, ensure the AdminSettings unmount path doesn't fire any `apiSave()` call when the user closes the modal.",
        "QA-data error",
        "QA / Frontend dev", "0.25 day",
        "/app/frontend/src/pages/admin/AdminSettings.js",
    ),

    # ============ Event Blocking ============
    (
        "TCID-EVENT-BLOCKING-005", "Event Blocking",
        "Cancel button doesn't save — Actual = Expected (QAT data error)",
        "", "Failed", "P3",
        "Cancel discards changes.",
        "(QAT row identical)",
        "Most likely tester data-entry artefact.",
        "Re-run. If failing, confirm the modal Close/Cancel handler resets local state and does NOT call POST /api/event-blocks.",
        "QA-data error",
        "QA / Frontend dev", "0.25 day",
        "/app/frontend/src/pages/admin/AdminEventBlocks.js",
    ),
    (
        "TCID-EVENT-BLOCKING-009", "Event Blocking",
        "Delete event-block — Blocked",
        "", "Blocked", "P1",
        "Event block deleted with confirmation toast.",
        "Test execution blocked (likely waiting on dependent test or env issue).",
        "Status 'Blocked' usually means the tester couldn't run the case (auth issue, missing data, dependency failed).",
        "Confirm DELETE /api/event-blocks/{id} works via curl as admin. If not, add the missing endpoint or fix the missing permission. Provide the QA team a seeded event-block to delete.",
        "Likely Yes",
        "Backend dev / QA", "0.25 day",
        "/app/backend/routes/event_blocks.py",
    ),
    (
        "TCID-EVENT-BLOCKING-011", "Event Blocking",
        "Duplicate single-slot block — Actual = Expected (QAT data error)",
        "", "Failed", "P3",
        "Conflict popup; new block not created.",
        "(QAT row identical)",
        "Likely tester data-entry artefact; conflict detection is implemented in event_blocks.py POST.",
        "Re-run. If genuinely failing, verify the overlap query in event_blocks.py POST handler.",
        "QA-data error",
        "QA / Backend dev", "0.25 day",
        "/app/backend/routes/event_blocks.py",
    ),
    (
        "TCID-EVENT-BLOCKING-012", "Event Blocking",
        "Multi-slot duplicate block — popup only shows first conflicting slot",
        "", "Failed", "P2",
        "Popup lists ALL conflicting slot names.",
        "Popup only shows 1 slot name even when multiple slots overlap.",
        "POST /api/event-blocks raises HTTPException with the FIRST conflicting slot only; loop short-circuits on first hit.",
        "In event_blocks.py POST: collect ALL conflicting (slot_label, date) pairs into a list before raising. Detail message becomes 'Slots A, B, C already have reservations that overlap on 2026-04-30'. Add pytest covering 3-slot overlap.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/backend/routes/event_blocks.py (create_event_block)",
    ),
    (
        "TCID-EVENT-BLOCKING-013", "Event Blocking",
        "Close (X) button shows wrong error",
        "PPA-57", "Failed", "P2",
        "Modal closes when X is clicked.",
        "Browser shows 'Please fill in this field' instead of closing.",
        "X button is inside the <form> so clicking it triggers HTML5 form validation before the click handler runs (default button type is `submit`).",
        "Add `type='button'` to the X close button (and any other in-form buttons that should not submit). Audit ALL admin modals for this pattern.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/frontend/src/pages/admin/AdminEventBlocks.js (Block Slots modal close button)",
    ),

    # ============ Reports & Analytics ============
    (
        "TCID-ANALYTICS-004", "Reports & Analytics",
        "Date picker only allows changing END date",
        "", "Failed", "P2",
        "User can change BOTH start and end date.",
        "Only end date is interactive; start date only updates when chosen date is BEFORE the default start.",
        "Single-handle date picker is being treated as a 'go back further' control instead of a true range picker.",
        "Replace with a proper date-range picker (shadcn `Calendar` with `mode='range'`) and bind both `from` and `to` to state. Or add two separate pickers (Start and End) with cross-validation (start ≤ end).",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/frontend/src/pages/admin/AdminAnalytics.js (date filter)",
    ),
    (
        "TCID-ANALYTICS-016", "Reports & Analytics",
        "Recent Reservations table shows stale data",
        "PPA-57", "Failed", "P2",
        "Shows the latest 10 confirmations / no-shows / cancellations across all buildings.",
        "Shows old data even after fresh reservations are created.",
        "Frontend caches the report response in a useState that isn't invalidated, OR backend query sorts by created_at ASC instead of DESC.",
        "(1) Backend: in /api/reports/stats handler, ensure recent_reservations query is sorted DESC by created_at and limited to 10. "
        "(2) Frontend: refetch when AdminAnalytics gains focus, or include a manual Refresh button. "
        "(3) Confirm caching headers on the API response are not forcing browser cache.",
        "Yes (verify deploy)", "Frontend/Backend dev", "DONE",
        "/app/backend/routes/reports.py (or services/reports.py), /app/frontend/src/pages/admin/AdminAnalytics.js",
    ),
]


# ---------- build the workbook ---------------------------------------------
wb = Workbook()
ws = wb.active
ws.title = "Failed Items"

HEADERS = [
    "ID", "Module", "Title", "Defect", "Status", "Priority",
    "Expected Result", "Actual Result",
    "Suspected Root Cause", "Recommended Solution",
    "Already Fixed?", "Owner", "Effort", "Files / Location",
]

hdr_fill = PatternFill("solid", fgColor="08263E")
hdr_font = Font(color="FFFFFF", bold=True)
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
left_wrap = Alignment(horizontal="left", vertical="top", wrap_text=True)
thin = Side(border_style="thin", color="B0B0B0")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

for c, h in enumerate(HEADERS, start=1):
    cell = ws.cell(row=1, column=c, value=h)
    cell.fill = hdr_fill
    cell.font = hdr_font
    cell.alignment = center
    cell.border = border

for r, row in enumerate(ITEMS, start=2):
    for c, val in enumerate(row, start=1):
        cell = ws.cell(row=r, column=c, value=val)
        cell.alignment = left_wrap if c >= 7 else center
        cell.border = border
    # Status color
    st = row[4]
    sc = ws.cell(row=r, column=5)
    sc.fill = PatternFill("solid", fgColor=STATUS_COLORS.get(st, "DDDDDD"))
    sc.font = Font(color="FFFFFF", bold=True)
    sc.alignment = center
    # Priority color
    pr = row[5]
    pc = ws.cell(row=r, column=6)
    pc.fill = PatternFill("solid", fgColor=PRIORITY_COLORS.get(pr, "DDDDDD"))
    pc.font = Font(color="FFFFFF", bold=True)
    pc.alignment = center
    # Already-Fixed color
    af = row[10]
    afc = ws.cell(row=r, column=11)
    afc.fill = PatternFill("solid", fgColor=FIXED_COLORS.get(af, "DDDDDD"))
    afc.font = Font(color="FFFFFF", bold=True)
    afc.alignment = center

WIDTHS = [27, 18, 50, 8, 9, 9, 45, 45, 50, 70, 18, 18, 12, 45]
for i, w in enumerate(WIDTHS, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.row_dimensions[1].height = 35
for r in range(2, len(ITEMS) + 2):
    ws.row_dimensions[r].height = 130
ws.freeze_panes = "A2"

# ---- Summary tab ----
sm = wb.create_sheet("Summary")
sm["A1"] = "QAT 4th Pass — Failed / Blocked Items"
sm["A1"].font = Font(size=16, bold=True, color="08263E")
sm["A2"] = "Source: 2026-03-23 QAT 4th Pass test report"
sm["A2"].font = Font(italic=True, color="666666")

sm["A4"] = "Total failing/blocked rows extracted"
sm["B4"] = len(ITEMS)
sm["A4"].font = Font(bold=True)

sm["A5"] = "By status"
sm["A5"].font = Font(bold=True)
i = 6
for st in ("Failed", "Blocked"):
    cell = sm.cell(row=i, column=1, value=st)
    cell.fill = PatternFill("solid", fgColor=STATUS_COLORS[st])
    cell.font = Font(color="FFFFFF", bold=True)
    sm.cell(row=i, column=2, value=sum(1 for x in ITEMS if x[4] == st))
    i += 1

i += 1
sm.cell(row=i, column=1, value="By priority").font = Font(bold=True); i += 1
for pr in ("P0", "P1", "P2", "P3"):
    cell = sm.cell(row=i, column=1, value=pr)
    cell.fill = PatternFill("solid", fgColor=PRIORITY_COLORS[pr])
    cell.font = Font(color="FFFFFF", bold=True)
    sm.cell(row=i, column=2, value=sum(1 for x in ITEMS if x[5] == pr))
    i += 1

i += 1
sm.cell(row=i, column=1, value="By 'Already Fixed?' assessment").font = Font(bold=True); i += 1
for af in ("Yes (verify deploy)", "Likely Yes", "Partial", "No", "QA-data error"):
    cell = sm.cell(row=i, column=1, value=af)
    cell.fill = PatternFill("solid", fgColor=FIXED_COLORS[af])
    cell.font = Font(color="FFFFFF", bold=True)
    sm.cell(row=i, column=2, value=sum(1 for x in ITEMS if x[10] == af))
    i += 1

i += 1
sm.cell(row=i, column=1, value="Items requiring genuine new code (not QA artefacts)").font = Font(bold=True, color="C0392B"); i += 1
real = [x for x in ITEMS if x[10] in ("No", "Partial")]
for x in real:
    sm.cell(row=i, column=1, value=f"{x[0]} — {x[2]}").font = Font(bold=True)
    sm.cell(row=i, column=2, value=f"{x[5]} / {x[1]} / {x[12]}")
    i += 1

sm.column_dimensions["A"].width = 75
sm.column_dimensions["B"].width = 35

wb.save(OUT)
print(f"Wrote {OUT}")
print(f"Total rows: {len(ITEMS)}")
print(f"Genuine code work needed: {len(real)} items")
