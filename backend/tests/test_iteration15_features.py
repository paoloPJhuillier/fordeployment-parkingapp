"""
Test iteration 15 features:
1. CSV Template downloads (admin only)
2. Login still works after removing register from frontend
3. Admin can still create users via POST /api/users
4. Reservations stats endpoint for History tab
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

class TestCSVTemplateDownloads:
    """Test CSV template download endpoints - Admin only"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        self.session = requests.Session()
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_cookies = login_response.cookies
        
    def test_download_users_template(self):
        """GET /api/templates/users returns CSV template"""
        response = self.session.get(
            f"{BASE_URL}/api/templates/users",
            cookies=self.admin_cookies
        )
        assert response.status_code == 200, f"Failed to download users template: {response.text}"
        
        # Check content type
        assert "text/csv" in response.headers.get("Content-Type", ""), "Response should be CSV"
        
        # Check content disposition header for filename
        content_disp = response.headers.get("Content-Disposition", "")
        assert "users_template.csv" in content_disp, "Content-Disposition should specify users_template.csv"
        
        # Verify CSV content has expected columns
        csv_content = response.text
        assert "email" in csv_content, "CSV should contain 'email' column"
        assert "first_name" in csv_content, "CSV should contain 'first_name' column"
        assert "last_name" in csv_content, "CSV should contain 'last_name' column"
        print(f"SUCCESS: Users template CSV downloaded - Content: {csv_content[:100]}...")
        
    def test_download_buildings_template(self):
        """GET /api/templates/buildings returns CSV template"""
        response = self.session.get(
            f"{BASE_URL}/api/templates/buildings",
            cookies=self.admin_cookies
        )
        assert response.status_code == 200, f"Failed to download buildings template: {response.text}"
        
        # Check content type
        assert "text/csv" in response.headers.get("Content-Type", ""), "Response should be CSV"
        
        # Verify CSV content
        csv_content = response.text
        assert "building_name" in csv_content, "CSV should contain 'building_name' column"
        assert "floor_label" in csv_content, "CSV should contain 'floor_label' column"
        assert "slot_labels" in csv_content, "CSV should contain 'slot_labels' column"
        print(f"SUCCESS: Buildings template CSV downloaded - Content: {csv_content[:100]}...")
        
    def test_download_zones_template(self):
        """GET /api/templates/zones returns CSV template"""
        response = self.session.get(
            f"{BASE_URL}/api/templates/zones",
            cookies=self.admin_cookies
        )
        assert response.status_code == 200, f"Failed to download zones template: {response.text}"
        
        # Check content type
        assert "text/csv" in response.headers.get("Content-Type", ""), "Response should be CSV"
        
        # Verify CSV content
        csv_content = response.text
        assert "zone_name" in csv_content, "CSV should contain 'zone_name' column"
        assert "building_names" in csv_content, "CSV should contain 'building_names' column"
        print(f"SUCCESS: Zones template CSV downloaded - Content: {csv_content[:100]}...")


class TestTemplatesRequireAdmin:
    """Test that template endpoints require admin authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as regular user"""
        self.session = requests.Session()
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert login_response.status_code == 200, f"User login failed: {login_response.text}"
        self.user_cookies = login_response.cookies
        
    def test_users_template_requires_admin(self):
        """Regular user cannot download users template"""
        response = self.session.get(
            f"{BASE_URL}/api/templates/users",
            cookies=self.user_cookies
        )
        assert response.status_code == 403, f"Expected 403 for non-admin user, got {response.status_code}"
        print("SUCCESS: Users template requires admin access")
        
    def test_buildings_template_requires_admin(self):
        """Regular user cannot download buildings template"""
        response = self.session.get(
            f"{BASE_URL}/api/templates/buildings",
            cookies=self.user_cookies
        )
        assert response.status_code == 403, f"Expected 403 for non-admin user, got {response.status_code}"
        print("SUCCESS: Buildings template requires admin access")
        
    def test_zones_template_requires_admin(self):
        """Regular user cannot download zones template"""
        response = self.session.get(
            f"{BASE_URL}/api/templates/zones",
            cookies=self.user_cookies
        )
        assert response.status_code == 403, f"Expected 403 for non-admin user, got {response.status_code}"
        print("SUCCESS: Zones template requires admin access")


class TestLoginStillWorks:
    """Test that login still works after removing register from frontend"""
    
    def test_admin_login(self):
        """Admin can still login"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain user object"
        assert data["user"]["role"] == "admin", "User role should be admin"
        assert data["user"]["email"] == "admin.test@cebuana.com"
        print(f"SUCCESS: Admin login works - User: {data['user']['first_name']}")
        
    def test_user_login(self):
        """Regular user can still login"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain user object"
        assert data["user"]["role"] == "user", "User role should be user"
        print(f"SUCCESS: User login works - User: {data['user']['first_name']}")
        
    def test_invalid_login_fails(self):
        """Invalid credentials should fail"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
        print("SUCCESS: Invalid login correctly returns 401")


class TestAdminCanCreateUsers:
    """Test that admin can still create users via POST /api/users (backend register for admin use)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        self.session = requests.Session()
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_cookies = login_response.cookies
        self.test_user_id = None
        
    def teardown_method(self, method):
        """Cleanup: delete test user if created"""
        if self.test_user_id:
            try:
                self.session.delete(
                    f"{BASE_URL}/api/users/{self.test_user_id}",
                    cookies=self.admin_cookies
                )
                print(f"Cleanup: Deleted test user {self.test_user_id}")
            except:
                pass
        
    def test_admin_create_user(self):
        """Admin can create new user via POST /api/users"""
        test_email = "TEST_iter15_create@test.com"
        
        # First cleanup if exists
        users_response = self.session.get(f"{BASE_URL}/api/users", cookies=self.admin_cookies)
        if users_response.status_code == 200:
            users = users_response.json()
            for u in users:
                if u.get("email") == test_email:
                    self.session.delete(f"{BASE_URL}/api/users/{u['id']}", cookies=self.admin_cookies)
        
        # Create user
        response = self.session.post(
            f"{BASE_URL}/api/users",
            json={
                "email": test_email,
                "password": "TempPass123!",
                "first_name": "Test",
                "last_name": "Iteration15",
                "role": "user",
                "company": "Test Company"
            },
            cookies=self.admin_cookies
        )
        assert response.status_code == 200 or response.status_code == 201, f"Failed to create user: {response.text}"
        
        data = response.json()
        assert data["email"] == test_email
        assert data["first_name"] == "Test"
        assert data.get("must_change_password") == True, "New user should have must_change_password=true"
        
        self.test_user_id = data["id"]
        print(f"SUCCESS: Admin created user - ID: {self.test_user_id}, must_change_password: {data.get('must_change_password')}")


class TestReservationStats:
    """Test /api/reservations/stats endpoint for History tab stats"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as user"""
        self.session = requests.Session()
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert login_response.status_code == 200, f"User login failed: {login_response.text}"
        self.user_cookies = login_response.cookies
        
    def test_get_stats(self):
        """GET /api/reservations/stats returns booking statistics"""
        response = self.session.get(
            f"{BASE_URL}/api/reservations/stats",
            cookies=self.user_cookies
        )
        assert response.status_code == 200, f"Failed to get stats: {response.text}"
        
        data = response.json()
        
        # Verify all required stat fields are present
        required_fields = ["total", "pending", "confirmed", "cancelled", "completed", "no_show"]
        for field in required_fields:
            assert field in data, f"Stats should contain '{field}' field"
            assert isinstance(data[field], int), f"'{field}' should be an integer"
        
        print(f"SUCCESS: Reservation stats returned - Total: {data['total']}, Confirmed: {data['confirmed']}, Completed: {data['completed']}, Cancelled: {data['cancelled']}, No-Show: {data['no_show']}")


class TestTemplatesUnauthenticated:
    """Test that template endpoints reject unauthenticated requests"""
    
    def test_users_template_requires_auth(self):
        """Unauthenticated request should fail"""
        response = requests.get(f"{BASE_URL}/api/templates/users")
        assert response.status_code == 401, f"Expected 401 for unauthenticated, got {response.status_code}"
        print("SUCCESS: Users template requires authentication")
        
    def test_buildings_template_requires_auth(self):
        """Unauthenticated request should fail"""
        response = requests.get(f"{BASE_URL}/api/templates/buildings")
        assert response.status_code == 401, f"Expected 401 for unauthenticated, got {response.status_code}"
        print("SUCCESS: Buildings template requires authentication")
        
    def test_zones_template_requires_auth(self):
        """Unauthenticated request should fail"""
        response = requests.get(f"{BASE_URL}/api/templates/zones")
        assert response.status_code == 401, f"Expected 401 for unauthenticated, got {response.status_code}"
        print("SUCCESS: Zones template requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
