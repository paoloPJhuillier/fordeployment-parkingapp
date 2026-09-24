"""
VAPT Security Fixes Test - Iteration 19
Tests for 3 vulnerabilities being addressed:
1. Session hijacking via cookie copy - fixed with device fingerprint + session revocation
2. Plaintext password in DOM - fixed by clearing after submission (frontend test)
3. PII disclosure in /auth/me - fixed by removing email from response

Note: Using Authorization header instead of cookie due to Secure flag on localhost.
Tests are consolidated to minimize login calls due to rate limiting (5/min).
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin.test@cebuana.com", "password": "Test123!"}
USER_CREDS = {"email": "user.test@cebuana.com", "password": "Test123!"}
ATTENDANT_CREDS = {"email": "attendant.test@cebuana.com", "password": "Test123!"}


def login_and_get_token(credentials: dict, user_agent: str = "TestBrowser/1.0") -> tuple:
    """Login and return (token, login_data)"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "User-Agent": user_agent
    })
    response = session.post(f"{BASE_URL}/api/auth/login", json=credentials)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token"), data
    return None, response


def make_authed_request(method: str, endpoint: str, token: str, user_agent: str, **kwargs):
    """Make authenticated request with token and User-Agent"""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": user_agent,
        "Content-Type": "application/json"
    }
    headers.update(kwargs.pop("headers", {}))
    return requests.request(method, f"{BASE_URL}{endpoint}", headers=headers, **kwargs)


class TestVAPTSecurityFixes:
    """Consolidated VAPT security fix tests to minimize logins"""
    
    def test_01_login_creates_session_and_returns_full_user_data(self):
        """
        POST /api/auth/login should:
        1. Create session with fingerprint in DB
        2. Return email in user object (needed for frontend)
        3. Return full UserResponse (email, company, created_at, etc.)
        """
        token, data = login_and_get_token(ADMIN_CREDS, "LoginTest/1.0")
        
        assert token is not None, f"Login failed: {data}"
        assert isinstance(data, dict), "Response should be dict"
        
        # Test 1: Verify login response includes email (VULN 3 fix allows email in login response)
        assert "user" in data, "Login response should contain user object"
        user = data["user"]
        
        assert "email" in user, "Login response user object should include email"
        assert user["email"] == ADMIN_CREDS["email"], "Email should match credentials"
        assert "first_name" in user, "Login user should include first_name"
        assert "last_name" in user, "Login user should include last_name"
        assert "role" in user, "Login user should include role"
        assert "created_at" in user, "Login user should include created_at"
        
        # Test 2: Verify access_token is returned
        assert "access_token" in data, "Login response should contain access_token"
        
        print(f"PASS: Login returns full user with email: {user['email']}")
    
    def test_02_auth_me_with_same_user_agent_and_no_pii(self):
        """
        GET /api/auth/me with same User-Agent should:
        1. Return 200 OK
        2. NOT return email field (VULN 3 fix)
        3. NOT return company/created_at
        4. Return only minimal fields (AuthMeResponse)
        """
        time.sleep(0.5)
        
        token, data = login_and_get_token(ADMIN_CREDS, "SameUATest/1.0")
        assert token, f"Login failed: {data}"
        
        # Access /auth/me with same User-Agent
        response = make_authed_request("GET", "/api/auth/me", token, "SameUATest/1.0")
        assert response.status_code == 200, f"GET /auth/me failed: {response.text}"
        
        me_data = response.json()
        actual_fields = set(me_data.keys())
        
        # Test VULN 3 fix: email must NOT be in /auth/me response
        assert "email" not in me_data, "SECURITY FAIL: /auth/me returns email"
        assert "company" not in me_data, "/auth/me should NOT return company"
        assert "created_at" not in me_data, "/auth/me should NOT return created_at"
        
        # Verify expected fields present
        expected_fields = {
            "id", "first_name", "last_name", "role",
            "assigned_buildings", "main_building", "tags",
            "is_blocked", "must_change_password"
        }
        missing = expected_fields - actual_fields
        assert len(missing) == 0, f"Missing expected fields: {missing}"
        
        print(f"PASS: /auth/me returns only minimal fields: {actual_fields}")
    
    def test_03_auth_me_with_different_user_agent_returns_device_mismatch(self):
        """
        GET /api/auth/me with DIFFERENT User-Agent should:
        1. Return 401 Unauthorized
        2. Return error 'device mismatch' (VULN 1 fix - fingerprint validation)
        """
        time.sleep(0.5)
        
        # Login with original User-Agent
        token, data = login_and_get_token(USER_CREDS, "OriginalDevice/1.0")
        assert token, f"Login failed: {data}"
        
        # Try to access /auth/me with DIFFERENT User-Agent (simulating hijack attempt)
        response = make_authed_request("GET", "/api/auth/me", token, "AttackerDevice/2.0")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        error_detail = response.json().get("detail", "")
        assert "device mismatch" in error_detail.lower(), f"Expected 'device mismatch', got: {error_detail}"
        
        print("PASS: Different User-Agent returns 401 'device mismatch'")
    
    def test_04_logout_revokes_session_and_blocks_replay(self):
        """
        POST /api/auth/logout should:
        1. Revoke the session in DB
        2. Block subsequent requests with same token (replay attack prevention)
        3. Return 'Session has been revoked' error
        """
        time.sleep(0.5)
        
        # Login
        token, data = login_and_get_token(ATTENDANT_CREDS, "LogoutTest/1.0")
        assert token, f"Login failed: {data}"
        
        # Verify /auth/me works before logout
        me_before = make_authed_request("GET", "/api/auth/me", token, "LogoutTest/1.0")
        assert me_before.status_code == 200, "Should access /auth/me before logout"
        
        # Logout
        logout_resp = make_authed_request("POST", "/api/auth/logout", token, "LogoutTest/1.0")
        assert logout_resp.status_code == 200, f"Logout failed: {logout_resp.text}"
        
        # Try to reuse the token after logout (replay attack)
        me_after = make_authed_request("GET", "/api/auth/me", token, "LogoutTest/1.0")
        
        assert me_after.status_code == 401, f"Expected 401 for revoked session, got {me_after.status_code}"
        
        error_detail = me_after.json().get("detail", "")
        assert "revoked" in error_detail.lower(), f"Expected 'revoked', got: {error_detail}"
        
        print("PASS: Session revoked, replay attack blocked")
    
    def test_05_admin_endpoints_still_work_after_vapt_fixes(self):
        """Verify VAPT fixes don't break admin protected routes"""
        time.sleep(0.5)
        
        token, data = login_and_get_token(ADMIN_CREDS, "AdminFlowTest/1.0")
        assert token, f"Login failed: {data}"
        
        # Access admin endpoints
        users_resp = make_authed_request("GET", "/api/users", token, "AdminFlowTest/1.0")
        assert users_resp.status_code == 200, f"Admin /users failed: {users_resp.text}"
        
        buildings_resp = make_authed_request("GET", "/api/buildings", token, "AdminFlowTest/1.0")
        assert buildings_resp.status_code == 200, "Admin /buildings failed"
        
        print("PASS: Admin endpoints work after VAPT fixes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
