"""
Test suite for M2 (HttpOnly Cookie Auth) and M4 (QR Code Token-based Lookup) security fixes.
Parking Reservation App - Cebuana Lhuillier

This tests:
- M2: JWT stored in HttpOnly cookie instead of localStorage
- M4: QR codes use token-based lookup instead of embedding PII
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASSWORD = "Test123!"


@pytest.fixture
def api_session():
    """Session without cookies"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestM2HttpOnlyCookieAuth:
    """Tests for M2: HttpOnly Cookie JWT Storage"""

    def test_login_sets_httponly_cookie(self, api_session):
        """POST /api/auth/login should set HttpOnly cookie with JWT token"""
        response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Check Set-Cookie header
        set_cookie_header = response.headers.get('Set-Cookie', '')
        print(f"Set-Cookie header: {set_cookie_header}")
        
        # Verify cookie contains HttpOnly flag
        assert 'access_token=' in set_cookie_header, "Cookie 'access_token' not set"
        assert 'httponly' in set_cookie_header.lower(), "HttpOnly flag not present in cookie"
        
        # Verify response still contains user data
        data = response.json()
        assert 'user' in data, "User data not in response"
        assert data['user']['email'] == USER_EMAIL

    def test_login_returns_user_data_in_response(self, api_session):
        """POST /api/auth/login should still return user data in JSON response body"""
        response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify user data structure
        assert 'user' in data
        user = data['user']
        assert user['email'] == ADMIN_EMAIL
        assert user['role'] == 'admin'
        assert 'first_name' in user
        assert 'last_name' in user
        assert 'id' in user

    def test_register_sets_httponly_cookie(self, api_session):
        """POST /api/auth/register should set HttpOnly cookie"""
        import uuid
        test_email = f"test_cookie_{uuid.uuid4().hex[:8]}@test.com"
        
        response = api_session.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "Cookie"
        })
        
        # Note: May get 429 due to rate limiting, skip if so
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping registration cookie test")
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        set_cookie_header = response.headers.get('Set-Cookie', '')
        assert 'access_token=' in set_cookie_header, "Cookie not set on registration"
        assert 'httponly' in set_cookie_header.lower(), "HttpOnly flag not present"
        
        # Cleanup - delete test user
        # (Would need admin auth for this)

    def test_cookie_auth_works_for_me_endpoint(self, api_session):
        """GET /api/auth/me should work with cookie authentication"""
        # First login to get cookie
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert login_response.status_code == 200
        
        # Now call /auth/me - cookie should be sent automatically by session
        me_response = api_session.get(f"{BASE_URL}/api/auth/me")
        
        assert me_response.status_code == 200, f"Auth/me failed: {me_response.text}"
        data = me_response.json()
        assert data['email'] == USER_EMAIL

    def test_logout_clears_cookie(self, api_session):
        """POST /api/auth/logout should clear the authentication cookie"""
        # First login
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert login_response.status_code == 200
        
        # Then logout
        logout_response = api_session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_response.status_code == 200
        
        # Check cookie is being cleared
        set_cookie_header = logout_response.headers.get('Set-Cookie', '')
        print(f"Logout Set-Cookie: {set_cookie_header}")
        
        # Cookie should be deleted (max-age=0 or expires in past)
        # After logout, /auth/me should fail
        me_response = api_session.get(f"{BASE_URL}/api/auth/me")
        # Should return 401 since cookie was cleared
        assert me_response.status_code == 401, f"Expected 401 after logout, got {me_response.status_code}"

    def test_cookie_auth_works_for_reservations(self, api_session):
        """GET /api/reservations should work with cookie auth"""
        # Login
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert login_response.status_code == 200
        
        # Access reservations
        res_response = api_session.get(f"{BASE_URL}/api/reservations")
        assert res_response.status_code == 200, f"Reservations failed: {res_response.text}"

    def test_cookie_auth_works_for_vehicles(self, api_session):
        """GET /api/vehicles should work with cookie auth"""
        # Login
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert login_response.status_code == 200
        
        # Access vehicles
        vehicles_response = api_session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_response.status_code == 200, f"Vehicles failed: {vehicles_response.text}"

    def test_cookie_has_secure_attributes(self, api_session):
        """Cookie should have proper security attributes (Secure, SameSite)"""
        response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        
        assert response.status_code == 200
        set_cookie_header = response.headers.get('Set-Cookie', '').lower()
        print(f"Cookie attributes: {set_cookie_header}")
        
        # Check for SameSite (should be lax or strict)
        assert 'samesite' in set_cookie_header, "SameSite attribute missing"
        
        # Secure flag should be present for HTTPS
        if BASE_URL.startswith('https'):
            assert 'secure' in set_cookie_header, "Secure flag missing for HTTPS"


class TestM4QRCodeTokenLookup:
    """Tests for M4: QR Code Token-based Lookup (no embedded PII)"""

    def test_qr_endpoint_returns_token(self, api_session):
        """GET /api/reservations/{id}/qr should return qr_token"""
        # Login
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert login_response.status_code == 200
        
        # Get reservations
        res_response = api_session.get(f"{BASE_URL}/api/reservations")
        assert res_response.status_code == 200
        
        reservations = res_response.json()
        
        if not reservations:
            pytest.skip("No reservations found for user - skipping QR test")
        
        # Get QR for first reservation
        reservation_id = reservations[0]['id']
        qr_response = api_session.get(f"{BASE_URL}/api/reservations/{reservation_id}/qr")
        
        assert qr_response.status_code == 200, f"QR endpoint failed: {qr_response.text}"
        qr_data = qr_response.json()
        
        # Verify response contains qr_token
        assert 'qr_token' in qr_data, "qr_token not in response"
        assert 'qr_code' in qr_data, "qr_code image not in response"
        assert 'reservation_id' in qr_data, "reservation_id not in response"
        
        # Verify qr_code is a base64 data URI
        assert qr_data['qr_code'].startswith('data:image/png;base64,'), "QR code should be base64 PNG"

    def test_scan_endpoint_returns_reservation_details(self, api_session):
        """GET /api/scan/{qr_token} should return reservation details"""
        # Login and get a reservation's QR token
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert login_response.status_code == 200
        
        res_response = api_session.get(f"{BASE_URL}/api/reservations")
        assert res_response.status_code == 200
        
        reservations = res_response.json()
        if not reservations:
            pytest.skip("No reservations found - skipping scan test")
        
        # Get QR token
        reservation_id = reservations[0]['id']
        qr_response = api_session.get(f"{BASE_URL}/api/reservations/{reservation_id}/qr")
        assert qr_response.status_code == 200
        
        qr_token = qr_response.json()['qr_token']
        
        # Now test the scan endpoint (public - no auth needed)
        scan_session = requests.Session()  # Fresh session without auth
        scan_response = scan_session.get(f"{BASE_URL}/api/scan/{qr_token}")
        
        assert scan_response.status_code == 200, f"Scan endpoint failed: {scan_response.text}"
        scan_data = scan_response.json()
        
        # Verify response contains expected fields
        assert 'reservation_id' in scan_data
        assert 'date' in scan_data
        assert 'start_time' in scan_data
        assert 'end_time' in scan_data
        assert 'status' in scan_data
        assert 'slot_label' in scan_data
        assert 'floor_label' in scan_data
        assert 'building_name' in scan_data
        assert 'vehicle_plate' in scan_data
        assert 'user_name' in scan_data
        
        print(f"Scan data: {scan_data}")

    def test_invalid_qr_token_returns_404(self, api_session):
        """GET /api/scan/{invalid_token} should return 404"""
        scan_response = api_session.get(f"{BASE_URL}/api/scan/invalid_token_12345")
        
        assert scan_response.status_code == 404, f"Expected 404, got {scan_response.status_code}"

    def test_qr_token_is_unique_per_reservation(self, api_session):
        """Each reservation should have a unique qr_token"""
        # Login as admin to see multiple reservations
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        
        # Get admin reservations
        res_response = api_session.get(f"{BASE_URL}/api/admin/reservations")
        assert res_response.status_code == 200
        
        reservations = res_response.json()
        if len(reservations) < 2:
            pytest.skip("Need at least 2 reservations to test uniqueness")
        
        # Get QR tokens for first two reservations
        qr_tokens = []
        for res in reservations[:2]:
            qr_response = api_session.get(f"{BASE_URL}/api/reservations/{res['id']}/qr")
            if qr_response.status_code == 200:
                qr_tokens.append(qr_response.json()['qr_token'])
        
        # Verify tokens are unique
        if len(qr_tokens) >= 2:
            assert qr_tokens[0] != qr_tokens[1], "QR tokens should be unique per reservation"

    def test_scan_endpoint_is_public(self):
        """Scan endpoint should be accessible without authentication"""
        # This test verifies the endpoint doesn't require auth
        session = requests.Session()  # No auth
        
        # Even with invalid token, we should get 404 not 401
        response = session.get(f"{BASE_URL}/api/scan/random_token_test")
        
        # Should be 404 (not found) not 401 (unauthorized)
        assert response.status_code == 404, f"Expected 404, got {response.status_code} - endpoint may require auth"


class TestCookieAuthAdminOperations:
    """Test that admin operations work with cookie auth"""

    def test_admin_can_list_users_with_cookie(self, api_session):
        """Admin should be able to list users with cookie auth"""
        # Login as admin
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        
        # List users
        users_response = api_session.get(f"{BASE_URL}/api/users")
        assert users_response.status_code == 200, f"Failed to list users: {users_response.text}"

    def test_admin_can_list_buildings_with_cookie(self, api_session):
        """Admin should be able to list buildings with cookie auth"""
        # Login as admin
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        
        # List buildings
        buildings_response = api_session.get(f"{BASE_URL}/api/buildings")
        assert buildings_response.status_code == 200


class TestAttendantCookieAuth:
    """Test attendant operations with cookie auth"""

    def test_attendant_can_access_daily_reservations(self, api_session):
        """Attendant should be able to access daily reservations with cookie auth"""
        # Login as attendant
        login_response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ATTENDANT_EMAIL,
            "password": ATTENDANT_PASSWORD
        })
        assert login_response.status_code == 200
        
        # Access daily reservations
        from datetime import date
        today = date.today().isoformat()
        res_response = api_session.get(f"{BASE_URL}/api/attendant/daily-reservations", params={"date": today})
        assert res_response.status_code == 200, f"Failed: {res_response.text}"
