"""
Backend tests for the Profile and Preferences API endpoints.
Phase 11.2 — ProfilePage Live API and Preferences Backend Integration
"""
from fastapi.testclient import TestClient


def test_get_profile_returns_default_user_with_preferences(client: TestClient):
    """GET /api/profile should return user information and nested preferences."""
    response = client.get("/api/profile")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "email" in data
    assert "full_name" in data
    assert "preference" in data
    
    pref = data["preference"]
    assert "dietary_type" in pref
    assert "weekly_budget" in pref
    assert "household_size" in pref
    assert isinstance(pref["weekly_budget"], float)
    assert isinstance(pref["household_size"], int)


def test_update_profile_preferences(client: TestClient):
    """PATCH /api/profile should update user details and preferences successfully."""
    payload = {
        "full_name": "Rajesh Kumar Updated",
        "dietary_type": "Vegetarian",
        "weekly_budget": 3500.0,
        "household_size": 5
    }
    response = client.patch("/api/profile", json=payload)
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert data["full_name"] == "Rajesh Kumar Updated"
    
    pref = data["preference"]
    assert pref["dietary_type"] == "Vegetarian"
    assert pref["weekly_budget"] == 3500.0
    assert pref["household_size"] == 5

    # Verify via subsequent GET
    get_res = client.get("/api/profile")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["full_name"] == "Rajesh Kumar Updated"
    assert get_data["preference"]["dietary_type"] == "Vegetarian"
    assert get_data["preference"]["weekly_budget"] == 3500.0
    assert get_data["preference"]["household_size"] == 5


def test_update_profile_validation_errors(client: TestClient):
    """PATCH /api/profile validation errors for invalid values."""
    # Test invalid budget (less than or equal to 0)
    payload_bad_budget = {"weekly_budget": 0.0}
    res1 = client.patch("/api/profile", json=payload_bad_budget)
    assert res1.status_code == 422

    # Test invalid household size (less than 1)
    payload_bad_household = {"household_size": 0}
    res2 = client.patch("/api/profile", json=payload_bad_household)
    assert res2.status_code == 422
