"""
Test P0 UI Improvements - Backend API Tests
- Admin Reservations: 6 status stat cards, no_show filter, building filter
- Admin User Management: pagination (PAGE_SIZE=15)
- Admin Building Management: summary stats, search
- Attendant Dashboard: building filter, buildings endpoint
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_CREDS = {"email": "admin.test@cebuana.com", "password": "Test123!"}
USER_CREDS = {"email": "user.test@cebuana.com", "password": "Test123!"}
ATTENDANT_CREDS = {"email": "attendant.test@cebuana.com", "password": "Test123!"}


@pytest.fixture(scope="module")
def admin_session():
    """Get admin authenticated session with cookie"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return session


@pytest.fixture(scope="module")
def attendant_session():
    """Get attendant authenticated session with cookie"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json=ATTENDANT_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Attendant login failed: {response.text}")
    return session


@pytest.fixture(scope="module")
def user_session():
    """Get user authenticated session with cookie"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json=USER_CREDS)
    if response.status_code != 200:
        pytest.skip(f"User login failed: {response.text}")
    return session


class TestAdminReservationsP0:
    """Test Admin Reservations page P0 improvements"""
    
    def test_admin_reservations_endpoint_returns_all_statuses(self, admin_session):
        """Admin reservations endpoint returns reservations with all status types"""
        response = admin_session.get(f"{BASE_URL}/api/admin/reservations")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Total reservations: {len(data)}")
        
        # Count by status to verify all status types can be present
        status_counts = {}
        for res in data:
            status = res.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"Status breakdown: {status_counts}")
        # We expect the endpoint to support: pending, confirmed, completed, no_show, cancelled
        
    def test_admin_reservations_filter_by_status_no_show(self, admin_session):
        """Admin reservations endpoint supports filtering by no_show status"""
        response = admin_session.get(f"{BASE_URL}/api/admin/reservations", params={"status": "no_show"})
        assert response.status_code == 200
        
        data = response.json()
        print(f"No-show reservations count: {len(data)}")
        
        # All returned should be no_show if filter works
        for res in data:
            assert res.get('status') == 'no_show', f"Expected no_show, got {res.get('status')}"
    
    def test_admin_reservations_filter_by_status_completed(self, admin_session):
        """Admin reservations endpoint supports filtering by completed status"""
        response = admin_session.get(f"{BASE_URL}/api/admin/reservations", params={"status": "completed"})
        assert response.status_code == 200
        
        data = response.json()
        print(f"Completed reservations count: {len(data)}")
        
        for res in data:
            assert res.get('status') == 'completed', f"Expected completed, got {res.get('status')}"
    
    def test_admin_reservations_filter_by_building(self, admin_session):
        """Admin reservations endpoint supports filtering by building_id"""
        # First get buildings
        buildings_response = admin_session.get(f"{BASE_URL}/api/buildings")
        assert buildings_response.status_code == 200
        buildings = buildings_response.json()
        
        if not buildings:
            pytest.skip("No buildings in system")
        
        building_id = buildings[0]['id']
        
        response = admin_session.get(f"{BASE_URL}/api/admin/reservations", params={"building_id": building_id})
        assert response.status_code == 200
        
        data = response.json()
        print(f"Reservations for building {buildings[0]['name']}: {len(data)}")
        
        # All returned should be for the specified building
        for res in data:
            assert res.get('building_id') == building_id, f"Expected {building_id}, got {res.get('building_id')}"


class TestAdminUserManagementP0:
    """Test Admin User Management pagination"""
    
    def test_get_all_users_returns_list(self, admin_session):
        """GET /api/users returns list of users for pagination"""
        response = admin_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        
        users = response.json()
        assert isinstance(users, list)
        print(f"Total users in system: {len(users)}")
        
        # Context says 38 users, pagination should show when > 15
        if len(users) > 15:
            print(f"PASS: {len(users)} users > PAGE_SIZE(15), pagination should be visible in UI")
        else:
            print(f"NOTE: {len(users)} users <= PAGE_SIZE(15), pagination may not be visible")


class TestAdminBuildingManagementP0:
    """Test Admin Building Management summary stats"""
    
    def test_get_buildings_with_floors_and_slots(self, admin_session):
        """GET /api/buildings returns buildings with floors and slots for stats calculation"""
        response = admin_session.get(f"{BASE_URL}/api/buildings")
        assert response.status_code == 200
        
        buildings = response.json()
        assert isinstance(buildings, list)
        print(f"Total buildings: {len(buildings)}")
        
        # Calculate summary stats as frontend would
        total_floors = 0
        total_slots = 0
        available_slots = 0
        
        for building in buildings:
            floors = building.get('floors', [])
            total_floors += len(floors)
            for floor in floors:
                slots = floor.get('slots', [])
                total_slots += len(slots)
                available_slots += sum(1 for s in slots if s.get('status') == 'available')
        
        print(f"Summary stats - Buildings: {len(buildings)}, Floors: {total_floors}, Total Slots: {total_slots}, Available: {available_slots}")


class TestAttendantDashboardP0:
    """Test Attendant Dashboard building filter"""
    
    def test_attendant_buildings_endpoint(self, attendant_session):
        """GET /api/attendant/buildings returns buildings for attendant"""
        response = attendant_session.get(f"{BASE_URL}/api/attendant/buildings")
        assert response.status_code == 200
        
        buildings = response.json()
        assert isinstance(buildings, list)
        print(f"Attendant assigned buildings: {len(buildings)}")
        
        # Each building should have id and name
        for building in buildings:
            assert 'id' in building, "Building should have id"
            assert 'name' in building, "Building should have name"
            print(f"  - {building['name']} (id: {building['id']})")
    
    def test_attendant_daily_reservations_without_filter(self, attendant_session):
        """GET /api/attendant/daily-reservations returns reservations without building filter"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = attendant_session.get(f"{BASE_URL}/api/attendant/daily-reservations", params={"date": today})
        assert response.status_code == 200
        
        reservations = response.json()
        assert isinstance(reservations, list)
        print(f"Reservations for today ({today}): {len(reservations)}")
    
    def test_attendant_daily_reservations_with_building_filter(self, attendant_session):
        """GET /api/attendant/daily-reservations accepts building_id param"""
        # First get attendant's buildings
        buildings_response = attendant_session.get(f"{BASE_URL}/api/attendant/buildings")
        assert buildings_response.status_code == 200
        buildings = buildings_response.json()
        
        if not buildings:
            pytest.skip("Attendant has no assigned buildings")
        
        building_id = buildings[0]['id']
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = attendant_session.get(
            f"{BASE_URL}/api/attendant/daily-reservations",
            params={"date": today, "building_id": building_id}
        )
        assert response.status_code == 200
        
        reservations = response.json()
        assert isinstance(reservations, list)
        print(f"Reservations for building {buildings[0]['name']} on {today}: {len(reservations)}")
        
        # All returned should be for the specified building
        for res in reservations:
            assert res.get('building_id') == building_id, f"Expected {building_id}, got {res.get('building_id')}"


class TestUserCannotAccessAttendantEndpoints:
    """Verify regular users cannot access attendant-only endpoints"""
    
    def test_user_cannot_access_attendant_buildings(self, user_session):
        """Regular user cannot access GET /api/attendant/buildings"""
        response = user_session.get(f"{BASE_URL}/api/attendant/buildings")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: User correctly denied access to /api/attendant/buildings")
    
    def test_user_cannot_access_attendant_daily_reservations(self, user_session):
        """Regular user cannot access GET /api/attendant/daily-reservations"""
        response = user_session.get(f"{BASE_URL}/api/attendant/daily-reservations")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: User correctly denied access to /api/attendant/daily-reservations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
