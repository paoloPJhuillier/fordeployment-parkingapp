"""
Comprehensive regression tests for backend refactoring.
Tests all API endpoints to ensure the monolith-to-modular refactoring preserved functionality.
Uses a shared session to avoid rate limiting and maintain authentication state.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASSWORD = "Test123!"

# Global sessions to avoid rate limiting
admin_session = None
user_session = None
attendant_session = None


def get_admin_session():
    """Get or create admin session"""
    global admin_session
    if admin_session is None:
        admin_session = requests.Session()
        resp = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if resp.status_code != 200:
            pytest.fail(f"Admin login failed: {resp.status_code} - {resp.text}")
    return admin_session


def get_user_session():
    """Get or create user session"""
    global user_session
    if user_session is None:
        user_session = requests.Session()
        resp = user_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        if resp.status_code != 200:
            pytest.fail(f"User login failed: {resp.status_code} - {resp.text}")
    return user_session


def get_attendant_session():
    """Get or create attendant session"""
    global attendant_session
    if attendant_session is None:
        attendant_session = requests.Session()
        resp = attendant_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ATTENDANT_EMAIL,
            "password": ATTENDANT_PASSWORD
        })
        if resp.status_code != 200:
            pytest.fail(f"Attendant login failed: {resp.status_code} - {resp.text}")
    return attendant_session


class TestHealthAndRoot:
    """Health check and API root endpoints"""
    
    def test_api_root(self):
        """GET /api/ should return API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Cebuana" in data["message"]
        print("✓ API root endpoint working")


class TestAuthEndpoints:
    """Authentication related endpoints"""
    
    def test_01_login_admin_success(self):
        """POST /api/auth/login with admin credentials"""
        session = get_admin_session()
        # Session should already be authenticated
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        print("✓ Admin login and session verified")
    
    def test_02_login_user_success(self):
        """Verify user login works"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"
        print("✓ User login and session verified")
    
    def test_03_login_attendant_success(self):
        """Verify attendant login works"""
        session = get_attendant_session()
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "attendant"
        print("✓ Attendant login and session verified")
    
    def test_04_auth_me_returns_minimal_response(self):
        """GET /api/auth/me should return minimal response (no email/PII)"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        
        # VAPT fix: /me should NOT return email
        assert "email" not in data, "/api/auth/me should not return email (VAPT fix)"
        assert "id" in data
        assert "first_name" in data
        assert "role" in data
        print("✓ /api/auth/me returns minimal response (no PII)")
    
    def test_05_auth_me_unauthenticated(self):
        """GET /api/auth/me without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ Unauthenticated /me returns 401")


class TestUserEndpoints:
    """User management endpoints - Admin only"""
    
    def test_01_get_users(self):
        """GET /api/users should return user list"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify user structure
        user = data[0]
        assert "id" in user
        assert "email" in user
        assert "first_name" in user
        assert "role" in user
        print(f"✓ GET /api/users returns {len(data)} users")
    
    def test_02_create_and_delete_user(self):
        """POST /api/users and DELETE /api/users/{id}"""
        session = get_admin_session()
        test_email = f"TEST_user_{int(time.time())}@test.com"
        
        # Create user
        create_resp = session.post(f"{BASE_URL}/api/users", json={
            "email": test_email,
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
            "company": "Test Corp",
            "role": "user",
            "assigned_buildings": [],
            "main_building": None,
            "tags": []
        })
        assert create_resp.status_code == 200
        created_user = create_resp.json()
        assert created_user["email"] == test_email
        assert created_user["must_change_password"] == True
        user_id = created_user["id"]
        print(f"✓ Created user: {user_id}")
        
        # Delete user (cleanup)
        delete_resp = session.delete(f"{BASE_URL}/api/users/{user_id}")
        assert delete_resp.status_code == 200
        print("✓ Deleted test user")
    
    def test_03_block_unblock_user(self):
        """PUT /api/users/{id}/block and /unblock"""
        session = get_admin_session()
        
        # Get a non-admin user
        users_resp = session.get(f"{BASE_URL}/api/users")
        users = users_resp.json()
        non_admin = next((u for u in users if u["role"] != "admin"), None)
        
        if non_admin:
            user_id = non_admin["id"]
            
            # Block user
            block_resp = session.put(f"{BASE_URL}/api/users/{user_id}/block")
            assert block_resp.status_code == 200
            print(f"✓ Blocked user {user_id}")
            
            # Unblock user
            unblock_resp = session.put(f"{BASE_URL}/api/users/{user_id}/unblock")
            assert unblock_resp.status_code == 200
            print(f"✓ Unblocked user {user_id}")
        else:
            pytest.skip("No non-admin user to test block/unblock")
    
    def test_04_update_user_tags(self):
        """PUT /api/users/{id}/tags"""
        session = get_admin_session()
        
        users_resp = session.get(f"{BASE_URL}/api/users")
        users = users_resp.json()
        non_admin = next((u for u in users if u["role"] != "admin"), None)
        
        if non_admin:
            user_id = non_admin["id"]
            original_tags = non_admin.get("tags", [])
            
            # Update tags
            tags_resp = session.put(f"{BASE_URL}/api/users/{user_id}/tags", 
                json={"tags": ["vip"]})
            assert tags_resp.status_code == 200
            print("✓ Updated user tags")
            
            # Restore original tags
            session.put(f"{BASE_URL}/api/users/{user_id}/tags", 
                json={"tags": original_tags})
        else:
            pytest.skip("No non-admin user to test tags")


class TestAdminReservations:
    """Admin reservation management endpoints"""
    
    def test_get_admin_reservations(self):
        """GET /api/admin/reservations"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/admin/reservations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/admin/reservations returns {len(data)} reservations")


class TestVehicleEndpoints:
    """Vehicle CRUD endpoints"""
    
    def test_01_get_vehicles(self):
        """GET /api/vehicles"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/vehicles")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/vehicles returns {len(data)} vehicles")
    
    def test_02_create_and_delete_vehicle(self):
        """POST /api/vehicles and DELETE /api/vehicles/{id}"""
        session = get_user_session()
        plate = f"TEST{int(time.time()) % 10000}"
        
        # Create vehicle
        create_resp = session.post(f"{BASE_URL}/api/vehicles", json={
            "plate_number": plate,
            "make": "Toyota",
            "model": "Vios",
            "color": "White"
        })
        assert create_resp.status_code == 200
        vehicle = create_resp.json()
        assert vehicle["plate_number"] == plate.upper()
        vehicle_id = vehicle["id"]
        print(f"✓ Created vehicle: {plate}")
        
        # Delete vehicle
        delete_resp = session.delete(f"{BASE_URL}/api/vehicles/{vehicle_id}")
        assert delete_resp.status_code == 200
        print("✓ Deleted test vehicle")


class TestBuildingEndpoints:
    """Building, floor, slot management endpoints"""
    
    def test_01_get_buildings(self):
        """GET /api/buildings"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/buildings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            building = data[0]
            assert "id" in building
            assert "name" in building
            assert "floors" in building
        print(f"✓ GET /api/buildings returns {len(data)} buildings")
    
    def test_02_get_available_slots(self):
        """GET /api/slots/available"""
        session = get_admin_session()
        
        # Get buildings first
        buildings_resp = session.get(f"{BASE_URL}/api/buildings")
        buildings = buildings_resp.json()
        
        if buildings:
            building_id = buildings[0]["id"]
            today = time.strftime("%Y-%m-%d")
            
            response = session.get(
                f"{BASE_URL}/api/slots/available",
                params={"building_id": building_id, "date": today}
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"✓ GET /api/slots/available returns {len(data)} slots")
        else:
            pytest.skip("No buildings to test slots")


class TestReservationEndpoints:
    """Reservation CRUD and QR endpoints"""
    
    def test_01_get_reservations(self):
        """GET /api/reservations"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/reservations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/reservations returns {len(data)} reservations")
    
    def test_02_get_reservation_stats(self):
        """GET /api/reservations/stats"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/reservations/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "pending" in data
        assert "confirmed" in data
        print("✓ GET /api/reservations/stats returns user booking stats")


class TestZoneEndpoints:
    """Zone management endpoints - Admin only"""
    
    def test_01_get_zones(self):
        """GET /api/zones"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/zones")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/zones returns {len(data)} zones")
    
    def test_02_get_user_buildings(self):
        """GET /api/zones/user-buildings"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/zones/user-buildings")
        assert response.status_code == 200
        data = response.json()
        assert "building_ids" in data
        assert "zones" in data
        print("✓ GET /api/zones/user-buildings returns user building assignments")


class TestParkingConfigEndpoints:
    """Parking configuration endpoints"""
    
    def test_get_parking_config(self):
        """GET /api/parking-config/{building_id}"""
        session = get_admin_session()
        
        # Get a building first
        buildings_resp = session.get(f"{BASE_URL}/api/buildings")
        buildings = buildings_resp.json()
        
        if buildings:
            building_id = buildings[0]["id"]
            response = session.get(f"{BASE_URL}/api/parking-config/{building_id}")
            assert response.status_code == 200
            data = response.json()
            assert "release_time" in data
            assert "default_start_time" in data
            assert "booking_window_days" in data
            assert "no_show_release_enabled" in data
            print("✓ GET /api/parking-config returns config with no-show settings")
        else:
            pytest.skip("No buildings to test parking config")


class TestReportsEndpoints:
    """Reports and stats endpoints - Admin only"""
    
    def test_get_reports_stats(self):
        """GET /api/reports/stats"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/reports/stats")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "daily_breakdown" in data
        assert "building_breakdown" in data
        print("✓ GET /api/reports/stats returns comprehensive stats")


class TestAttendantEndpoints:
    """Attendant-specific endpoints"""
    
    def test_01_get_daily_reservations(self):
        """GET /api/attendant/daily-reservations"""
        session = get_attendant_session()
        response = session.get(f"{BASE_URL}/api/attendant/daily-reservations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/attendant/daily-reservations returns {len(data)} reservations")
    
    def test_02_get_attendant_buildings(self):
        """GET /api/attendant/buildings"""
        session = get_attendant_session()
        response = session.get(f"{BASE_URL}/api/attendant/buildings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/attendant/buildings returns {len(data)} buildings")


class TestNotificationEndpoints:
    """Notification endpoints"""
    
    def test_01_get_notifications(self):
        """GET /api/notifications"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/notifications returns {len(data)} notifications")
    
    def test_02_get_unread_count(self):
        """GET /api/notifications/unread-count"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"✓ GET /api/notifications/unread-count returns count: {data['count']}")
    
    def test_03_mark_all_read(self):
        """PUT /api/notifications/read-all"""
        session = get_user_session()
        response = session.put(f"{BASE_URL}/api/notifications/read-all")
        assert response.status_code == 200
        print("✓ PUT /api/notifications/read-all successful")


class TestTemplateEndpoints:
    """CSV template download endpoints - Admin only"""
    
    def test_01_get_users_template(self):
        """GET /api/templates/users"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/templates/users")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "email" in response.text
        print("✓ GET /api/templates/users returns CSV template")
    
    def test_02_get_buildings_template(self):
        """GET /api/templates/buildings"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/templates/buildings")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        print("✓ GET /api/templates/buildings returns CSV template")
    
    def test_03_get_zones_template(self):
        """GET /api/templates/zones"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/templates/zones")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        print("✓ GET /api/templates/zones returns CSV template")


class TestSiteContentEndpoints:
    """Site content CMS endpoints"""
    
    def test_01_get_site_content_public(self):
        """GET /api/site-content (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/site-content")
        assert response.status_code == 200
        data = response.json()
        assert "heading_line1" in data or "heading_highlight" in data
        print("✓ GET /api/site-content returns public content")
    
    def test_02_update_site_content_admin_only(self):
        """PUT /api/admin/site-content requires admin"""
        session = get_admin_session()
        response = session.put(f"{BASE_URL}/api/admin/site-content", 
            json={"announcement": ""})
        assert response.status_code == 200
        print("✓ PUT /api/admin/site-content successful for admin")


class TestAuthorizationGuards:
    """Test that endpoints properly require authentication/authorization"""
    
    def test_01_users_requires_admin(self):
        """GET /api/users should require admin role"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 403  # Forbidden for non-admin
        print("✓ GET /api/users properly requires admin role")
    
    def test_02_zones_requires_admin(self):
        """GET /api/zones should require admin role"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/zones")
        assert response.status_code == 403
        print("✓ GET /api/zones properly requires admin role")
    
    def test_03_reports_requires_admin(self):
        """GET /api/reports/stats should require admin role"""
        session = get_user_session()
        response = session.get(f"{BASE_URL}/api/reports/stats")
        assert response.status_code == 403
        print("✓ GET /api/reports/stats properly requires admin role")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
