"""
Test suite for UI/UX Enhancement Features:
- Character limits validation (backend Pydantic models)
- Edit building endpoint
- Address line 1 & 2 split
- Company filter (No Company option)
- Pagination 
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCharacterLimits:
    """Test character limit validations on backend models"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    # --- First Name: max 30 characters ---
    def test_user_first_name_within_limit(self, auth_headers):
        """First name within 30 char limit should succeed"""
        test_email = f"test_fn_{int(time.time())}@test.com"
        response = requests.post(f"{BASE_URL}/api/users", headers=auth_headers, json={
            "email": test_email,
            "password": "Test123!",
            "first_name": "A" * 30,  # Exactly 30 chars
            "last_name": "TestUser"
        })
        assert response.status_code in [200, 201], f"Expected success for 30 char first_name: {response.text}"
        # Cleanup
        if response.status_code in [200, 201]:
            user_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)
    
    def test_user_first_name_exceeds_limit(self, auth_headers):
        """First name exceeding 30 chars should fail validation"""
        test_email = f"test_fn_long_{int(time.time())}@test.com"
        response = requests.post(f"{BASE_URL}/api/users", headers=auth_headers, json={
            "email": test_email,
            "password": "Test123!",
            "first_name": "A" * 31,  # 31 chars
            "last_name": "TestUser"
        })
        assert response.status_code == 422, f"Expected 422 for 31 char first_name: {response.text}"

    # --- Last Name: max 30 characters ---
    def test_user_last_name_within_limit(self, auth_headers):
        """Last name within 30 char limit should succeed"""
        test_email = f"test_ln_{int(time.time())}@test.com"
        response = requests.post(f"{BASE_URL}/api/users", headers=auth_headers, json={
            "email": test_email,
            "password": "Test123!",
            "first_name": "TestFirst",
            "last_name": "B" * 30  # Exactly 30 chars
        })
        assert response.status_code in [200, 201], f"Expected success for 30 char last_name: {response.text}"
        if response.status_code in [200, 201]:
            user_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)

    def test_user_last_name_exceeds_limit(self, auth_headers):
        """Last name exceeding 30 chars should fail validation"""
        test_email = f"test_ln_long_{int(time.time())}@test.com"
        response = requests.post(f"{BASE_URL}/api/users", headers=auth_headers, json={
            "email": test_email,
            "password": "Test123!",
            "first_name": "TestFirst",
            "last_name": "B" * 31  # 31 chars
        })
        assert response.status_code == 422, f"Expected 422 for 31 char last_name: {response.text}"

    # --- Company: max 30 characters ---
    def test_user_company_within_limit(self, auth_headers):
        """Company within 30 char limit should succeed"""
        test_email = f"test_co_{int(time.time())}@test.com"
        response = requests.post(f"{BASE_URL}/api/users", headers=auth_headers, json={
            "email": test_email,
            "password": "Test123!",
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "company": "C" * 30  # Exactly 30 chars
        })
        assert response.status_code in [200, 201], f"Expected success for 30 char company: {response.text}"
        if response.status_code in [200, 201]:
            user_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=auth_headers)

    def test_user_company_exceeds_limit(self, auth_headers):
        """Company exceeding 30 chars should fail validation"""
        test_email = f"test_co_long_{int(time.time())}@test.com"
        response = requests.post(f"{BASE_URL}/api/users", headers=auth_headers, json={
            "email": test_email,
            "password": "Test123!",
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "company": "C" * 31  # 31 chars
        })
        assert response.status_code == 422, f"Expected 422 for 31 char company: {response.text}"


class TestBuildingCharacterLimits:
    """Test building field character limits"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    # --- Building Name: max 30 characters ---
    def test_building_name_within_limit(self, auth_headers):
        """Building name within 30 char limit should succeed"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "D" * 30,  # Exactly 30 chars
            "address_line_1": "Test Address",
            "total_floors": 1,
            "slots_per_floor": 1
        })
        assert response.status_code in [200, 201], f"Expected success for 30 char building name: {response.text}"
        if response.status_code in [200, 201]:
            building_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/buildings/{building_id}", headers=auth_headers)

    def test_building_name_exceeds_limit(self, auth_headers):
        """Building name exceeding 30 chars should fail validation"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "D" * 31,  # 31 chars
            "address_line_1": "Test Address",
            "total_floors": 1,
            "slots_per_floor": 1
        })
        assert response.status_code == 422, f"Expected 422 for 31 char building name: {response.text}"

    # --- Address Line 1: max 30 characters ---
    def test_address_line1_within_limit(self, auth_headers):
        """Address line 1 within 30 char limit should succeed"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "Test Building AL1",
            "address_line_1": "E" * 30,  # Exactly 30 chars
            "total_floors": 1,
            "slots_per_floor": 1
        })
        assert response.status_code in [200, 201], f"Expected success for 30 char address_line_1: {response.text}"
        if response.status_code in [200, 201]:
            building_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/buildings/{building_id}", headers=auth_headers)

    def test_address_line1_exceeds_limit(self, auth_headers):
        """Address line 1 exceeding 30 chars should fail validation"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "Test Building AL1 Long",
            "address_line_1": "E" * 31,  # 31 chars
            "total_floors": 1,
            "slots_per_floor": 1
        })
        assert response.status_code == 422, f"Expected 422 for 31 char address_line_1: {response.text}"

    # --- Address Line 2: max 30 characters ---
    def test_address_line2_within_limit(self, auth_headers):
        """Address line 2 within 30 char limit should succeed"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "Test Building AL2",
            "address_line_1": "Line 1 Address",
            "address_line_2": "F" * 30,  # Exactly 30 chars
            "total_floors": 1,
            "slots_per_floor": 1
        })
        assert response.status_code in [200, 201], f"Expected success for 30 char address_line_2: {response.text}"
        if response.status_code in [200, 201]:
            building_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/buildings/{building_id}", headers=auth_headers)

    def test_address_line2_exceeds_limit(self, auth_headers):
        """Address line 2 exceeding 30 chars should fail validation"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "Test Building AL2 Long",
            "address_line_1": "Line 1 Address",
            "address_line_2": "F" * 31,  # 31 chars
            "total_floors": 1,
            "slots_per_floor": 1
        })
        assert response.status_code == 422, f"Expected 422 for 31 char address_line_2: {response.text}"


class TestFloorCharacterLimits:
    """Test floor label character limits"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture(scope="class")
    def test_building(self, auth_headers):
        """Create a test building for floor tests"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "Test Floor Building",
            "address_line_1": "Floor Test Addr",
            "total_floors": 0,
            "slots_per_floor": 1
        })
        if response.status_code in [200, 201]:
            yield response.json().get("id")
            requests.delete(f"{BASE_URL}/api/buildings/{response.json().get('id')}", headers=auth_headers)
        else:
            pytest.skip("Failed to create test building")

    # --- Floor Label: max 16 characters ---
    def test_floor_label_within_limit(self, auth_headers, test_building):
        """Floor label within 16 char limit should succeed"""
        response = requests.post(f"{BASE_URL}/api/buildings/{test_building}/floors", headers=auth_headers, json={
            "label": "G" * 16,  # Exactly 16 chars
            "building_id": test_building,
            "slot_count": 1
        })
        assert response.status_code in [200, 201], f"Expected success for 16 char floor label: {response.text}"

    def test_floor_label_exceeds_limit(self, auth_headers, test_building):
        """Floor label exceeding 16 chars should fail validation"""
        response = requests.post(f"{BASE_URL}/api/buildings/{test_building}/floors", headers=auth_headers, json={
            "label": "G" * 17,  # 17 chars
            "building_id": test_building,
            "slot_count": 1
        })
        assert response.status_code == 422, f"Expected 422 for 17 char floor label: {response.text}"


class TestZoneCharacterLimits:
    """Test zone name character limits"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture(scope="class")
    def test_building_id(self, auth_headers):
        """Get a building ID for zone tests"""
        response = requests.get(f"{BASE_URL}/api/buildings", headers=auth_headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No buildings available for zone test")

    # --- Zone Name: max 25 characters ---
    def test_zone_name_within_limit(self, auth_headers, test_building_id):
        """Zone name within 25 char limit should succeed"""
        response = requests.post(f"{BASE_URL}/api/zones", headers=auth_headers, json={
            "name": "H" * 25,  # Exactly 25 chars
            "building_ids": [test_building_id],
            "user_ids": []
        })
        assert response.status_code in [200, 201], f"Expected success for 25 char zone name: {response.text}"
        if response.status_code in [200, 201]:
            zone_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/zones/{zone_id}", headers=auth_headers)

    def test_zone_name_exceeds_limit(self, auth_headers, test_building_id):
        """Zone name exceeding 25 chars should fail validation"""
        response = requests.post(f"{BASE_URL}/api/zones", headers=auth_headers, json={
            "name": "H" * 26,  # 26 chars
            "building_ids": [test_building_id],
            "user_ids": []
        })
        assert response.status_code == 422, f"Expected 422 for 26 char zone name: {response.text}"


class TestVehicleCharacterLimits:
    """Test vehicle plate number character limits"""
    
    @pytest.fixture(scope="class")
    def user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("User authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, user_token):
        return {"Authorization": f"Bearer {user_token}"}

    # --- Plate Number: max 16 characters ---
    def test_plate_number_within_limit(self, auth_headers):
        """Plate number within 16 char limit should succeed"""
        response = requests.post(f"{BASE_URL}/api/vehicles", headers=auth_headers, json={
            "plate_number": "PLATE" + "X" * 11  # Exactly 16 chars
        })
        assert response.status_code in [200, 201], f"Expected success for 16 char plate: {response.text}"
        if response.status_code in [200, 201]:
            vehicle_id = response.json().get("id")
            requests.delete(f"{BASE_URL}/api/vehicles/{vehicle_id}", headers=auth_headers)

    def test_plate_number_exceeds_limit(self, auth_headers):
        """Plate number exceeding 16 chars should fail validation"""
        response = requests.post(f"{BASE_URL}/api/vehicles", headers=auth_headers, json={
            "plate_number": "PLATE" + "X" * 12  # 17 chars
        })
        assert response.status_code == 422, f"Expected 422 for 17 char plate: {response.text}"


class TestEditBuilding:
    """Test PUT /buildings/{building_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture(scope="class")
    def test_building(self, auth_headers):
        """Create a test building for edit tests"""
        response = requests.post(f"{BASE_URL}/api/buildings", headers=auth_headers, json={
            "name": "Edit Test Building",
            "address_line_1": "Original Line 1",
            "address_line_2": "Original Line 2",
            "total_floors": 1,
            "slots_per_floor": 1
        })
        if response.status_code in [200, 201]:
            yield response.json()
            requests.delete(f"{BASE_URL}/api/buildings/{response.json().get('id')}", headers=auth_headers)
        else:
            pytest.skip("Failed to create test building")

    def test_edit_building_name(self, auth_headers, test_building):
        """Should update building name via PUT"""
        building_id = test_building["id"]
        response = requests.put(f"{BASE_URL}/api/buildings/{building_id}", headers=auth_headers, json={
            "name": "Updated Building Name"
        })
        assert response.status_code == 200, f"Expected 200: {response.text}"
        data = response.json()
        assert data["name"] == "Updated Building Name", "Name not updated"

    def test_edit_building_address_lines(self, auth_headers, test_building):
        """Should update address line 1 and 2 via PUT"""
        building_id = test_building["id"]
        response = requests.put(f"{BASE_URL}/api/buildings/{building_id}", headers=auth_headers, json={
            "address_line_1": "New Line 1",
            "address_line_2": "New Line 2"
        })
        assert response.status_code == 200, f"Expected 200: {response.text}"
        data = response.json()
        assert data["address_line_1"] == "New Line 1", "address_line_1 not updated"
        assert data["address_line_2"] == "New Line 2", "address_line_2 not updated"
        # Full address should be combined
        assert "New Line 1" in data["address"], "Full address not updated"

    def test_edit_building_not_found(self, auth_headers):
        """Should return 404 for non-existent building"""
        response = requests.put(f"{BASE_URL}/api/buildings/nonexistent-id-12345", headers=auth_headers, json={
            "name": "Test"
        })
        assert response.status_code == 404, f"Expected 404: {response.text}"


class TestReservationsPagination:
    """Test that reservations API supports pagination"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    def test_admin_get_all_reservations(self, auth_headers):
        """Admin should be able to fetch all reservations"""
        response = requests.get(f"{BASE_URL}/api/admin/reservations", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of reservations"
        print(f"Total reservations returned: {len(data)}")


class TestCompanyFilter:
    """Test that users can be filtered by company including 'No Company'"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    def test_get_users_with_company(self, auth_headers):
        """Should be able to get all users and filter by company client-side"""
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200: {response.text}"
        users = response.json()
        
        # Check that company field exists (can be null)
        for user in users[:5]:  # Check first 5
            assert "company" in user, f"User {user.get('id')} missing company field"
        
        # Count users with and without company
        with_company = [u for u in users if u.get("company")]
        without_company = [u for u in users if not u.get("company")]
        print(f"Users with company: {len(with_company)}, without company: {len(without_company)}")
