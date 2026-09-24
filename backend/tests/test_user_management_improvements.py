"""
Test User Management Improvements:
1. GET /api/users returns updated_at field
2. POST /api/users/bulk-set-building works with valid data
3. POST /api/users/bulk-set-building rejects empty user_ids
4. POST /api/users/bulk-assign-zone works with valid data
5. POST /api/users/bulk-assign-zone rejects invalid zone_id
6. CSV template includes main_building and zone columns
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestUserManagementImprovements:
    """Tests for new User Management features"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        """Create authenticated admin session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed - skipping tests")
        return session

    @pytest.fixture(scope="class")
    def test_user_ids(self, admin_session):
        """Get some user IDs for testing"""
        response = admin_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        users = response.json()
        # Get first 2 user IDs that are not admins
        user_ids = [u["id"] for u in users if u["role"] == "user"][:2]
        assert len(user_ids) >= 1, "Need at least 1 user for testing"
        return user_ids

    @pytest.fixture(scope="class")
    def zone_ids(self, admin_session):
        """Get zone IDs for testing"""
        response = admin_session.get(f"{BASE_URL}/api/zones")
        assert response.status_code == 200
        zones = response.json()
        return [z["id"] for z in zones]

    @pytest.fixture(scope="class")
    def building_ids(self, admin_session):
        """Get building IDs for testing"""
        response = admin_session.get(f"{BASE_URL}/api/buildings")
        assert response.status_code == 200
        buildings = response.json()
        return [b["id"] for b in buildings]

    # Test 1: GET /api/users returns updated_at field
    def test_users_response_has_updated_at_field(self, admin_session):
        """Test that GET /api/users returns updated_at field in response"""
        response = admin_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0, "Should have at least one user"
        
        # Check first user has updated_at field (can be null)
        first_user = users[0]
        assert "updated_at" in first_user, "Response should include updated_at field"
        assert "created_at" in first_user, "Response should include created_at field"
        print(f"PASS: GET /api/users includes updated_at field. Sample: {first_user.get('updated_at')}")

    # Test 2: POST /api/users/bulk-set-building with valid data
    def test_bulk_set_building_success(self, admin_session, test_user_ids, building_ids):
        """Test bulk-set-building with valid user_ids and building"""
        if not building_ids:
            pytest.skip("No buildings available for testing")
        
        building_id = building_ids[0]
        payload = {
            "user_ids": test_user_ids,
            "main_building": building_id
        }
        response = admin_session.post(f"{BASE_URL}/api/users/bulk-set-building", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "modified" in data
        assert data["modified"] >= 0
        print(f"PASS: bulk-set-building modified {data['modified']} users")

    # Test 3: POST /api/users/bulk-set-building rejects empty user_ids
    def test_bulk_set_building_empty_user_ids(self, admin_session, building_ids):
        """Test bulk-set-building rejects empty user_ids list"""
        if not building_ids:
            pytest.skip("No buildings available for testing")
        
        payload = {
            "user_ids": [],
            "main_building": building_ids[0]
        }
        response = admin_session.post(f"{BASE_URL}/api/users/bulk-set-building", json=payload)
        assert response.status_code == 400, f"Expected 400 for empty user_ids, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        assert "No users selected" in data["detail"] or "user" in data["detail"].lower()
        print(f"PASS: bulk-set-building correctly rejects empty user_ids")

    # Test 4: POST /api/users/bulk-set-building to remove building (null)
    def test_bulk_set_building_remove(self, admin_session, test_user_ids):
        """Test bulk-set-building to remove main building (set to null)"""
        payload = {
            "user_ids": test_user_ids[:1],
            "main_building": None
        }
        response = admin_session.post(f"{BASE_URL}/api/users/bulk-set-building", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "modified" in data
        print(f"PASS: bulk-set-building can set main_building to null")

    # Test 5: POST /api/users/bulk-assign-zone with valid data
    def test_bulk_assign_zone_success(self, admin_session, test_user_ids, zone_ids):
        """Test bulk-assign-zone with valid user_ids and zone_id"""
        if not zone_ids:
            pytest.skip("No zones available for testing")
        
        zone_id = zone_ids[0]
        payload = {
            "user_ids": test_user_ids,
            "zone_id": zone_id
        }
        response = admin_session.post(f"{BASE_URL}/api/users/bulk-assign-zone", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "zone_name" in data
        print(f"PASS: bulk-assign-zone added users to zone '{data['zone_name']}'")

    # Test 6: POST /api/users/bulk-assign-zone rejects invalid zone_id
    def test_bulk_assign_zone_invalid_zone(self, admin_session, test_user_ids):
        """Test bulk-assign-zone rejects invalid zone_id"""
        invalid_zone_id = str(uuid.uuid4())
        payload = {
            "user_ids": test_user_ids,
            "zone_id": invalid_zone_id
        }
        response = admin_session.post(f"{BASE_URL}/api/users/bulk-assign-zone", json=payload)
        assert response.status_code == 404, f"Expected 404 for invalid zone, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        assert "Zone not found" in data["detail"] or "not found" in data["detail"].lower()
        print(f"PASS: bulk-assign-zone correctly rejects invalid zone_id")

    # Test 7: POST /api/users/bulk-assign-zone rejects empty user_ids
    def test_bulk_assign_zone_empty_user_ids(self, admin_session, zone_ids):
        """Test bulk-assign-zone rejects empty user_ids list"""
        if not zone_ids:
            pytest.skip("No zones available for testing")
        
        payload = {
            "user_ids": [],
            "zone_id": zone_ids[0]
        }
        response = admin_session.post(f"{BASE_URL}/api/users/bulk-assign-zone", json=payload)
        assert response.status_code == 400, f"Expected 400 for empty user_ids, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        print(f"PASS: bulk-assign-zone correctly rejects empty user_ids")

    # Test 8: CSV template includes main_building and zone columns
    def test_users_template_has_new_columns(self, admin_session):
        """Test that users template CSV includes main_building and zone columns"""
        response = admin_session.get(f"{BASE_URL}/api/templates/users")
        assert response.status_code == 200
        
        csv_content = response.text
        # Check headers
        first_line = csv_content.split('\n')[0].lower()
        assert "main_building" in first_line, "Template should have main_building column"
        assert "zone" in first_line, "Template should have zone column"
        print(f"PASS: Template CSV includes main_building and zone columns")
        print(f"Template headers: {first_line}")

    # Test 9: Verify updated_at is set after update
    def test_updated_at_set_after_bulk_update(self, admin_session, test_user_ids, building_ids):
        """Test that updated_at is set after bulk update"""
        if not building_ids:
            pytest.skip("No buildings available for testing")
        
        # First, do a bulk update
        payload = {
            "user_ids": test_user_ids[:1],
            "main_building": building_ids[0]
        }
        response = admin_session.post(f"{BASE_URL}/api/users/bulk-set-building", json=payload)
        assert response.status_code == 200
        
        # Then verify the user has updated_at set
        response = admin_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        users = response.json()
        
        updated_user = next((u for u in users if u["id"] == test_user_ids[0]), None)
        if updated_user:
            # updated_at should be set after bulk update
            assert updated_user.get("updated_at") is not None, "updated_at should be set after bulk update"
            print(f"PASS: updated_at is set after bulk update: {updated_user['updated_at']}")
        else:
            print("WARN: Could not find updated user to verify updated_at")


class TestUserManagementAPIAuth:
    """Test that bulk endpoints require admin auth"""

    def test_bulk_set_building_requires_auth(self):
        """Test bulk-set-building requires authentication"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/users/bulk-set-building", json={
            "user_ids": ["test"],
            "main_building": "test"
        })
        assert response.status_code == 401, "Should require auth"
        print("PASS: bulk-set-building requires authentication")

    def test_bulk_assign_zone_requires_auth(self):
        """Test bulk-assign-zone requires authentication"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/users/bulk-assign-zone", json={
            "user_ids": ["test"],
            "zone_id": "test"
        })
        assert response.status_code == 401, "Should require auth"
        print("PASS: bulk-assign-zone requires authentication")

    def test_template_requires_auth(self):
        """Test template download requires admin auth"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/templates/users")
        assert response.status_code == 401, "Should require auth"
        print("PASS: template download requires authentication")
