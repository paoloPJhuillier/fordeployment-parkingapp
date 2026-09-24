"""
VAPT retest - iteration 37
Covers: V-02 (data access), V-03 (CORS fail-closed app layer),
V-08 (CSV injection on single-user POST/PUT), V-10 (build-info),
plus regression on V-01/V-04/V-06/V-07/V-09 and existing flows.
"""
import os
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
LOCAL_URL = "http://localhost:8001"

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


# ---------- V-10 build-info (public) ----------
def test_v10_build_info_public():
    r = requests.get(f"{BASE_URL}/api/system/build-info", timeout=20)
    assert r.status_code == 200, f"build-info should be public: {r.status_code}"
    data = r.json()
    assert "deployed_at" in data
    assert "server_time" in data and isinstance(data["server_time"], int)
    pkgs = data.get("python_packages") or {}
    for k in ("fastapi", "motor", "couchbase", "pyjwt", "bcrypt"):
        assert k in pkgs, f"missing package key {k}"
        assert pkgs[k] and pkgs[k] != "unknown", f"{k} version is unknown/empty: {pkgs[k]}"


# ---------- V-02a parking-config role-based response ----------
def _find_building_id(sess):
    r = sess.get(f"{BASE_URL}/api/buildings", timeout=20)
    assert r.status_code == 200
    bs = r.json()
    assert bs, "no buildings"
    return bs[0]["id"]


def test_v02a_parking_config_admin_full_fields(admin_session):
    bid = _find_building_id(admin_session)
    r = admin_session.get(f"{BASE_URL}/api/parking-config/{bid}", timeout=20)
    assert r.status_code == 200
    data = r.json()
    required = {
        "id", "building_id", "release_time", "default_start_time",
        "default_end_time", "booking_window_days",
        "no_show_release_enabled", "no_show_release_minutes",
        "waitlist_enabled", "waitlist_notification_window_minutes",
        "main_building_exclusive",
    }
    missing = required - set(data.keys())
    assert not missing, f"admin view missing fields: {missing}; got: {list(data.keys())}"


def test_v02a_parking_config_user_trimmed(user_session, admin_session):
    bid = _find_building_id(admin_session)
    r = user_session.get(f"{BASE_URL}/api/parking-config/{bid}", timeout=20)
    assert r.status_code == 200
    data = r.json()
    allowed = {"id", "building_id", "release_time", "default_start_time",
               "default_end_time", "booking_window_days"}
    keys = set(data.keys())
    assert keys == allowed, f"user view leaked keys: extra={keys - allowed} missing={allowed - keys}"
    # explicitly ensure forbidden keys are absent
    for forbidden in ("no_show_release_enabled", "no_show_release_minutes",
                      "waitlist_enabled", "waitlist_notification_window_minutes",
                      "main_building_exclusive"):
        assert forbidden not in data, f"user view leaked {forbidden}"


# ---------- V-02b slot-registrations scoping ----------
def test_v02b_slot_regs_admin_sees_all(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/slot-registrations", timeout=20)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_v02b_slot_regs_user_scoped_to_self(user_session):
    # Fetch current user id via /api/auth/me if available; fall back to decoding cookie not needed
    r_me = user_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r_me.status_code == 200, f"/auth/me failed {r_me.status_code}"
    my_id = r_me.json().get("id")
    r = user_session.get(f"{BASE_URL}/api/slot-registrations", timeout=20)
    assert r.status_code == 200
    regs = r.json()
    assert isinstance(regs, list)
    for reg in regs:
        assert reg.get("user_id") == my_id, f"V-02b leak: user saw reg for other user {reg.get('user_id')}"


def test_v02b_slot_regs_attendant_scoped_to_buildings(attendant_session):
    r_me = attendant_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r_me.status_code == 200
    assigned = r_me.json().get("assigned_buildings", []) or []
    r = attendant_session.get(f"{BASE_URL}/api/slot-registrations", timeout=20)
    assert r.status_code == 200
    regs = r.json()
    if not assigned:
        assert regs == [], "attendant with no buildings should see []"
        return
    for reg in regs:
        assert reg.get("building_id") in assigned, \
            f"attendant saw reg outside assigned buildings: {reg.get('building_id')} not in {assigned}"


def test_v02b_user_cannot_view_other_users_regs(user_session, admin_session):
    # find any user id that's NOT the calling user
    r_me = user_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    my_id = r_me.json().get("id")
    r_users = admin_session.get(f"{BASE_URL}/api/users", timeout=20)
    assert r_users.status_code == 200
    other = next((u for u in r_users.json() if u["id"] != my_id), None)
    assert other, "no other user to test"
    r = user_session.get(f"{BASE_URL}/api/slot-registrations/user/{other['id']}", timeout=20)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


# ---------- V-03 CORS fail-closed (app layer, localhost) ----------
def test_v03_cors_fail_closed_local():
    """Hit FastAPI directly - no ingress. With empty CORS_ORIGINS env,
    foreign origin must NOT get Access-Control-Allow-Origin echoed back."""
    headers = {
        "Origin": "https://evil.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    r = requests.options(f"{LOCAL_URL}/api/auth/login", headers=headers, timeout=10)
    aco = r.headers.get("access-control-allow-origin", "")
    assert aco == "", f"V-03 FAIL: foreign origin echoed ACAO={aco!r}"


# ---------- V-08 CSV injection on POST/PUT /api/users ----------
def test_v08_csv_injection_post_users(admin_session):
    import uuid as _uuid
    payload = {
        "email": f"TEST_vapt_{_uuid.uuid4().hex[:8]}@example.com",
        "password": "Test123!",
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
    r = admin_session.post(f"{BASE_URL}/api/users", json=payload, timeout=20)
    assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["first_name"].startswith("'="), f"first_name not sanitized: {data['first_name']!r}"
    assert data["last_name"].startswith("'+"), f"last_name not sanitized: {data['last_name']!r}"
    assert data["company"].startswith("'-"), f"company not sanitized: {data['company']!r}"
    assert data["job_family"].startswith("'@"), f"job_family not sanitized: {data['job_family']!r}"
    uid = data["id"]

    # now test PUT
    update = {
        "email": payload["email"],
        "first_name": "=UPDATE()",
        "last_name": "+upd",
        "company": "-upd",
        "role": "user",
        "assigned_buildings": [],
        "main_building": None,
        "tags": [],
        "default_start_time": None,
        "default_end_time": None,
        "parking_sticker_number": None,
        "job_family": "@upd",
    }
    r2 = admin_session.put(f"{BASE_URL}/api/users/{uid}", json=update, timeout=20)
    assert r2.status_code == 200, f"update failed: {r2.status_code} {r2.text}"
    d2 = r2.json()
    assert d2["first_name"].startswith("'="), f"PUT first_name not sanitized: {d2['first_name']!r}"
    assert d2["job_family"].startswith("'@"), f"PUT job_family not sanitized: {d2['job_family']!r}"

    # cleanup
    admin_session.delete(f"{BASE_URL}/api/users/{uid}", timeout=20)


# ---------- REGRESSION ----------
def test_regression_admin_list_users(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/users", timeout=20)
    assert r.status_code == 200 and len(r.json()) > 0


def test_regression_buildings_nested(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/buildings", timeout=20)
    assert r.status_code == 200
    bs = r.json()
    assert bs and isinstance(bs, list)


def test_regression_user_login_basic_flows(user_session, attendant_session):
    # just assert sessions actually return /auth/me
    for s in (user_session, attendant_session):
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200


def test_regression_db_info_admin(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/system/db-info", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert "db_type" in data and "label" in data


def test_regression_collection_stats_admin(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/system/collection-stats", timeout=90)
    assert r.status_code == 200
    data = r.json()
    assert "collections" in data and isinstance(data["collections"], list)


def test_regression_v07_no_version_on_root():
    r = requests.get(f"{BASE_URL}/api/", timeout=10)
    # must not disclose a version key
    if r.status_code == 200:
        try:
            data = r.json()
            assert "version" not in data, f"V-07 regression: version leaked: {data}"
        except ValueError:
            pass


def test_regression_v01_bulk_upload_role_enforcement(admin_session):
    """Bulk upload must coerce admin role to 'user' (V-01)."""
    csv = b"first_name,last_name,email,role\nTEST_Rgr,Tgr,TEST_vapt37_regression@example.com,admin\n"
    files = {"file": ("u.csv", csv, "text/csv")}
    r = admin_session.post(
        f"{BASE_URL}/api/users/bulk-upload", files=files, data={"default_password": "Test123!"}, timeout=30
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Now fetch this user
    rr = admin_session.get(f"{BASE_URL}/api/users", timeout=20)
    target = next((u for u in rr.json() if u["email"] == "test_vapt37_regression@example.com"), None)
    if target:
        assert target["role"] == "user", f"V-01 regression: role not coerced: {target['role']}"
        admin_session.delete(f"{BASE_URL}/api/users/{target['id']}", timeout=20)
    _ = body  # silence
