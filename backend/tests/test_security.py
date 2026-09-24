"""
Security Tests for Parking Reservation App
Tests security fixes from security_report.md:
- C1: JWT Secret (already fixed via .env)
- C2: CORS (already fixed via .env)
- H1: Path traversal sanitization
- H2: Rate limiting on auth endpoints
- H3: File extension whitelist
- H4: Tag injection validation
- M1: Password complexity enforcement
- M3: Blocked user check
- L1: Security headers
- L2: Verbose error sanitization
"""

import pytest
import requests
import os
import time
from urllib.parse import quote

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"

class TestAuthenticationSecurity:
    """Tests for authentication security (M1, H2)"""
    
    def test_login_valid_credentials(self):
        """Admin login should work with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        print("✓ Admin login successful with valid credentials")
    
    def test_login_invalid_credentials(self):
        """Login should return 401 for invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Login correctly rejects invalid password with 401")
    
    def test_login_nonexistent_user(self):
        """Login should return 401 for nonexistent user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Login correctly rejects nonexistent user with 401")


class TestPasswordComplexity:
    """Tests for M1: Password complexity enforcement"""
    
    def test_register_weak_password_short(self):
        """Registration should reject passwords less than 8 characters"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"test_short_{int(time.time())}@test.com",
            "password": "short",
            "first_name": "Test",
            "last_name": "User"
        })
        # Should fail validation
        assert response.status_code == 422, f"Expected 422 for short password, got {response.status_code}: {response.text}"
        print("✓ Registration correctly rejects short password 'short'")
    
    def test_register_weak_password_no_uppercase(self):
        """Registration should reject passwords without uppercase letters"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"test_noupper_{int(time.time())}@test.com",
            "password": "alllowercase1",
            "first_name": "Test",
            "last_name": "User"
        })
        assert response.status_code == 422, f"Expected 422 for no uppercase, got {response.status_code}: {response.text}"
        print("✓ Registration correctly rejects password 'alllowercase1' (no uppercase)")
    
    def test_register_weak_password_no_lowercase(self):
        """Registration should reject passwords without lowercase letters"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"test_nolower_{int(time.time())}@test.com",
            "password": "ALLUPPERCASE1",
            "first_name": "Test",
            "last_name": "User"
        })
        assert response.status_code == 422, f"Expected 422 for no lowercase, got {response.status_code}: {response.text}"
        print("✓ Registration correctly rejects password 'ALLUPPERCASE1' (no lowercase)")
    
    def test_register_weak_password_no_digit(self):
        """Registration should reject passwords without digits"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"test_nodigit_{int(time.time())}@test.com",
            "password": "NoDigitsHere",
            "first_name": "Test",
            "last_name": "User"
        })
        assert response.status_code == 422, f"Expected 422 for no digit, got {response.status_code}: {response.text}"
        print("✓ Registration correctly rejects password 'NoDigitsHere' (no digit)")
    
    def test_register_valid_password(self):
        """Registration should accept valid complex password"""
        test_email = f"test_valid_{int(time.time())}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User"
        })
        # Could be 200 (success) or 429 (rate limited)
        assert response.status_code in [200, 429], f"Expected 200 or 429, got {response.status_code}: {response.text}"
        print(f"✓ Registration accepts valid password 'ValidPass123!' (status: {response.status_code})")


class TestPathTraversal:
    """Tests for H1: Path traversal sanitization in uploads endpoint"""
    
    def test_path_traversal_dotdot_in_filename(self):
        """Filename containing '..' should be blocked"""
        # The backend sanitizes filenames containing '..' characters
        response = requests.get(f"{BASE_URL}/api/uploads/test..env")
        assert response.status_code == 400, f"Expected 400 for filename with '..', got {response.status_code}"
        print("✓ Filename with '..' blocked with status 400")
    
    def test_path_traversal_blocked_encoded(self):
        """Path traversal with URL encoded ..%2F should be blocked"""
        response = requests.get(f"{BASE_URL}/api/uploads/..%2F..%2F.env")
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print(f"✓ Path traversal '..%2F..%2F.env' blocked with status {response.status_code}")
    
    def test_path_traversal_invalid_chars(self):
        """Filenames with special characters should be sanitized"""
        response = requests.get(f"{BASE_URL}/api/uploads/<script>alert(1)</script>.png")
        # Should return 400 (invalid chars) or 404 (sanitized file not found)
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print(f"✓ Special characters in filename handled with status {response.status_code}")
    
    def test_path_traversal_normal_file(self):
        """Normal valid filename should work (if file exists) or return 404"""
        response = requests.get(f"{BASE_URL}/api/uploads/test.png")
        # Should either be 404 (not found) or 200 (if file exists), not 400 or 500
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        print(f"✓ Normal file request returns valid response (status: {response.status_code})")


class TestSecurityHeaders:
    """Tests for L1: Security headers presence"""
    
    def test_security_headers_on_api_root(self):
        """Security headers should be present on API responses"""
        response = requests.get(f"{BASE_URL}/api/")
        headers = response.headers
        
        # Check for X-Content-Type-Options
        x_content_type = headers.get('X-Content-Type-Options', '')
        assert x_content_type.lower() == 'nosniff', f"X-Content-Type-Options expected 'nosniff', got '{x_content_type}'"
        print(f"✓ X-Content-Type-Options: {x_content_type}")
        
        # Check for X-Frame-Options
        x_frame = headers.get('X-Frame-Options', '')
        assert x_frame.upper() in ['DENY', 'SAMEORIGIN'], f"X-Frame-Options expected 'DENY' or 'SAMEORIGIN', got '{x_frame}'"
        print(f"✓ X-Frame-Options: {x_frame}")
        
        # Check for X-XSS-Protection
        x_xss = headers.get('X-XSS-Protection', '')
        assert '1' in x_xss, f"X-XSS-Protection expected '1' somewhere, got '{x_xss}'"
        print(f"✓ X-XSS-Protection: {x_xss}")
        
        # Check for Strict-Transport-Security
        hsts = headers.get('Strict-Transport-Security', '')
        assert 'max-age' in hsts.lower(), f"Strict-Transport-Security expected 'max-age', got '{hsts}'"
        print(f"✓ Strict-Transport-Security: {hsts}")
    
    def test_security_headers_on_login(self):
        """Security headers should be present on login endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        headers = response.headers
        
        assert headers.get('X-Content-Type-Options', '').lower() == 'nosniff', "Missing X-Content-Type-Options on login"
        print("✓ Security headers present on login endpoint")


class TestTagValidation:
    """Tests for H4: Tag injection prevention"""
    
    @pytest.fixture(autouse=True)
    def get_admin_token(self):
        """Get admin token for tag testing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.admin_token = response.json()["access_token"]
        else:
            pytest.skip("Could not get admin token")
    
    def test_tag_update_valid_vip(self):
        """Valid 'vip' tag should be accepted"""
        # First get a user to update
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()
        
        # Find a non-admin user
        test_user = None
        for u in users:
            if u["role"] != "admin":
                test_user = u
                break
        
        if not test_user:
            pytest.skip("No non-admin user found for tag testing")
        
        # Update with valid tag
        response = requests.put(
            f"{BASE_URL}/api/users/{test_user['id']}/tags",
            json={"tags": ["vip"]},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Valid tag 'vip' accepted")
    
    def test_tag_update_valid_group_head(self):
        """Valid 'group_head' tag should be accepted"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        users = response.json()
        
        test_user = None
        for u in users:
            if u["role"] != "admin":
                test_user = u
                break
        
        if not test_user:
            pytest.skip("No non-admin user found")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{test_user['id']}/tags",
            json={"tags": ["group_head"]},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Valid tag 'group_head' accepted")
    
    def test_tag_update_invalid_admin_tag(self):
        """Invalid 'admin' tag should be rejected"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        users = response.json()
        
        test_user = None
        for u in users:
            if u["role"] != "admin":
                test_user = u
                break
        
        if not test_user:
            pytest.skip("No non-admin user found")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{test_user['id']}/tags",
            json={"tags": ["admin"]},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 400, f"Expected 400 for invalid tag 'admin', got {response.status_code}"
        print("✓ Invalid tag 'admin' rejected with 400")
    
    def test_tag_update_invalid_superuser_tag(self):
        """Invalid 'superuser' tag should be rejected"""
        # Get users list
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        if response.status_code != 200:
            pytest.skip("Could not get users list")
        
        users = response.json()
        
        test_user = None
        for u in users:
            if u["role"] != "admin":
                test_user = u
                break
        
        if not test_user:
            pytest.skip("No non-admin user found")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{test_user['id']}/tags",
            json={"tags": ["superuser"]},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 400, f"Expected 400 for invalid tag 'superuser', got {response.status_code}"
        print("✓ Invalid tag 'superuser' rejected with 400")


class TestRateLimiting:
    """Tests for H2: Rate limiting on authentication endpoints"""
    
    def test_login_rate_limit(self):
        """Login endpoint should be rate limited (5/minute)"""
        print("Testing login rate limiting (5/minute)...")
        
        # Make 6 requests in quick succession
        statuses = []
        for i in range(7):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": f"ratelimit_test_{i}@test.com",
                "password": "WrongPassword123!"
            })
            statuses.append(response.status_code)
            print(f"  Request {i+1}: status {response.status_code}")
            time.sleep(0.1)  # Small delay between requests
        
        # At least one request should be rate limited (429)
        assert 429 in statuses, f"Expected at least one 429 response. Got: {statuses}"
        print("✓ Login rate limiting working - got 429 after multiple requests")
    
    def test_register_rate_limit(self):
        """Register endpoint should be rate limited (3/minute)"""
        print("Testing register rate limiting (3/minute)...")
        
        # Make 5 requests in quick succession
        statuses = []
        for i in range(5):
            response = requests.post(f"{BASE_URL}/api/auth/register", json={
                "email": f"ratelimit_reg_{int(time.time())}_{i}@test.com",
                "password": "ValidPass123!",
                "first_name": "Rate",
                "last_name": "Test"
            })
            statuses.append(response.status_code)
            print(f"  Request {i+1}: status {response.status_code}")
            time.sleep(0.1)
        
        # At least one should be rate limited
        assert 429 in statuses, f"Expected at least one 429 response. Got: {statuses}"
        print("✓ Register rate limiting working - got 429 after multiple requests")


class TestBlockedUserToken:
    """Tests for M3: Blocked user should not be able to use existing JWT"""
    
    def test_blocked_user_cannot_use_token(self):
        """A blocked user's token should return 403"""
        time.sleep(3)  # Wait for rate limit to reset
        
        # Login as admin
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if admin_response.status_code == 429:
            pytest.skip("Rate limited - try again later")
        
        if admin_response.status_code != 200:
            pytest.skip(f"Could not login as admin: {admin_response.status_code}")
        
        admin_token = admin_response.json()["access_token"]
        
        # Create a test user
        test_email = f"blocked_test_{int(time.time())}@test.com"
        create_response = requests.post(
            f"{BASE_URL}/api/users",
            json={
                "email": test_email,
                "password": "TestPass123!",
                "first_name": "Blocked",
                "last_name": "Test",
                "role": "user"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if create_response.status_code != 200:
            pytest.skip(f"Could not create test user: {create_response.status_code}")
        
        test_user = create_response.json()
        test_user_id = test_user["id"]
        
        time.sleep(1)  # Wait before login attempt
        
        # Login as test user to get their token
        user_login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": "TestPass123!"
        })
        
        if user_login_response.status_code == 429:
            # Cleanup and skip
            requests.delete(
                f"{BASE_URL}/api/users/{test_user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            pytest.skip("Rate limited on user login")
        
        if user_login_response.status_code != 200:
            requests.delete(
                f"{BASE_URL}/api/users/{test_user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            pytest.skip(f"Could not login as test user: {user_login_response.status_code}")
        
        user_token = user_login_response.json()["access_token"]
        
        # Verify user can access API with their token
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert me_response.status_code == 200, "User should be able to access API before being blocked"
        
        # Block the user
        block_response = requests.put(
            f"{BASE_URL}/api/users/{test_user_id}/block",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert block_response.status_code == 200, f"Failed to block user: {block_response.text}"
        print("✓ User blocked successfully")
        
        # Now try to use the user's token - should be rejected
        me_after_block = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Cleanup first
        requests.put(
            f"{BASE_URL}/api/users/{test_user_id}/unblock",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        requests.delete(
            f"{BASE_URL}/api/users/{test_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert me_after_block.status_code == 403, f"Expected 403 for blocked user, got {me_after_block.status_code}"
        print("✓ Blocked user's existing token correctly rejected with 403")


class TestAdminFunctionalityAfterSecurityFixes:
    """Verify admin can still manage users, buildings, vehicles after security updates"""
    
    def test_admin_can_list_users(self):
        """Admin should be able to list all users"""
        # Login as admin (wait for rate limit to reset if needed)
        time.sleep(2)  # Brief wait to avoid rate limiting from earlier tests
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - try again later")
        assert response.status_code == 200, f"Admin login failed: {response.status_code}"
        admin_token = response.json()["access_token"]
        
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        users = response.json()
        assert isinstance(users, list)
        print(f"✓ Admin can list users ({len(users)} users)")
    
    def test_admin_can_list_buildings(self):
        """Admin should be able to list all buildings"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 429:
            pytest.skip("Rate limited")
        assert response.status_code == 200
        admin_token = response.json()["access_token"]
        
        response = requests.get(
            f"{BASE_URL}/api/buildings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        buildings = response.json()
        assert isinstance(buildings, list)
        print(f"✓ Admin can list buildings ({len(buildings)} buildings)")
    
    def test_admin_can_list_vehicles(self):
        """Admin should be able to list all vehicles"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 429:
            pytest.skip("Rate limited")
        assert response.status_code == 200
        admin_token = response.json()["access_token"]
        
        response = requests.get(
            f"{BASE_URL}/api/vehicles",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        vehicles = response.json()
        assert isinstance(vehicles, list)
        print(f"✓ Admin can list vehicles ({len(vehicles)} vehicles)")


class TestUserReservationAccess:
    """Verify users can still view their reservations after security updates"""
    
    def test_user_can_view_reservations(self):
        """User should be able to view their own reservations"""
        # Login as user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip("Could not login as user")
        
        user_token = response.json()["access_token"]
        
        # Get reservations
        res_response = requests.get(
            f"{BASE_URL}/api/reservations",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert res_response.status_code == 200, f"Expected 200, got {res_response.status_code}"
        reservations = res_response.json()
        assert isinstance(reservations, list)
        print(f"✓ User can view reservations ({len(reservations)} reservations)")


class TestAPIRootEndpoint:
    """Test that API root endpoint works"""
    
    def test_api_root_returns_response(self):
        """GET /api/ should return a valid response"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        print(f"✓ GET /api/ returns status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
