"""
Test suite for slot management features (Iteration 6)
Tests: Building creation with slot_prefix, Floor creation with slot_labels/slot_prefix,
       Bulk slot addition, Slot rename, Slot delete
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"

class TestSlotManagement:
    """Tests for new slot management features"""
    
    admin_token = None
    test_building_id = None
    test_floor_id = None
    test_slot_ids = []
    cleanup_building_ids = []
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_admin_token(self, request):
        """Get admin token before running tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        request.cls.admin_token = response.json()["access_token"]
        request.cls.cleanup_building_ids = []
        request.cls.test_slot_ids = []
        yield
        # Cleanup after all tests in class
        headers = {"Authorization": f"Bearer {request.cls.admin_token}"}
        for bid in request.cls.cleanup_building_ids:
            try:
                requests.delete(f"{BASE_URL}/api/buildings/{bid}", headers=headers)
                print(f"Cleaned up building: {bid}")
            except:
                pass


class TestBuildingCreationWithSlotPrefix(TestSlotManagement):
    """Test POST /api/buildings with slot_prefix creates slots with custom prefix"""
    
    def test_create_building_with_custom_slot_prefix(self):
        """Create building with slot_prefix='P-' should create slots P-1, P-2, etc."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        unique_name = f"TEST_Building_Prefix_{uuid.uuid4().hex[:6]}"
        
        response = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address for Prefix Building",
            "total_floors": 1,
            "slots_per_floor": 5,
            "slot_prefix": "P-"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Store for cleanup
        self.cleanup_building_ids.append(data["id"])
        self.__class__.test_building_id = data["id"]
        
        # Verify building was created
        assert data["name"] == unique_name
        assert len(data["floors"]) == 1
        
        # Verify slots have custom prefix
        floor = data["floors"][0]
        assert len(floor["slots"]) == 5, f"Expected 5 slots, got {len(floor['slots'])}"
        
        slot_labels = [s["label"] for s in floor["slots"]]
        expected_labels = ["P-1", "P-2", "P-3", "P-4", "P-5"]
        assert slot_labels == expected_labels, f"Expected {expected_labels}, got {slot_labels}"
        
        print(f"PASS: Building created with slot labels: {slot_labels}")
    
    def test_create_building_without_prefix_uses_floor_default(self):
        """Building without slot_prefix uses default F{floor_num}- prefix"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        unique_name = f"TEST_Building_Default_{uuid.uuid4().hex[:6]}"
        
        response = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address for Default Prefix",
            "total_floors": 1,
            "slots_per_floor": 3
            # No slot_prefix - should use default
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Store for cleanup
        self.cleanup_building_ids.append(data["id"])
        
        floor = data["floors"][0]
        slot_labels = [s["label"] for s in floor["slots"]]
        
        # Default prefix should be "F1-" for Floor 1
        expected_labels = ["F1-1", "F1-2", "F1-3"]
        assert slot_labels == expected_labels, f"Expected {expected_labels}, got {slot_labels}"
        
        print(f"PASS: Building created with default slot labels: {slot_labels}")


class TestFloorCreationWithCustomLabels(TestSlotManagement):
    """Test POST /api/buildings/{id}/floors with slot_labels or slot_prefix"""
    
    def test_add_floor_with_slot_labels(self):
        """Add floor with explicit slot_labels creates slots with exact custom labels"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # First create a building
        unique_name = f"TEST_Building_FloorLabels_{uuid.uuid4().hex[:6]}"
        building_resp = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address",
            "total_floors": 0,  # No initial floors
            "slots_per_floor": 0
        })
        assert building_resp.status_code == 200
        building_id = building_resp.json()["id"]
        self.cleanup_building_ids.append(building_id)
        
        # Add floor with custom labels
        custom_labels = ["VIP-01", "VIP-02", "EV-01", "EV-02"]
        floor_resp = requests.post(f"{BASE_URL}/api/buildings/{building_id}/floors", headers=headers, json={
            "label": "VIP Floor",
            "building_id": building_id,
            "slot_labels": custom_labels,
            "slot_count": len(custom_labels)
        })
        
        assert floor_resp.status_code == 200, f"Expected 200, got {floor_resp.status_code}: {floor_resp.text}"
        floor_data = floor_resp.json()
        
        # Store floor ID
        self.__class__.test_floor_id = floor_data["id"]
        
        # Verify slots have exact custom labels
        slot_labels = [s["label"] for s in floor_data["slots"]]
        assert slot_labels == custom_labels, f"Expected {custom_labels}, got {slot_labels}"
        
        print(f"PASS: Floor added with custom slot labels: {slot_labels}")
    
    def test_add_floor_with_slot_prefix(self):
        """Add floor with slot_prefix creates slots with prefix+number pattern"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create building first
        unique_name = f"TEST_Building_FloorPrefix_{uuid.uuid4().hex[:6]}"
        building_resp = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address",
            "total_floors": 0,
            "slots_per_floor": 0
        })
        building_id = building_resp.json()["id"]
        self.cleanup_building_ids.append(building_id)
        
        # Add floor with prefix
        floor_resp = requests.post(f"{BASE_URL}/api/buildings/{building_id}/floors", headers=headers, json={
            "label": "B1",
            "building_id": building_id,
            "slot_count": 4,
            "slot_prefix": "B1-"
        })
        
        assert floor_resp.status_code == 200, f"Expected 200, got {floor_resp.status_code}: {floor_resp.text}"
        floor_data = floor_resp.json()
        
        slot_labels = [s["label"] for s in floor_data["slots"]]
        expected = ["B1-1", "B1-2", "B1-3", "B1-4"]
        assert slot_labels == expected, f"Expected {expected}, got {slot_labels}"
        
        print(f"PASS: Floor added with prefix slot labels: {slot_labels}")


class TestBulkSlotAddition(TestSlotManagement):
    """Test POST /api/floors/{id}/slots for bulk adding slots"""
    
    def test_add_slots_with_custom_labels(self):
        """Bulk add slots with slot_labels creates slots with exact labels"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create building with floor first
        unique_name = f"TEST_Building_BulkLabels_{uuid.uuid4().hex[:6]}"
        building_resp = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address",
            "total_floors": 1,
            "slots_per_floor": 2,
            "slot_prefix": "X-"
        })
        building_id = building_resp.json()["id"]
        floor_id = building_resp.json()["floors"][0]["id"]
        self.cleanup_building_ids.append(building_id)
        
        # Initial slots should be X-1, X-2
        initial_slots = building_resp.json()["floors"][0]["slots"]
        assert len(initial_slots) == 2
        
        # Add bulk slots with custom labels
        custom_labels = ["PREMIUM-A", "PREMIUM-B", "HANDICAP-1"]
        bulk_resp = requests.post(f"{BASE_URL}/api/floors/{floor_id}/slots", headers=headers, json={
            "slot_labels": custom_labels
        })
        
        assert bulk_resp.status_code == 200, f"Expected 200, got {bulk_resp.status_code}: {bulk_resp.text}"
        data = bulk_resp.json()
        
        assert data["message"] == f"Added {len(custom_labels)} slots", f"Unexpected message: {data['message']}"
        
        new_slot_labels = [s["label"] for s in data["slots"]]
        assert new_slot_labels == custom_labels, f"Expected {custom_labels}, got {new_slot_labels}"
        
        # Store slot IDs for later tests
        for s in data["slots"]:
            self.test_slot_ids.append(s["id"])
        
        print(f"PASS: Bulk added slots with custom labels: {new_slot_labels}")
    
    def test_add_slots_with_prefix_and_count(self):
        """Bulk add slots with slot_prefix and slot_count"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create building
        unique_name = f"TEST_Building_BulkPrefix_{uuid.uuid4().hex[:6]}"
        building_resp = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address",
            "total_floors": 1,
            "slots_per_floor": 2,
            "slot_prefix": "A-"
        })
        building_id = building_resp.json()["id"]
        floor_id = building_resp.json()["floors"][0]["id"]
        self.cleanup_building_ids.append(building_id)
        
        # Add 3 more slots with prefix
        bulk_resp = requests.post(f"{BASE_URL}/api/floors/{floor_id}/slots", headers=headers, json={
            "slot_count": 3,
            "slot_prefix": "A-"
        })
        
        assert bulk_resp.status_code == 200, f"Expected 200, got {bulk_resp.status_code}: {bulk_resp.text}"
        data = bulk_resp.json()
        
        # Should start from 3 (since 2 already exist)
        new_slot_labels = [s["label"] for s in data["slots"]]
        expected = ["A-3", "A-4", "A-5"]
        assert new_slot_labels == expected, f"Expected {expected}, got {new_slot_labels}"
        
        print(f"PASS: Bulk added slots with prefix: {new_slot_labels}")
    
    def test_add_slots_validation_error(self):
        """Adding slots without labels or count returns 400"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get any floor
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", headers=headers)
        buildings = buildings_resp.json()
        if not buildings or not buildings[0].get("floors"):
            pytest.skip("No floors available for testing")
        
        floor_id = buildings[0]["floors"][0]["id"]
        
        # Try to add with empty payload
        response = requests.post(f"{BASE_URL}/api/floors/{floor_id}/slots", headers=headers, json={})
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("PASS: Empty bulk add returns 400")


class TestSlotRename(TestSlotManagement):
    """Test PUT /api/slots/{id} for renaming slots"""
    
    def test_rename_slot_success(self):
        """Rename a slot to a new alphanumeric label"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create building with slot
        unique_name = f"TEST_Building_Rename_{uuid.uuid4().hex[:6]}"
        building_resp = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address",
            "total_floors": 1,
            "slots_per_floor": 1,
            "slot_prefix": "OLD-"
        })
        building_id = building_resp.json()["id"]
        slot_id = building_resp.json()["floors"][0]["slots"][0]["id"]
        original_label = building_resp.json()["floors"][0]["slots"][0]["label"]
        self.cleanup_building_ids.append(building_id)
        
        assert original_label == "OLD-1", f"Expected OLD-1, got {original_label}"
        
        # Rename the slot
        new_label = "NEW-PREMIUM-X1"
        rename_resp = requests.put(f"{BASE_URL}/api/slots/{slot_id}", headers=headers, json={
            "label": new_label
        })
        
        assert rename_resp.status_code == 200, f"Expected 200, got {rename_resp.status_code}: {rename_resp.text}"
        data = rename_resp.json()
        
        assert data["new_label"] == new_label, f"Expected label {new_label}, got {data.get('new_label')}"
        print(f"PASS: Slot renamed from {original_label} to {new_label}")
        
        # Verify by fetching buildings
        verify_resp = requests.get(f"{BASE_URL}/api/buildings", headers=headers)
        buildings = verify_resp.json()
        test_building = next((b for b in buildings if b["id"] == building_id), None)
        assert test_building is not None
        
        slot_label = test_building["floors"][0]["slots"][0]["label"]
        assert slot_label == new_label, f"Expected {new_label} after rename, got {slot_label}"
        print(f"PASS: Slot rename verified in database: {slot_label}")
    
    def test_rename_nonexistent_slot_fails(self):
        """Renaming non-existent slot returns 404"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        fake_id = "nonexistent-slot-id-12345"
        
        response = requests.put(f"{BASE_URL}/api/slots/{fake_id}", headers=headers, json={
            "label": "NEW-LABEL"
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: Rename non-existent slot returns 404")


class TestSlotDelete(TestSlotManagement):
    """Test DELETE /api/slots/{id}"""
    
    def test_delete_slot_success(self):
        """Delete a slot without active reservations"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create building with slots
        unique_name = f"TEST_Building_Delete_{uuid.uuid4().hex[:6]}"
        building_resp = requests.post(f"{BASE_URL}/api/buildings", headers=headers, json={
            "name": unique_name,
            "address": "Test Address",
            "total_floors": 1,
            "slots_per_floor": 3,
            "slot_prefix": "DEL-"
        })
        building_id = building_resp.json()["id"]
        slots = building_resp.json()["floors"][0]["slots"]
        slot_to_delete = slots[0]
        self.cleanup_building_ids.append(building_id)
        
        # Delete the slot
        delete_resp = requests.delete(f"{BASE_URL}/api/slots/{slot_to_delete['id']}", headers=headers)
        
        assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"
        data = delete_resp.json()
        assert "deleted" in data["message"].lower()
        print(f"PASS: Slot {slot_to_delete['label']} deleted successfully")
        
        # Verify slot is removed
        verify_resp = requests.get(f"{BASE_URL}/api/buildings", headers=headers)
        buildings = verify_resp.json()
        test_building = next((b for b in buildings if b["id"] == building_id), None)
        remaining_slots = test_building["floors"][0]["slots"]
        
        assert len(remaining_slots) == 2, f"Expected 2 remaining slots, got {len(remaining_slots)}"
        remaining_ids = [s["id"] for s in remaining_slots]
        assert slot_to_delete["id"] not in remaining_ids, "Deleted slot should not appear in list"
        print("PASS: Slot removal verified in database")
    
    def test_delete_nonexistent_slot_fails(self):
        """Deleting non-existent slot returns 404"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        fake_id = "nonexistent-slot-99999"
        
        response = requests.delete(f"{BASE_URL}/api/slots/{fake_id}", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: Delete non-existent slot returns 404")
    
    def test_delete_slot_with_active_reservation_fails(self):
        """Deleting a slot with active reservation returns 400"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get existing slots with potential reservations
        buildings_resp = requests.get(f"{BASE_URL}/api/buildings", headers=headers)
        buildings = buildings_resp.json()
        
        # Find a slot that might have a reservation (from existing data)
        # First check admin reservations
        res_resp = requests.get(f"{BASE_URL}/api/admin/reservations", headers=headers)
        reservations = res_resp.json()
        
        # Find a pending or confirmed reservation
        active_res = [r for r in reservations if r["status"] in ["pending", "confirmed"]]
        
        if not active_res:
            pytest.skip("No active reservations to test slot deletion block")
        
        slot_id = active_res[0]["slot_id"]
        
        # Try to delete the slot with active reservation
        response = requests.delete(f"{BASE_URL}/api/slots/{slot_id}", headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "active" in data["detail"].lower() or "reservation" in data["detail"].lower()
        print(f"PASS: Cannot delete slot with active reservation: {data['detail']}")


class TestFloorNotFound(TestSlotManagement):
    """Test 404 handling for floor endpoints"""
    
    def test_add_floor_to_nonexistent_building(self):
        """Adding floor to non-existent building returns 404"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        fake_building_id = "nonexistent-building-12345"
        
        response = requests.post(f"{BASE_URL}/api/buildings/{fake_building_id}/floors", headers=headers, json={
            "label": "Test Floor",
            "building_id": fake_building_id,
            "slot_count": 5
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: Add floor to non-existent building returns 404")
    
    def test_add_slots_to_nonexistent_floor(self):
        """Adding slots to non-existent floor returns 404"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        fake_floor_id = "nonexistent-floor-99999"
        
        response = requests.post(f"{BASE_URL}/api/floors/{fake_floor_id}/slots", headers=headers, json={
            "slot_count": 5,
            "slot_prefix": "X-"
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: Add slots to non-existent floor returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
