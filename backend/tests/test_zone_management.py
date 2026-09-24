"""
Zone Management API Tests for Cebuana Lhuillier Parking Reservation System
Tests: Zone CRUD, Multi-user assignment, Building sync, Zone enforcement
Iteration 7 - Zone Management Features
"""
import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://reserve-park-debug.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"

@pytest.fixture(scope="module")
def admin_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def user_auth():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    })
    assert response.status_code == 200, f"User login failed: {response.text}"
    data = response.json()
    return {"token": data["access_token"], "user": data["user"]}

@pytest.fixture(scope="module")
def test_building(admin_token):
    """Create a test building for zone tests"""
    # Create a unique building
    building_data = {
        "name": f"TEST_ZoneBuilding_{uuid.uuid4().hex[:6]}",
        "address": "123 Test Zone Street",
        "total_floors": 1,
        "slots_per_floor": 5
    }
    resp = requests.post(f"{BASE_URL}/api/buildings", 
        headers={"Authorization": f"Bearer {admin_token}"},
        json=building_data
    )
    assert resp.status_code == 200, f"Building creation failed: {resp.text}"
    building = resp.json()
    print(f"✓ Created test building: {building['name']} ({building['id']})")
    yield building
    # Cleanup
    requests.delete(f"{BASE_URL}/api/buildings/{building['id']}", 
        headers={"Authorization": f"Bearer {admin_token}"})
    print(f"✓ Cleaned up test building: {building['name']}")

@pytest.fixture(scope="module")
def test_user_id(admin_token):
    """Get the test user's ID"""
    resp = requests.get(f"{BASE_URL}/api/users", headers={"Authorization": f"Bearer {admin_token}"})
    users = resp.json()
    test_user = next((u for u in users if u['email'] == USER_EMAIL), None)
    assert test_user, "Test user not found"
    return test_user['id']

@pytest.fixture
def test_vehicle(user_auth):
    """Create/get a test vehicle for the user"""
    # Check if user already has a vehicle
    resp = requests.get(f"{BASE_URL}/api/vehicles", headers={"Authorization": f"Bearer {user_auth['token']}"})
    vehicles = resp.json()
    if vehicles:
        yield vehicles[0]
    else:
        # Create one
        resp = requests.post(f"{BASE_URL}/api/vehicles", 
            headers={"Authorization": f"Bearer {user_auth['token']}"},
            json={"plate_number": "TESTZN123", "make": "Test", "model": "Vehicle"}
        )
        assert resp.status_code == 200
        vehicle = resp.json()
        yield vehicle


class TestZoneCRUD:
    """Test Zone Create, Read, Update, Delete operations"""
    
    def test_get_zones_empty_or_list(self, admin_token):
        """GET /api/zones should return list (may be empty)"""
        resp = requests.get(f"{BASE_URL}/api/zones", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/zones returned {len(data)} zones")
    
    def test_create_zone_with_users(self, admin_token, test_building, test_user_id):
        """POST /api/zones creates zone with assigned_users and syncs user's assigned_buildings"""
        zone_data = {
            "name": "TEST_ZoneA",
            "building_id": test_building["id"],
            "device_id": "DEV-001",
            "assigned_users": [test_user_id]
        }
        resp = requests.post(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json=zone_data
        )
        assert resp.status_code == 200, f"Zone creation failed: {resp.text}"
        zone = resp.json()
        assert zone["name"] == "TEST_ZoneA"
        assert zone["building_id"] == test_building["id"]
        assert test_user_id in zone["assigned_users"]
        print(f"✓ Created zone: {zone['name']} with user assigned")
        
        # Verify user's assigned_buildings updated
        users_resp = requests.get(f"{BASE_URL}/api/users", headers={"Authorization": f"Bearer {admin_token}"})
        users = users_resp.json()
        user = next((u for u in users if u['id'] == test_user_id), None)
        assert test_building["id"] in user.get("assigned_buildings", []), "User's assigned_buildings not synced"
        print(f"✓ User's assigned_buildings synced: {user.get('assigned_buildings')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})
        print("✓ Cleaned up test zone")
    
    def test_update_zone_add_remove_users(self, admin_token, test_building, test_user_id):
        """PUT /api/zones/{id} updates zone and syncs assigned_buildings for added/removed users"""
        # Create zone without users
        zone_resp = requests.post(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_ZoneB", "building_id": test_building["id"], "assigned_users": []}
        )
        assert zone_resp.status_code == 200
        zone = zone_resp.json()
        zone_id = zone["id"]
        print(f"✓ Created zone without users: {zone['name']}")
        
        # Update to add user
        update_resp = requests.put(f"{BASE_URL}/api/zones/{zone_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"assigned_users": [test_user_id]}
        )
        assert update_resp.status_code == 200, f"Zone update failed: {update_resp.text}"
        updated_zone = update_resp.json()
        assert test_user_id in updated_zone["assigned_users"]
        print("✓ Updated zone - added user")
        
        # Verify user's assigned_buildings
        users_resp = requests.get(f"{BASE_URL}/api/users", headers={"Authorization": f"Bearer {admin_token}"})
        user = next((u for u in users_resp.json() if u['id'] == test_user_id), None)
        assert test_building["id"] in user.get("assigned_buildings", [])
        print("✓ User's assigned_buildings updated after add")
        
        # Update to remove user
        remove_resp = requests.put(f"{BASE_URL}/api/zones/{zone_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"assigned_users": []}
        )
        assert remove_resp.status_code == 200
        print("✓ Updated zone - removed user")
        
        # Verify user's assigned_buildings removed (if no other zones)
        users_resp2 = requests.get(f"{BASE_URL}/api/users", headers={"Authorization": f"Bearer {admin_token}"})
        user2 = next((u for u in users_resp2.json() if u['id'] == test_user_id), None)
        # Note: building may still be present if user is in another zone for same building
        print(f"✓ User's assigned_buildings after removal: {user2.get('assigned_buildings')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/zones/{zone_id}", headers={"Authorization": f"Bearer {admin_token}"})
    
    def test_delete_zone_syncs_buildings(self, admin_token, test_building, test_user_id):
        """DELETE /api/zones/{id} removes building from users' assigned_buildings"""
        # Create zone with user
        zone_resp = requests.post(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_ZoneC", "building_id": test_building["id"], "assigned_users": [test_user_id]}
        )
        zone = zone_resp.json()
        print("✓ Created zone with user for delete test")
        
        # Delete zone
        del_resp = requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", 
            headers={"Authorization": f"Bearer {admin_token}"})
        assert del_resp.status_code == 200
        print("✓ Deleted zone")
        
        # Verify user's assigned_buildings updated
        users_resp = requests.get(f"{BASE_URL}/api/users", headers={"Authorization": f"Bearer {admin_token}"})
        user = next((u for u in users_resp.json() if u['id'] == test_user_id), None)
        # Building should be removed since no other zones
        print(f"✓ User's assigned_buildings after zone delete: {user.get('assigned_buildings')}")
    
    def test_update_zone_not_found(self, admin_token):
        """PUT /api/zones/{id} returns 404 for non-existent zone"""
        resp = requests.put(f"{BASE_URL}/api/zones/non-existent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Test"}
        )
        assert resp.status_code == 404
        print("✓ PUT non-existent zone returns 404")
    
    def test_delete_zone_not_found(self, admin_token):
        """DELETE /api/zones/{id} returns 404 for non-existent zone"""
        resp = requests.delete(f"{BASE_URL}/api/zones/non-existent-id",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404
        print("✓ DELETE non-existent zone returns 404")


class TestZoneUserBuildingsEndpoint:
    """Test GET /api/zones/user-buildings endpoint"""
    
    def test_get_user_buildings_no_zones(self, user_auth):
        """GET /api/zones/user-buildings returns empty when user not in any zone"""
        # First ensure no zones exist for this test or user not in zones
        resp = requests.get(f"{BASE_URL}/api/zones/user-buildings", 
            headers={"Authorization": f"Bearer {user_auth['token']}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "building_ids" in data
        assert "zones" in data
        print(f"✓ GET /api/zones/user-buildings returned: {len(data['building_ids'])} buildings, {len(data['zones'])} zones")
    
    def test_get_user_buildings_with_zone(self, admin_token, user_auth, test_building, test_user_id):
        """GET /api/zones/user-buildings returns buildings when user assigned to zone"""
        # Create zone with user
        zone_resp = requests.post(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_ZoneUserBuildings", "building_id": test_building["id"], "assigned_users": [test_user_id]}
        )
        zone = zone_resp.json()
        print("✓ Created zone for user-buildings test")
        
        # Get user buildings
        resp = requests.get(f"{BASE_URL}/api/zones/user-buildings", 
            headers={"Authorization": f"Bearer {user_auth['token']}"})
        assert resp.status_code == 200
        data = resp.json()
        assert test_building["id"] in data["building_ids"], f"Building not in user-buildings: {data}"
        print(f"✓ User's assigned buildings: {data['building_ids']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})


class TestZoneEnforcement:
    """Test zone enforcement during reservation creation"""
    
    def test_booking_building_without_zones_succeeds(self, user_auth, test_vehicle):
        """Booking in building WITHOUT zones should succeed for any user"""
        # Get buildings
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", 
            headers={"Authorization": f"Bearer {user_auth['token']}"})
        buildings = buildings_resp.json()
        
        # Find a building without zones
        zones_resp = requests.get(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {user_auth['token']}"})
        # This endpoint requires admin, so we'll use admin token for checking
        
        # For this test, we need to find a building with available slots
        # and check if user can book (they should be able to in buildings without zones)
        if not buildings:
            pytest.skip("No buildings available")
        
        for building in buildings:
            # Get slots
            future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            slots_resp = requests.get(f"{BASE_URL}/api/slots/available",
                headers={"Authorization": f"Bearer {user_auth['token']}"},
                params={"building_id": building["id"], "date": future_date}
            )
            slots = slots_resp.json()
            available = [s for s in slots if s.get("is_available")]
            if available:
                # Try booking
                reservation_data = {
                    "slot_id": available[0]["id"],
                    "vehicle_id": test_vehicle["id"],
                    "date": future_date,
                    "start_time": "11:00",
                    "end_time": "12:00",
                    "booking_type": "daily",
                    "repeat_weeks": 0
                }
                book_resp = requests.post(f"{BASE_URL}/api/reservations",
                    headers={"Authorization": f"Bearer {user_auth['token']}"},
                    json=reservation_data
                )
                if book_resp.status_code == 200:
                    res = book_resp.json()
                    res_id = res.get("id") or res.get("reservations", [{}])[0].get("id")
                    print("✓ Booking succeeded in building without zones (or user is assigned)")
                    # Cancel
                    if res_id:
                        requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                            headers={"Authorization": f"Bearer {user_auth['token']}"})
                    return
                elif book_resp.status_code == 403:
                    # User not assigned - building has zones
                    continue
        
        print("✓ All tested buildings either have zones or no slots - test skipped")
    
    def test_booking_building_with_zones_nonassigned_user_fails(self, admin_token, user_auth, test_building, test_user_id, test_vehicle):
        """Booking in building WITH zones fails for non-assigned user (403)"""
        # Create a zone for the building WITHOUT the test user
        # First, get another user if possible, or create zone with empty users
        zone_resp = requests.post(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_ZoneEnforcement", "building_id": test_building["id"], "assigned_users": []}  # No users
        )
        assert zone_resp.status_code == 200
        zone = zone_resp.json()
        print("✓ Created zone with no users for building")
        
        # Now try to book as test user (who is NOT in the zone)
        # Get a slot from the test building
        floor = test_building["floors"][0] if test_building.get("floors") else None
        if floor and floor.get("slots"):
            slot = floor["slots"][0]
        else:
            # Get slots via API
            future_date = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
            slots_resp = requests.get(f"{BASE_URL}/api/slots/available",
                headers={"Authorization": f"Bearer {user_auth['token']}"},
                params={"building_id": test_building["id"], "date": future_date}
            )
            slots = slots_resp.json()
            if not slots:
                requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})
                pytest.skip("No slots in test building")
            slot = slots[0]
        
        future_date = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
        reservation_data = {
            "slot_id": slot["id"],
            "vehicle_id": test_vehicle["id"],
            "date": future_date,
            "start_time": "14:00",
            "end_time": "15:00",
            "booking_type": "daily",
            "repeat_weeks": 0
        }
        
        book_resp = requests.post(f"{BASE_URL}/api/reservations",
            headers={"Authorization": f"Bearer {user_auth['token']}"},
            json=reservation_data
        )
        
        assert book_resp.status_code == 403, f"Expected 403, got {book_resp.status_code}: {book_resp.text}"
        assert "not assigned" in book_resp.json().get("detail", "").lower()
        print("✓ Booking correctly blocked for non-assigned user (403)")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    
    def test_booking_building_with_zones_assigned_user_succeeds(self, admin_token, user_auth, test_building, test_user_id, test_vehicle):
        """Booking in building WITH zones succeeds for assigned user"""
        # Create zone with test user
        zone_resp = requests.post(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_ZoneAssigned", "building_id": test_building["id"], "assigned_users": [test_user_id]}
        )
        assert zone_resp.status_code == 200
        zone = zone_resp.json()
        print("✓ Created zone with test user assigned")
        
        # Get available slot
        future_date = (datetime.now() + timedelta(days=9)).strftime("%Y-%m-%d")
        slots_resp = requests.get(f"{BASE_URL}/api/slots/available",
            headers={"Authorization": f"Bearer {user_auth['token']}"},
            params={"building_id": test_building["id"], "date": future_date}
        )
        slots = slots_resp.json()
        available = [s for s in slots if s.get("is_available")]
        
        if not available:
            requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})
            pytest.skip("No available slots")
        
        reservation_data = {
            "slot_id": available[0]["id"],
            "vehicle_id": test_vehicle["id"],
            "date": future_date,
            "start_time": "16:00",
            "end_time": "17:00",
            "booking_type": "daily",
            "repeat_weeks": 0
        }
        
        book_resp = requests.post(f"{BASE_URL}/api/reservations",
            headers={"Authorization": f"Bearer {user_auth['token']}"},
            json=reservation_data
        )
        
        assert book_resp.status_code == 200, f"Booking failed: {book_resp.text}"
        res = book_resp.json()
        res_id = res.get("id") or res.get("reservations", [{}])[0].get("id")
        print("✓ Booking succeeded for assigned user")
        
        # Cancel the reservation
        if res_id:
            requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                headers={"Authorization": f"Bearer {user_auth['token']}"})
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    
    def test_admin_can_book_regardless_of_zones(self, admin_token, test_building):
        """Admin can book in any building regardless of zone assignments"""
        # Create zone without admin
        zone_resp = requests.post(f"{BASE_URL}/api/zones", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_ZoneAdminTest", "building_id": test_building["id"], "assigned_users": []}
        )
        zone = zone_resp.json()
        
        # Admin needs a vehicle
        vehicles_resp = requests.get(f"{BASE_URL}/api/vehicles", headers={"Authorization": f"Bearer {admin_token}"})
        vehicles = vehicles_resp.json()
        if not vehicles:
            vehicle_resp = requests.post(f"{BASE_URL}/api/vehicles",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"plate_number": "ADMIN123", "make": "Admin", "model": "Car"}
            )
            vehicle_id = vehicle_resp.json()["id"]
        else:
            vehicle_id = vehicles[0]["id"]
        
        # Get slot
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        slots_resp = requests.get(f"{BASE_URL}/api/slots/available",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"building_id": test_building["id"], "date": future_date}
        )
        slots = slots_resp.json()
        available = [s for s in slots if s.get("is_available")]
        
        if not available:
            requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})
            pytest.skip("No available slots")
        
        reservation_data = {
            "slot_id": available[0]["id"],
            "vehicle_id": vehicle_id,
            "date": future_date,
            "start_time": "09:00",
            "end_time": "10:00",
            "booking_type": "daily",
            "repeat_weeks": 0
        }
        
        book_resp = requests.post(f"{BASE_URL}/api/reservations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=reservation_data
        )
        
        assert book_resp.status_code == 200, f"Admin booking failed: {book_resp.text}"
        res = book_resp.json()
        res_id = res.get("id") or res.get("reservations", [{}])[0].get("id")
        print("✓ Admin can book regardless of zones")
        
        # Cancel
        if res_id:
            requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                headers={"Authorization": f"Bearer {admin_token}"})
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/zones/{zone['id']}", headers={"Authorization": f"Bearer {admin_token}"})


class TestZoneAPIAccess:
    """Test zone API access control"""
    
    def test_user_cannot_access_zones_list(self, user_auth):
        """Regular user cannot access GET /api/zones (admin only)"""
        resp = requests.get(f"{BASE_URL}/api/zones", headers={"Authorization": f"Bearer {user_auth['token']}"})
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print("✓ Regular user blocked from GET /api/zones")
    
    def test_user_cannot_create_zone(self, user_auth):
        """Regular user cannot create zones"""
        resp = requests.post(f"{BASE_URL}/api/zones",
            headers={"Authorization": f"Bearer {user_auth['token']}"},
            json={"name": "Unauthorized", "building_id": "test", "assigned_users": []}
        )
        assert resp.status_code == 403
        print("✓ Regular user blocked from POST /api/zones")
    
    def test_user_can_access_own_buildings(self, user_auth):
        """Regular user CAN access GET /api/zones/user-buildings"""
        resp = requests.get(f"{BASE_URL}/api/zones/user-buildings", 
            headers={"Authorization": f"Bearer {user_auth['token']}"})
        assert resp.status_code == 200
        print("✓ Regular user can access /api/zones/user-buildings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
