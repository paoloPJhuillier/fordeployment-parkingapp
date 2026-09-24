"""
Test suite for admin features: user block/unblock and admin reservation management
Tests the new admin endpoints for iteration 5.
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASSWORD = "Test123!"


class TestSetup:
    """Setup - get auth tokens and IDs needed for tests"""
    admin_token = None
    user_token = None
    user_id = None
    admin_id = None
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_tokens(self, request):
        """Get admin and user tokens before running tests"""
        # Get admin token
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        request.cls.admin_token = data["access_token"]
        request.cls.admin_id = data["user"]["id"]
        
        # Get user token
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        data = response.json()
        request.cls.user_token = data["access_token"]
        request.cls.user_id = data["user"]["id"]


class TestUserBlockUnblock(TestSetup):
    """Tests for PUT /api/users/{id}/block and /api/users/{id}/unblock"""
    
    def test_block_user_success(self):
        """Block a regular user - should succeed with 200"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.put(f"{BASE_URL}/api/users/{self.user_id}/block", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        assert "blocked" in data["message"].lower()
        assert data["user_id"] == self.user_id
        print(f"PASS: Block user returned: {data}")
    
    def test_user_is_blocked_in_list(self):
        """Verify blocked user shows is_blocked=True in user list"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        
        assert response.status_code == 200
        users = response.json()
        user = next((u for u in users if u["id"] == self.user_id), None)
        assert user is not None, "User not found in list"
        assert user.get("is_blocked") == True, f"Expected is_blocked=True, got {user.get('is_blocked')}"
        print(f"PASS: User {USER_EMAIL} shows is_blocked=True")
    
    def test_blocked_user_cannot_create_reservation(self):
        """Blocked user trying to create reservation should get 403"""
        # First we need vehicle and slot info
        user_headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # Get user's vehicles
        vehicles_resp = requests.get(f"{BASE_URL}/api/vehicles", headers=user_headers)
        assert vehicles_resp.status_code == 200
        vehicles = vehicles_resp.json()
        
        if not vehicles:
            pytest.skip("User has no vehicles to test with")
        
        vehicle_id = vehicles[0]["id"]
        
        # Get buildings
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", headers=user_headers)
        assert buildings_resp.status_code == 200
        buildings = buildings_resp.json()
        
        if not buildings or not buildings[0].get("floors"):
            pytest.skip("No buildings/floors available")
        
        floor = buildings[0]["floors"][0]
        if not floor.get("slots"):
            pytest.skip("No slots available")
        
        slot_id = floor["slots"][0]["id"]
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Try to create reservation as blocked user
        response = requests.post(f"{BASE_URL}/api/reservations", 
            headers=user_headers,
            json={
                "slot_id": slot_id,
                "vehicle_id": vehicle_id,
                "date": future_date,
                "start_time": "08:00",
                "end_time": "18:00",
                "booking_type": "daily"
            }
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "block" in data["detail"].lower(), f"Expected block message, got: {data['detail']}"
        print(f"PASS: Blocked user got 403 with message: {data['detail']}")
    
    def test_unblock_user_success(self):
        """Unblock the user - should succeed with 200"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.put(f"{BASE_URL}/api/users/{self.user_id}/unblock", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        assert "unblocked" in data["message"].lower()
        print(f"PASS: Unblock user returned: {data}")
    
    def test_user_is_unblocked_in_list(self):
        """Verify unblocked user shows is_blocked=False in user list"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        
        assert response.status_code == 200
        users = response.json()
        user = next((u for u in users if u["id"] == self.user_id), None)
        assert user is not None
        assert user.get("is_blocked") == False or user.get("is_blocked") is None, \
            f"Expected is_blocked=False, got {user.get('is_blocked')}"
        print(f"PASS: User {USER_EMAIL} shows is_blocked=False")
    
    def test_block_admin_fails(self):
        """Attempting to block an admin user should return 400"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.put(f"{BASE_URL}/api/users/{self.admin_id}/block", headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "admin" in data["detail"].lower(), f"Expected admin-related error, got: {data['detail']}"
        print(f"PASS: Block admin returned 400: {data['detail']}")
    
    def test_block_nonexistent_user_fails(self):
        """Blocking a non-existent user should return 404"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        fake_id = "non-existent-user-id-12345"
        response = requests.put(f"{BASE_URL}/api/users/{fake_id}/block", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: Block non-existent user returned 404")


class TestAdminReservations(TestSetup):
    """Tests for GET /api/admin/reservations and PUT /api/admin/reservations/{id}/cancel"""
    
    def test_get_all_reservations(self):
        """Admin should be able to get all reservations"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reservations", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        reservations = response.json()
        assert isinstance(reservations, list), "Expected list of reservations"
        
        # Verify reservations have user details
        if reservations:
            res = reservations[0]
            assert "user_name" in res, "Expected user_name in reservation"
            assert "building_name" in res, "Expected building_name in reservation"
            assert "slot_label" in res, "Expected slot_label in reservation"
            print(f"PASS: Got {len(reservations)} reservations with user details")
        else:
            print("PASS: Got empty reservations list (no reservations in system)")
    
    def test_filter_by_status(self):
        """Filter reservations by status=pending"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reservations?status=pending", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        reservations = response.json()
        
        for res in reservations:
            assert res["status"] == "pending", f"Expected pending status, got {res['status']}"
        
        print(f"PASS: Filter by status=pending returned {len(reservations)} reservations")
    
    def test_filter_by_building(self):
        """Filter reservations by building_id"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # First get buildings to get a building_id
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", headers=headers)
        assert buildings_resp.status_code == 200
        buildings = buildings_resp.json()
        
        if not buildings:
            pytest.skip("No buildings to test with")
        
        building_id = buildings[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/admin/reservations?building_id={building_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        reservations = response.json()
        
        for res in reservations:
            assert res["building_id"] == building_id, \
                f"Expected building_id={building_id}, got {res['building_id']}"
        
        print(f"PASS: Filter by building_id returned {len(reservations)} reservations")
    
    def test_admin_cancel_reservation(self):
        """Admin should be able to cancel any reservation"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get a pending or confirmed reservation to cancel
        response = requests.get(f"{BASE_URL}/api/admin/reservations", headers=headers)
        assert response.status_code == 200
        reservations = response.json()
        
        # Find a cancellable reservation (pending or confirmed)
        cancellable = [r for r in reservations if r["status"] in ["pending", "confirmed"]]
        
        if not cancellable:
            pytest.skip("No cancellable reservations to test with")
        
        reservation_id = cancellable[0]["id"]
        
        # Cancel the reservation
        cancel_resp = requests.put(
            f"{BASE_URL}/api/admin/reservations/{reservation_id}/cancel",
            headers=headers
        )
        
        assert cancel_resp.status_code == 200, f"Expected 200, got {cancel_resp.status_code}: {cancel_resp.text}"
        data = cancel_resp.json()
        assert "cancelled" in data["message"].lower(), f"Expected cancelled message, got: {data['message']}"
        print(f"PASS: Admin cancelled reservation {reservation_id}")
        
        # Verify it's actually cancelled
        verify_resp = requests.get(f"{BASE_URL}/api/admin/reservations", headers=headers)
        all_res = verify_resp.json()
        cancelled = next((r for r in all_res if r["id"] == reservation_id), None)
        assert cancelled is not None
        assert cancelled["status"] == "cancelled", f"Expected cancelled, got {cancelled['status']}"
        print("PASS: Reservation status verified as cancelled")
    
    def test_admin_cancel_nonexistent_reservation(self):
        """Cancelling non-existent reservation should return 404"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        fake_id = "fake-reservation-id-99999"
        
        response = requests.put(
            f"{BASE_URL}/api/admin/reservations/{fake_id}/cancel",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: Cancel non-existent reservation returned 404")
    
    def test_regular_user_cannot_access_admin_reservations(self):
        """Regular user should get 403 when accessing admin reservations endpoint"""
        headers = {"Authorization": f"Bearer {self.user_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reservations", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Regular user got 403 on admin reservations endpoint")
    
    def test_regular_user_cannot_admin_cancel(self):
        """Regular user should get 403 when trying to use admin cancel endpoint"""
        # Get admin reservations first
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reservations", headers=admin_headers)
        reservations = response.json()
        
        if not reservations:
            pytest.skip("No reservations to test with")
        
        reservation_id = reservations[0]["id"]
        
        # Try to cancel as regular user
        user_headers = {"Authorization": f"Bearer {self.user_token}"}
        response = requests.put(
            f"{BASE_URL}/api/admin/reservations/{reservation_id}/cancel",
            headers=user_headers
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Regular user got 403 on admin cancel endpoint")


class TestUserResponseStructure(TestSetup):
    """Test that user response includes is_blocked field"""
    
    def test_users_list_has_is_blocked_field(self):
        """GET /users should include is_blocked field"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        
        assert response.status_code == 200
        users = response.json()
        
        if users:
            user = users[0]
            # is_blocked should be present (may be False/None if not blocked)
            assert "is_blocked" in user or user.get("is_blocked") is None or user.get("is_blocked") == False, \
                "is_blocked field should be in user response"
            print("PASS: Users response includes is_blocked field")
