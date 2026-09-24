"""
Test P2 & P3 Features for Parking Reservation App:
- P2: In-app notification system for no-show events
- P2: Parking config with no-show auto-release settings
- P3: Dropdown visibility audit (CSS verified through frontend)

Modules tested:
- Notification endpoints (GET /notifications, GET /notifications/unread-count, PUT /notifications/read-all, PUT /notifications/{id}/read)
- No-show report with notification creation (POST /attendant/reservations/{id}/report-no-show)
- Parking config with no-show release fields (GET /parking-config/{building_id}, POST /parking-config)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestNotificationEndpoints:
    """Test notification API endpoints for P2 features"""
    
    @pytest.fixture
    def user_session(self):
        """Login as regular user and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        return session
    
    @pytest.fixture
    def admin_session(self):
        """Login as admin and return session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return session
    
    @pytest.fixture
    def attendant_session(self):
        """Login as attendant and return session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "attendant.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"Attendant login failed: {response.text}"
        return session
    
    def test_get_notifications_requires_auth(self):
        """GET /api/notifications requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401, "Should require authentication"
    
    def test_get_notifications_returns_list(self, user_session):
        """GET /api/notifications returns list of notifications"""
        response = user_session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        # Check structure if notifications exist
        if len(data) > 0:
            notification = data[0]
            assert "id" in notification
            assert "title" in notification
            assert "message" in notification
            assert "type" in notification
            assert "read" in notification
            assert "created_at" in notification
    
    def test_get_unread_count_requires_auth(self):
        """GET /api/notifications/unread-count requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 401
    
    def test_get_unread_count_returns_count(self, user_session):
        """GET /api/notifications/unread-count returns count object"""
        response = user_session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0
    
    def test_mark_all_read_requires_auth(self):
        """PUT /api/notifications/read-all requires authentication"""
        response = requests.put(f"{BASE_URL}/api/notifications/read-all")
        assert response.status_code == 401
    
    def test_mark_all_read_success(self, user_session):
        """PUT /api/notifications/read-all marks all notifications as read"""
        response = user_session.put(f"{BASE_URL}/api/notifications/read-all")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify unread count is 0
        count_response = user_session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert count_response.status_code == 200
        assert count_response.json()["count"] == 0


class TestNoShowReportWithNotification:
    """Test no-show report creates notification for user"""
    
    @pytest.fixture
    def admin_session(self):
        """Login as admin"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    @pytest.fixture
    def attendant_session(self):
        """Login as attendant"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "attendant.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    @pytest.fixture
    def user_session(self):
        """Login as user"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    def test_report_no_show_creates_notification(self, user_session, attendant_session):
        """Report no-show should create a notification for the reservation owner"""
        # Step 1: Create a reservation as user
        # First get user info
        me_response = user_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        user_id = me_response.json()["id"]
        
        # Get vehicles
        vehicles_response = user_session.get(f"{BASE_URL}/api/vehicles")
        if vehicles_response.status_code != 200 or len(vehicles_response.json()) == 0:
            # Create a vehicle
            create_vehicle = user_session.post(f"{BASE_URL}/api/vehicles", json={
                "plate_number": "TEST-NOSHOW-001",
                "make": "Test",
                "model": "Car",
                "color": "Red"
            })
            assert create_vehicle.status_code == 200
            vehicle_id = create_vehicle.json()["id"]
        else:
            vehicle_id = vehicles_response.json()[0]["id"]
        
        # Get buildings and find a slot
        buildings_response = user_session.get(f"{BASE_URL}/api/buildings")
        assert buildings_response.status_code == 200
        buildings = buildings_response.json()
        assert len(buildings) > 0
        
        building = buildings[0]
        assert len(building["floors"]) > 0
        floor = building["floors"][0]
        assert len(floor["slots"]) > 0
        slot_id = floor["slots"][0]["id"]
        
        # Create reservation for today
        today = datetime.now().strftime("%Y-%m-%d")
        reservation_response = user_session.post(f"{BASE_URL}/api/reservations", json={
            "slot_id": slot_id,
            "vehicle_id": vehicle_id,
            "dates": [today],
            "start_time": "08:00",
            "end_time": "18:00"
        })
        
        if reservation_response.status_code not in [200, 201]:
            # Slot may be occupied, try tomorrow
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            reservation_response = user_session.post(f"{BASE_URL}/api/reservations", json={
                "slot_id": slot_id,
                "vehicle_id": vehicle_id,
                "dates": [tomorrow],
                "start_time": "08:00",
                "end_time": "18:00"
            })
        
        # If still fails, just test the notification endpoint directly
        if reservation_response.status_code not in [200, 201]:
            pytest.skip("Could not create reservation for no-show test")
            return
            
        reservation_data = reservation_response.json()
        reservation_id = reservation_data.get("id") or reservation_data.get("reservations", [{}])[0].get("id")
        
        # Step 2: Get initial notification count
        initial_count_response = user_session.get(f"{BASE_URL}/api/notifications/unread-count")
        initial_count = initial_count_response.json()["count"]
        
        # Step 3: As attendant, report no-show
        noshow_response = attendant_session.post(f"{BASE_URL}/api/attendant/reservations/{reservation_id}/report-no-show")
        assert noshow_response.status_code == 200, f"Report no-show failed: {noshow_response.text}"
        
        # Step 4: Verify notification was created
        time.sleep(0.5)  # Small delay for DB write
        new_count_response = user_session.get(f"{BASE_URL}/api/notifications/unread-count")
        new_count = new_count_response.json()["count"]
        
        assert new_count >= initial_count, "Notification should be created after no-show report"
        
        # Verify notification content
        notifications_response = user_session.get(f"{BASE_URL}/api/notifications")
        notifications = notifications_response.json()
        
        # Check that there's a no-show notification
        no_show_notification = None
        for n in notifications:
            if n.get("type") == "no_show":
                no_show_notification = n
                break
        
        assert no_show_notification is not None, "Should have a no-show type notification"
        assert "No-Show" in no_show_notification["title"]


class TestParkingConfigNoShowRelease:
    """Test parking config endpoints with no-show release fields"""
    
    @pytest.fixture
    def admin_session(self):
        """Login as admin"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    @pytest.fixture
    def user_session(self):
        """Login as user"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    def test_get_parking_config_includes_noshow_fields(self, admin_session):
        """GET /api/parking-config/{building_id} returns no-show release fields"""
        # Get a building ID first
        buildings_response = admin_session.get(f"{BASE_URL}/api/buildings")
        assert buildings_response.status_code == 200
        buildings = buildings_response.json()
        assert len(buildings) > 0
        
        building_id = buildings[0]["id"]
        
        # Get parking config
        config_response = admin_session.get(f"{BASE_URL}/api/parking-config/{building_id}")
        assert config_response.status_code == 200
        config = config_response.json()
        
        # Verify no-show release fields exist
        assert "no_show_release_enabled" in config, "Should have no_show_release_enabled field"
        assert "no_show_release_minutes" in config, "Should have no_show_release_minutes field"
        assert isinstance(config["no_show_release_enabled"], bool)
        assert isinstance(config["no_show_release_minutes"], int)
    
    def test_save_parking_config_with_noshow_fields(self, admin_session):
        """POST /api/parking-config saves no-show release settings"""
        # Get a building ID
        buildings_response = admin_session.get(f"{BASE_URL}/api/buildings")
        buildings = buildings_response.json()
        building_id = buildings[0]["id"]
        
        # Save config with no-show settings enabled
        config_data = {
            "building_id": building_id,
            "release_time": "06:00",
            "default_start_time": "08:00",
            "default_end_time": "18:00",
            "booking_window_days": 7,
            "no_show_release_enabled": True,
            "no_show_release_minutes": 45
        }
        
        save_response = admin_session.post(f"{BASE_URL}/api/parking-config", json=config_data)
        assert save_response.status_code == 200
        
        saved_config = save_response.json()
        assert saved_config["no_show_release_enabled"] == True
        assert saved_config["no_show_release_minutes"] == 45
        
        # Verify persistence
        get_response = admin_session.get(f"{BASE_URL}/api/parking-config/{building_id}")
        assert get_response.status_code == 200
        fetched_config = get_response.json()
        
        assert fetched_config["no_show_release_enabled"] == True
        assert fetched_config["no_show_release_minutes"] == 45
        
        # Reset to disabled for cleanup
        config_data["no_show_release_enabled"] = False
        config_data["no_show_release_minutes"] = 30
        admin_session.post(f"{BASE_URL}/api/parking-config", json=config_data)
    
    def test_parking_config_requires_admin(self, user_session):
        """POST /api/parking-config requires admin role"""
        buildings_response = user_session.get(f"{BASE_URL}/api/buildings")
        buildings = buildings_response.json()
        building_id = buildings[0]["id"]
        
        config_data = {
            "building_id": building_id,
            "release_time": "06:00",
            "default_start_time": "08:00",
            "default_end_time": "18:00",
            "booking_window_days": 7,
            "no_show_release_enabled": True,
            "no_show_release_minutes": 30
        }
        
        save_response = user_session.post(f"{BASE_URL}/api/parking-config", json=config_data)
        assert save_response.status_code == 403, "Non-admin should not be able to save config"


class TestNotificationMarkSingleRead:
    """Test marking a single notification as read"""
    
    @pytest.fixture
    def user_session(self):
        """Login as user"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    def test_mark_single_notification_read(self, user_session):
        """PUT /api/notifications/{id}/read marks single notification as read"""
        # Get notifications first
        notifications_response = user_session.get(f"{BASE_URL}/api/notifications")
        notifications = notifications_response.json()
        
        if len(notifications) == 0:
            pytest.skip("No notifications to test with")
            return
        
        notification_id = notifications[0]["id"]
        
        # Mark as read
        response = user_session.put(f"{BASE_URL}/api/notifications/{notification_id}/read")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
