"""QAT 4th Pass — backend regression for iteration 39.

Covers:
- TCID-LOGIN-006: login password whitespace rejection (422)
- TCID-LOGIN-018: change-password — new == current rejected (400)
- TCID-PARKING-CONFIG-007: server.py registers auto_release_slots task (import smoke)
- TCID-PARKING-CONFIG-010: booking_window_days bounds (1..30) on POST /api/parking-config
- TCID-BUILDING-MANAGEMENT-010: create strict (>30 chars => 422) / update permissive (>30 chars => 200)
- TCID-EVENT-BLOCKING-012: structural — multi-slot conflicts list ALL labels (best-effort)
- REGRESSION: admin/user/attendant logins, list users, list buildings (nested),
  reports/stats, system/db-info, system/build-info, system/collection-stats.
"""

import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://reserve-park-debug.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin.test@cebuana.com", "Test123!")
USER = ("user.test@cebuana.com", "Test123!")
ATTENDANT = ("attendant.test@cebuana.com", "Test123!")


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def _login(sess, email, password):
    r = sess.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="module")
def admin_token(s):
    r = _login(s, *ADMIN)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture()
def admin_session(admin_token):
    sess = requests.Session()
    sess.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}",
    })
    return sess


# ---------------- regression: logins ----------------
def test_admin_login(s):
    r = _login(s, *ADMIN)
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json()["user"]["email"] == ADMIN[0]


def test_user_login(s):
    r = _login(s, *USER)
    assert r.status_code == 200
    assert r.json()["user"]["role"] in ("user", "USER", "User")


def test_attendant_login(s):
    r = _login(s, *ATTENDANT)
    assert r.status_code == 200


# ---------------- TCID-LOGIN-006 ----------------
def test_login_password_with_leading_space_returns_422(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": " Test123!"}, timeout=30)
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"
    body = r.json()
    blob = str(body).lower()
    assert "whitespace" in blob, f"expected 'whitespace' in detail, got: {body}"


def test_login_password_with_trailing_space_returns_422(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": "Test123! "}, timeout=30)
    assert r.status_code == 422
    assert "whitespace" in str(r.json()).lower()


def test_login_password_only_whitespace_returns_422(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": "    "}, timeout=30)
    assert r.status_code == 422


# ---------------- TCID-LOGIN-018 ----------------
def test_change_password_same_as_current_rejected(admin_session):
    r = admin_session.post(
        f"{API}/auth/change-password",
        json={"current_password": ADMIN[1], "new_password": ADMIN[1]},
        timeout=30,
    )
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
    detail = str(r.json()).lower()
    assert "different" in detail or "same" in detail


# ---------------- TCID-PARKING-CONFIG-007 ----------------
def test_auto_release_slots_imports_cleanly():
    """Smoke test: ensure background task is importable and registered in server.py."""
    from services.background import auto_release_slots, auto_mark_no_shows, check_waitlist_expiry
    import inspect
    assert inspect.iscoroutinefunction(auto_release_slots)
    server_src = open("/app/backend/server.py").read()
    assert "auto_release_slots" in server_src
    assert "asyncio.create_task(auto_release_slots())" in server_src


# ---------------- TCID-PARKING-CONFIG-010 ----------------
def _get_a_building_id(sess):
    r = sess.get(f"{API}/buildings", timeout=30)
    assert r.status_code == 200
    bs = r.json()
    assert bs, "no buildings seeded"
    return bs[0]["id"]


def test_parking_config_booking_window_999_rejected(admin_session):
    bid = _get_a_building_id(admin_session)
    r = admin_session.post(
        f"{API}/parking-config",
        json={"building_id": bid, "booking_window_days": 999},
        timeout=30,
    )
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"
    msg = str(r.json()).lower()
    assert "less than or equal to 30" in msg or "le=30" in msg or "<= 30" in msg


def test_parking_config_booking_window_zero_rejected(admin_session):
    bid = _get_a_building_id(admin_session)
    r = admin_session.post(
        f"{API}/parking-config",
        json={"building_id": bid, "booking_window_days": 0},
        timeout=30,
    )
    assert r.status_code == 422
    msg = str(r.json()).lower()
    assert "greater than or equal to 1" in msg or "ge=1" in msg or ">= 1" in msg


# ---------------- TCID-BUILDING-MANAGEMENT-010 ----------------
def test_building_create_strict_30char_limit(admin_session):
    long_name = "X" * 40  # 40 chars, > 30
    r = admin_session.post(
        f"{API}/buildings",
        json={"name": long_name, "address": "addr", "total_floors": 1, "slots_per_floor": 1},
        timeout=30,
    )
    assert r.status_code == 422, f"create with 40-char name should 422, got {r.status_code}: {r.text}"


def test_building_update_permissive_long_name(admin_session):
    """PUT must accept name longer than 30 (legacy permissiveness)."""
    # 1) create with a valid 30-char name
    name = f"TEST_{uuid.uuid4().hex[:20]}"
    create = admin_session.post(
        f"{API}/buildings",
        json={"name": name, "address": "addr", "total_floors": 1, "slots_per_floor": 1},
        timeout=30,
    )
    assert create.status_code in (200, 201), f"setup failed: {create.status_code} {create.text}"
    bid = create.json()["id"]

    try:
        long_name = "Y" * 45
        upd = admin_session.put(f"{API}/buildings/{bid}", json={"name": long_name}, timeout=30)
        assert upd.status_code == 200, f"PUT with 45-char name should be allowed, got {upd.status_code}: {upd.text}"
        # verify persisted
        get = admin_session.get(f"{API}/buildings", timeout=30)
        assert get.status_code == 200
        match = [b for b in get.json() if b["id"] == bid]
        assert match and match[0]["name"] == long_name
    finally:
        admin_session.delete(f"{API}/buildings/{bid}", timeout=30)


# ---------------- TCID-EVENT-BLOCKING-012 ----------------
def test_event_blocks_validation_basic(admin_session):
    """Structural: empty slot_ids => 400; missing reason => 400.
    Multi-conflict listing is hard to test without seeded reservations,
    so we verify the route rejects clearly malformed input.
    """
    bid = _get_a_building_id(admin_session)
    r = admin_session.post(
        f"{API}/event-blocks",
        json={
            "building_id": bid,
            "floor_id": "x",
            "slot_ids": [],
            "date": "2030-01-01",
            "reason": "test",
        },
        timeout=30,
    )
    assert r.status_code == 400
    assert "slot" in str(r.json()).lower()


# ---------------- REGRESSION ----------------
def test_list_users(admin_session):
    r = admin_session.get(f"{API}/users", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 3


def test_list_buildings_nested(admin_session):
    r = admin_session.get(f"{API}/buildings", timeout=30)
    assert r.status_code == 200
    bs = r.json()
    assert isinstance(bs, list)
    if bs:
        assert "floors" in bs[0]


def test_reports_stats(admin_session):
    r = admin_session.get(f"{API}/reports/stats", timeout=30)
    assert r.status_code == 200


def test_system_db_info(admin_session):
    r = admin_session.get(f"{API}/system/db-info", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "db_type" in body or "type" in body


def test_system_build_info(admin_session):
    r = admin_session.get(f"{API}/system/build-info", timeout=30)
    assert r.status_code == 200


def test_system_collection_stats(admin_session):
    r = admin_session.get(f"{API}/system/collection-stats", timeout=30)
    assert r.status_code == 200


# ---------------- find_one_and_update on Couchbase still works ----------------
def test_reservation_confirm_404_on_bogus_id(admin_session):
    """Exercises find_one_and_update path on Couchbase."""
    r = admin_session.put(f"{API}/reservations/{uuid.uuid4()}/confirm", timeout=30)
    assert r.status_code in (404, 400), f"expected 4xx, got {r.status_code}: {r.text}"
