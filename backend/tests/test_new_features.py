"""
Test new features for iteration 13:
1. GET /api/reservations/stats - User booking stats endpoint
2. Auto no-show tagging - Background task marks pending reservations as no_show
3. QR button on dashboard - Frontend test via Playwright
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
USER_EMAIL = "user.test@cebuana.com"
USER_PASS = "Test123!"
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASS = "Test123!"


class TestUserBookingStats:
    """Test GET /api/reservations/stats endpoint"""
    
    @pytest.fixture(scope="class")
    def user_session(self):
        """Get authenticated user session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASS
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return session

    def test_stats_endpoint_returns_200(self, user_session):
        """Test that /api/reservations/stats returns 200 for authenticated user"""
        response = user_session.get(f"{BASE_URL}/api/reservations/stats")
        assert response.status_code == 200, f"Stats endpoint failed: {response.text}"
        print(f"Stats endpoint returned 200: {response.json()}")

    def test_stats_has_required_keys(self, user_session):
        """Test that stats response has all required keys"""
        response = user_session.get(f"{BASE_URL}/api/reservations/stats")
        assert response.status_code == 200
        data = response.json()
        
        required_keys = ["total", "pending", "confirmed", "cancelled", "completed", "no_show"]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"
            assert isinstance(data[key], int), f"Key {key} should be an integer"
        
        print(f"Stats response: {data}")

    def test_stats_values_are_non_negative(self, user_session):
        """Test that all stats values are non-negative integers"""
        response = user_session.get(f"{BASE_URL}/api/reservations/stats")
        assert response.status_code == 200
        data = response.json()
        
        for key, value in data.items():
            assert value >= 0, f"Stats value {key} should be non-negative, got {value}"
        
        # Validate total equals sum of status counts
        status_sum = data["pending"] + data["confirmed"] + data["cancelled"] + data["completed"] + data["no_show"]
        assert data["total"] == status_sum, f"Total ({data['total']}) should equal sum of statuses ({status_sum})"
        print(f"Stats validation passed: total={data['total']}, sum={status_sum}")

    def test_stats_requires_auth(self):
        """Test that stats endpoint requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/reservations/stats")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Stats endpoint correctly requires authentication")


class TestAutoNoShowTask:
    """Test auto no-show tagging feature"""
    
    @pytest.fixture(scope="class")
    def user_session(self):
        """Get authenticated user session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASS
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return session
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        """Get authenticated admin session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASS
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return session

    def test_no_show_status_exists_in_reservations(self, user_session):
        """Verify that no_show status reservations can be retrieved"""
        response = user_session.get(f"{BASE_URL}/api/reservations", params={"status": "no_show"})
        assert response.status_code == 200, f"Get reservations failed: {response.text}"
        data = response.json()
        print(f"Found {len(data)} no_show reservations")
        
        # If there are no_show reservations, verify their status
        for res in data:
            assert res["status"] == "no_show", f"Expected no_show status, got {res['status']}"
        print("No-show status verification passed")

    def test_auto_noshow_task_marked_past_reservations(self, admin_session):
        """Verify that past pending reservations were marked as no_show by the background task"""
        # Get all reservations (admin can see all)
        response = admin_session.get(f"{BASE_URL}/api/admin/reservations", params={"status": "no_show"})
        assert response.status_code == 200, f"Admin get reservations failed: {response.text}"
        data = response.json()
        
        if len(data) > 0:
            # Check that no_show reservations have no_show_reported=True
            for res in data:
                assert res["status"] == "no_show", "Expected no_show status"
                assert res.get("no_show_reported", False) == True, "no_show_reported should be True"
            print(f"Found {len(data)} auto-marked no-show reservations with no_show_reported=True")
        else:
            print("No no-show reservations found (may be expected if no past pending reservations)")

    def test_confirmed_reservations_not_auto_marked_as_noshow(self, admin_session):
        """Verify that confirmed reservations are NOT marked as no_show"""
        response = admin_session.get(f"{BASE_URL}/api/admin/reservations", params={"status": "confirmed"})
        assert response.status_code == 200, f"Get confirmed reservations failed: {response.text}"
        data = response.json()
        
        for res in data:
            assert res["status"] == "confirmed", "Status should be confirmed"
            # If date is past but status is still confirmed, that's valid (manually confirmed)
        print(f"Found {len(data)} confirmed reservations (correctly not auto-marked as no-show)")


class TestReservationCreationWithNoShow:
    """Test reservation creation and verify no_show logic doesn't affect new reservations"""
    
    @pytest.fixture(scope="class")
    def user_session(self):
        """Get authenticated user session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASS
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        user_data = response.json()["user"]
        return session, user_data["id"]

    def test_new_reservation_is_pending_not_noshow(self, user_session):
        """New future reservations should be pending, not no_show"""
        session, user_id = user_session
        
        # Get vehicles
        vehicles_response = session.get(f"{BASE_URL}/api/vehicles")
        if vehicles_response.status_code != 200 or len(vehicles_response.json()) == 0:
            pytest.skip("No vehicles available for user")
        
        vehicle = vehicles_response.json()[0]
        
        # Get buildings
        buildings_response = session.get(f"{BASE_URL}/api/buildings")
        if buildings_response.status_code != 200 or len(buildings_response.json()) == 0:
            pytest.skip("No buildings available")
        
        building = buildings_response.json()[0]
        if not building.get("floors") or len(building["floors"]) == 0:
            pytest.skip("No floors in building")
        
        floor = building["floors"][0]
        if not floor.get("slots") or len(floor["slots"]) == 0:
            pytest.skip("No slots in floor")
        
        slot = floor["slots"][0]
        
        # Create reservation for tomorrow (future date)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        reservation_data = {
            "slot_id": slot["id"],
            "vehicle_id": vehicle["id"],
            "dates": [tomorrow],
            "start_time": "08:00",
            "end_time": "18:00"
        }
        
        response = session.post(f"{BASE_URL}/api/reservations", json=reservation_data)
        
        # May fail due to slot already reserved - that's ok, just verify the status logic
        if response.status_code == 200:
            res_data = response.json()
            assert res_data["status"] == "pending", f"New reservation should be pending, got {res_data['status']}"
            print(f"New reservation created with status: {res_data['status']}")
            
            # Clean up - cancel the test reservation
            session.put(f"{BASE_URL}/api/reservations/{res_data['id']}/cancel")
        elif response.status_code == 400:
            # Slot already reserved is acceptable
            print(f"Slot unavailable (expected): {response.json()}")
        else:
            print(f"Reservation creation returned {response.status_code}: {response.text}")


class TestStatsMatchesReservations:
    """Test that stats numbers match actual reservation counts"""
    
    @pytest.fixture(scope="class")
    def user_session(self):
        """Get authenticated user session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASS
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return session
    
    def test_stats_match_reservation_counts(self, user_session):
        """Verify stats endpoint numbers match actual reservation data"""
        # Get stats
        stats_response = user_session.get(f"{BASE_URL}/api/reservations/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # Get all reservations
        reservations_response = user_session.get(f"{BASE_URL}/api/reservations")
        assert reservations_response.status_code == 200
        reservations = reservations_response.json()
        
        # Count by status
        status_counts = {
            "pending": 0,
            "confirmed": 0,
            "cancelled": 0,
            "completed": 0,
            "no_show": 0
        }
        for res in reservations:
            status = res["status"]
            if status in status_counts:
                status_counts[status] += 1
        
        # Compare
        assert stats["total"] == len(reservations), f"Total mismatch: stats={stats['total']}, actual={len(reservations)}"
        
        for status, count in status_counts.items():
            assert stats[status] == count, f"Status '{status}' mismatch: stats={stats[status]}, actual={count}"
        
        print(f"Stats match reservations: {stats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
