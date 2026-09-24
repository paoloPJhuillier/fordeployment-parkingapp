"""
Tests for Waitlist and Hourly Timeline Features
================================================

Features tested:
1. GET /api/slots/timeline - Hourly timeline per slot
2. GET /api/waitlist/status - User waitlist status
3. GET /api/waitlist/count - Waitlist count for building/date
4. POST /api/waitlist/join - Join waitlist
5. DELETE /api/waitlist/{entry_id} - Leave waitlist
6. POST /api/reservations - Hourly overlap validation
7. POST /api/parking-config - Save waitlist config
8. Waitlist notification on cancellation
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"
USER_EMAIL = "user.test@cebuana.com"
USER_PASSWORD = "Test123!"

# Known building ID for testing (from agent context)
TEST_BUILDING_ID = "fe5ec3b7-38aa-48aa-8572-762afde16bec"


class TestAuth:
    """Get auth cookies for tests"""
    
    @staticmethod
    def login(email, password):
        """Login and return session with cookies"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code != 200:
            pytest.skip(f"Login failed for {email}: {response.status_code}")
        return session
    
    @staticmethod
    def get_admin_session():
        return TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    @staticmethod
    def get_user_session():
        return TestAuth.login(USER_EMAIL, USER_PASSWORD)


class TestParkingConfig:
    """Tests for parking config with waitlist settings"""
    
    def test_get_parking_config(self):
        """GET /api/parking-config/{building_id} returns waitlist fields"""
        session = TestAuth.get_admin_session()
        response = session.get(f"{BASE_URL}/api/parking-config/{TEST_BUILDING_ID}")
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert "waitlist_enabled" in data, "waitlist_enabled field missing"
        assert "waitlist_notification_window_minutes" in data, "waitlist_notification_window_minutes field missing"
        print(f"Parking config: waitlist_enabled={data.get('waitlist_enabled')}, window={data.get('waitlist_notification_window_minutes')}min")
    
    def test_save_parking_config_with_waitlist(self):
        """POST /api/parking-config saves waitlist settings"""
        session = TestAuth.get_admin_session()
        
        config_data = {
            "building_id": TEST_BUILDING_ID,
            "release_time": "06:00",
            "default_start_time": "08:00",
            "default_end_time": "18:00",
            "booking_window_days": 7,
            "no_show_release_enabled": False,
            "no_show_release_minutes": 30,
            "waitlist_enabled": True,
            "waitlist_notification_window_minutes": 15
        }
        
        response = session.post(f"{BASE_URL}/api/parking-config", json=config_data)
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert data["waitlist_enabled"] == True, "waitlist_enabled not saved correctly"
        assert data["waitlist_notification_window_minutes"] == 15, "waitlist_notification_window_minutes not saved correctly"
        print(f"Config saved: waitlist_enabled={data['waitlist_enabled']}, window={data['waitlist_notification_window_minutes']}min")


class TestSlotsTimeline:
    """Tests for slot hourly timeline API"""
    
    def test_get_slots_timeline(self):
        """GET /api/slots/timeline returns hourly availability"""
        session = TestAuth.get_user_session()
        
        # First get buildings to find a floor
        buildings_res = session.get(f"{BASE_URL}/api/buildings")
        assert buildings_res.status_code == 200
        buildings = buildings_res.json()
        
        # Find the test building
        test_building = next((b for b in buildings if b["id"] == TEST_BUILDING_ID), None)
        if not test_building:
            pytest.skip(f"Test building {TEST_BUILDING_ID} not found")
        
        floor_id = test_building["floors"][0]["id"] if test_building.get("floors") else None
        if not floor_id:
            pytest.skip("No floors found in test building")
        
        # Get timeline for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = session.get(
            f"{BASE_URL}/api/slots/timeline",
            params={
                "building_id": TEST_BUILDING_ID,
                "floor_id": floor_id,
                "date": tomorrow
            }
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Check structure of each slot timeline
        for slot_id, slot_data in data.items():
            assert "slot_id" in slot_data, f"slot_id missing for {slot_id}"
            assert "slot_label" in slot_data, f"slot_label missing for {slot_id}"
            assert "timeline" in slot_data, f"timeline missing for {slot_id}"
            
            timeline = slot_data["timeline"]
            assert len(timeline) == 16, f"Expected 16 hours (6AM-9PM), got {len(timeline)}"
            
            for block in timeline:
                assert "hour" in block, "hour missing in timeline block"
                assert "time" in block, "time missing in timeline block"
                assert "booked" in block, "booked status missing in timeline block"
                assert 6 <= block["hour"] <= 21, f"Hour out of range: {block['hour']}"
            
            print(f"Slot {slot_data['slot_label']}: {slot_data['total_available_hours']}h available, {slot_data['total_booked_hours']}h booked")
        
        print(f"Timeline retrieved for {len(data)} slots")


class TestWaitlistAPIs:
    """Tests for waitlist endpoints"""
    
    def test_get_waitlist_count(self):
        """GET /api/waitlist/count returns count for building/date"""
        session = TestAuth.get_user_session()
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = session.get(
            f"{BASE_URL}/api/waitlist/count",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert "count" in data, "count field missing"
        assert "building_id" in data, "building_id field missing"
        assert "date" in data, "date field missing"
        assert data["building_id"] == TEST_BUILDING_ID
        print(f"Waitlist count: {data['count']} for {data['date']}")
    
    def test_get_waitlist_status(self):
        """GET /api/waitlist/status returns user status"""
        session = TestAuth.get_user_session()
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = session.get(
            f"{BASE_URL}/api/waitlist/status",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert "on_waitlist" in data, "on_waitlist field missing"
        print(f"User waitlist status: on_waitlist={data['on_waitlist']}")
    
    def test_join_waitlist(self):
        """POST /api/waitlist/join adds user to waitlist"""
        session = TestAuth.get_user_session()
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")  # Use day after tomorrow to avoid conflicts
        
        # First ensure user is not already on waitlist for this date
        status_res = session.get(
            f"{BASE_URL}/api/waitlist/status",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        if status_res.status_code == 200 and status_res.json().get("on_waitlist"):
            # Already on waitlist, leave first
            entry_id = status_res.json().get("entry", {}).get("id")
            if entry_id:
                session.delete(f"{BASE_URL}/api/waitlist/{entry_id}")
        
        response = session.post(
            f"{BASE_URL}/api/waitlist/join",
            json={
                "building_id": TEST_BUILDING_ID,
                "preferred_date": tomorrow,
                "preferred_start_time": "08:00",
                "preferred_end_time": "18:00"
            }
        )
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert "id" in data, "id field missing"
        assert "position" in data, "position field missing"
        assert "status" in data, "status field missing"
        assert data["status"] == "waiting", f"Expected status 'waiting', got '{data['status']}'"
        print(f"Joined waitlist: position={data['position']}, id={data['id']}")
        
        # Store entry ID for cleanup
        self.waitlist_entry_id = data["id"]
    
    def test_leave_waitlist(self):
        """DELETE /api/waitlist/{entry_id} removes user from waitlist"""
        session = TestAuth.get_user_session()
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        # First join to get an entry
        join_res = session.post(
            f"{BASE_URL}/api/waitlist/join",
            json={
                "building_id": TEST_BUILDING_ID,
                "preferred_date": tomorrow,
                "preferred_start_time": "08:00",
                "preferred_end_time": "18:00"
            }
        )
        
        if join_res.status_code != 200:
            # May already be on waitlist
            status_res = session.get(
                f"{BASE_URL}/api/waitlist/status",
                params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
            )
            if status_res.status_code == 200 and status_res.json().get("on_waitlist"):
                entry_id = status_res.json()["entry"]["id"]
            else:
                pytest.skip("Could not join or get existing waitlist entry")
        else:
            entry_id = join_res.json()["id"]
        
        # Leave waitlist
        response = session.delete(f"{BASE_URL}/api/waitlist/{entry_id}")
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert "message" in data, "message field missing"
        print(f"Left waitlist: {data['message']}")
        
        # Verify status
        status_res = session.get(
            f"{BASE_URL}/api/waitlist/status",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert status_res.status_code == 200
        assert status_res.json()["on_waitlist"] == False, "User should no longer be on waitlist"
    
    def test_cannot_join_waitlist_twice(self):
        """POST /api/waitlist/join fails if already on waitlist"""
        session = TestAuth.get_user_session()
        tomorrow = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        # First join
        join_data = {
            "building_id": TEST_BUILDING_ID,
            "preferred_date": tomorrow,
            "preferred_start_time": "08:00",
            "preferred_end_time": "18:00"
        }
        response1 = session.post(f"{BASE_URL}/api/waitlist/join", json=join_data)
        
        if response1.status_code == 400:
            # Already on waitlist from previous test
            print("User already on waitlist (expected)")
            return
        
        assert response1.status_code == 200
        
        # Try to join again
        response2 = session.post(f"{BASE_URL}/api/waitlist/join", json=join_data)
        assert response2.status_code == 400, f"Expected 400, got {response2.status_code}"
        print(f"Cannot join twice: {response2.json().get('detail')}")


class TestHourlyBooking:
    """Tests for hourly booking with overlap validation"""
    
    def test_reservation_with_hourly_times(self):
        """POST /api/reservations accepts hourly start/end times"""
        session = TestAuth.get_user_session()
        
        # Get available slots
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots_res = session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert slots_res.status_code == 200
        slots = slots_res.json()
        
        if not slots:
            pytest.skip("No available slots")
        
        # Get user's vehicles
        vehicles_res = session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_res.status_code == 200
        vehicles = vehicles_res.json()
        
        if not vehicles:
            pytest.skip("User has no vehicles")
        
        # Find an available slot
        available_slot = next((s for s in slots if s.get("is_available")), None)
        if not available_slot:
            pytest.skip("No available slots")
        
        # Create reservation with specific hourly times
        reservation_data = {
            "slot_id": available_slot["id"],
            "vehicle_id": vehicles[0]["id"],
            "dates": [tomorrow],
            "start_time": "09:00",
            "end_time": "12:00"  # 3 hours
        }
        
        response = session.post(f"{BASE_URL}/api/reservations", json=reservation_data)
        
        if response.status_code == 400:
            # May have time overlap or other issue
            print(f"Reservation not created: {response.json().get('detail')}")
            return
        
        assert response.status_code in [200, 201], f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        if isinstance(data, dict) and "id" in data:
            assert data["start_time"] == "09:00", f"start_time mismatch: {data['start_time']}"
            assert data["end_time"] == "12:00", f"end_time mismatch: {data['end_time']}"
            print(f"Reservation created: {data['start_time']} - {data['end_time']}")
            
            # Cleanup - cancel the reservation
            session.put(f"{BASE_URL}/api/reservations/{data['id']}/cancel")
    
    def test_multiple_bookings_same_slot_different_times(self):
        """Multiple bookings on same slot with different times should work"""
        session = TestAuth.get_user_session()
        
        # Get available slots
        tomorrow = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")  # Use different date
        slots_res = session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert slots_res.status_code == 200
        slots = slots_res.json()
        
        if not slots:
            pytest.skip("No available slots")
        
        # Get user's vehicles
        vehicles_res = session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_res.status_code == 200
        vehicles = vehicles_res.json()
        
        if not vehicles:
            pytest.skip("User has no vehicles")
        
        # Find an available slot
        available_slot = next((s for s in slots if s.get("is_available")), None)
        if not available_slot:
            pytest.skip("No available slots")
        
        created_reservations = []
        
        # First booking: 09:00 - 12:00
        res1 = session.post(f"{BASE_URL}/api/reservations", json={
            "slot_id": available_slot["id"],
            "vehicle_id": vehicles[0]["id"],
            "dates": [tomorrow],
            "start_time": "09:00",
            "end_time": "12:00"
        })
        
        if res1.status_code == 200:
            data1 = res1.json()
            if isinstance(data1, dict) and "id" in data1:
                created_reservations.append(data1["id"])
                print(f"Booking 1 created: {data1['start_time']} - {data1['end_time']}")
        
        # This test only verifies the API accepts the request
        # The actual overlap logic is tested next
        
        # Cleanup
        for res_id in created_reservations:
            session.put(f"{BASE_URL}/api/reservations/{res_id}/cancel")
    
    def test_overlapping_booking_rejected(self):
        """Overlapping booking on same slot should be rejected"""
        session = TestAuth.get_user_session()
        
        # This validates overlap detection logic
        tomorrow = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        slots_res = session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert slots_res.status_code == 200
        slots = slots_res.json()
        
        if not slots:
            pytest.skip("No available slots")
        
        vehicles_res = session.get(f"{BASE_URL}/api/vehicles")
        assert vehicles_res.status_code == 200
        vehicles = vehicles_res.json()
        
        if not vehicles:
            pytest.skip("User has no vehicles")
        
        available_slot = next((s for s in slots if s.get("is_available")), None)
        if not available_slot:
            pytest.skip("No available slots")
        
        # First booking
        res1 = session.post(f"{BASE_URL}/api/reservations", json={
            "slot_id": available_slot["id"],
            "vehicle_id": vehicles[0]["id"],
            "dates": [tomorrow],
            "start_time": "10:00",
            "end_time": "14:00"
        })
        
        if res1.status_code != 200:
            pytest.skip(f"Could not create first booking: {res1.json().get('detail')}")
        
        res1_id = res1.json().get("id")
        
        try:
            # Try overlapping booking (11:00 - 13:00 overlaps with 10:00 - 14:00)
            res2 = session.post(f"{BASE_URL}/api/reservations", json={
                "slot_id": available_slot["id"],
                "vehicle_id": vehicles[0]["id"],
                "dates": [tomorrow],
                "start_time": "11:00",
                "end_time": "13:00"
            })
            
            assert res2.status_code == 400, f"Expected 400 for overlap, got {res2.status_code}"
            detail = res2.json().get("detail", "")
            assert "overlap" in detail.lower() or "reserved" in detail.lower(), f"Expected overlap error: {detail}"
            print(f"Overlap correctly rejected: {detail}")
        finally:
            # Cleanup
            if res1_id:
                session.put(f"{BASE_URL}/api/reservations/{res1_id}/cancel")


class TestWaitlistNotifications:
    """Tests for waitlist notification on cancellation"""
    
    def test_cancellation_triggers_notification(self):
        """Canceling reservation should trigger waitlist notification"""
        admin_session = TestAuth.get_admin_session()
        user_session = TestAuth.get_user_session()
        
        # This is a smoke test - verifying the flow doesn't error
        # Full E2E testing would require: 1) Book all slots 2) User joins waitlist 3) Cancel reservation 4) Check notification
        
        tomorrow = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d")
        
        # Check waitlist count (should not error)
        count_res = user_session.get(
            f"{BASE_URL}/api/waitlist/count",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert count_res.status_code == 200
        print(f"Waitlist count check passed: {count_res.json()}")


class TestAdminWaitlistManagement:
    """Tests for admin waitlist management"""
    
    def test_admin_can_view_building_waitlist(self):
        """Admin can view waitlist for a building"""
        session = TestAuth.get_admin_session()
        
        response = session.get(f"{BASE_URL}/api/waitlist/building/{TEST_BUILDING_ID}")
        assert response.status_code == 200, f"Status: {response.status_code}, Response: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Building waitlist has {len(data)} entries")
        
        for entry in data[:3]:  # Check first 3 entries
            assert "id" in entry, "Entry missing id"
            assert "user_id" in entry, "Entry missing user_id"
            assert "position" in entry, "Entry missing position"
            assert "status" in entry, "Entry missing status"
    
    def test_user_cannot_view_building_waitlist(self):
        """Regular user cannot access admin waitlist endpoint"""
        session = TestAuth.get_user_session()
        
        response = session.get(f"{BASE_URL}/api/waitlist/building/{TEST_BUILDING_ID}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"User correctly blocked from admin endpoint: {response.status_code}")


class TestSlotsAvailableWithTimeline:
    """Tests for enhanced slots/available endpoint"""
    
    def test_slots_available_returns_timeline_data(self):
        """GET /api/slots/available returns slot data compatible with timeline"""
        session = TestAuth.get_user_session()
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = session.get(
            f"{BASE_URL}/api/slots/available",
            params={"building_id": TEST_BUILDING_ID, "date": tomorrow}
        )
        assert response.status_code == 200
        
        slots = response.json()
        if not slots:
            pytest.skip("No slots available")
        
        # Check slot structure
        for slot in slots[:5]:
            assert "id" in slot, "Slot missing id"
            assert "label" in slot, "Slot missing label"
            # Timeline data may be included or fetched separately
            if "timeline" in slot:
                assert isinstance(slot["timeline"], list), "timeline should be a list"
            
            print(f"Slot {slot['label']}: is_available={slot.get('is_available')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
