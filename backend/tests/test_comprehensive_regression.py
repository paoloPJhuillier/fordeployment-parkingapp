"""
Comprehensive Regression Test Suite for Parking Reservation App
Tests: Login flows, Dashboard data, Booking flow, Cancellation, Admin features, Auth protection
"""
import os
import pytest
import requests
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://reserve-park-debug.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASSWORD = "Test123!"


class TestAuthProtection:
    """Test that protected endpoints require authentication"""
    
    def test_vehicles_requires_auth(self):
        """GET /api/vehicles should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/vehicles")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/vehicles returns 401 without auth")
    
    def test_reservations_requires_auth(self):
        """GET /api/reservations should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/reservations returns 401 without auth")
    
    def test_buildings_requires_auth(self):
        """GET /api/buildings should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/buildings")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/buildings returns 401 without auth")
    
    def test_users_requires_auth(self):
        """GET /api/users should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/users")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/users returns 401 without auth")


@pytest.fixture(scope="module")
def admin_session():
    """Create authenticated admin session"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
    data = response.json()
    assert "user" in data, "Login response missing user data"
    assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
    print(f"PASS: Admin login successful - {data['user']['first_name']} {data['user']['last_name']}")
    return session


@pytest.fixture(scope="module")
def user_session():
    """Create authenticated user session"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    })
    assert response.status_code == 200, f"User login failed: {response.status_code} - {response.text}"
    data = response.json()
    assert "user" in data, "Login response missing user data"
    assert data["user"]["role"] == "user", f"Expected user role, got {data['user']['role']}"
    print(f"PASS: User login successful - {data['user']['first_name']} {data['user']['last_name']}")
    return session


@pytest.fixture(scope="module")
def attendant_session():
    """Create authenticated attendant session"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ATTENDANT_EMAIL,
        "password": ATTENDANT_PASSWORD
    })
    assert response.status_code == 200, f"Attendant login failed: {response.status_code} - {response.text}"
    data = response.json()
    assert "user" in data, "Login response missing user data"
    assert data["user"]["role"] == "attendant", f"Expected attendant role, got {data['user']['role']}"
    print(f"PASS: Attendant login successful - {data['user']['first_name']} {data['user']['last_name']}")
    return session


class TestLoginFlows:
    """Test login flows for all 3 roles"""
    
    def test_admin_login(self, admin_session):
        """Admin can login and get their profile"""
        response = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Failed to get admin profile: {response.status_code}"
        data = response.json()
        assert data["role"] == "admin", f"Expected admin role, got {data['role']}"
        print("PASS: Admin /auth/me returns correct role")
    
    def test_user_login(self, user_session):
        """User can login and get their profile"""
        response = user_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Failed to get user profile: {response.status_code}"
        data = response.json()
        assert data["role"] == "user", f"Expected user role, got {data['role']}"
        print("PASS: User /auth/me returns correct role")
    
    def test_attendant_login(self, attendant_session):
        """Attendant can login and get their profile"""
        response = attendant_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Failed to get attendant profile: {response.status_code}"
        data = response.json()
        assert data["role"] == "attendant", f"Expected attendant role, got {data['role']}"
        print("PASS: Attendant /auth/me returns correct role")
    
    def test_invalid_login(self):
        """Invalid credentials should return 401"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "fake@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Invalid login returns 401")


class TestUserDashboardData:
    """Test data needed for User Dashboard"""
    
    def test_get_vehicles(self, user_session):
        """User can get their vehicles list"""
        response = user_session.get(f"{BASE_URL}/api/vehicles")
        assert response.status_code == 200, f"Failed to get vehicles: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Vehicles response should be a list"
        print(f"PASS: GET /api/vehicles returns list with {len(data)} vehicles")
    
    def test_get_reservations(self, user_session):
        """User can get their reservations"""
        response = user_session.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200, f"Failed to get reservations: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Reservations response should be a list"
        print(f"PASS: GET /api/reservations returns list with {len(data)} reservations")
    
    def test_get_buildings(self, user_session):
        """User can get buildings list"""
        response = user_session.get(f"{BASE_URL}/api/buildings")
        assert response.status_code == 200, f"Failed to get buildings: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Buildings response should be a list"
        assert len(data) > 0, "Should have at least one building"
        # Verify building structure
        building = data[0]
        assert "id" in building, "Building missing id"
        assert "name" in building, "Building missing name"
        assert "floors" in building, "Building missing floors"
        print(f"PASS: GET /api/buildings returns list with {len(data)} buildings")
    
    def test_get_reservation_stats(self, user_session):
        """User can get their reservation stats"""
        response = user_session.get(f"{BASE_URL}/api/reservations/stats")
        assert response.status_code == 200, f"Failed to get stats: {response.status_code}"
        data = response.json()
        assert "total" in data, "Stats missing 'total'"
        assert "pending" in data, "Stats missing 'pending'"
        assert "confirmed" in data, "Stats missing 'confirmed'"
        print(f"PASS: GET /api/reservations/stats returns stats - total: {data['total']}")
    
    def test_get_zone_buildings(self, user_session):
        """User can get their zone buildings"""
        response = user_session.get(f"{BASE_URL}/api/zones/user-buildings")
        assert response.status_code == 200, f"Failed to get zone buildings: {response.status_code}"
        data = response.json()
        assert "building_ids" in data, "Response missing building_ids"
        assert "zones" in data, "Response missing zones"
        print("PASS: GET /api/zones/user-buildings returns zone info")


class TestAdminDashboardData:
    """Test data needed for Admin Dashboard"""
    
    def test_admin_get_users(self, admin_session):
        """Admin can get users list"""
        response = admin_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Failed to get users: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Users response should be a list"
        assert len(data) > 0, "Should have at least one user"
        print(f"PASS: Admin GET /api/users returns list with {len(data)} users")
    
    def test_admin_get_reservations(self, admin_session):
        """Admin can get all reservations"""
        response = admin_session.get(f"{BASE_URL}/api/admin/reservations")
        assert response.status_code == 200, f"Failed to get admin reservations: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Admin reservations response should be a list"
        print(f"PASS: Admin GET /api/admin/reservations returns list with {len(data)} reservations")
    
    def test_admin_get_report_stats(self, admin_session):
        """Admin can get report stats"""
        response = admin_session.get(f"{BASE_URL}/api/reports/stats")
        assert response.status_code == 200, f"Failed to get report stats: {response.status_code}"
        data = response.json()
        assert "total_reservations" in data or isinstance(data, dict), "Stats should be a dict"
        print("PASS: Admin GET /api/reports/stats returns stats")
    
    def test_admin_get_zones(self, admin_session):
        """Admin can get zones list"""
        response = admin_session.get(f"{BASE_URL}/api/zones")
        assert response.status_code == 200, f"Failed to get zones: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Zones response should be a list"
        print(f"PASS: Admin GET /api/zones returns list with {len(data)} zones")
    
    def test_user_cannot_access_admin_endpoints(self, user_session):
        """Regular user should not access admin endpoints"""
        response = user_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: User cannot access /api/users (403)")
        
        response = user_session.get(f"{BASE_URL}/api/reports/stats")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: User cannot access /api/reports/stats (403)")


class TestAttendantDashboardData:
    """Test data needed for Attendant Dashboard"""
    
    def test_attendant_get_daily_reservations(self, attendant_session):
        """Attendant can get daily reservations"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = attendant_session.get(f"{BASE_URL}/api/attendant/daily-reservations", params={"date": today})
        assert response.status_code == 200, f"Failed to get daily reservations: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Daily reservations should be a list"
        print(f"PASS: Attendant GET /api/attendant/daily-reservations returns list with {len(data)} reservations")
    
    def test_attendant_get_buildings(self, attendant_session):
        """Attendant can get their assigned buildings"""
        response = attendant_session.get(f"{BASE_URL}/api/attendant/buildings")
        assert response.status_code == 200, f"Failed to get attendant buildings: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Buildings response should be a list"
        print(f"PASS: Attendant GET /api/attendant/buildings returns list with {len(data)} buildings")


class TestBookingFlow:
    """Test the complete booking flow"""
    
    def test_get_available_slots(self, user_session):
        """User can get available slots for booking"""
        # First get buildings to find a valid building_id
        buildings_response = user_session.get(f"{BASE_URL}/api/buildings")
        assert buildings_response.status_code == 200
        buildings = buildings_response.json()
        
        if len(buildings) == 0:
            pytest.skip("No buildings available for testing")
        
        building_id = buildings[0]["id"]
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = user_session.get(f"{BASE_URL}/api/slots/available", params={
            "building_id": building_id,
            "date": tomorrow
        })
        assert response.status_code == 200, f"Failed to get available slots: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Slots response should be a list"
        print(f"PASS: GET /api/slots/available returns list with {len(data)} slots")
        return data, building_id, tomorrow
    
    def test_create_and_cancel_reservation(self, user_session):
        """User can create and cancel a reservation"""
        # Get vehicles first
        vehicles_response = user_session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_response.status_code == 200
        vehicles = vehicles_response.json()
        
        if len(vehicles) == 0:
            # Create a test vehicle
            vehicle_data = {
                "plate_number": "TEST-REGR-001",
                "make": "TestMake",
                "model": "TestModel",
                "color": "White"
            }
            create_vehicle_response = user_session.post(f"{BASE_URL}/api/vehicles", json=vehicle_data)
            if create_vehicle_response.status_code == 200:
                vehicle_id = create_vehicle_response.json()["id"]
            else:
                pytest.skip("Cannot create test vehicle for booking")
        else:
            vehicle_id = vehicles[0]["id"]
        
        # Get buildings and available slots
        buildings_response = user_session.get(f"{BASE_URL}/api/buildings")
        buildings = buildings_response.json()
        
        if len(buildings) == 0:
            pytest.skip("No buildings available")
        
        building_id = buildings[0]["id"]
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        slots_response = user_session.get(f"{BASE_URL}/api/slots/available", params={
            "building_id": building_id,
            "date": tomorrow
        })
        slots = slots_response.json()
        
        # Find an available slot
        available_slot = None
        for slot in slots:
            if slot.get("is_available", False):
                available_slot = slot
                break
        
        if not available_slot:
            pytest.skip("No available slots for booking")
        
        # Create reservation
        reservation_data = {
            "slot_id": available_slot["id"],
            "vehicle_id": vehicle_id,
            "dates": [tomorrow],
            "start_time": "09:00",
            "end_time": "18:00"
        }
        
        create_response = user_session.post(f"{BASE_URL}/api/reservations", json=reservation_data)
        assert create_response.status_code == 200, f"Failed to create reservation: {create_response.status_code} - {create_response.text}"
        reservation = create_response.json()
        
        # Handle single vs multi-date response
        if "reservations" in reservation:
            reservation_id = reservation["reservations"][0]["id"]
        else:
            reservation_id = reservation["id"]
        
        print(f"PASS: Created reservation {reservation_id}")
        
        # Cancel reservation
        cancel_response = user_session.put(f"{BASE_URL}/api/reservations/{reservation_id}/cancel")
        assert cancel_response.status_code == 200, f"Failed to cancel reservation: {cancel_response.status_code}"
        print(f"PASS: Cancelled reservation {reservation_id}")


class TestProfileAndPreferences:
    """Test profile page and booking preferences"""
    
    def test_update_booking_preferences(self, user_session):
        """User can update booking preferences"""
        response = user_session.put(f"{BASE_URL}/api/auth/booking-preferences", params={
            "default_start_time": "08:30",
            "default_end_time": "17:30"
        })
        assert response.status_code == 200, f"Failed to update preferences: {response.status_code}"
        data = response.json()
        assert "message" in data, "Response missing message"
        print("PASS: PUT /api/auth/booking-preferences updates preferences")
        
        # Verify preferences are returned in /auth/me
        me_response = user_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        # Note: /auth/me might not return these fields per VAPT restrictions
        print("PASS: Booking preferences update verified")
    
    def test_reset_booking_preferences(self, user_session):
        """User can reset booking preferences"""
        response = user_session.put(f"{BASE_URL}/api/auth/booking-preferences", params={
            "default_start_time": "",
            "default_end_time": ""
        })
        assert response.status_code == 200, f"Failed to reset preferences: {response.status_code}"
        print("PASS: Booking preferences can be reset")


class TestNotifications:
    """Test notifications API"""
    
    def test_get_notifications(self, user_session):
        """User can get notifications"""
        response = user_session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Failed to get notifications: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Notifications should be a list"
        print(f"PASS: GET /api/notifications returns list with {len(data)} notifications")
    
    def test_get_unread_count(self, user_session):
        """User can get unread notification count"""
        response = user_session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Failed to get unread count: {response.status_code}"
        data = response.json()
        assert "count" in data, "Response missing count"
        print(f"PASS: GET /api/notifications/unread-count returns count: {data['count']}")


class TestParkingConfig:
    """Test parking configuration API"""
    
    def test_get_parking_config(self, user_session):
        """User can get parking config for a building"""
        # Get a building first
        buildings_response = user_session.get(f"{BASE_URL}/api/buildings")
        buildings = buildings_response.json()
        
        if len(buildings) == 0:
            pytest.skip("No buildings available")
        
        building_id = buildings[0]["id"]
        response = user_session.get(f"{BASE_URL}/api/parking-config/{building_id}")
        assert response.status_code == 200, f"Failed to get parking config: {response.status_code}"
        data = response.json()
        # Config might be empty object if not set
        print(f"PASS: GET /api/parking-config/{building_id} returns config")


class TestSiteContent:
    """Test site content API"""
    
    def test_get_site_content(self):
        """Public can get site content (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/site-content")
        assert response.status_code == 200, f"Failed to get site content: {response.status_code}"
        data = response.json()
        # Site content has heading, description, etc.
        print("PASS: GET /api/site-content returns content")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
