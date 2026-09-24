#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Cebuana Lhuillier Parking Reservation System
Tests all major endpoints and user flows
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ParkingAPITester:
    def __init__(self, base_url: str = "https://reserve-park-debug.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Test data storage
        self.admin_token = None
        self.user_token = None
        self.attendant_token = None
        self.test_building_id = None
        self.test_floor_id = None
        self.test_slot_id = None
        self.test_vehicle_id = None
        self.test_reservation_id = None
        
        # Test counters
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name: str, test_func, *args, **kwargs) -> bool:
        """Run a single test and track results"""
        self.tests_run += 1
        self.log(f"🔍 Running: {name}")
        
        try:
            result = test_func(*args, **kwargs)
            if result:
                self.tests_passed += 1
                self.log(f"✅ PASSED: {name}")
                return True
            else:
                self.failed_tests.append(name)
                self.log(f"❌ FAILED: {name}", "ERROR")
                return False
        except Exception as e:
            self.failed_tests.append(f"{name}: {str(e)}")
            self.log(f"❌ ERROR in {name}: {str(e)}", "ERROR")
            return False

    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    token: str = None, expected_status: int = 200) -> tuple:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            
            if not success:
                self.log(f"Request failed: {method} {url} - Status: {response.status_code}, Body: {response.text[:200]}")
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return success, response_data
            
        except Exception as e:
            self.log(f"Request exception: {str(e)}")
            return False, {"error": str(e)}

    # ==================== AUTHENTICATION TESTS ====================
    
    def test_admin_registration(self) -> bool:
        """Test admin user registration"""
        admin_data = {
            "email": f"admin.test.{datetime.now().strftime('%H%M%S')}@cebuana.com",
            "password": "AdminPass123!",
            "first_name": "Admin",
            "last_name": "Tester",
            "company": "Cebuana Lhuillier",
            "role": "admin"
        }
        
        success, response = self.make_request('POST', 'auth/register', admin_data, expected_status=200)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            self.log(f"Admin registered: {admin_data['email']}")
            return True
        return False

    def test_user_registration(self) -> bool:
        """Test regular user registration"""
        user_data = {
            "email": f"user.test.{datetime.now().strftime('%H%M%S')}@cebuana.com",
            "password": "UserPass123!",
            "first_name": "User",
            "last_name": "Tester",
            "company": "Cebuana Lhuillier",
            "role": "user"
        }
        
        success, response = self.make_request('POST', 'auth/register', user_data, expected_status=200)
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            self.log(f"User registered: {user_data['email']}")
            return True
        return False

    def test_attendant_registration(self) -> bool:
        """Test attendant user registration"""
        attendant_data = {
            "email": f"attendant.test.{datetime.now().strftime('%H%M%S')}@cebuana.com",
            "password": "AttendantPass123!",
            "first_name": "Attendant",
            "last_name": "Tester",
            "company": "Cebuana Lhuillier",
            "role": "attendant"
        }
        
        success, response = self.make_request('POST', 'auth/register', attendant_data, expected_status=200)
        if success and 'access_token' in response:
            self.attendant_token = response['access_token']
            self.log(f"Attendant registered: {attendant_data['email']}")
            return True
        return False

    def test_auth_me(self) -> bool:
        """Test getting current user info"""
        if not self.admin_token:
            return False
        
        success, response = self.make_request('GET', 'auth/me', token=self.admin_token)
        return success and 'email' in response

    # ==================== BUILDING MANAGEMENT TESTS ====================
    
    def test_create_building(self) -> bool:
        """Test building creation (admin only)"""
        if not self.admin_token:
            return False
        
        building_data = {
            "name": f"Test Building {datetime.now().strftime('%H%M%S')}",
            "address": "123 Test Street, Makati City",
            "total_floors": 2,
            "slots_per_floor": 10
        }
        
        success, response = self.make_request('POST', 'buildings', building_data, 
                                            token=self.admin_token, expected_status=200)
        if success and 'id' in response:
            self.test_building_id = response['id']
            if response.get('floors'):
                self.test_floor_id = response['floors'][0]['id']
                if response['floors'][0].get('slots'):
                    self.test_slot_id = response['floors'][0]['slots'][0]['id']
            self.log(f"Building created: {building_data['name']}")
            return True
        return False

    def test_get_buildings(self) -> bool:
        """Test getting all buildings"""
        success, response = self.make_request('GET', 'buildings', token=self.user_token)
        return success and isinstance(response, list)

    def test_add_floor(self) -> bool:
        """Test adding a floor to building"""
        if not self.admin_token or not self.test_building_id:
            return False
        
        floor_data = {
            "label": "Test Floor 3",
            "building_id": self.test_building_id,
            "slot_count": 15
        }
        
        success, response = self.make_request('POST', f'buildings/{self.test_building_id}/floors', 
                                            floor_data, token=self.admin_token)
        return success and 'id' in response

    # ==================== VEHICLE MANAGEMENT TESTS ====================
    
    def test_create_vehicle(self) -> bool:
        """Test vehicle registration"""
        if not self.user_token:
            return False
        
        vehicle_data = {
            "plate_number": f"TEST{datetime.now().strftime('%H%M')}",
            "make": "Toyota",
            "model": "Camry",
            "color": "White"
        }
        
        success, response = self.make_request('POST', 'vehicles', vehicle_data, 
                                            token=self.user_token, expected_status=200)
        if success and 'id' in response:
            self.test_vehicle_id = response['id']
            self.log(f"Vehicle created: {vehicle_data['plate_number']}")
            return True
        return False

    def test_get_vehicles(self) -> bool:
        """Test getting user vehicles"""
        if not self.user_token:
            return False
        
        success, response = self.make_request('GET', 'vehicles', token=self.user_token)
        return success and isinstance(response, list)

    # ==================== RESERVATION TESTS ====================
    
    def test_get_available_slots(self) -> bool:
        """Test getting available parking slots"""
        if not self.user_token or not self.test_building_id:
            return False
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        endpoint = f'slots/available?building_id={self.test_building_id}&date={tomorrow}'
        
        success, response = self.make_request('GET', endpoint, token=self.user_token)
        return success and isinstance(response, list)

    def test_create_reservation(self) -> bool:
        """Test creating a parking reservation"""
        if not self.user_token or not self.test_slot_id or not self.test_vehicle_id:
            return False
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        reservation_data = {
            "slot_id": self.test_slot_id,
            "vehicle_id": self.test_vehicle_id,
            "date": tomorrow,
            "start_time": "08:00",
            "end_time": "18:00",
            "booking_type": "daily"
        }
        
        success, response = self.make_request('POST', 'reservations', reservation_data, 
                                            token=self.user_token, expected_status=200)
        if success and 'id' in response:
            self.test_reservation_id = response['id']
            self.log(f"Reservation created for slot: {self.test_slot_id}")
            return True
        return False

    def test_get_reservations(self) -> bool:
        """Test getting user reservations"""
        if not self.user_token:
            return False
        
        success, response = self.make_request('GET', 'reservations', token=self.user_token)
        return success and isinstance(response, list)

    def test_cancel_reservation(self) -> bool:
        """Test cancelling a reservation"""
        if not self.user_token or not self.test_reservation_id:
            return False
        
        success, response = self.make_request('PUT', f'reservations/{self.test_reservation_id}/cancel', 
                                            token=self.user_token)
        return success and 'message' in response

    # ==================== ATTENDANT TESTS ====================
    
    def test_attendant_daily_reservations(self) -> bool:
        """Test attendant getting daily reservations"""
        if not self.attendant_token:
            return False
        
        today = datetime.now().strftime('%Y-%m-%d')
        endpoint = f'attendant/daily-reservations?date={today}'
        
        success, response = self.make_request('GET', endpoint, token=self.attendant_token)
        return success and isinstance(response, list)

    def test_confirm_reservation(self) -> bool:
        """Test attendant confirming a reservation"""
        if not self.attendant_token:
            return False
        
        # Create a new reservation first for confirmation test
        if not self.test_slot_id or not self.test_vehicle_id:
            return False
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        reservation_data = {
            "slot_id": self.test_slot_id,
            "vehicle_id": self.test_vehicle_id,
            "date": tomorrow,
            "start_time": "09:00",
            "end_time": "17:00",
            "booking_type": "daily"
        }
        
        # Create reservation with user token
        success, response = self.make_request('POST', 'reservations', reservation_data, 
                                            token=self.user_token, expected_status=200)
        if not success:
            return False
        
        reservation_id = response['id']
        
        # Confirm with attendant token
        confirm_data = {"photo": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/8A"}
        
        success, response = self.make_request('POST', f'reservations/{reservation_id}/confirm-with-photo', 
                                            confirm_data, token=self.attendant_token)
        return success and 'message' in response

    # ==================== ADMIN TESTS ====================
    
    def test_get_users(self) -> bool:
        """Test admin getting all users"""
        if not self.admin_token:
            return False
        
        success, response = self.make_request('GET', 'users', token=self.admin_token)
        return success and isinstance(response, list)

    def test_get_stats(self) -> bool:
        """Test admin getting system statistics"""
        if not self.admin_token:
            return False
        
        success, response = self.make_request('GET', 'reports/stats', token=self.admin_token)
        return success and 'summary' in response

    def test_ai_insights(self) -> bool:
        """Test AI insights generation"""
        if not self.admin_token:
            return False
        
        success, response = self.make_request('GET', 'reports/ai-insights', token=self.admin_token)
        return success and 'insights' in response

    # ==================== PARKING CONFIG TESTS ====================
    
    def test_get_parking_config(self) -> bool:
        """Test getting parking configuration"""
        if not self.user_token or not self.test_building_id:
            return False
        
        success, response = self.make_request('GET', f'parking-config/{self.test_building_id}', 
                                            token=self.user_token)
        return success and 'building_id' in response

    def test_save_parking_config(self) -> bool:
        """Test saving parking configuration"""
        if not self.admin_token or not self.test_building_id:
            return False
        
        config_data = {
            "building_id": self.test_building_id,
            "release_time": "06:00",
            "default_start_time": "08:00",
            "default_end_time": "18:00",
            "booking_window_days": 7
        }
        
        success, response = self.make_request('POST', 'parking-config', config_data, 
                                            token=self.admin_token)
        return success and 'building_id' in response

    # ==================== MAIN TEST RUNNER ====================
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting Cebuana Lhuillier Parking API Tests")
        self.log(f"Testing against: {self.base_url}")
        
        # Test API root
        self.run_test("API Root Endpoint", lambda: self.make_request('GET', '', expected_status=200)[0])
        
        # Authentication Tests
        self.log("\n📝 AUTHENTICATION TESTS")
        self.run_test("Admin Registration", self.test_admin_registration)
        self.run_test("User Registration", self.test_user_registration)
        self.run_test("Attendant Registration", self.test_attendant_registration)
        self.run_test("Get Current User Info", self.test_auth_me)
        
        # Building Management Tests
        self.log("\n🏢 BUILDING MANAGEMENT TESTS")
        self.run_test("Create Building", self.test_create_building)
        self.run_test("Get Buildings", self.test_get_buildings)
        self.run_test("Add Floor to Building", self.test_add_floor)
        
        # Vehicle Management Tests
        self.log("\n🚗 VEHICLE MANAGEMENT TESTS")
        self.run_test("Create Vehicle", self.test_create_vehicle)
        self.run_test("Get Vehicles", self.test_get_vehicles)
        
        # Reservation Tests
        self.log("\n📅 RESERVATION TESTS")
        self.run_test("Get Available Slots", self.test_get_available_slots)
        self.run_test("Create Reservation", self.test_create_reservation)
        self.run_test("Get Reservations", self.test_get_reservations)
        self.run_test("Cancel Reservation", self.test_cancel_reservation)
        
        # Attendant Tests
        self.log("\n👮 ATTENDANT TESTS")
        self.run_test("Get Daily Reservations", self.test_attendant_daily_reservations)
        self.run_test("Confirm Reservation", self.test_confirm_reservation)
        
        # Admin Tests
        self.log("\n👑 ADMIN TESTS")
        self.run_test("Get All Users", self.test_get_users)
        self.run_test("Get System Stats", self.test_get_stats)
        self.run_test("Generate AI Insights", self.test_ai_insights)
        
        # Configuration Tests
        self.log("\n⚙️ CONFIGURATION TESTS")
        self.run_test("Get Parking Config", self.test_get_parking_config)
        self.run_test("Save Parking Config", self.test_save_parking_config)
        
        # Final Results
        self.print_results()

    def print_results(self):
        """Print final test results"""
        self.log("\n" + "="*60)
        self.log("📊 TEST RESULTS SUMMARY")
        self.log("="*60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed}")
        self.log(f"Failed: {len(self.failed_tests)}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                self.log(f"  - {test}")
        
        self.log("\n🎯 KEY TEST DATA:")
        if self.test_building_id:
            self.log(f"  Building ID: {self.test_building_id}")
        if self.test_vehicle_id:
            self.log(f"  Vehicle ID: {self.test_vehicle_id}")
        if self.test_reservation_id:
            self.log(f"  Reservation ID: {self.test_reservation_id}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = ParkingAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        tester.log("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        tester.log(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())