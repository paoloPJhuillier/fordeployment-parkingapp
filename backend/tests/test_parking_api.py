"""
Comprehensive API Tests for Cebuana Lhuillier Parking Reservation System
Tests all critical endpoints: Auth, Vehicles, Buildings, Reservations, QR Codes
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://reserve-park-debug.preview.emergentagent.com')

# Test credentials from requirements
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASSWORD = "Test123!"

class TestAuthEndpoints:
    """Test authentication endpoints for all 3 roles"""
    
    def test_user_login_success(self):
        """Test user login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["role"] == "user"
        assert data["user"]["email"] == USER_EMAIL
        print(f"✓ User login successful: {data['user']['first_name']}")
    
    def test_admin_login_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['first_name']}")
    
    def test_attendant_login_success(self):
        """Test attendant login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ATTENDANT_EMAIL,
            "password": ATTENDANT_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "attendant"
        print(f"✓ Attendant login successful: {data['user']['first_name']}")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")
    
    def test_auth_me_endpoint(self):
        """Test /auth/me returns current user"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        token = login_resp.json()["access_token"]
        
        # Test /auth/me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == USER_EMAIL
        print("✓ /auth/me endpoint working correctly")


class TestVehicleManagement:
    """Test vehicle CRUD operations"""
    
    @pytest.fixture
    def user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_vehicles(self, user_token):
        """Test fetching user vehicles"""
        response = requests.get(f"{BASE_URL}/api/vehicles", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} vehicles")
    
    def test_create_and_delete_vehicle(self, user_token):
        """Test creating and deleting a vehicle"""
        # Create vehicle
        create_resp = requests.post(f"{BASE_URL}/api/vehicles", 
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "plate_number": "TEST123XYZ",
                "make": "Test Make",
                "model": "Test Model",
                "color": "Blue"
            }
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        vehicle_data = create_resp.json()
        assert vehicle_data["plate_number"] == "TEST123XYZ"
        vehicle_id = vehicle_data["id"]
        print(f"✓ Vehicle created with ID: {vehicle_id}")
        
        # Verify vehicle exists
        get_resp = requests.get(f"{BASE_URL}/api/vehicles", headers={
            "Authorization": f"Bearer {user_token}"
        })
        vehicles = get_resp.json()
        assert any(v["id"] == vehicle_id for v in vehicles)
        print("✓ Vehicle verified in list")
        
        # Delete vehicle
        delete_resp = requests.delete(f"{BASE_URL}/api/vehicles/{vehicle_id}", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert delete_resp.status_code == 200
        print("✓ Vehicle deleted successfully")


class TestBuildingManagement:
    """Test building and slot endpoints"""
    
    @pytest.fixture
    def user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_buildings(self, user_token):
        """Test fetching buildings"""
        response = requests.get(f"{BASE_URL}/api/buildings", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should have at least one building (Main Office)"
        
        # Check building structure
        building = data[0]
        assert "id" in building
        assert "name" in building
        assert "floors" in building
        print(f"✓ Retrieved {len(data)} buildings: {[b['name'] for b in data]}")
    
    def test_get_available_slots(self, user_token):
        """Test fetching available slots for a building"""
        # First get buildings
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", headers={
            "Authorization": f"Bearer {user_token}"
        })
        buildings = buildings_resp.json()
        assert len(buildings) > 0
        building_id = buildings[0]["id"]
        
        # Get available slots
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/api/slots/available", 
            headers={"Authorization": f"Bearer {user_token}"},
            params={"building_id": building_id, "date": today}
        )
        assert response.status_code == 200
        slots = response.json()
        assert isinstance(slots, list)
        
        # Verify slot structure
        if slots:
            slot = slots[0]
            assert "id" in slot
            assert "label" in slot
            assert "is_available" in slot
        print(f"✓ Retrieved {len(slots)} slots for building")


class TestReservationSystem:
    """Test reservation CRUD and QR code functionality"""
    
    @pytest.fixture
    def user_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    def test_get_reservations(self, user_auth):
        """Test fetching user reservations"""
        response = requests.get(f"{BASE_URL}/api/reservations", headers={
            "Authorization": f"Bearer {user_auth['token']}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} reservations")
        
        # Return reservation for QR test
        return data
    
    def test_qr_code_endpoint(self, user_auth):
        """Test QR code retrieval for existing reservation"""
        # Get reservations first
        reservations_resp = requests.get(f"{BASE_URL}/api/reservations", headers={
            "Authorization": f"Bearer {user_auth['token']}"
        })
        reservations = reservations_resp.json()
        
        if not reservations:
            pytest.skip("No reservations to test QR code")
        
        # Get QR for first reservation
        res_id = reservations[0]["id"]
        response = requests.get(f"{BASE_URL}/api/reservations/{res_id}/qr", headers={
            "Authorization": f"Bearer {user_auth['token']}"
        })
        assert response.status_code == 200, f"QR code fetch failed: {response.text}"
        data = response.json()
        assert "qr_code" in data
        assert data["qr_code"].startswith("data:image/png;base64,")
        print(f"✓ QR code retrieved successfully for reservation {res_id[:8]}...")
    
    def test_create_reservation_with_repeat_weeks(self, user_auth):
        """Test creating reservation with repeat_weeks parameter"""
        # Get a building and available slots
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", headers={
            "Authorization": f"Bearer {user_auth['token']}"
        })
        buildings = buildings_resp.json()
        if not buildings:
            pytest.skip("No buildings available")
        
        building = buildings[0]
        
        # Get available slots for a future date
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        slots_resp = requests.get(f"{BASE_URL}/api/slots/available",
            headers={"Authorization": f"Bearer {user_auth['token']}"},
            params={"building_id": building["id"], "date": future_date}
        )
        slots = slots_resp.json()
        available_slots = [s for s in slots if s.get("is_available")]
        
        if not available_slots:
            pytest.skip("No available slots for testing")
        
        # Get user vehicles
        vehicles_resp = requests.get(f"{BASE_URL}/api/vehicles", headers={
            "Authorization": f"Bearer {user_auth['token']}"
        })
        vehicles = vehicles_resp.json()
        
        if not vehicles:
            # Create a test vehicle
            create_vehicle = requests.post(f"{BASE_URL}/api/vehicles",
                headers={"Authorization": f"Bearer {user_auth['token']}"},
                json={"plate_number": "TESTREPEAT1", "make": "Test", "model": "Car"}
            )
            vehicle_id = create_vehicle.json()["id"]
        else:
            vehicle_id = vehicles[0]["id"]
        
        # Create reservation with repeat_weeks=2
        reservation_data = {
            "slot_id": available_slots[0]["id"],
            "vehicle_id": vehicle_id,
            "date": future_date,
            "start_time": "10:00",
            "end_time": "14:00",
            "booking_type": "weekly",
            "repeat_weeks": 2
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations",
            headers={"Authorization": f"Bearer {user_auth['token']}"},
            json=reservation_data
        )
        
        # Check response - might be single or multiple
        assert response.status_code == 200, f"Reservation failed: {response.text}"
        data = response.json()
        
        # If repeat created multiple reservations
        if "count" in data:
            assert data["count"] >= 1
            print(f"✓ Created {data['count']} repeat reservations")
            # Clean up - cancel created reservations
            for res in data.get("reservations", []):
                requests.put(f"{BASE_URL}/api/reservations/{res['id']}/cancel",
                    headers={"Authorization": f"Bearer {user_auth['token']}"})
        else:
            print("✓ Created single reservation (slot conflicts on repeat dates)")
            # Clean up
            if "id" in data:
                requests.put(f"{BASE_URL}/api/reservations/{data['id']}/cancel",
                    headers={"Authorization": f"Bearer {user_auth['token']}"})
    
    def test_cancel_reservation(self, user_auth):
        """Test canceling a reservation"""
        # Get existing reservations
        reservations_resp = requests.get(f"{BASE_URL}/api/reservations", headers={
            "Authorization": f"Bearer {user_auth['token']}"
        })
        reservations = reservations_resp.json()
        
        # Find a pending reservation to cancel
        pending = [r for r in reservations if r["status"] in ["pending", "confirmed"]]
        
        if not pending:
            pytest.skip("No pending reservations to test cancel")
        
        res_id = pending[0]["id"]
        response = requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel", headers={
            "Authorization": f"Bearer {user_auth['token']}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("reservation", {}).get("status") == "cancelled"
        print(f"✓ Reservation {res_id[:8]}... cancelled successfully")


class TestAttendantFeatures:
    """Test attendant-specific endpoints"""
    
    @pytest.fixture
    def attendant_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ATTENDANT_EMAIL,
            "password": ATTENDANT_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_daily_reservations(self, attendant_token):
        """Test attendant daily reservations endpoint"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/api/attendant/daily-reservations",
            headers={"Authorization": f"Bearer {attendant_token}"},
            params={"date": today}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Attendant retrieved {len(data)} daily reservations")
    
    def test_confirm_reservation_endpoint(self, attendant_token):
        """Test reservation confirmation endpoint exists"""
        # This just verifies the endpoint is accessible
        # Actual confirmation requires a valid pending reservation
        response = requests.post(f"{BASE_URL}/api/reservations/fake-id/confirm-with-photo",
            headers={"Authorization": f"Bearer {attendant_token}"},
            json={"photo": None}
        )
        # Should return 404 (not found) not 405 (method not allowed)
        assert response.status_code in [404, 400]
        print("✓ Confirm reservation endpoint accessible")


class TestAdminFeatures:
    """Test admin-specific endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_users_list(self, admin_token):
        """Test admin can fetch all users"""
        response = requests.get(f"{BASE_URL}/api/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least 3 test users
        print(f"✓ Admin retrieved {len(data)} users")
    
    def test_get_report_stats(self, admin_token):
        """Test admin reports/stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/reports/stats", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        print(f"✓ Admin stats: {data['summary']}")
    
    def test_parking_config_endpoint(self, admin_token):
        """Test parking config endpoint"""
        # Get buildings first
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        buildings = buildings_resp.json()
        if not buildings:
            pytest.skip("No buildings for config test")
        
        building_id = buildings[0]["id"]
        response = requests.get(f"{BASE_URL}/api/parking-config/{building_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "default_start_time" in data
        assert "default_end_time" in data
        print(f"✓ Parking config retrieved: {data['default_start_time']} - {data['default_end_time']}")


class TestAPIRoot:
    """Test API root endpoint"""
    
    def test_api_root(self):
        """Test API root returns version info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Cebuana" in data["message"]
        print(f"✓ API root: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
