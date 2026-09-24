#!/usr/bin/env python3
"""
Test overlap validation specifically for the Cebuana Lhuillier Parking System
"""

import requests
import sys
from datetime import datetime, timedelta

def test_overlap_validation():
    """Test that users cannot book overlapping time slots on the same day"""
    base_url = "https://reserve-park-debug.preview.emergentagent.com"
    
    # Register a test user
    user_data = {
        "email": f"overlap.test.{datetime.now().strftime('%H%M%S')}@cebuana.com",
        "password": "TestPass123!",
        "first_name": "Overlap",
        "last_name": "Tester",
        "role": "user"
    }
    
    # Register user
    response = requests.post(f"{base_url}/api/auth/register", json=user_data)
    if response.status_code != 200:
        print(f"❌ User registration failed: {response.text}")
        return False
    
    user_token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'}
    
    # Create a vehicle
    vehicle_data = {
        "plate_number": f"OVR{datetime.now().strftime('%H%M')}",
        "make": "Honda",
        "model": "Civic",
        "color": "Blue"
    }
    
    response = requests.post(f"{base_url}/api/vehicles", json=vehicle_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Vehicle creation failed: {response.text}")
        return False
    
    vehicle_id = response.json()['id']
    
    # Get buildings to find a slot
    response = requests.get(f"{base_url}/api/buildings", headers=headers)
    if response.status_code != 200 or not response.json():
        print(f"❌ No buildings available: {response.text}")
        return False
    
    building = response.json()[0]
    building_id = building['id']
    
    # Get available slots for a future date
    future_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
    response = requests.get(f"{base_url}/api/slots/available?building_id={building_id}&date={future_date}", headers=headers)
    if response.status_code != 200 or not response.json():
        print(f"❌ No slots available: {response.text}")
        return False
    
    available_slots = [s for s in response.json() if s.get('is_available', True)]
    if len(available_slots) < 2:
        print(f"❌ Need at least 2 available slots for testing")
        return False
    
    slot_id = available_slots[0]['id']
    
    # Test 1: Create first reservation (08:00-12:00)
    reservation1_data = {
        "slot_id": slot_id,
        "vehicle_id": vehicle_id,
        "date": future_date,
        "start_time": "08:00",
        "end_time": "12:00",
        "booking_type": "daily"
    }
    
    response = requests.post(f"{base_url}/api/reservations", json=reservation1_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ First reservation failed: {response.text}")
        return False
    
    print("✅ First reservation created successfully (08:00-12:00)")
    
    # Test 2: Try to create overlapping reservation (10:00-14:00) - should fail
    reservation2_data = {
        "slot_id": available_slots[1]['id'],  # Different slot
        "vehicle_id": vehicle_id,
        "date": future_date,
        "start_time": "10:00",
        "end_time": "14:00",
        "booking_type": "daily"
    }
    
    response = requests.post(f"{base_url}/api/reservations", json=reservation2_data, headers=headers)
    if response.status_code == 400 and "already have a booking" in response.text:
        print("✅ Overlap validation working - overlapping reservation rejected")
        return True
    elif response.status_code == 200:
        print("❌ Overlap validation failed - overlapping reservation was allowed")
        return False
    else:
        print(f"❌ Unexpected response: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    print("🔍 Testing overlap validation...")
    success = test_overlap_validation()
    sys.exit(0 if success else 1)