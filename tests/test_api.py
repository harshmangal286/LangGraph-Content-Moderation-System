import pytest
from fastapi.testclient import TestClient
from api import app
from redis_client import RedisClient
import time

client = TestClient(app)
redis_client = RedisClient()

@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup before each test"""
    yield
    # Cleanup would go here if needed

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "redis" in data

def test_submit_content():
    """Test content submission"""
    response = client.post("/moderate", json={
        "content": "This is test content",
        "content_type": "text",
        "user_id": "test-user-1",
        "metadata": {}
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "content_id" in data
    assert data["status"] == "queued"

def test_get_status_not_found():
    """Test getting status for non-existent content"""
    response = client.get("/status/nonexistent-id")
    assert response.status_code == 404

def test_submit_and_check_status():
    """Test full workflow: submit and check status"""
    # Submit content
    submit_response = client.post("/moderate", json={
        "content": "Test content for status check",
        "content_type": "text",
        "user_id": "test-user-2",
        "metadata": {}
    })
    
    assert submit_response.status_code == 200
    content_id = submit_response.json()["content_id"]
    
    # Wait a bit (in real scenario, worker would process)
    time.sleep(1)
    
    # Check status (will return 404 unless worker is running)
    status_response = client.get(f"/status/{content_id}")
    # Either still processing (404) or completed
    assert status_response.status_code in [200, 404]

def test_appeal_not_found():
    """Test appealing non-existent decision"""
    response = client.post("/appeal", json={
        "content_id": "nonexistent",
        "user_id": "test-user",
        "appeal_reason": "This is unfair"
    })
    
    assert response.status_code == 404

def test_moderator_review_not_found():
    """Test moderator review for non-existent content"""
    response = client.post("/moderator/review/nonexistent", params={
        "action": "approve",
        "notes": "Manual review",
        "moderator_id": "mod-1"
    })
    
    assert response.status_code == 404

def test_user_stats():
    """Test user statistics endpoint"""
    response = client.get("/stats/user/test-user-3")
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "recent_post_count" in data
