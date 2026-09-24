"""
VAPT retest - iteration 38
Focused retest after adding find_one_and_update + find_one_and_delete to the
Couchbase adapter (gap caught in iteration_37).

Covers:
- V-08 PUT sanitization (was 500 on Couchbase before fix)
- Reservation confirm flows: PUT /api/reservations/{id}/confirm and
  POST /api/reservations/{id}/confirm-with-photo (both use find_one_and_update)
- Full regression: logins, list users, list buildings, db-info,
  collection-stats, build-info, sync-mongo-to-couchbase
- Re-runs V-02/V-03/V-10/V-11 from iteration_37 are imported by re-using the
  iter37 file (run them together via pytest tests/).
"""
import os
import uuid
import pytest
import requests


def _load_frontend_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env() or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN = {"email": "admin.test@cebuana.com", "password": "Test123!"}
USER = {"email": "user.test@cebuana.com", "password": "Test123!"}
ATTENDANT = {"email": "attendant.test@cebuana.com", "password": "Test123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {creds['email']}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def user_session():
    return _login(USER)


@pytest.fixture(scope="module")
def attendant_session():
    return _login(ATTENDANT)


# ---------- V-08 PUT sanitization (the hot fix path) ----------
def test_v08_put_user_sanitization_couchbase(admin_session):
    """After adding find_one_and_update to the Couchbase adapter,
    PUT /api/users/{id} must succeed and return CSV-prefixed values."""
    payload = {
        "email": f"TEST_iter38_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Test123!",
        "first_name": "Seed",
        "last_name": "User",
        "company": "Co",
        "role": "user",
        "assigned_buildings": [],
        "main_building": None,
        "tags": [],
        "default_start_time": None,
        "default_end_time": None,
        "parking_sticker_number": None,
        "job_family": "team",
    }
    r = admin_session.post(f"{BASE_URL}/api/users", json=payload, timeout=30)
    assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
    uid = r.json()["id"]

    update = {
        "email": payload["email"],
        "first_name": "=CMD()",
        "last_name": "+attack",
        "company": "-evil",
        "role": "user",
        "assigned_buildings": [],
        "main_building": None,
        "tags": [],
        "default_start_time": None,
        "default_end_time": None,
        "parking_sticker_number": None,
        "job_family": "@formula",
    }
    try:
        r2 = admin_session.put(f"{BASE_URL}/api/users/{uid}", json=update, timeout=30)
        assert r2.status_code == 200, f"PUT failed (find_one_and_update missing?): {r2.status_code} {r2.text}"
        d = r2.json()
        assert d["first_name"].startswith("'="), f"first_name not sanitized: {d['first_name']!r}"
        assert d["last_name"].startswith("'+"), f"last_name not sanitized: {d['last_name']!r}"
        assert d["company"].startswith("'-"), f"company not sanitized: {d['company']!r}"
        assert d["job_family"].startswith("'@"), f"job_family not sanitized: {d['job_family']!r}"

        # Confirm persisted via list endpoint (no GET-by-id route exists)
        r3 = admin_session.get(f"{BASE_URL}/api/users", timeout=20)
        assert r3.status_code == 200
        match = next((u for u in r3.json() if u["id"] == uid), None)
        assert match is not None, "PUT'd user not found in list"
        assert match["first_name"].startswith("'=")
        assert match["job_family"].startswith("'@")
    finally:
        admin_session.delete(f"{BASE_URL}/api/users/{uid}", timeout=20)


# ---------- Reservation confirm uses find_one_and_update ----------
def test_reservations_confirm_no_500_on_missing(attendant_session):
    """PUT /api/reservations/{id}/confirm — must hit find_one_and_update
    and return 404 (not 500) for a non-existent id."""
    bogus = f"nonexistent-{uuid.uuid4().hex}"
    r = attendant_session.put(
        f"{BASE_URL}/api/reservations/{bogus}/confirm", timeout=30
    )
    assert r.status_code != 500, (
        f"500 indicates Couchbase adapter regression: {r.status_code} {r.text}"
    )
    assert r.status_code == 404, f"expected 404 for missing reservation, got {r.status_code} {r.text}"


def test_reservations_confirm_with_photo_no_500_on_missing(attendant_session):
    """POST /api/reservations/{id}/confirm-with-photo — must hit find_one_and_update
    and return 404 (not 500) for a non-existent id."""
    bogus = f"nonexistent-{uuid.uuid4().hex}"
    r = attendant_session.post(
        f"{BASE_URL}/api/reservations/{bogus}/confirm-with-photo",
        json={"photo": "data:image/png;base64,iVBORw0KGgo="},
        timeout=30,
    )
    assert r.status_code != 500, (
        f"500 indicates Couchbase adapter regression: {r.status_code} {r.text}"
    )
    assert r.status_code == 404, f"expected 404 for missing reservation, got {r.status_code} {r.text}"


def test_reservations_confirm_full_lifecycle(admin_session, user_session, attendant_session):
    """End-to-end: create reservation as user, confirm as attendant via the
    real find_one_and_update path, verify status flipped to 'confirmed'.
    Skips gracefully if seed data is incomplete."""
    # Discover a building, slot and vehicle visible to the user
    r_bld = user_session.get(f"{BASE_URL}/api/buildings", timeout=20)
    if r_bld.status_code != 200 or not r_bld.json():
        pytest.skip("no buildings visible to user")
    building = r_bld.json()[0]
    bid = building["id"]

    # Get user's own info -> user_id and main vehicle
    r_me = user_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r_me.status_code == 200
    me = r_me.json()

    r_v = user_session.get(f"{BASE_URL}/api/vehicles", timeout=20)
    if r_v.status_code != 200 or not r_v.json():
        pytest.skip("user has no vehicles")
    vehicle_id = r_v.json()[0]["id"]

    # Find an available slot for tomorrow via /api/slots/available?building_id=
    from datetime import date, timedelta
    target_date = (date.today() + timedelta(days=1)).isoformat()

    r_slots = user_session.get(
        f"{BASE_URL}/api/slots/available",
        params={"building_id": bid, "date": target_date, "start_time": "08:00", "end_time": "10:00"},
        timeout=30,
    )
    if r_slots.status_code != 200 or not r_slots.json():
        pytest.skip("no slots available endpoint or no free slots")
    slot = r_slots.json()[0]
    slot_id = slot["id"]
    floor_id = slot.get("floor_id")

    # Create reservation
    payload = {
        "building_id": bid,
        "floor_id": floor_id,
        "slot_id": slot_id,
        "vehicle_id": vehicle_id,
        "date": target_date,
        "start_time": "08:00",
        "end_time": "10:00",
    }
    r_res = user_session.post(f"{BASE_URL}/api/reservations", json=payload, timeout=30)
    if r_res.status_code != 200:
        pytest.skip(f"could not create reservation: {r_res.status_code} {r_res.text}")
    res = r_res.json()
    rid = res["id"]

    try:
        # Confirm via attendant — exercises find_one_and_update on db.reservations
        r_conf = attendant_session.put(
            f"{BASE_URL}/api/reservations/{rid}/confirm", timeout=30
        )
        assert r_conf.status_code != 500, f"confirm 500: {r_conf.text}"
        # attendant may not be assigned to this building -> 403 acceptable, but not 500
        if r_conf.status_code in (200,):
            # Verify status flipped
            r_get = admin_session.get(f"{BASE_URL}/api/reservations/{rid}", timeout=20)
            assert r_get.status_code == 200
            assert r_get.json().get("status") in ("confirmed", "CONFIRMED")
        else:
            assert r_conf.status_code in (403, 404), f"unexpected: {r_conf.status_code} {r_conf.text}"
    finally:
        # cleanup as admin
        admin_session.delete(f"{BASE_URL}/api/reservations/{rid}", timeout=20)


# ---------- Regression: logins ----------
def test_regression_admin_login(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 200
    assert r.json().get("role") == "admin"


def test_regression_user_login(user_session):
    r = user_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 200
    assert r.json().get("role") == "user"


def test_regression_attendant_login(attendant_session):
    r = attendant_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 200
    assert r.json().get("role") == "attendant"


# ---------- Regression: list users / buildings ----------
def test_regression_list_users(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/users", timeout=20)
    assert r.status_code == 200
    assert isinstance(r.json(), list) and len(r.json()) > 0


def test_regression_list_buildings_nested(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/buildings", timeout=20)
    assert r.status_code == 200
    bs = r.json()
    assert isinstance(bs, list) and bs


# ---------- Regression: reports/stats ----------
def test_regression_reports_stats(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/reports/stats", timeout=30)
    # endpoint may not exist; accept 200 OR 404 but not 500
    assert r.status_code != 500, f"reports/stats 500: {r.text}"
    if r.status_code == 200:
        assert isinstance(r.json(), (dict, list))


# ---------- Regression: system endpoints ----------
def test_regression_system_db_info(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/system/db-info", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert "db_type" in data and "label" in data


def test_regression_system_collection_stats(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/system/collection-stats", timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert "collections" in data and isinstance(data["collections"], list)
    assert len(data["collections"]) > 0


def test_regression_system_build_info_public():
    r = requests.get(f"{BASE_URL}/api/system/build-info", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert "deployed_at" in data
    assert "server_time" in data and isinstance(data["server_time"], int)
    pkgs = data.get("python_packages") or {}
    for k in ("fastapi", "motor", "couchbase", "pyjwt", "bcrypt"):
        assert k in pkgs, f"missing package key {k}"
        assert pkgs[k] and pkgs[k] != "unknown"


def test_regression_system_sync_mongo_to_couchbase(admin_session):
    """Endpoint should run end-to-end (idempotent upsert). We accept 200 or 409
    (concurrent sync running) but not 5xx."""
    r = admin_session.post(f"{BASE_URL}/api/system/sync-mongo-to-couchbase", timeout=300)
    assert r.status_code in (200, 409, 400), (
        f"sync endpoint regression: {r.status_code} {r.text}"
    )
    if r.status_code == 200:
        body = r.json()
        # tolerant key check
        assert isinstance(body, dict)
