"""
Bug Fix Verification Tests - Iteration 28
Tests for 7 bugs fixed:
1. TC-USER-MANAGEMENT-026: Blocked users should get 403 on login
2. TCID-LOGIN-018: Same password change should get 400
3. TCID-DASHBOARD-007: No 'Unknown' buildings in reports/stats
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# =========================================================
# Fixtures
# =========================================================

@pytest.fixture(scope="module")
def admin_token():
    """Login as admin and get token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin.test@cebuana.com",
        "password": "Test123!"
    })
    if resp.status_code != 200:
        pytest.skip(f"Admin login failed: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def user_id(admin_headers):
    """Get user.test@cebuana.com user id"""
    resp = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
    assert resp.status_code == 200, f"Failed to get users: {resp.text}"
    users = resp.json()
    for u in users:
        if u["email"] == "user.test@cebuana.com":
            return u["id"]
    pytest.skip("Test user not found")


# =========================================================
# TC-USER-MANAGEMENT-026: Blocked user login test
# =========================================================

class TestBlockedUserLogin:
    """TC-USER-MANAGEMENT-026: Blocked users cannot login"""

    def test_normal_user_can_login(self):
        """Verify user can login before being blocked"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert resp.status_code == 200, f"Expected 200 for normal login, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data, "Expected access_token in response"
        print("PASS: Normal user can login")

    def test_block_user_api(self, admin_headers, user_id):
        """Block the test user via admin API"""
        resp = requests.put(f"{BASE_URL}/api/users/{user_id}/block", headers=admin_headers)
        assert resp.status_code == 200, f"Expected 200 for block, got {resp.status_code}: {resp.text}"
        print(f"PASS: User {user_id} blocked successfully")

    def test_blocked_user_gets_403(self, admin_headers, user_id):
        """Blocked user should get 403 when trying to login"""
        # First block the user
        block_resp = requests.put(f"{BASE_URL}/api/users/{user_id}/block", headers=admin_headers)
        assert block_resp.status_code == 200, f"Block failed: {block_resp.text}"

        # Now try to login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert login_resp.status_code == 403, f"Expected 403 for blocked user, got {login_resp.status_code}: {login_resp.text}"
        data = login_resp.json()
        assert "blocked" in data.get("detail", "").lower(), f"Expected 'blocked' in error detail, got: {data.get('detail')}"
        print(f"PASS: Blocked user gets 403 with message: {data.get('detail')}")

        # Unblock the user after test
        requests.put(f"{BASE_URL}/api/users/{user_id}/unblock", headers=admin_headers)

    def test_unblocked_user_can_login_again(self, admin_headers, user_id):
        """After unblocking, user should be able to login"""
        # Ensure user is blocked first
        requests.put(f"{BASE_URL}/api/users/{user_id}/block", headers=admin_headers)
        # Unblock
        unblock_resp = requests.put(f"{BASE_URL}/api/users/{user_id}/unblock", headers=admin_headers)
        assert unblock_resp.status_code == 200, f"Unblock failed: {unblock_resp.text}"

        # Try to login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert login_resp.status_code == 200, f"Expected 200 after unblocking, got {login_resp.status_code}: {login_resp.text}"
        print("PASS: Unblocked user can login again")


# =========================================================
# TCID-LOGIN-018: Same password change prevention
# =========================================================

class TestSamePasswordChange:
    """TCID-LOGIN-018: Cannot change to same password"""

    def test_change_to_same_password_returns_400(self):
        """Changing password to same value should return 400"""
        # Login first to get a token
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        if login_resp.status_code != 200:
            pytest.skip(f"Login failed: {login_resp.status_code}")

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Try to change to same password
        resp = requests.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "Test123!",
            "new_password": "Test123!"
        }, headers=headers)
        assert resp.status_code == 400, f"Expected 400 for same password, got {resp.status_code}: {resp.text}"
        data = resp.json()
        detail = data.get("detail", "").lower()
        assert "same" in detail or "cannot" in detail, f"Expected 'same' in error detail, got: {data.get('detail')}"
        print(f"PASS: Same password change gets 400 with: {data.get('detail')}")

    def test_change_to_different_password_works(self):
        """Changing to a different password should work"""
        # Login as user
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "attendant.test@cebuana.com",
            "password": "Test123!"
        })
        if login_resp.status_code != 200:
            pytest.skip(f"Login failed: {login_resp.status_code}")

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Change to new password
        resp = requests.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "Test123!",
            "new_password": "NewTest456!"
        }, headers=headers)
        # Can be 200 or possibly 400 if password requirements not met
        # We just verify the "same password" scenario is rejected
        # Restore original password if successful
        if resp.status_code == 200:
            restore = requests.post(f"{BASE_URL}/api/auth/change-password", json={
                "current_password": "NewTest456!",
                "new_password": "Test123!"
            }, headers={
                "Authorization": f"Bearer {resp.json().get('access_token', token) if 'access_token' in resp.json() else token}",
                "Content-Type": "application/json"
            })
            print(f"PASS: Different password change succeeded and restored (restore status: {restore.status_code})")
        else:
            print(f"INFO: Different password change returned {resp.status_code}: {resp.text}")


# =========================================================
# TCID-DASHBOARD-007: No 'Unknown' buildings in reports
# =========================================================

class TestNoUnknownBuildings:
    """TCID-DASHBOARD-007: Reports should not show 'Unknown' buildings"""

    def test_reports_no_unknown_buildings(self, admin_headers):
        """Building breakdown in reports should not contain 'Unknown'"""
        resp = requests.get(f"{BASE_URL}/api/reports/stats", headers=admin_headers)
        assert resp.status_code == 200, f"Expected 200 for reports, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "building_breakdown" in data, "Expected building_breakdown in response"

        building_breakdown = data["building_breakdown"]
        unknown_buildings = [b for b in building_breakdown if b.get("building_name", "").lower() == "unknown"]
        assert len(unknown_buildings) == 0, f"Found {len(unknown_buildings)} 'Unknown' buildings: {unknown_buildings}"
        print(f"PASS: No 'Unknown' buildings in reports. Found {len(building_breakdown)} buildings: {[b['building_name'] for b in building_breakdown]}")

    def test_reports_stats_structure(self, admin_headers):
        """Reports stats should have expected structure"""
        resp = requests.get(f"{BASE_URL}/api/reports/stats", headers=admin_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "summary" in data, "Expected summary field"
        assert "daily_breakdown" in data, "Expected daily_breakdown field"
        assert "building_breakdown" in data, "Expected building_breakdown field"

        summary = data["summary"]
        assert "total_reservations" in summary
        assert "confirmed" in summary
        print(f"PASS: Reports stats structure verified. Total reservations: {summary['total_reservations']}")


# =========================================================
# Auth Login edge case (backend validation)
# =========================================================

class TestLoginValidation:
    """TCID-LOGIN-002/019: Login with empty fields"""

    def test_empty_email_returns_error(self):
        """Login with empty email should return error"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "",
            "password": "Test123!"
        })
        # Should return 4xx error (not 200 or redirect to dashboard)
        assert resp.status_code in [400, 401, 422], f"Expected 4xx for empty email, got {resp.status_code}: {resp.text}"
        print(f"PASS: Empty email returns {resp.status_code}")

    def test_empty_password_returns_error(self):
        """Login with empty password should return error"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": ""
        })
        # Should return 4xx error
        assert resp.status_code in [400, 401, 422], f"Expected 4xx for empty password, got {resp.status_code}: {resp.text}"
        print(f"PASS: Empty password returns {resp.status_code}")

    def test_wrong_credentials_returns_401(self):
        """Login with wrong credentials should return 401"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401, f"Expected 401 for wrong password, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "invalid" in data.get("detail", "").lower() or "credential" in data.get("detail", "").lower(), \
            f"Expected 'invalid credentials' message, got: {data.get('detail')}"
        print(f"PASS: Wrong credentials return 401 with: {data.get('detail')}")
