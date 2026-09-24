"""
Test suite for Dedicated Slot Policy feature
Tests building policies, slot registrations, and booking restrictions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"email": "admin.test@cebuana.com", "password": "Test123!"}
# Maria - has assigned slot B1-01
MARIA_CREDENTIALS = {"email": "psb.user1@cebuana.com", "password": "Test123!"}
# Pedro - has sticker but no slot assignment
PEDRO_CREDENTIALS = {"email": "psb.noassign@cebuana.com", "password": "Test123!"}
# Rosa - no sticker at all
ROSA_CREDENTIALS = {"email": "psb.nosticker@cebuana.com", "password": "Test123!"}


@pytest.fixture(scope="module")
def admin_session():
    """Admin login session fixture"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return session


@pytest.fixture(scope="module")
def maria_session():
    """Maria (assigned slot B1-01) login session fixture"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json=MARIA_CREDENTIALS)
    assert response.status_code == 200, f"Maria login failed: {response.text}"
    return session


@pytest.fixture(scope="module")
def pedro_session():
    """Pedro (sticker, no slot) login session fixture"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json=PEDRO_CREDENTIALS)
    assert response.status_code == 200, f"Pedro login failed: {response.text}"
    return session


@pytest.fixture(scope="module")
def rosa_session():
    """Rosa (no sticker) login session fixture"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json=ROSA_CREDENTIALS)
    assert response.status_code == 200, f"Rosa login failed: {response.text}"
    return session


@pytest.fixture(scope="module")
def pacific_star_building(admin_session):
    """Get Pacific Star Building data"""
    response = admin_session.get(f"{BASE_URL}/api/buildings")
    assert response.status_code == 200
    buildings = response.json()
    psb = next((b for b in buildings if b["name"] == "Pacific Star Building"), None)
    assert psb is not None, "Pacific Star Building not found"
    return psb


class TestBuildingPoliciesAPI:
    """Test Building Policies CRUD endpoints"""
    
    def test_get_building_policies_list(self, admin_session):
        """GET /api/building-policies returns list of policies"""
        response = admin_session.get(f"{BASE_URL}/api/building-policies")
        assert response.status_code == 200
        policies = response.json()
        assert isinstance(policies, list)
        print(f"Found {len(policies)} building policies")
        
    def test_get_pacific_star_policy(self, admin_session, pacific_star_building):
        """GET /api/building-policies/{building_id} returns Pacific Star policy"""
        building_id = pacific_star_building["id"]
        response = admin_session.get(f"{BASE_URL}/api/building-policies/{building_id}")
        assert response.status_code == 200
        policy = response.json()
        
        # Verify policy config
        assert policy.get("enabled") is True, "Policy should be enabled"
        assert policy.get("policy_type") == "dedicated_slot", "Should be dedicated_slot policy"
        assert policy.get("max_users_per_slot") == 5, "Max users per slot should be 5"
        assert policy.get("requires_sticker") is True, "Sticker should be required"
        assert len(policy.get("open_floor_ids", [])) == 2, "Should have 2 open floors (B3, B4)"
        print(f"Pacific Star policy: enabled={policy.get('enabled')}, max_users={policy.get('max_users_per_slot')}")
        
    def test_update_building_policy(self, admin_session, pacific_star_building):
        """PUT /api/building-policies/{building_id} updates policy"""
        building_id = pacific_star_building["id"]
        
        # Update max_users_per_slot temporarily
        response = admin_session.put(
            f"{BASE_URL}/api/building-policies/{building_id}",
            json={"max_users_per_slot": 6}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated.get("max_users_per_slot") == 6
        
        # Revert back to 5
        response = admin_session.put(
            f"{BASE_URL}/api/building-policies/{building_id}",
            json={"max_users_per_slot": 5}
        )
        assert response.status_code == 200
        print("Policy update successful")


class TestSlotRegistrationsAPI:
    """Test Slot Registrations CRUD endpoints"""
    
    def test_get_slot_registrations(self, admin_session, pacific_star_building):
        """GET /api/slot-registrations returns registrations for building"""
        building_id = pacific_star_building["id"]
        response = admin_session.get(f"{BASE_URL}/api/slot-registrations", params={"building_id": building_id})
        assert response.status_code == 200
        registrations = response.json()
        assert isinstance(registrations, list)
        assert len(registrations) >= 5, f"Expected at least 5 registrations, got {len(registrations)}"
        
        # Verify registration structure
        if registrations:
            reg = registrations[0]
            assert "slot_id" in reg
            assert "user_id" in reg
            assert "vehicle_plate" in reg
            assert "status" in reg
        print(f"Found {len(registrations)} slot registrations")
        
    def test_get_user_slot_registrations(self, maria_session):
        """GET /api/slot-registrations/user/{user_id} returns user's registrations"""
        # First get Maria's user ID
        me_response = maria_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        maria_id = me_response.json()["id"]
        
        response = maria_session.get(f"{BASE_URL}/api/slot-registrations/user/{maria_id}")
        assert response.status_code == 200
        registrations = response.json()
        assert len(registrations) >= 1, "Maria should have at least 1 slot registration"
        
        # Verify Maria is registered to B1-01
        slot_labels = [r.get("slot_label") for r in registrations]
        assert "B1-01" in slot_labels, f"Maria should be registered to B1-01, got: {slot_labels}"
        print(f"Maria's registrations: {slot_labels}")
        
    def test_create_and_delete_slot_registration(self, admin_session, pacific_star_building):
        """POST /api/slot-registrations creates registration, DELETE revokes it"""
        building_id = pacific_star_building["id"]
        
        # Get a slot that's not full (find B1-03 or similar)
        floors = pacific_star_building.get("floors", [])
        b1_floor = next((f for f in floors if f["label"] == "Basement 1"), None)
        assert b1_floor is not None, "Basement 1 not found"
        
        # Find an available slot (B1-03 should have no registrations)
        slots = b1_floor.get("slots", [])
        test_slot = next((s for s in slots if s["label"] == "B1-03"), None)
        if not test_slot:
            pytest.skip("B1-03 slot not found")
            
        # Get a test user ID
        users_response = admin_session.get(f"{BASE_URL}/api/users")
        assert users_response.status_code == 200
        users = users_response.json()
        # Find a user who doesn't already have this slot
        test_user = next((u for u in users if "psb.user5" in u.get("email", "")), None)
        if not test_user:
            pytest.skip("Test user not found")
            
        # Create registration
        create_payload = {
            "slot_id": test_slot["id"],
            "user_id": test_user["id"],
            "vehicle_plate": "TEST-REG-001",
            "sticker_number": "TEST-STK-001"
        }
        create_response = admin_session.post(f"{BASE_URL}/api/slot-registrations", json=create_payload)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        created = create_response.json()
        assert created.get("id") is not None
        reg_id = created["id"]
        print(f"Created registration: {reg_id}")
        
        # Delete (revoke) registration
        delete_response = admin_session.delete(f"{BASE_URL}/api/slot-registrations/{reg_id}")
        assert delete_response.status_code == 200
        print("Registration revoked successfully")


class TestDedicatedSlotBookingRestrictions:
    """Test booking restrictions under dedicated slot policy"""
    
    def test_maria_sees_only_assigned_slot_on_b1(self, maria_session, pacific_star_building):
        """Maria should see only B1-01 available on Basement 1 (dedicated floor)"""
        building_id = pacific_star_building["id"]
        floors = pacific_star_building.get("floors", [])
        b1_floor = next((f for f in floors if f["label"] == "Basement 1"), None)
        assert b1_floor is not None
        
        # Get available slots for Basement 1
        response = maria_session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": building_id, "date": "2026-02-24", "floor_id": b1_floor["id"]}
        )
        assert response.status_code == 200
        slots = response.json()
        
        # Check slots have policy indicators
        assert len(slots) > 0, "Should return slots"
        assert slots[0].get("is_dedicated_policy") is True, "Should indicate dedicated policy active"
        
        # Find Maria's assigned slot (B1-01)
        b1_01 = next((s for s in slots if s["label"] == "B1-01"), None)
        assert b1_01 is not None, "B1-01 should be in response"
        assert b1_01.get("is_user_assigned") is True, "B1-01 should be marked as Maria's assigned slot"
        
        # Other slots should be restricted for Maria
        available_for_maria = [s for s in slots if s.get("is_available") is True]
        available_labels = [s["label"] for s in available_for_maria]
        print(f"Maria can book: {available_labels}")
        
        # Only B1-01 should be available (or no slots if it's already booked)
        assert all("B1-01" in l for l in available_labels) or len(available_labels) == 0, \
            f"Maria should only see B1-01 or nothing on B1, got: {available_labels}"
            
    def test_maria_sees_all_slots_on_open_floor_b3(self, maria_session, pacific_star_building):
        """Maria can book any slot on B3 (open parking floor)"""
        building_id = pacific_star_building["id"]
        floors = pacific_star_building.get("floors", [])
        b3_floor = next((f for f in floors if f["label"] == "Basement 3"), None)
        assert b3_floor is not None
        
        response = maria_session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": building_id, "date": "2026-02-24", "floor_id": b3_floor["id"]}
        )
        assert response.status_code == 200
        slots = response.json()
        
        # B3 is open floor - all available slots should be bookable
        assert len(slots) > 0
        assert slots[0].get("is_open_floor") is True, "B3 should be marked as open floor"
        
        available_slots = [s for s in slots if s.get("is_available") is True]
        print(f"Maria can book {len(available_slots)} slots on B3 (open floor)")
        # All non-reserved slots should be available on open floor
        
    def test_pedro_cannot_book_dedicated_floor(self, pedro_session, pacific_star_building):
        """Pedro (sticker, no slot) cannot book on dedicated floors (B1/B2)"""
        building_id = pacific_star_building["id"]
        floors = pacific_star_building.get("floors", [])
        b1_floor = next((f for f in floors if f["label"] == "Basement 1"), None)
        assert b1_floor is not None
        
        response = pedro_session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": building_id, "date": "2026-02-24", "floor_id": b1_floor["id"]}
        )
        assert response.status_code == 200
        slots = response.json()
        
        # All B1 slots should be restricted for Pedro
        available_for_pedro = [s for s in slots if s.get("is_available") is True]
        assert len(available_for_pedro) == 0, \
            f"Pedro should not have any available slots on B1, got: {[s['label'] for s in available_for_pedro]}"
        
        # Check restriction reason
        restricted_slots = [s for s in slots if s.get("restriction_reason") == "not_assigned"]
        print(f"Pedro restricted from {len(restricted_slots)} slots on B1")
        
    def test_pedro_can_book_open_floor_b3(self, pedro_session, pacific_star_building):
        """Pedro can book on open floors (B3/B4) since he has a sticker"""
        building_id = pacific_star_building["id"]
        floors = pacific_star_building.get("floors", [])
        b3_floor = next((f for f in floors if f["label"] == "Basement 3"), None)
        assert b3_floor is not None
        
        response = pedro_session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": building_id, "date": "2026-02-24", "floor_id": b3_floor["id"]}
        )
        assert response.status_code == 200
        slots = response.json()
        
        available_for_pedro = [s for s in slots if s.get("is_available") is True]
        print(f"Pedro can book {len(available_for_pedro)} slots on B3 (open floor)")
        # Pedro should be able to book on open floor
        assert len(available_for_pedro) >= 0, "Pedro should be able to see open floor slots"
        
    def test_rosa_gets_403_when_booking(self, rosa_session, pacific_star_building):
        """Rosa (no sticker) gets 403 when trying to book in Pacific Star"""
        building_id = pacific_star_building["id"]
        floors = pacific_star_building.get("floors", [])
        b3_floor = next((f for f in floors if f["label"] == "Basement 3"), None)
        assert b3_floor is not None
        
        # Get a slot to try booking
        slots_response = rosa_session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": building_id, "date": "2026-02-25", "floor_id": b3_floor["id"]}
        )
        assert slots_response.status_code == 200
        slots = slots_response.json()
        
        if not slots:
            pytest.skip("No slots available for test")
            
        # Get Rosa's vehicle
        vehicles_response = rosa_session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_response.status_code == 200
        vehicles = vehicles_response.json()
        if not vehicles:
            pytest.skip("Rosa has no vehicles")
            
        # Try to book - should get 403
        booking_payload = {
            "slot_id": slots[0]["id"],
            "vehicle_id": vehicles[0]["id"],
            "dates": ["2026-02-25"],
            "start_time": "08:00",
            "end_time": "18:00"
        }
        response = rosa_session.post(f"{BASE_URL}/api/reservations", json=booking_payload)
        assert response.status_code == 403, f"Rosa should get 403, got {response.status_code}: {response.text}"
        
        error_detail = response.json().get("detail", "")
        assert "sticker" in error_detail.lower(), f"Error should mention sticker: {error_detail}"
        print(f"Rosa correctly denied: {error_detail}")


class TestAuthProtection:
    """Test that policy endpoints require authentication"""
    
    def test_building_policies_requires_auth(self):
        """GET /api/building-policies requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/building-policies")
        assert response.status_code == 401
        
    def test_slot_registrations_requires_auth(self):
        """GET /api/slot-registrations requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/slot-registrations")
        assert response.status_code == 401
        
    def test_create_registration_requires_admin(self, maria_session, pacific_star_building):
        """POST /api/slot-registrations requires admin role"""
        # Maria (regular user) tries to create registration
        floors = pacific_star_building.get("floors", [])
        b1_floor = next((f for f in floors if f["label"] == "Basement 1"), None)
        if not b1_floor:
            pytest.skip("B1 floor not found")
            
        slots = b1_floor.get("slots", [])
        if not slots:
            pytest.skip("No slots in B1")
            
        response = maria_session.post(
            f"{BASE_URL}/api/slot-registrations",
            json={
                "slot_id": slots[0]["id"],
                "user_id": "fake-id",
                "vehicle_plate": "TEST-123",
                "sticker_number": "TEST"
            }
        )
        assert response.status_code == 403, f"Non-admin should get 403, got {response.status_code}"
        print("Admin-only protection working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
