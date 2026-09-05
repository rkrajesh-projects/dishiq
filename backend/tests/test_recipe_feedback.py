"""
Backend tests for the Recipe Feedback and Ratings API endpoints.
Phase 11.3 — Recipe Feedback Loop and Ratings
"""
from fastapi.testclient import TestClient


def test_submit_recipe_feedback_success(client: TestClient):
    """POST /api/recipes/{recipe_id}/feedback should submit feedback successfully."""
    # Paneer Bhurji is seeded with name "Paneer Bhurji" in seed.py.
    # Let's search or get all recipes to find a valid recipe ID.
    recipes_res = client.get("/api/recipes")
    assert recipes_res.status_code == 200
    recipes_data = recipes_res.json()["items"]
    assert len(recipes_data) > 0
    recipe_id = recipes_data[0]["id"]

    # Submit feedback
    payload = {
        "rating": 5,
        "difficulty": "Easy",
        "notes": "Absolutely loved it! Very simple and tasty."
    }
    response = client.post(f"/api/recipes/{recipe_id}/feedback", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["recipe_id"] == recipe_id
    assert data["rating"] == 5
    assert data["difficulty"] == "Easy"
    assert data["notes"] == "Absolutely loved it! Very simple and tasty."
    assert "user_id" in data
    assert "created_at" in data


def test_submit_recipe_feedback_duplicate_prevented(client: TestClient):
    """POST /api/recipes/{recipe_id}/feedback should reject duplicate submissions."""
    recipes_res = client.get("/api/recipes")
    recipes_data = recipes_res.json()["items"]
    recipe_id = recipes_data[0]["id"]

    # Submit first time (if not already submitted by previous test)
    payload = {
        "rating": 4,
        "difficulty": "Medium",
        "notes": "Good recipe."
    }
    # Clear any previous test feedback by using index 1 (or we can just attempt first call which might conflict, or clean state)
    # Actually, let's use the second recipe in the list to avoid conflicts with previous test
    assert len(recipes_data) > 1
    recipe_id = recipes_data[1]["id"]

    response1 = client.post(f"/api/recipes/{recipe_id}/feedback", json=payload)
    assert response1.status_code == 201

    # Submit second time (duplicate)
    response2 = client.post(f"/api/recipes/{recipe_id}/feedback", json=payload)
    assert response2.status_code == 400
    assert "Feedback already submitted" in response2.json()["error"]["message"]


def test_submit_recipe_feedback_not_found(client: TestClient):
    """POST /api/recipes/{recipe_id}/feedback returns 404 if recipe does not exist."""
    payload = {
        "rating": 5,
        "difficulty": "Easy"
    }
    response = client.post("/api/recipes/non_existent_recipe_id/feedback", json=payload)
    assert response.status_code == 404


def test_submit_recipe_feedback_validation_error(client: TestClient):
    """POST /api/recipes/{recipe_id}/feedback returns 422 for invalid ratings."""
    recipes_res = client.get("/api/recipes")
    recipe_id = recipes_res.json()["items"][0]["id"]

    # Rating less than 1
    response1 = client.post(f"/api/recipes/{recipe_id}/feedback", json={"rating": 0})
    assert response1.status_code == 422

    # Rating greater than 5
    response2 = client.post(f"/api/recipes/{recipe_id}/feedback", json={"rating": 6})
    assert response2.status_code == 422
