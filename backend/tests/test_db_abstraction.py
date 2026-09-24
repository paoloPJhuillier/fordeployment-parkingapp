"""
Regression + smoke tests for the Database Abstraction Layer.
Covers:
  - MongoDB mode regression (core flows unchanged)
  - New GET /api/system/db-info admin-only endpoint (auth & payload)
  - Works for whichever DB_TYPE is currently active in backend/.env
"""

import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://reserve-park-debug.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin.test@cebuana.com", "password": "Test123!"}
USER = {"email": "user.test@cebuana.com", "password": "Test123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def user_session():
    return _login(USER)


# ---------- AUTH ----------
class TestAuth:
    def test_login_admin(self):
        r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data.get("user", {}).get("email") == ADMIN["email"]
        assert data["user"]["role"] == "admin"

    def test_login_bad_creds(self):
        r = requests.post(f"{API}/auth/login", json={"email": "nope@x.com", "password": "wrong"}, timeout=30)
        assert r.status_code in (400, 401, 403)

    def test_auth_me(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        data = r.json()
        # /auth/me may return user directly or wrap in {user: ...}
        user = data.get("user", data)
        assert user.get("email") == ADMIN["email"] or user.get("first_name") == "Admin"

    def test_logout(self):
        s = _login(ADMIN)
        r = s.post(f"{API}/auth/logout", timeout=30)
        assert r.status_code in (200, 204)


# ---------- NEW SYSTEM DB-INFO ENDPOINT ----------
class TestDbInfo:
    def test_unauthenticated_blocked(self):
        r = requests.get(f"{API}/system/db-info", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_non_admin_forbidden(self, user_session):
        r = user_session.get(f"{API}/system/db-info", timeout=30)
        assert r.status_code == 403, f"expected 403 for non-admin, got {r.status_code}: {r.text}"

    def test_admin_payload_shape(self, admin_session):
        r = admin_session.get(f"{API}/system/db-info", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("db_type", "label", "connected", "host", "database_name"):
            assert key in data, f"missing field '{key}' in {data}"
        assert data["db_type"] in ("mongodb", "couchbase")
        assert isinstance(data["connected"], bool)
        if data["db_type"] == "mongodb":
            assert data["label"] == "MongoDB"
        elif data["db_type"] == "couchbase":
            assert data["label"] == "Couchbase Capella"
        # Must be connected for the app to serve anything
        assert data["connected"] is True


# ---------- USERS CRUD regression ----------
class TestUsers:
    def test_list_users(self, admin_session):
        r = admin_session.get(f"{API}/users", timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        assert len(users) > 0
        emails = [u.get("email") for u in users]
        assert ADMIN["email"] in emails

    def test_create_update_delete_user(self, admin_session):
        # Only mutate if MongoDB is active (per review note: read-only for Couchbase)
        info = admin_session.get(f"{API}/system/db-info", timeout=30).json()
        if info["db_type"] != "mongodb":
            pytest.skip("Skipping mutations; active DB is not MongoDB")

        payload = {
            "email": "TEST_abstraction_user@example.com",
            "password": "Temp123!",
            "first_name": "TEST",
            "last_name": "Abstraction",
            "role": "user",
        }
        # Cleanup existing
        existing = admin_session.get(f"{API}/users", timeout=30).json()
        for u in existing:
            if u.get("email") == payload["email"]:
                admin_session.delete(f"{API}/users/{u['id']}", timeout=30)

        r = admin_session.post(f"{API}/users", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        uid = r.json().get("id")
        assert uid

        # Update (PUT requires full body per server schema)
        r2 = admin_session.put(f"{API}/users/{uid}", json={
            "email": payload["email"],
            "first_name": "Updated",
            "last_name": payload["last_name"],
            "role": "user",
        }, timeout=30)
        assert r2.status_code == 200, r2.text

        # Verify
        users = admin_session.get(f"{API}/users", timeout=30).json()
        match = [u for u in users if u.get("id") == uid]
        assert match and match[0]["first_name"] == "Updated"

        # Delete
        r3 = admin_session.delete(f"{API}/users/{uid}", timeout=30)
        assert r3.status_code in (200, 204)


# ---------- BUILDINGS nested ----------
class TestBuildings:
    def test_list_buildings_nested(self, admin_session):
        r = admin_session.get(f"{API}/buildings", timeout=30)
        assert r.status_code == 200, r.text
        buildings = r.json()
        assert isinstance(buildings, list)
        assert len(buildings) > 0
        # Verify nested floors and slots are present on at least one building
        total_floors = 0
        total_slots = 0
        for b in buildings:
            floors = b.get("floors") or []
            total_floors += len(floors)
            for f in floors:
                total_slots += len(f.get("slots") or [])
        assert total_floors > 0, "no floors found on any building"
        assert total_slots > 0, "no slots found on any floor"


# ---------- OTHER READ-ONLY endpoints ----------
class TestReadOnly:
    def test_reservations_list(self, admin_session):
        r = admin_session.get(f"{API}/reservations", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_reports_stats(self, admin_session):
        r = admin_session.get(f"{API}/reports/stats", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        summary = data.get("summary", data)
        assert "total_reservations" in summary or "total" in summary or isinstance(summary, dict)

    def test_notifications(self, admin_session):
        r = admin_session.get(f"{API}/notifications", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_zones(self, admin_session):
        r = admin_session.get(f"{API}/zones", timeout=30)
        assert r.status_code == 200

    def test_vehicles(self, admin_session):
        r = admin_session.get(f"{API}/vehicles", timeout=30)
        assert r.status_code == 200
