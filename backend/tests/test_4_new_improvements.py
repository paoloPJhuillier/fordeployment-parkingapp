"""
Tests for 4 New Improvements (Rate-limit safe version):
1. Configurable start/end booking time per user (default_start_time, default_end_time)
2. Status label 'Reserved' instead of 'Pending' (frontend-only, backend keeps 'pending')
3. Remove/block parking slot in admin (PUT /api/slots/{id}/status?status=maintenance)
4. Buildings count tile shows only buildings within user's zone

Note: Uses module-scoped fixtures to minimize login calls and avoid rate limiting (5/min)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://reserve-park-debug.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASS = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASS = "Test123!"
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASS = "Test123!"

# Module-scoped sessions to avoid rate limiting
@pytest.fixture(scope="module")
def admin_session():
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return session

@pytest.fixture(scope="module")
def user_session():
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASS})
    assert resp.status_code == 200, f"User login failed: {resp.text}"
    return session


class TestUserBookingTimes:
    """Feature 1: Configurable start/end booking time per user"""
    
    def test_create_user_with_booking_times(self, admin_session):
        """POST /api/users should accept default_start_time and default_end_time fields"""
        import uuid
        test_email = f"test_booking_times_{uuid.uuid4().hex[:8]}@test.com"
        
        payload = {
            "email": test_email,
            "password": "Test123!",
            "first_name": "BookingTime",
            "last_name": "TestUser",
            "role": "user",
            "default_start_time": "09:00",
            "default_end_time": "17:00"
        }
        
        resp = admin_session.post(f"{BASE_URL}/api/users", json=payload)
        assert resp.status_code == 200 or resp.status_code == 201, f"Create user failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert data.get("default_start_time") == "09:00", f"Expected default_start_time '09:00', got {data.get('default_start_time')}"
        assert data.get("default_end_time") == "17:00", f"Expected default_end_time '17:00', got {data.get('default_end_time')}"
        
        # Cleanup
        user_id = data.get("id")
        if user_id:
            admin_session.delete(f"{BASE_URL}/api/users/{user_id}")
        
        print(f"✓ Create user with booking times works - {data.get('default_start_time')}/{data.get('default_end_time')}")
    
    def test_update_user_booking_times(self, admin_session):
        """PUT /api/users/{id} should update default_start_time and default_end_time"""
        # First get a user to update
        resp = admin_session.get(f"{BASE_URL}/api/users")
        assert resp.status_code == 200, f"Get users failed: {resp.text}"
        
        users = resp.json()
        # Find a non-admin user to update
        test_user = None
        for u in users:
            if u.get("role") == "user" and u.get("email") == USER_EMAIL:
                test_user = u
                break
        
        if not test_user:
            pytest.skip("No test user found to update")
        
        user_id = test_user["id"]
        
        # Update with new booking times
        update_payload = {
            "email": test_user["email"],
            "first_name": test_user["first_name"],
            "last_name": test_user["last_name"],
            "role": test_user["role"],
            "company": test_user.get("company"),
            "assigned_buildings": test_user.get("assigned_buildings", []),
            "main_building": test_user.get("main_building"),
            "tags": test_user.get("tags", []),
            "default_start_time": "07:30",
            "default_end_time": "16:30"
        }
        
        resp = admin_session.put(f"{BASE_URL}/api/users/{user_id}", json=update_payload)
        assert resp.status_code == 200, f"Update user failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert data.get("default_start_time") == "07:30", f"Expected '07:30', got {data.get('default_start_time')}"
        assert data.get("default_end_time") == "16:30", f"Expected '16:30', got {data.get('default_end_time')}"
        
        print(f"✓ Update user booking times works - {data.get('default_start_time')}/{data.get('default_end_time')}")
    
    def test_auth_me_returns_booking_times(self, user_session):
        """GET /api/auth/me should return default_start_time and default_end_time"""
        resp = user_session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200, f"Get /auth/me failed: {resp.text}"
        
        data = resp.json()
        # These fields should be present (even if null)
        assert "default_start_time" in data, f"default_start_time not in /auth/me response: {data}"
        assert "default_end_time" in data, f"default_end_time not in /auth/me response: {data}"
        
        print(f"✓ /auth/me returns booking times - start: {data.get('default_start_time')}, end: {data.get('default_end_time')}")
    
    def test_get_users_includes_booking_times(self, admin_session):
        """GET /api/users should include default_start_time and default_end_time"""
        resp = admin_session.get(f"{BASE_URL}/api/users")
        assert resp.status_code == 200, f"Get users failed: {resp.text}"
        
        users = resp.json()
        assert len(users) > 0, "No users returned"
        
        # Check first user has the fields
        first_user = users[0]
        assert "default_start_time" in first_user, f"default_start_time not in user response: {first_user.keys()}"
        assert "default_end_time" in first_user, f"default_end_time not in user response: {first_user.keys()}"
        
        print("✓ GET /api/users includes booking time fields")


class TestSlotManagement:
    """Feature 3: Remove/block parking slot in admin"""
    
    def get_test_slot(self, admin_session):
        """Get a slot ID for testing"""
        resp = admin_session.get(f"{BASE_URL}/api/buildings")
        assert resp.status_code == 200, f"Get buildings failed: {resp.text}"
        
        buildings = resp.json()
        for building in buildings:
            floors = building.get("floors", [])
            for floor in floors:
                slots = floor.get("slots", [])
                for slot in slots:
                    if slot.get("status") == "available":
                        return slot
        return None
    
    def test_block_slot_with_maintenance_status(self, admin_session):
        """PUT /api/slots/{id}/status?status=maintenance should block a slot"""
        slot = self.get_test_slot(admin_session)
        if not slot:
            pytest.skip("No available slot found for testing")
        
        slot_id = slot["id"]
        original_status = slot.get("status")
        
        # Block the slot
        resp = admin_session.put(f"{BASE_URL}/api/slots/{slot_id}/status?status=maintenance")
        assert resp.status_code == 200, f"Block slot failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert data.get("status") == "maintenance", f"Expected status 'maintenance', got {data.get('status')}"
        
        print(f"✓ Block slot works - slot {slot['label']} status changed to maintenance")
        
        # Restore the slot
        if original_status:
            admin_session.put(f"{BASE_URL}/api/slots/{slot_id}/status?status={original_status}")
    
    def test_unblock_slot_with_available_status(self, admin_session):
        """PUT /api/slots/{id}/status?status=available should unblock a slot"""
        slot = self.get_test_slot(admin_session)
        if not slot:
            pytest.skip("No available slot found for testing")
        
        slot_id = slot["id"]
        
        # First block it
        admin_session.put(f"{BASE_URL}/api/slots/{slot_id}/status?status=maintenance")
        
        # Now unblock it
        resp = admin_session.put(f"{BASE_URL}/api/slots/{slot_id}/status?status=available")
        assert resp.status_code == 200, f"Unblock slot failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert data.get("status") == "available", f"Expected status 'available', got {data.get('status')}"
        
        print(f"✓ Unblock slot works - slot {slot['label']} status changed to available")
    
    def test_invalid_status_rejected(self, admin_session):
        """PUT /api/slots/{id}/status with invalid status should return 400"""
        slot = self.get_test_slot(admin_session)
        if not slot:
            pytest.skip("No available slot found for testing")
        
        slot_id = slot["id"]
        
        resp = admin_session.put(f"{BASE_URL}/api/slots/{slot_id}/status?status=invalid_status")
        assert resp.status_code == 400, f"Expected 400 for invalid status, got {resp.status_code}"
        
        print("✓ Invalid slot status rejected with 400")
    
    def test_nonexistent_slot_returns_404(self, admin_session):
        """PUT /api/slots/{id}/status for non-existent slot should return 404"""
        fake_slot_id = "nonexistent-slot-id-12345"
        
        resp = admin_session.put(f"{BASE_URL}/api/slots/{fake_slot_id}/status?status=maintenance")
        assert resp.status_code == 404, f"Expected 404 for non-existent slot, got {resp.status_code}"
        
        print("✓ Non-existent slot returns 404")


class TestReservationsCRUD:
    """Verify existing reservation CRUD still works"""
    
    def test_get_user_reservations(self, user_session):
        """GET /api/reservations should work"""
        resp = user_session.get(f"{BASE_URL}/api/reservations")
        assert resp.status_code == 200, f"Get reservations failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ Get user reservations works - {len(data)} reservations")
    
    def test_get_reservation_stats(self, user_session):
        """GET /api/reservations/stats should work"""
        resp = user_session.get(f"{BASE_URL}/api/reservations/stats")
        assert resp.status_code == 200, f"Get stats failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert "total" in data, f"Expected 'total' in stats: {data}"
        print(f"✓ Get reservation stats works - total: {data.get('total')}")
    
    def test_admin_get_reservations(self, admin_session):
        """GET /api/admin/reservations should work"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/reservations")
        assert resp.status_code == 200, f"Admin get reservations failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ Admin get reservations works - {len(data)} reservations")


class TestZoneBuildingsEndpoint:
    """Feature 4: Test zones/user-buildings endpoint"""
    
    def test_get_user_buildings_endpoint(self, user_session):
        """GET /api/zones/user-buildings should work and return expected structure"""
        resp = user_session.get(f"{BASE_URL}/api/zones/user-buildings")
        # This endpoint may return empty data if user not in zones, which is OK
        assert resp.status_code == 200, f"Get user buildings failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert "building_ids" in data, f"Expected 'building_ids' in response: {data}"
        assert "zones" in data, f"Expected 'zones' in response: {data}"
        
        print(f"✓ GET /api/zones/user-buildings works - {len(data.get('building_ids', []))} buildings, {len(data.get('zones', []))} zones")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
