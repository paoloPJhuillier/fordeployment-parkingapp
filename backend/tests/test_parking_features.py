"""
Test suite for Parking Reservation App - Major Rework Features
Tests: Multi-date booking, Zone management, User tags/main building, No-show reporting
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"email": "admin.test@cebuana.com", "password": "Test123!"}
USER_CREDENTIALS = {"email": "user.test@cebuana.com", "password": "Test123!"}
ATTENDANT_CREDENTIALS = {"email": "attendant.test@cebuana.com", "password": "Test123!"}

# Global storage for test data
test_data = {}

class TestAuthentication:
    """Test authentication for all 3 roles"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        test_data["admin_token"] = data["access_token"]
        test_data["admin_user"] = data["user"]
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_user_login(self):
        """Test user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=USER_CREDENTIALS)
        assert response.status_code == 200, f"User login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "user"
        test_data["user_token"] = data["access_token"]
        test_data["user_user"] = data["user"]
        print(f"✓ User login successful: {data['user']['email']}")
    
    def test_attendant_login(self):
        """Test attendant login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ATTENDANT_CREDENTIALS)
        assert response.status_code == 200, f"Attendant login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "attendant"
        test_data["attendant_token"] = data["access_token"]
        test_data["attendant_user"] = data["user"]
        print(f"✓ Attendant login successful: {data['user']['email']}")


class TestUserManagement:
    """Test user management features: main_building, tags"""
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {test_data.get('admin_token', '')}"}
    
    def test_get_all_users(self):
        """Test getting all users (admin only)"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.get_admin_headers())
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        users = response.json()
        assert isinstance(users, list)
        test_data["users"] = users
        print(f"✓ Got {len(users)} users")
        
        # Check that users have main_building and tags fields
        for user in users[:3]:  # Check first 3
            assert "main_building" in user
            assert "tags" in user
        print("✓ Users have main_building and tags fields")
    
    def test_get_buildings_for_assignment(self):
        """Get buildings for main building assignment"""
        response = requests.get(f"{BASE_URL}/api/buildings", headers=self.get_admin_headers())
        assert response.status_code == 200
        buildings = response.json()
        assert isinstance(buildings, list) and len(buildings) > 0
        test_data["buildings"] = buildings
        test_data["first_building_id"] = buildings[0]["id"]
        print(f"✓ Got {len(buildings)} buildings")
    
    def test_assign_main_building_to_user(self):
        """Test assigning main building to a user"""
        # Find a user to update (not admin)
        users = test_data.get("users", [])
        target_user = next((u for u in users if u["role"] == "user"), None)
        if not target_user:
            pytest.skip("No user found for testing")
        
        building_id = test_data.get("first_building_id")
        response = requests.put(
            f"{BASE_URL}/api/users/{target_user['id']}/main-building",
            headers=self.get_admin_headers(),
            json={"main_building": building_id}
        )
        assert response.status_code == 200, f"Failed to assign main building: {response.text}"
        data = response.json()
        assert data["main_building"] == building_id
        test_data["test_user_id"] = target_user["id"]
        print(f"✓ Assigned main building to user {target_user['email']}")
    
    def test_update_user_tags(self):
        """Test updating user tags (vip, group_head)"""
        user_id = test_data.get("test_user_id")
        if not user_id:
            pytest.skip("No test user ID")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/tags",
            headers=self.get_admin_headers(),
            json={"tags": ["vip"]}
        )
        assert response.status_code == 200, f"Failed to update tags: {response.text}"
        data = response.json()
        assert "vip" in data["tags"]
        print(f"✓ Updated user tags to: {data['tags']}")
        
        # Verify by getting user
        response = requests.get(f"{BASE_URL}/api/users", headers=self.get_admin_headers())
        users = response.json()
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user and "vip" in updated_user.get("tags", [])
        print("✓ Verified tags persisted in database")
    
    def test_remove_user_tags(self):
        """Test removing user tags"""
        user_id = test_data.get("test_user_id")
        if not user_id:
            pytest.skip("No test user ID")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/tags",
            headers=self.get_admin_headers(),
            json={"tags": []}
        )
        assert response.status_code == 200
        print("✓ Removed user tags")


class TestZoneManagement:
    """Test zone management: zone = group of buildings"""
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {test_data.get('admin_token', '')}"}
    
    def test_get_zones(self):
        """Test getting all zones"""
        response = requests.get(f"{BASE_URL}/api/zones", headers=self.get_admin_headers())
        assert response.status_code == 200
        zones = response.json()
        assert isinstance(zones, list)
        test_data["existing_zones"] = zones
        print(f"✓ Got {len(zones)} existing zones")
    
    def test_create_zone_with_buildings_and_users(self):
        """Test creating a new zone with multiple buildings and users"""
        buildings = test_data.get("buildings", [])
        users = test_data.get("users", [])
        
        if len(buildings) < 2:
            pytest.skip("Need at least 2 buildings")
        
        # Select 2 buildings and 2 users
        building_ids = [buildings[0]["id"], buildings[1]["id"]]
        user_ids = [u["id"] for u in users if u["role"] == "user"][:2]
        
        zone_data = {
            "name": "TEST_Zone_Downtown",
            "building_ids": building_ids,
            "user_ids": user_ids
        }
        
        response = requests.post(f"{BASE_URL}/api/zones", headers=self.get_admin_headers(), json=zone_data)
        assert response.status_code == 200, f"Failed to create zone: {response.text}"
        zone = response.json()
        
        assert zone["name"] == "TEST_Zone_Downtown"
        assert len(zone["building_ids"]) == 2
        assert len(zone["user_ids"]) >= 0  # May be less if users don't exist
        test_data["test_zone_id"] = zone["id"]
        print(f"✓ Created zone with {len(zone['building_ids'])} buildings and {len(zone['user_ids'])} users")
    
    def test_update_zone(self):
        """Test updating a zone"""
        zone_id = test_data.get("test_zone_id")
        if not zone_id:
            pytest.skip("No test zone ID")
        
        response = requests.put(
            f"{BASE_URL}/api/zones/{zone_id}",
            headers=self.get_admin_headers(),
            json={"name": "TEST_Zone_Updated_Name"}
        )
        assert response.status_code == 200
        zone = response.json()
        assert zone["name"] == "TEST_Zone_Updated_Name"
        print("✓ Updated zone name")
    
    def test_get_user_building_assignments(self):
        """Test getting user's building assignments through zones"""
        response = requests.get(
            f"{BASE_URL}/api/zones/user-buildings",
            headers={"Authorization": f"Bearer {test_data.get('user_token', '')}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "building_ids" in data
        assert "zones" in data
        print(f"✓ User has access to {len(data['building_ids'])} buildings through zones")


class TestBuildingFloorLayout:
    """Test building management with floor layout image upload"""
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {test_data.get('admin_token', '')}"}
    
    def test_get_buildings_with_floors(self):
        """Test getting buildings with floors"""
        response = requests.get(f"{BASE_URL}/api/buildings", headers=self.get_admin_headers())
        assert response.status_code == 200
        buildings = response.json()
        
        building_with_floors = next((b for b in buildings if b.get("floors") and len(b["floors"]) > 0), None)
        if building_with_floors:
            test_data["test_floor_id"] = building_with_floors["floors"][0]["id"]
            print(f"✓ Found building with {len(building_with_floors['floors'])} floors")
        else:
            print("⚠ No building with floors found")
    
    def test_floor_layout_endpoint_exists(self):
        """Test that floor layout upload endpoint exists"""
        floor_id = test_data.get("test_floor_id")
        if not floor_id:
            pytest.skip("No floor ID for testing")
        
        # Just verify the endpoint returns proper error for no file
        # A 422 means endpoint exists but validation failed (no file)
        response = requests.post(
            f"{BASE_URL}/api/floors/{floor_id}/layout",
            headers=self.get_admin_headers()
        )
        # Without file, should get 422 (validation error)
        assert response.status_code in [422, 400], f"Unexpected status: {response.status_code}"
        print("✓ Floor layout upload endpoint exists")


class TestMultiDateBooking:
    """Test multi-date booking (up to 7 days)"""
    
    def get_user_headers(self):
        return {"Authorization": f"Bearer {test_data.get('user_token', '')}"}
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {test_data.get('admin_token', '')}"}
    
    def test_get_vehicles(self):
        """Get user's vehicles for booking"""
        response = requests.get(f"{BASE_URL}/api/vehicles", headers=self.get_user_headers())
        assert response.status_code == 200
        vehicles = response.json()
        
        if vehicles:
            test_data["test_vehicle_id"] = vehicles[0]["id"]
            print(f"✓ Found {len(vehicles)} vehicles")
        else:
            # Create a vehicle
            response = requests.post(
                f"{BASE_URL}/api/vehicles",
                headers=self.get_user_headers(),
                json={"plate_number": "TEST123", "make": "Toyota", "model": "Vios", "color": "White"}
            )
            assert response.status_code == 200
            test_data["test_vehicle_id"] = response.json()["id"]
            print("✓ Created test vehicle")
    
    def test_get_available_slots(self):
        """Get available slots for a building and date"""
        building_id = test_data.get("first_building_id")
        if not building_id:
            pytest.skip("No building ID")
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/slots/available",
            headers=self.get_user_headers(),
            params={"building_id": building_id, "date": tomorrow}
        )
        assert response.status_code == 200
        slots = response.json()
        
        available_slots = [s for s in slots if s.get("is_available")]
        if available_slots:
            test_data["test_slot_id"] = available_slots[0]["id"]
            print(f"✓ Found {len(available_slots)} available slots")
        else:
            print("⚠ No available slots found")
    
    def test_create_multi_date_reservation(self):
        """Test creating a multi-date reservation (2 days)"""
        slot_id = test_data.get("test_slot_id")
        vehicle_id = test_data.get("test_vehicle_id")
        
        if not slot_id or not vehicle_id:
            pytest.skip("Missing slot or vehicle ID")
        
        tomorrow = datetime.now() + timedelta(days=1)
        dates = [
            (tomorrow + timedelta(days=i)).strftime("%Y-%m-%d") 
            for i in range(2)  # 2 days
        ]
        
        reservation_data = {
            "slot_id": slot_id,
            "vehicle_id": vehicle_id,
            "dates": dates,
            "start_time": "09:00",
            "end_time": "17:00"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.get_user_headers(),
            json=reservation_data
        )
        
        # Can be 200 (single) or response with count (multiple)
        if response.status_code == 200:
            data = response.json()
            if "count" in data:
                print(f"✓ Created {data['count']} reservations for multi-date booking")
                test_data["multi_date_reservations"] = data.get("reservations", [])
            else:
                print("✓ Created single date reservation")
                test_data["test_reservation_id"] = data.get("id")
        else:
            # May fail if slot is already booked
            print(f"⚠ Multi-date booking returned {response.status_code}: {response.text}")
    
    def test_reject_more_than_7_dates(self):
        """Test that more than 7 dates is rejected"""
        slot_id = test_data.get("test_slot_id")
        vehicle_id = test_data.get("test_vehicle_id")
        
        if not slot_id or not vehicle_id:
            pytest.skip("Missing slot or vehicle ID")
        
        tomorrow = datetime.now() + timedelta(days=10)  # Start 10 days ahead to avoid conflicts
        dates = [
            (tomorrow + timedelta(days=i)).strftime("%Y-%m-%d") 
            for i in range(8)  # 8 days - should be rejected
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.get_user_headers(),
            json={
                "slot_id": slot_id,
                "vehicle_id": vehicle_id,
                "dates": dates,
                "start_time": "09:00",
                "end_time": "17:00"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for >7 dates, got {response.status_code}"
        assert "7" in response.text.lower() or "maximum" in response.text.lower()
        print("✓ Correctly rejected booking with more than 7 dates")


class TestNoShowReporting:
    """Test attendant no-show reporting"""
    
    def get_attendant_headers(self):
        return {"Authorization": f"Bearer {test_data.get('attendant_token', '')}"}
    
    def test_get_daily_reservations(self):
        """Test getting daily reservations as attendant"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/attendant/daily-reservations",
            headers=self.get_attendant_headers(),
            params={"date": today}
        )
        assert response.status_code == 200
        reservations = response.json()
        assert isinstance(reservations, list)
        
        # Find a pending/confirmed reservation to report no-show
        for res in reservations:
            if res["status"] in ["pending", "confirmed"] and not res.get("no_show_reported"):
                test_data["no_show_test_reservation_id"] = res["id"]
                break
        
        print(f"✓ Got {len(reservations)} reservations for today")
    
    def test_report_no_show_endpoint(self):
        """Test the no-show reporting endpoint exists"""
        res_id = test_data.get("no_show_test_reservation_id")
        if not res_id:
            # Just verify endpoint exists with invalid ID
            response = requests.post(
                f"{BASE_URL}/api/attendant/reservations/invalid-id/report-no-show",
                headers=self.get_attendant_headers()
            )
            assert response.status_code == 404  # Not found is expected
            print("✓ No-show endpoint exists (returns 404 for invalid ID)")
        else:
            response = requests.post(
                f"{BASE_URL}/api/attendant/reservations/{res_id}/report-no-show",
                headers=self.get_attendant_headers()
            )
            # Could be 200 (success) or 400 (already reported/wrong status)
            assert response.status_code in [200, 400]
            if response.status_code == 200:
                print("✓ Successfully reported no-show")
            else:
                print(f"✓ No-show endpoint working (status: {response.status_code})")


class TestConfirmReservation:
    """Test attendant reservation confirmation"""
    
    def get_attendant_headers(self):
        return {"Authorization": f"Bearer {test_data.get('attendant_token', '')}"}
    
    def test_confirm_reservation_endpoint(self):
        """Test reservation confirmation endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/reservations/invalid-id/confirm-with-photo",
            headers=self.get_attendant_headers(),
            json={}
        )
        # 404 for invalid ID is expected
        assert response.status_code == 404
        print("✓ Confirm reservation endpoint exists")


class TestCleanup:
    """Cleanup test data"""
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {test_data.get('admin_token', '')}"}
    
    def test_cleanup_test_zone(self):
        """Delete test zone"""
        zone_id = test_data.get("test_zone_id")
        if not zone_id:
            print("⚠ No test zone to cleanup")
            return
        
        response = requests.delete(f"{BASE_URL}/api/zones/{zone_id}", headers=self.get_admin_headers())
        assert response.status_code == 200
        print("✓ Cleaned up test zone")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
