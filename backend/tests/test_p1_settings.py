"""
Test P1 Features: Admin Settings Page
- CSV Template Downloads (users, buildings, zones)
- Site Content API (GET /api/site-content, PUT /api/admin/site-content)

Optimized to minimize login requests to avoid rate limiting.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"

# Shared session for admin tests
_admin_session = None

def get_admin_session():
    """Get a shared admin session to avoid multiple logins"""
    global _admin_session
    if _admin_session is None:
        _admin_session = requests.Session()
        response = _admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        _admin_session.cookies.update(response.cookies)
    return _admin_session


class TestCSVTemplates:
    """Test CSV template download endpoints (requires admin auth)"""
    
    def test_download_users_template(self):
        """Test GET /api/templates/users returns CSV"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/templates/users")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify CSV content type
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        # Verify CSV has expected columns
        content = response.text
        assert "email" in content
        assert "first_name" in content
        assert "last_name" in content
        print(f"Users template CSV:\n{content[:200]}")
    
    def test_download_buildings_template(self):
        """Test GET /api/templates/buildings returns CSV"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/templates/buildings")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify CSV content type
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        # Verify CSV has expected columns
        content = response.text
        assert "building_name" in content
        assert "floor_label" in content
        assert "slot_labels" in content
        print(f"Buildings template CSV:\n{content[:200]}")
    
    def test_download_zones_template(self):
        """Test GET /api/templates/zones returns CSV"""
        session = get_admin_session()
        response = session.get(f"{BASE_URL}/api/templates/zones")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify CSV content type
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        # Verify CSV has expected columns
        content = response.text
        assert "zone_name" in content
        assert "building_names" in content
        print(f"Zones template CSV:\n{content[:200]}")
    
    def test_templates_require_admin_auth(self):
        """Test that templates endpoints require admin authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        
        # Test users template
        response = no_auth_session.get(f"{BASE_URL}/api/templates/users")
        assert response.status_code == 401, f"Users template should require auth: {response.status_code}"
        
        # Test buildings template
        response = no_auth_session.get(f"{BASE_URL}/api/templates/buildings")
        assert response.status_code == 401, f"Buildings template should require auth: {response.status_code}"
        
        # Test zones template
        response = no_auth_session.get(f"{BASE_URL}/api/templates/zones")
        assert response.status_code == 401, f"Zones template should require auth: {response.status_code}"
        print("All template endpoints correctly require admin auth")


class TestSiteContentAPI:
    """Test Site Content API for login page customization"""
    
    def test_get_site_content_public_no_auth(self):
        """Test GET /api/site-content is public (no auth required) and returns default content"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/site-content")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Should have all content fields
        assert "heading_line1" in data
        assert "heading_highlight" in data
        assert "heading_line3" in data
        assert "description" in data
        assert "badge1_text" in data
        assert "badge2_text" in data
        assert "announcement" in data
        print(f"Site content response: {data}")
    
    def test_update_site_content_requires_admin(self):
        """Test PUT /api/admin/site-content requires admin auth"""
        # Test without auth
        session = requests.Session()
        response = session.put(f"{BASE_URL}/api/admin/site-content", json={
            "heading_line1": "Test"
        })
        assert response.status_code == 401, f"Should require auth: {response.status_code}"
        print("Site content update correctly requires admin auth")
    
    def test_update_and_verify_site_content(self):
        """Test PUT /api/admin/site-content updates content successfully"""
        session = get_admin_session()
        
        # Update content
        test_content = {
            "heading_line1": "TEST_Reserve Your",
            "heading_highlight": "TEST_Parking Spot",
            "heading_line3": "TEST_with Ease",
            "description": "TEST_Description text for testing",
            "badge1_text": "TEST_Badge1",
            "badge2_text": "TEST_Badge2",
            "announcement": "TEST_Announcement text"
        }
        response = session.put(f"{BASE_URL}/api/admin/site-content", json=test_content)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert data["message"] == "Site content updated"
        print(f"Update response: {data}")
        
        # Verify content was updated by reading it back
        get_response = session.get(f"{BASE_URL}/api/site-content")
        assert get_response.status_code == 200
        
        content = get_response.json()
        assert content["heading_line1"] == "TEST_Reserve Your"
        assert content["heading_highlight"] == "TEST_Parking Spot"
        assert content["announcement"] == "TEST_Announcement text"
        print(f"Verified content after update: {content}")
    
    def test_partial_update_site_content(self):
        """Test that partial updates work (only updating some fields)"""
        session = get_admin_session()
        
        # Update only announcement
        response = session.put(f"{BASE_URL}/api/admin/site-content", json={
            "announcement": "TEST_New Announcement Only"
        })
        assert response.status_code == 200
        
        # Verify announcement was updated
        get_response = session.get(f"{BASE_URL}/api/site-content")
        content = get_response.json()
        assert content["announcement"] == "TEST_New Announcement Only"
        print(f"Partial update worked: announcement = {content['announcement']}")
    
    def test_clear_announcement_and_reset(self):
        """Test clearing the announcement field and reset to defaults"""
        session = get_admin_session()
        
        # Set announcement to empty string
        response = session.put(f"{BASE_URL}/api/admin/site-content", json={
            "announcement": ""
        })
        assert response.status_code == 200
        
        # Verify announcement is cleared
        get_response = session.get(f"{BASE_URL}/api/site-content")
        content = get_response.json()
        assert content["announcement"] == ""
        print("Announcement cleared successfully")
        
        # Reset to default content
        default_content = {
            "heading_line1": "Reserve Your",
            "heading_highlight": "Parking Spot",
            "heading_line3": "with Ease",
            "description": "Seamlessly book, manage, and track your parking reservations across all Cebuana Lhuillier buildings.",
            "badge1_text": "Multiple Buildings",
            "badge2_text": "Secure Access",
            "announcement": ""
        }
        response = session.put(f"{BASE_URL}/api/admin/site-content", json=default_content)
        assert response.status_code == 200
        print("Site content reset to defaults")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
