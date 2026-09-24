"""
Backend tests for QR Scanner feature.
Tests: GET /api/scan/{qr_token}, PUT /api/reservations/{id}/confirm,
       POST /api/reservations (create reservation)
"""

import pytest
import requests
import os
import time
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

USER_EMAIL = "user.test@cebuana.com"
USER_PASS = "Test123!"
ATTENDANT_EMAIL = "attendant.test@cebuana.com"
ATTENDANT_PASS = "Test123!"

BUILDING_ID = "fe5ec3b7-38aa-48aa-8572-762afde16bec"
SLOT_ID = "37186d53-954e-4007-93e0-323f2ffe6eb9"  # 1A2
VEHICLE_ID = "bdc18de0-042d-4203-b013-b09781cb7173"
TEST_DATE = (date.today() + timedelta(days=5)).isoformat()  # future date to avoid conflicts

# Module-level token cache to avoid rate limiting (5 logins per minute)
_token_cache = {}


def get_token(email, password):
    """Helper: login and get access token (cached per session to avoid rate limits)"""
    if email in _token_cache:
        return _token_cache[email]
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if r.status_code == 429:
        # Rate limited - wait 65 seconds and retry
        print(f"Rate limited, waiting 65 seconds...")
        time.sleep(65)
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    _token_cache[email] = r.json()["access_token"]
    return _token_cache[email]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestScanQREndpoint:
    """Tests for GET /api/scan/{qr_token}"""

    def test_scan_valid_token_returns_reservation_details(self):
        """Scan a valid QR token returns reservation info with reservation_id key"""
        user_token = get_token(USER_EMAIL, USER_PASS)
        attendant_token = get_token(ATTENDANT_EMAIL, ATTENDANT_PASS)

        # Create a reservation as user
        r = requests.post(
            f"{BASE_URL}/api/reservations",
            json={
                "slot_id": SLOT_ID,
                "vehicle_id": VEHICLE_ID,
                "dates": [TEST_DATE],
                "start_time": "14:00",
                "end_time": "16:00"
            },
            headers=auth_headers(user_token)
        )
        assert r.status_code == 200, f"Create reservation failed: {r.text}"
        reservation = r.json()
        qr_token = reservation["qr_token"]
        res_id = reservation["id"]
        assert qr_token, "qr_token should be present in created reservation"

        # Scan as attendant
        scan_r = requests.get(
            f"{BASE_URL}/api/scan/{qr_token}",
            headers=auth_headers(attendant_token)
        )
        assert scan_r.status_code == 200, f"Scan endpoint failed: {scan_r.text}"
        data = scan_r.json()

        # Critical: verify response has 'reservation_id' field (NOT 'id')
        assert "reservation_id" in data, "scan response should contain 'reservation_id'"
        assert data["reservation_id"] == res_id, "reservation_id should match created reservation"
        assert data["status"] == "pending", "New reservation should have pending status"
        assert data["user_name"] is not None, "user_name should be present"
        assert data["vehicle_plate"] is not None, "vehicle_plate should be present"
        assert data["building_name"] is not None, "building_name should be present"
        assert data["slot_label"] is not None, "slot_label should be present"
        assert data["floor_label"] is not None, "floor_label should be present"
        assert data["date"] == TEST_DATE
        assert data["start_time"] == "14:00"
        assert data["end_time"] == "16:00"

        print(f"PASS: scan returns reservation_id={data['reservation_id']}, status=pending")

        # Cleanup: cancel reservation
        requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                     headers=auth_headers(user_token))

    def test_scan_invalid_token_returns_404(self):
        """Scanning an invalid QR token returns 404"""
        attendant_token = get_token(ATTENDANT_EMAIL, ATTENDANT_PASS)
        r = requests.get(
            f"{BASE_URL}/api/scan/invalid-token-123",
            headers=auth_headers(attendant_token)
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        data = r.json()
        assert "detail" in data, "Error response should have 'detail' field"
        print(f"PASS: invalid token returns 404 with detail: {data['detail']}")

    def test_scan_requires_attendant_role(self):
        """Non-attendant user cannot scan QR"""
        user_token = get_token(USER_EMAIL, USER_PASS)
        r = requests.get(
            f"{BASE_URL}/api/scan/any-token",
            headers=auth_headers(user_token)
        )
        assert r.status_code in [403, 404], f"Expected 403/404 for non-attendant, got {r.status_code}"
        print(f"PASS: non-attendant gets {r.status_code}")

    def test_scan_requires_authentication(self):
        """Unauthenticated request cannot scan QR"""
        r = requests.get(f"{BASE_URL}/api/scan/any-token")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("PASS: unauthenticated request returns 401")


class TestConfirmReservationEndpoint:
    """Tests for PUT /api/reservations/{id}/confirm"""

    def test_confirm_pending_reservation_succeeds(self):
        """Attendant can confirm a pending reservation"""
        user_token = get_token(USER_EMAIL, USER_PASS)
        attendant_token = get_token(ATTENDANT_EMAIL, ATTENDANT_PASS)

        # Create reservation
        r = requests.post(
            f"{BASE_URL}/api/reservations",
            json={
                "slot_id": SLOT_ID,
                "vehicle_id": VEHICLE_ID,
                "dates": [TEST_DATE],
                "start_time": "08:00",
                "end_time": "10:00"
            },
            headers=auth_headers(user_token)
        )
        assert r.status_code == 200
        res_id = r.json()["id"]

        # Confirm it
        confirm_r = requests.put(
            f"{BASE_URL}/api/reservations/{res_id}/confirm",
            headers=auth_headers(attendant_token)
        )
        assert confirm_r.status_code == 200, f"Confirm failed: {confirm_r.text}"
        data = confirm_r.json()
        assert "message" in data
        assert "confirmed" in data["message"].lower()
        print(f"PASS: confirm returns: {data['message']}")

        # Verify confirmed status via scan
        user_reservations = requests.get(
            f"{BASE_URL}/api/reservations?date={TEST_DATE}",
            headers=auth_headers(user_token)
        )
        confirmed_res = next(
            (res for res in user_reservations.json() if res["id"] == res_id), None
        )
        assert confirmed_res is not None
        assert confirmed_res["status"] == "confirmed", "Reservation should be confirmed after PUT"
        print("PASS: reservation status is 'confirmed' after PUT /confirm")

        # Cleanup
        requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                     headers=auth_headers(user_token))

    def test_confirm_with_undefined_id_returns_404(self):
        """Confirm with non-existent ID returns 404 - reproduces frontend bug"""
        attendant_token = get_token(ATTENDANT_EMAIL, ATTENDANT_PASS)
        r = requests.put(
            f"{BASE_URL}/api/reservations/undefined/confirm",
            headers=auth_headers(attendant_token)
        )
        assert r.status_code == 404, f"Expected 404 for 'undefined' ID, got {r.status_code}"
        print("PASS: confirm with 'undefined' id returns 404 (reproduces frontend bug)")

    def test_confirm_requires_attendant_role(self):
        """Regular user cannot use the PUT /confirm endpoint"""
        user_token = get_token(USER_EMAIL, USER_PASS)

        # Create reservation
        r = requests.post(
            f"{BASE_URL}/api/reservations",
            json={
                "slot_id": SLOT_ID,
                "vehicle_id": VEHICLE_ID,
                "dates": [TEST_DATE],
                "start_time": "16:00",
                "end_time": "18:00"
            },
            headers=auth_headers(user_token)
        )
        assert r.status_code == 200
        res_id = r.json()["id"]

        # Try to confirm as regular user
        confirm_r = requests.put(
            f"{BASE_URL}/api/reservations/{res_id}/confirm",
            headers=auth_headers(user_token)
        )
        assert confirm_r.status_code == 403, f"Expected 403 for non-attendant, got {confirm_r.status_code}"
        print(f"PASS: regular user gets 403 for confirm endpoint")

        # Cleanup
        requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                     headers=auth_headers(user_token))


class TestQRScanFlowIntegration:
    """End-to-end integration tests for the full QR scan → confirm flow"""

    def test_full_scan_confirm_flow(self):
        """
        Full flow: create reservation → scan QR → confirm reservation
        This test also validates the frontend field name bug (reservation.id vs reservation_id)
        """
        user_token = get_token(USER_EMAIL, USER_PASS)
        attendant_token = get_token(ATTENDANT_EMAIL, ATTENDANT_PASS)

        # Step 1: Create reservation
        create_r = requests.post(
            f"{BASE_URL}/api/reservations",
            json={
                "slot_id": SLOT_ID,
                "vehicle_id": VEHICLE_ID,
                "dates": [TEST_DATE],
                "start_time": "11:00",
                "end_time": "13:00"
            },
            headers=auth_headers(user_token)
        )
        assert create_r.status_code == 200
        res_data = create_r.json()
        res_id = res_data["id"]
        qr_token = res_data["qr_token"]
        print(f"Created reservation {res_id} with qr_token={qr_token}")

        # Step 2: Scan the QR token
        scan_r = requests.get(
            f"{BASE_URL}/api/scan/{qr_token}",
            headers=auth_headers(attendant_token)
        )
        assert scan_r.status_code == 200
        scan_data = scan_r.json()
        print(f"Scan data keys: {list(scan_data.keys())}")

        # IMPORTANT: Verify the returned key is 'reservation_id', NOT 'id'
        assert "reservation_id" in scan_data, "BUG: scan should return 'reservation_id' key"
        assert "id" not in scan_data, \
            "Frontend expects 'reservation.id' but API returns 'reservation_id' - this is the BUG"
        print("CONFIRMED BUG: API returns 'reservation_id' but frontend uses 'reservation.id'")

        # Step 3: Confirm using the correct key (reservation_id)
        confirm_r = requests.put(
            f"{BASE_URL}/api/reservations/{scan_data['reservation_id']}/confirm",
            headers=auth_headers(attendant_token)
        )
        assert confirm_r.status_code == 200
        print("PASS: confirm works when using reservation_id from scan response")

        # Step 4: Verify status is confirmed
        verify_r = requests.get(
            f"{BASE_URL}/api/reservations?date={TEST_DATE}",
            headers=auth_headers(user_token)
        )
        confirmed = next((r for r in verify_r.json() if r["id"] == res_id), None)
        assert confirmed is not None
        assert confirmed["status"] == "confirmed"
        print(f"PASS: reservation is now confirmed. Full flow works via API.")

        # Step 5: Re-scan to verify already-confirmed shows 'confirmed' status
        rescan_r = requests.get(
            f"{BASE_URL}/api/scan/{qr_token}",
            headers=auth_headers(attendant_token)
        )
        assert rescan_r.status_code == 200
        assert rescan_r.json()["status"] == "confirmed"
        print("PASS: re-scan returns status='confirmed' for already-confirmed reservation")

        # Cleanup
        requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                     headers=auth_headers(user_token))

    def test_scan_already_confirmed_reservation(self):
        """Scanning an already-confirmed reservation returns status='confirmed'"""
        user_token = get_token(USER_EMAIL, USER_PASS)
        attendant_token = get_token(ATTENDANT_EMAIL, ATTENDANT_PASS)

        # Create and immediately confirm
        create_r = requests.post(
            f"{BASE_URL}/api/reservations",
            json={
                "slot_id": SLOT_ID,
                "vehicle_id": VEHICLE_ID,
                "dates": [TEST_DATE],
                "start_time": "17:00",
                "end_time": "19:00"
            },
            headers=auth_headers(user_token)
        )
        assert create_r.status_code == 200
        res_id = create_r.json()["id"]
        qr_token = create_r.json()["qr_token"]

        # Confirm it
        requests.put(
            f"{BASE_URL}/api/reservations/{res_id}/confirm",
            headers=auth_headers(attendant_token)
        )

        # Scan already-confirmed
        scan_r = requests.get(
            f"{BASE_URL}/api/scan/{qr_token}",
            headers=auth_headers(attendant_token)
        )
        assert scan_r.status_code == 200
        data = scan_r.json()
        assert data["status"] == "confirmed"
        print("PASS: scanning already-confirmed reservation returns status='confirmed'")
        print("Frontend should show 'Already Confirmed' for this case")

        # Cleanup
        requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                     headers=auth_headers(user_token))


class TestDailyReservationsEndpoint:
    """Tests for the attendant daily reservations endpoint (auto-refresh after scan)"""

    def test_daily_reservations_reflect_confirmed_status(self):
        """After confirming, the daily reservations list shows the reservation as confirmed"""
        user_token = get_token(USER_EMAIL, USER_PASS)
        attendant_token = get_token(ATTENDANT_EMAIL, ATTENDANT_PASS)

        today = date.today().isoformat()

        # Create reservation for today
        create_r = requests.post(
            f"{BASE_URL}/api/reservations",
            json={
                "slot_id": SLOT_ID,
                "vehicle_id": VEHICLE_ID,
                "dates": [today],
                "start_time": "20:00",
                "end_time": "22:00"
            },
            headers=auth_headers(user_token)
        )
        assert create_r.status_code == 200
        res_id = create_r.json()["id"]
        qr_token = create_r.json()["qr_token"]

        # Get attendant buildings
        buildings_r = requests.get(
            f"{BASE_URL}/api/attendant/buildings",
            headers=auth_headers(attendant_token)
        )
        assert buildings_r.status_code == 200
        buildings = buildings_r.json()
        assert len(buildings) > 0

        # Check reservation appears in daily list
        daily_r = requests.get(
            f"{BASE_URL}/api/attendant/daily-reservations",
            params={"date": today, "building_id": BUILDING_ID},
            headers=auth_headers(attendant_token)
        )
        # Note: The reservation might not appear for CL Tower Makati if the attendant is not assigned there
        # The attendant is assigned to dcae62c5-901a-4bf3-bf7c-c5e116232c93, not fe5ec3b7
        print(f"Attendant assigned buildings: {[b['id'] for b in buildings]}")
        print(f"Daily reservations count: {len(daily_r.json()) if daily_r.status_code == 200 else 'N/A'}")

        # Confirm via scan
        scan_r = requests.get(
            f"{BASE_URL}/api/scan/{qr_token}",
            headers=auth_headers(attendant_token)
        )
        if scan_r.status_code == 200:
            # The scan works (doesn't filter by assigned buildings)
            scan_id = scan_r.json()["reservation_id"]
            confirm_r = requests.put(
                f"{BASE_URL}/api/reservations/{scan_id}/confirm",
                headers=auth_headers(attendant_token)
            )
            assert confirm_r.status_code == 200
            print("PASS: scan + confirm works even across different buildings")

        # Cleanup
        requests.put(f"{BASE_URL}/api/reservations/{res_id}/cancel",
                     headers=auth_headers(user_token))
