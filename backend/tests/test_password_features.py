"""
Tests for Password Change Features - Iteration 14
Features tested:
1. POST /api/users (admin create) sets must_change_password: true
2. POST /api/auth/login returns must_change_password in user object
3. POST /api/auth/change-password changes password and sets must_change_password to false
4. PUT /api/users/{id}/reset-password resets password and sets must_change_password to true
5. GET /api/auth/me returns must_change_password field
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPasswordFeatures:
    """Password management feature tests"""
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        """Login as admin and return authenticated session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return session
    
    @pytest.fixture(scope="class")
    def test_user_email(self):
        """Generate unique email for test user"""
        return f"TEST_pwdchange_{uuid.uuid4().hex[:8]}@test.com"
    
    def test_01_admin_login_returns_must_change_password_field(self, admin_session):
        """GET /api/auth/me should return must_change_password field"""
        response = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Get me failed: {response.text}"
        
        data = response.json()
        assert "must_change_password" in data, "must_change_password field missing from /api/auth/me response"
        assert isinstance(data["must_change_password"], bool), "must_change_password should be boolean"
        print(f"SUCCESS: /api/auth/me returns must_change_password={data['must_change_password']}")
    
    def test_02_admin_create_user_sets_must_change_password_true(self, admin_session, test_user_email):
        """POST /api/users (admin create) should set must_change_password: true"""
        user_data = {
            "email": test_user_email,
            "password": "Changeme1",  # Temporary password
            "first_name": "Test",
            "last_name": "PasswordChange",
            "company": "Test Company",
            "role": "user"
        }
        
        response = admin_session.post(f"{BASE_URL}/api/users", json=user_data)
        assert response.status_code == 200, f"Create user failed: {response.text}"
        
        data = response.json()
        assert data.get("must_change_password") == True, \
            f"Admin-created user should have must_change_password=true, got {data.get('must_change_password')}"
        
        print("SUCCESS: Admin-created user has must_change_password=true")
        return data["id"]
    
    def test_03_login_as_new_user_returns_must_change_password(self, test_user_email):
        """POST /api/auth/login should return must_change_password in user object"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user_email,
            "password": "Changeme1"
        })
        assert response.status_code == 200, f"New user login failed: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain user object"
        user = data["user"]
        
        assert "must_change_password" in user, "user object should contain must_change_password"
        assert user["must_change_password"] == True, \
            f"Newly created user should have must_change_password=true, got {user.get('must_change_password')}"
        
        print("SUCCESS: Login response includes must_change_password=true for new user")
        return session  # Return session for next tests
    
    def test_04_new_user_auth_me_shows_must_change_password(self, test_user_email):
        """GET /api/auth/me should show must_change_password=true for new user"""
        session = requests.Session()
        # Login first
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user_email,
            "password": "Changeme1"
        })
        assert login_response.status_code == 200
        
        # Check /api/auth/me
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Get me failed: {response.text}"
        
        data = response.json()
        assert data.get("must_change_password") == True, \
            f"/api/auth/me should return must_change_password=true, got {data.get('must_change_password')}"
        
        print("SUCCESS: /api/auth/me returns must_change_password=true for new user")
    
    def test_05_change_password_sets_must_change_password_false(self, test_user_email):
        """POST /api/auth/change-password should set must_change_password to false"""
        session = requests.Session()
        # Login first
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user_email,
            "password": "Changeme1"
        })
        assert login_response.status_code == 200
        
        # Change password
        new_password = "NewPass123!"
        response = session.post(f"{BASE_URL}/api/auth/change-password", json={
            "new_password": new_password
        })
        assert response.status_code == 200, f"Change password failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        print(f"SUCCESS: Password change returned: {data['message']}")
        
        # Verify must_change_password is now false
        me_response = session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data.get("must_change_password") == False, \
            f"After password change, must_change_password should be false, got {me_data.get('must_change_password')}"
        
        print("SUCCESS: must_change_password is now false after password change")
    
    def test_06_can_login_with_new_password(self, test_user_email):
        """User should be able to login with new password"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user_email,
            "password": "NewPass123!"  # The new password
        })
        assert response.status_code == 200, f"Login with new password failed: {response.text}"
        
        data = response.json()
        assert data["user"]["must_change_password"] == False, \
            "After password change, must_change_password should remain false"
        
        print("SUCCESS: Login with new password works, must_change_password=false")
    
    def test_07_admin_reset_password_sets_must_change_password_true(self, admin_session, test_user_email):
        """PUT /api/users/{id}/reset-password should set must_change_password to true"""
        # First get user ID
        users_response = admin_session.get(f"{BASE_URL}/api/users")
        assert users_response.status_code == 200
        
        users = users_response.json()
        test_user = next((u for u in users if u["email"] == test_user_email), None)
        assert test_user is not None, f"Test user {test_user_email} not found"
        
        user_id = test_user["id"]
        
        # Reset password
        response = admin_session.put(f"{BASE_URL}/api/users/{user_id}/reset-password", json={
            "password": "ResetPass1"
        })
        assert response.status_code == 200, f"Reset password failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        print(f"SUCCESS: Admin reset password returned: {data['message']}")
        
        # Verify user now has must_change_password=true
        users_response2 = admin_session.get(f"{BASE_URL}/api/users")
        users2 = users_response2.json()
        updated_user = next((u for u in users2 if u["id"] == user_id), None)
        
        # Note: The users list endpoint should include must_change_password
        if "must_change_password" in updated_user:
            assert updated_user["must_change_password"] == True, \
                "After admin reset, must_change_password should be true"
            print("SUCCESS: User has must_change_password=true after admin reset")
        else:
            print("WARNING: must_change_password not in user list response - checking login")
    
    def test_08_user_login_after_admin_reset_shows_must_change_password(self, test_user_email):
        """After admin reset, user login should show must_change_password=true"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user_email,
            "password": "ResetPass1"  # The reset password
        })
        assert response.status_code == 200, f"Login after reset failed: {response.text}"
        
        data = response.json()
        assert data["user"]["must_change_password"] == True, \
            f"After admin reset, must_change_password should be true, got {data['user'].get('must_change_password')}"
        
        print("SUCCESS: After admin reset, login shows must_change_password=true")
    
    def test_09_cleanup_test_user(self, admin_session, test_user_email):
        """Cleanup: Delete test user"""
        # Get user ID
        users_response = admin_session.get(f"{BASE_URL}/api/users")
        users = users_response.json()
        test_user = next((u for u in users if u["email"] == test_user_email), None)
        
        if test_user:
            delete_response = admin_session.delete(f"{BASE_URL}/api/users/{test_user['id']}")
            assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
            print(f"SUCCESS: Test user {test_user_email} cleaned up")
        else:
            print("WARNING: Test user already deleted")


class TestPasswordValidation:
    """Password validation tests"""
    
    @pytest.fixture(scope="class")
    def user_session(self):
        """Login as regular user"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        return session
    
    def test_change_password_requires_uppercase(self, user_session):
        """Change password should require uppercase letter"""
        response = user_session.post(f"{BASE_URL}/api/auth/change-password", json={
            "new_password": "newpassword123"  # Missing uppercase
        })
        # Should fail validation
        assert response.status_code == 422, f"Should reject password without uppercase: {response.text}"
        print("SUCCESS: Password without uppercase rejected")
    
    def test_change_password_requires_lowercase(self, user_session):
        """Change password should require lowercase letter"""
        response = user_session.post(f"{BASE_URL}/api/auth/change-password", json={
            "new_password": "NEWPASSWORD123"  # Missing lowercase
        })
        assert response.status_code == 422, f"Should reject password without lowercase: {response.text}"
        print("SUCCESS: Password without lowercase rejected")
    
    def test_change_password_requires_digit(self, user_session):
        """Change password should require digit"""
        response = user_session.post(f"{BASE_URL}/api/auth/change-password", json={
            "new_password": "NewPassword"  # Missing digit
        })
        assert response.status_code == 422, f"Should reject password without digit: {response.text}"
        print("SUCCESS: Password without digit rejected")
    
    def test_change_password_requires_min_length(self, user_session):
        """Change password should require minimum length"""
        response = user_session.post(f"{BASE_URL}/api/auth/change-password", json={
            "new_password": "Pass1"  # Too short
        })
        assert response.status_code == 422, f"Should reject short password: {response.text}"
        print("SUCCESS: Short password rejected")


class TestAdminResetPasswordEndpoint:
    """Tests for admin reset password endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    @pytest.fixture(scope="class")
    def user_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "user.test@cebuana.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        return session
    
    def test_admin_can_reset_user_password(self, admin_session):
        """Admin should be able to reset any user's password"""
        # Get users list
        users_response = admin_session.get(f"{BASE_URL}/api/users")
        assert users_response.status_code == 200
        
        users = users_response.json()
        # Find a non-admin user
        regular_user = next((u for u in users if u["role"] == "user"), None)
        
        if regular_user:
            response = admin_session.put(f"{BASE_URL}/api/users/{regular_user['id']}/reset-password", json={
                "password": "TempPass123"
            })
            # Should succeed
            assert response.status_code == 200, f"Admin reset password failed: {response.text}"
            print("SUCCESS: Admin can reset user password")
            
            # Reset back to original for other tests
            admin_session.put(f"{BASE_URL}/api/users/{regular_user['id']}/reset-password", json={
                "password": "Test123!"
            })
        else:
            pytest.skip("No regular user found to test")
    
    def test_non_admin_cannot_reset_password(self, user_session, admin_session):
        """Non-admin users should not be able to reset passwords"""
        # Get any user ID
        users_response = admin_session.get(f"{BASE_URL}/api/users")
        users = users_response.json()
        
        if users:
            target_user = users[0]
            response = user_session.put(f"{BASE_URL}/api/users/{target_user['id']}/reset-password", json={
                "password": "HackerPass1"
            })
            # Should be forbidden
            assert response.status_code in [401, 403], \
                f"Non-admin should not be able to reset passwords, got {response.status_code}"
            print("SUCCESS: Non-admin cannot reset user passwords")
    
    def test_reset_password_for_nonexistent_user(self, admin_session):
        """Reset password for non-existent user should return 404"""
        fake_id = str(uuid.uuid4())
        response = admin_session.put(f"{BASE_URL}/api/users/{fake_id}/reset-password", json={
            "password": "SomePass123"
        })
        assert response.status_code == 404, f"Should return 404 for non-existent user: {response.text}"
        print("SUCCESS: 404 returned for non-existent user")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
