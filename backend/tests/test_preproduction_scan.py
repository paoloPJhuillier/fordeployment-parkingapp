"""
Pre-Production Full Scan Test Suite
Tests: Auth, Buildings, Hourly Booking, Reservations, Waitlist, Parking Config,
       Building Policies, Notifications, No-Show, Zones
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
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASSWORD = "Test123!"

# Building IDs
CL_TOWER_MAKATI_ID = "fe5ec3b7-38aa-48aa-8572-762afde16bec"  # Waitlist enabled
PACIFIC_STAR_ID = "c723d30a-6353-431d-b606-cb2d59efb852"  # Dedicated slot policy

@pytest.fixture(scope="module")
def admin_session():
    """Admin session with login"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    yield session
    session.close()

@pytest.fixture(scope="module")
def user_session():
    """User session with login"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert resp.status_code == 200, f"User login failed: {resp.text}"
    yield session
    session.close()

@pytest.fixture(scope="module")
def attendant_session():
    """Attendant session with login"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": ATTENDANT_EMAIL, "password": ATTENDANT_PASSWORD})
    assert resp.status_code == 200, f"Attendant login failed: {resp.text}"
    yield session
    session.close()


# --- AUTH TESTS ---
class TestAuth:
    """Test cookie-based authentication for all roles"""
    
    def test_admin_login(self):
        """Admin can login and get access_token cookie"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        data = resp.json()
        assert "user" in data
        assert data["user"]["role"] == "admin"
        # Verify cookie is set by checking /me
        me_resp = session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200
        print(f"PASS: Admin login successful - {data['user']['email']}")
    
    def test_user_login(self):
        """Regular user can login"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
        assert resp.status_code == 200, f"User login failed: {resp.text}"
        data = resp.json()
        assert data["user"]["role"] == "user"
        print(f"PASS: User login successful - {data['user']['email']}")
    
    def test_attendant_login(self):
        """Attendant can login"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": ATTENDANT_EMAIL, "password": ATTENDANT_PASSWORD})
        assert resp.status_code == 200, f"Attendant login failed: {resp.text}"
        data = resp.json()
        assert data["user"]["role"] == "attendant"
        print(f"PASS: Attendant login successful - {data['user']['email']}")
    
    def test_invalid_login(self):
        """Invalid credentials returns 401"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": "nonexistent@test.com", "password": "wrongpass"})
        assert resp.status_code == 401
        print("PASS: Invalid login correctly rejected")
    
    def test_role_based_access_admin_only(self, user_session):
        """User cannot access admin-only endpoints"""
        resp = user_session.get(f"{BASE_URL}/api/zones")
        assert resp.status_code == 403
        print("PASS: User correctly denied access to admin-only /api/zones")


# --- BUILDINGS TESTS ---
class TestBuildings:
    """Test building endpoints"""
    
    def test_get_buildings(self, user_session):
        """GET /api/buildings returns building list with floors"""
        resp = user_session.get(f"{BASE_URL}/api/buildings")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "Expected at least one building"
        # Check structure
        for bldg in data[:3]:
            assert "id" in bldg
            assert "name" in bldg
            assert "floors" in bldg
        print(f"PASS: GET /api/buildings returned {len(data)} buildings")
    
    def test_building_has_floors_and_slots(self, user_session):
        """Buildings contain floors with slots"""
        resp = user_session.get(f"{BASE_URL}/api/buildings")
        assert resp.status_code == 200
        data = resp.json()
        # Find CL Tower Makati
        cl_tower = next((b for b in data if b["id"] == CL_TOWER_MAKATI_ID), None)
        if cl_tower:
            assert len(cl_tower.get("floors", [])) > 0, "CL Tower should have floors"
            if cl_tower["floors"]:
                first_floor = cl_tower["floors"][0]
                assert "id" in first_floor
                assert "label" in first_floor
                assert "slots" in first_floor
            print(f"PASS: CL Tower Makati has {len(cl_tower.get('floors', []))} floors")


# --- HOURLY BOOKING FLOW TESTS ---
class TestHourlyBooking:
    """Test hourly slot availability and booking"""
    
    def test_slots_available_with_timeline(self, user_session):
        """GET /api/slots/available returns slots with 24-hour timeline"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        resp = user_session.get(f"{BASE_URL}/api/slots/available?building_id={CL_TOWER_MAKATI_ID}&date={tomorrow}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            slot = data[0]
            assert "timeline" in slot, "Slot should have timeline array"
            timeline = slot["timeline"]
            assert isinstance(timeline, list)
            # Check that timeline has 24 hours (0-23)
            hours = [t["hour"] for t in timeline]
            assert 0 in hours, "Timeline should start at hour 0"
            assert 23 in hours, "Timeline should end at hour 23"
            # Check timeline structure
            for block in timeline[:3]:
                assert "hour" in block
                assert "time" in block
                assert "booked" in block
            print(f"PASS: GET /api/slots/available returns timeline with {len(timeline)} hours")
        else:
            print("SKIP: No slots available for this building/date")
    
    def test_overlap_validation_same_user(self, user_session):
        """Same user cannot book overlapping times on same date"""
        # Get user's vehicles
        vehicles_resp = user_session.get(f"{BASE_URL}/api/vehicles")
        if vehicles_resp.status_code != 200 or len(vehicles_resp.json()) == 0:
            pytest.skip("User has no vehicles")
        vehicle_id = vehicles_resp.json()[0]["id"]
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots_resp = user_session.get(f"{BASE_URL}/api/slots/available?building_id={CL_TOWER_MAKATI_ID}&date={tomorrow}")
        slots = slots_resp.json()
        available_slots = [sl for sl in slots if sl.get("is_available")]
        if len(available_slots) < 2:
            pytest.skip("Not enough available slots")
        
        slot1 = available_slots[0]
        slot2 = available_slots[1]
        
        # Book first slot 10:00-12:00
        resp1 = user_session.post(f"{BASE_URL}/api/reservations", json={
            "slot_id": slot1["id"],
            "vehicle_id": vehicle_id,
            "dates": [tomorrow],
            "start_time": "10:00",
            "end_time": "12:00"
        })
        if resp1.status_code != 200:
            pytest.skip(f"Could not create first booking: {resp1.text}")
        res1_data = resp1.json()
        res1_id = res1_data.get("id") or res1_data.get("reservations", [{}])[0].get("id")
        
        # Try to book different slot with overlapping time (11:00-13:00)
        resp2 = user_session.post(f"{BASE_URL}/api/reservations", json={
            "slot_id": slot2["id"],
            "vehicle_id": vehicle_id,
            "dates": [tomorrow],
            "start_time": "11:00",
            "end_time": "13:00"
        })
        
        # Clean up first
        user_session.put(f"{BASE_URL}/api/reservations/{res1_id}/cancel")
        
        assert resp2.status_code == 400, "Overlapping booking should be rejected"
        assert "overlap" in resp2.text.lower() or "already" in resp2.text.lower()
        print("PASS: Overlap validation - same user cannot book overlapping times")


# --- RESERVATION MANAGEMENT TESTS ---
class TestReservationManagement:
    """Test reservation CRUD operations"""
    
    def test_get_user_reservations(self, user_session):
        """GET /api/reservations returns user's reservations"""
        resp = user_session.get(f"{BASE_URL}/api/reservations")
        assert resp.status_code == 200, f"Get reservations failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/reservations returned {len(data)} reservations")
    
    def test_cancel_reservation(self, user_session):
        """PUT /api/reservations/{id}/cancel cancels reservation"""
        # Get user's vehicles
        vehicles_resp = user_session.get(f"{BASE_URL}/api/vehicles")
        if vehicles_resp.status_code != 200 or len(vehicles_resp.json()) == 0:
            pytest.skip("User has no vehicles")
        vehicle_id = vehicles_resp.json()[0]["id"]
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots_resp = user_session.get(f"{BASE_URL}/api/slots/available?building_id={CL_TOWER_MAKATI_ID}&date={tomorrow}")
        slots = slots_resp.json()
        available_slot = next((sl for sl in slots if sl.get("is_available")), None)
        if not available_slot:
            pytest.skip("No available slots")
        
        # Create
        create_resp = user_session.post(f"{BASE_URL}/api/reservations", json={
            "slot_id": available_slot["id"],
            "vehicle_id": vehicle_id,
            "dates": [tomorrow],
            "start_time": "08:00",
            "end_time": "09:00"
        })
        if create_resp.status_code != 200:
            pytest.skip(f"Could not create reservation: {create_resp.text}")
        res_data = create_resp.json()
        res_id = res_data.get("id") or res_data.get("reservations", [{}])[0].get("id")
        
        # Cancel
        cancel_resp = user_session.put(f"{BASE_URL}/api/reservations/{res_id}/cancel")
        assert cancel_resp.status_code == 200
        
        # Verify cancelled
        reservations_resp = user_session.get(f"{BASE_URL}/api/reservations")
        reservations = reservations_resp.json()
        cancelled = next((r for r in reservations if r["id"] == res_id), None)
        assert cancelled is not None
        assert cancelled["status"] == "cancelled"
        print("PASS: Reservation cancelled successfully")


# --- WAITLIST TESTS ---
class TestWaitlist:
    """Test waitlist functionality (for CL Tower Makati)"""
    
    def test_waitlist_count(self, user_session):
        """GET /api/waitlist/count returns count for building/date"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        resp = user_session.get(f"{BASE_URL}/api/waitlist/count?building_id={CL_TOWER_MAKATI_ID}&date={tomorrow}")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "building_id" in data
        assert "date" in data
        print(f"PASS: GET /api/waitlist/count returns count={data['count']}")
    
    def test_waitlist_status(self, user_session):
        """GET /api/waitlist/status returns user's waitlist position"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        resp = user_session.get(f"{BASE_URL}/api/waitlist/status?building_id={CL_TOWER_MAKATI_ID}&date={tomorrow}")
        assert resp.status_code == 200
        data = resp.json()
        assert "on_waitlist" in data
        print(f"PASS: GET /api/waitlist/status - on_waitlist={data['on_waitlist']}")
    
    def test_waitlist_join_and_leave(self, user_session):
        """POST /api/waitlist/join and DELETE /api/waitlist/{id}"""
        # Check waitlist is enabled
        config_resp = user_session.get(f"{BASE_URL}/api/parking-config/{CL_TOWER_MAKATI_ID}")
        if config_resp.status_code != 200:
            pytest.skip("Could not get parking config")
        config = config_resp.json()
        if not config.get("waitlist_enabled"):
            pytest.skip("Waitlist not enabled for this building")
        
        future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        # First leave if already on waitlist
        status_resp = user_session.get(f"{BASE_URL}/api/waitlist/status?building_id={CL_TOWER_MAKATI_ID}&date={future_date}")
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            if status_data.get("on_waitlist") and status_data.get("entry"):
                user_session.delete(f"{BASE_URL}/api/waitlist/{status_data['entry']['id']}")
        
        # Join waitlist
        join_resp = user_session.post(f"{BASE_URL}/api/waitlist/join", json={
            "building_id": CL_TOWER_MAKATI_ID,
            "preferred_date": future_date,
            "preferred_start_time": "08:00",
            "preferred_end_time": "18:00"
        })
        assert join_resp.status_code == 200, f"Join waitlist failed: {join_resp.text}"
        join_data = join_resp.json()
        assert "id" in join_data
        assert "position" in join_data
        entry_id = join_data["id"]
        print(f"PASS: Joined waitlist at position {join_data['position']}")
        
        # Try joining again - should fail
        dup_resp = user_session.post(f"{BASE_URL}/api/waitlist/join", json={
            "building_id": CL_TOWER_MAKATI_ID,
            "preferred_date": future_date,
            "preferred_start_time": "08:00",
            "preferred_end_time": "18:00"
        })
        assert dup_resp.status_code == 400, "Duplicate join should be rejected"
        print("PASS: Duplicate waitlist join correctly rejected")
        
        # Leave waitlist
        leave_resp = user_session.delete(f"{BASE_URL}/api/waitlist/{entry_id}")
        assert leave_resp.status_code == 200
        print("PASS: Left waitlist successfully")


# --- PARKING CONFIG TESTS ---
class TestParkingConfig:
    """Test parking configuration endpoints"""
    
    def test_get_parking_config(self, admin_session):
        """GET /api/parking-config/{building_id} returns config with waitlist fields"""
        resp = admin_session.get(f"{BASE_URL}/api/parking-config/{CL_TOWER_MAKATI_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert "building_id" in data
        assert "release_time" in data
        assert "default_start_time" in data
        assert "default_end_time" in data
        assert "waitlist_enabled" in data
        assert "waitlist_notification_window_minutes" in data
        print(f"PASS: GET parking config - waitlist_enabled={data.get('waitlist_enabled')}, window={data.get('waitlist_notification_window_minutes')}min")
    
    def test_save_parking_config(self, admin_session):
        """POST /api/parking-config saves config including waitlist fields"""
        # Get current config
        get_resp = admin_session.get(f"{BASE_URL}/api/parking-config/{CL_TOWER_MAKATI_ID}")
        current_config = get_resp.json()
        
        # Update with same values (to not break anything)
        save_resp = admin_session.post(f"{BASE_URL}/api/parking-config", json={
            "building_id": CL_TOWER_MAKATI_ID,
            "release_time": current_config.get("release_time", "06:00"),
            "default_start_time": current_config.get("default_start_time", "08:00"),
            "default_end_time": current_config.get("default_end_time", "18:00"),
            "booking_window_days": current_config.get("booking_window_days", 7),
            "no_show_release_enabled": current_config.get("no_show_release_enabled", False),
            "no_show_release_minutes": current_config.get("no_show_release_minutes", 30),
            "waitlist_enabled": current_config.get("waitlist_enabled", True),
            "waitlist_notification_window_minutes": current_config.get("waitlist_notification_window_minutes", 15)
        })
        assert save_resp.status_code == 200, f"Save config failed: {save_resp.text}"
        data = save_resp.json()
        assert data["waitlist_enabled"] == current_config.get("waitlist_enabled", True)
        print("PASS: POST /api/parking-config saves config successfully")


# --- BUILDING POLICIES TESTS ---
class TestBuildingPolicies:
    """Test building policies for Pacific Star (dedicated slot policy)"""
    
    def test_get_building_policy(self, admin_session):
        """GET /api/building-policies/{building_id} returns policy"""
        resp = admin_session.get(f"{BASE_URL}/api/building-policies/{PACIFIC_STAR_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert "building_id" in data
        assert "enabled" in data
        if data.get("enabled"):
            assert "policy_type" in data
            assert "max_users_per_slot" in data
        print(f"PASS: GET building policy - enabled={data.get('enabled')}, policy_type={data.get('policy_type')}")
    
    def test_slot_registrations_list(self, admin_session):
        """GET /api/slot-registrations returns registrations for building"""
        resp = admin_session.get(f"{BASE_URL}/api/slot-registrations?building_id={PACIFIC_STAR_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"PASS: GET slot-registrations returned {len(data)} registrations")


# --- NOTIFICATIONS TESTS ---
class TestNotifications:
    """Test notification endpoints"""
    
    def test_get_notifications(self, user_session):
        """GET /api/notifications returns user notifications"""
        resp = user_session.get(f"{BASE_URL}/api/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/notifications returned {len(data)} notifications")
    
    def test_get_unread_count(self, user_session):
        """GET /api/notifications/unread-count returns count"""
        resp = user_session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        print(f"PASS: GET unread-count = {data['count']}")
    
    def test_mark_all_read(self, user_session):
        """PUT /api/notifications/read-all marks all read"""
        resp = user_session.put(f"{BASE_URL}/api/notifications/read-all")
        assert resp.status_code == 200
        print("PASS: PUT /api/notifications/read-all successful")


# --- ZONES TESTS ---
class TestZones:
    """Test zone management"""
    
    def test_get_zones(self, admin_session):
        """GET /api/zones returns zones with building_ids and user_ids"""
        resp = admin_session.get(f"{BASE_URL}/api/zones")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for zone in data[:3]:
            assert "id" in zone
            assert "name" in zone
            assert "building_ids" in zone
            assert "user_ids" in zone
        print(f"PASS: GET /api/zones returned {len(data)} zones")
    
    def test_user_building_assignments(self, user_session):
        """GET /api/zones/user-buildings returns user's assigned buildings"""
        resp = user_session.get(f"{BASE_URL}/api/zones/user-buildings")
        assert resp.status_code == 200
        data = resp.json()
        assert "building_ids" in data
        assert "zones" in data
        print(f"PASS: User assigned to {len(data['building_ids'])} buildings via {len(data['zones'])} zones")


# --- ATTENDANT TESTS ---
class TestAttendant:
    """Test attendant-specific endpoints"""
    
    def test_attendant_daily_reservations(self, attendant_session):
        """GET /api/attendant/daily-reservations returns today's reservations"""
        today = datetime.now().strftime("%Y-%m-%d")
        resp = attendant_session.get(f"{BASE_URL}/api/attendant/daily-reservations?date={today}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"PASS: Attendant sees {len(data)} reservations for today")
    
    def test_attendant_buildings(self, attendant_session):
        """GET /api/attendant/buildings returns attendant's assigned buildings"""
        resp = attendant_session.get(f"{BASE_URL}/api/attendant/buildings")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"PASS: Attendant has {len(data)} assigned buildings")


# --- QR CODE TESTS ---
class TestQRCode:
    """Test QR code functionality"""
    
    def test_get_qr_code(self, user_session):
        """GET /api/reservations/{id}/qr returns QR code"""
        # Get user reservations
        res_resp = user_session.get(f"{BASE_URL}/api/reservations")
        reservations = res_resp.json()
        if not isinstance(reservations, list):
            pytest.skip(f"Unexpected reservations response: {reservations}")
        
        pending_res = next((r for r in reservations if r.get("status") in ["pending", "confirmed"]), None)
        
        if not pending_res:
            pytest.skip("No active reservations to test QR")
        
        qr_resp = user_session.get(f"{BASE_URL}/api/reservations/{pending_res['id']}/qr")
        assert qr_resp.status_code == 200
        data = qr_resp.json()
        assert "qr_code" in data
        assert "qr_token" in data
        print("PASS: GET QR code returns qr_code and qr_token")


# --- RESERVATION STATS TESTS ---
class TestReservationStats:
    """Test reservation statistics"""
    
    def test_get_user_stats(self, user_session):
        """GET /api/reservations/stats returns booking statistics"""
        resp = user_session.get(f"{BASE_URL}/api/reservations/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "pending" in data
        assert "confirmed" in data
        assert "cancelled" in data
        assert "completed" in data
        assert "no_show" in data
        print(f"PASS: User stats - total={data['total']}, no_show={data['no_show']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
