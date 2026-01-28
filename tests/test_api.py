"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Soccer Team": {
            "description": "Join our competitive soccer team and represent Mergington High",
            "schedule": "Mondays and Wednesdays, 3:30 PM - 5:30 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "sarah@mergington.edu"]
        },
        "Basketball Club": {
            "description": "Practice basketball skills and participate in local tournaments",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 6:00 PM",
            "max_participants": 15,
            "participants": ["james@mergington.edu", "emily@mergington.edu"]
        },
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": []
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that root redirects to the static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_activities_success(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Chess Club" in data
        
        # Verify activity structure
        assert data["Soccer Team"]["max_participants"] == 25
        assert len(data["Soccer Team"]["participants"]) == 2
        assert "alex@mergington.edu" in data["Soccer Team"]["participants"]

    def test_get_activities_returns_dict(self, client):
        """Test that activities endpoint returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_signup_already_registered(self, client):
        """Test signup when student is already registered"""
        response = client.post(
            "/activities/Soccer Team/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"]

    def test_signup_with_special_characters(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Soccer%20Team/signup?email=newplayer@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newplayer@mergington.edu" in activities_data["Soccer Team"]["participants"]


class TestUnregisterFromActivity:
    """Tests for the POST /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        # Verify student is registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" in activities_data["Soccer Team"]["participants"]

        # Unregister
        response = client.post(
            "/activities/Soccer Team/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "alex@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]

        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]

    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_unregister_not_registered(self, client):
        """Test unregister when student is not registered"""
        response = client.post(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "not signed up" in data["detail"]

    def test_unregister_with_special_characters(self, client):
        """Test unregister with URL-encoded activity name"""
        response = client.post(
            "/activities/Basketball%20Club/unregister?email=james@mergington.edu"
        )
        assert response.status_code == 200


class TestWorkflow:
    """Integration tests for complete workflows"""

    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signup and unregister"""
        email = "workflow@mergington.edu"
        activity = "Chess Club"

        # Get initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])

        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200

        # Verify signup
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        assert email in response.json()[activity]["participants"]

        # Unregister
        unregister_response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200

        # Verify unregistration
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
        assert email not in response.json()[activity]["participants"]

    def test_multiple_signups_different_activities(self, client):
        """Test signing up for multiple different activities"""
        email = "multi@mergington.edu"

        # Sign up for multiple activities
        response1 = client.post(f"/activities/Soccer Team/signup?email={email}")
        assert response1.status_code == 200

        response2 = client.post(f"/activities/Basketball Club/signup?email={email}")
        assert response2.status_code == 200

        response3 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response3.status_code == 200

        # Verify all signups
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email in data["Soccer Team"]["participants"]
        assert email in data["Basketball Club"]["participants"]
        assert email in data["Chess Club"]["participants"]
