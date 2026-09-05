import pytest
from datetime import datetime, timezone
from fastapi import status
from app.models.recipe import Recipe
from app.models.user import User
from app.api.pantry import get_current_user


def _get_seeded_recipe_and_user(db):
    """Retrieve first user and recipe from the seeded database."""
    user = get_current_user(db)
    recipe = db.query(Recipe).first()
    
    # Ensure recipe has at least 3 instructions for step navigation testing
    if not recipe.instructions or len(recipe.instructions) < 3:
        recipe.instructions = ["Step 1: Prep", "Step 2: Cook", "Step 3: Garnish"]
        db.add(recipe)
        db.commit()
        db.refresh(recipe)
        
    return user, recipe


# 1. Start cooking session successfully
# 2. Invalid recipe returns appropriate error
# 13. Response schema is correct
# 14. Invalid request is handled correctly
def test_start_cooking_session(client, seeded_db):
    user, recipe = _get_seeded_recipe_and_user(seeded_db)
    
    # Successful start
    payload = {"recipe_id": recipe.id, "notes": "Making paneer bhurji"}
    response = client.post("/api/cooking/sessions", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert data["id"] is not None
    assert data["user_id"] == user.id
    assert data["recipe_id"] == recipe.id
    assert data["current_step"] == 0
    assert data["status"] == "active"
    assert data["started_at"] is not None
    assert data["completed_at"] is None
    assert data["notes"] == "Making paneer bhurji"

    # Invalid recipe ID -> 404
    payload_bad = {"recipe_id": "nonexistent-recipe-uuid"}
    response_bad = client.post("/api/cooking/sessions", json=payload_bad)
    assert response_bad.status_code == status.HTTP_404_NOT_FOUND
    assert response_bad.json()["error"]["code"] == "RECIPE_NOT_FOUND"

    # Invalid request body (missing recipe_id) -> 422
    response_invalid = client.post("/api/cooking/sessions", json={})
    assert response_invalid.status_code == 422


# 3. Retrieve existing session
# 4. Retrieve nonexistent session
def test_get_cooking_session(client, seeded_db):
    user, recipe = _get_seeded_recipe_and_user(seeded_db)
    
    # Create session
    payload = {"recipe_id": recipe.id}
    response_create = client.post("/api/cooking/sessions", json=payload)
    session_id = response_create.json()["id"]

    # Retrieve existing
    response_get = client.get(f"/api/cooking/sessions/{session_id}")
    assert response_get.status_code == status.HTTP_200_OK
    assert response_get.json()["id"] == session_id
    assert response_get.json()["recipe_id"] == recipe.id

    # Retrieve nonexistent -> 404
    response_missing = client.get("/api/cooking/sessions/nonexistent-session-uuid")
    assert response_missing.status_code == status.HTTP_404_NOT_FOUND
    assert response_missing.json()["error"]["code"] == "SESSION_NOT_FOUND"


# 5. Next step increments current_step
# 6. Next step cannot exceed available steps
def test_next_step_navigation(client, seeded_db):
    user, recipe = _get_seeded_recipe_and_user(seeded_db)
    total_steps = len(recipe.instructions)
    assert total_steps >= 3

    # Create session
    payload = {"recipe_id": recipe.id}
    response_create = client.post("/api/cooking/sessions", json=payload)
    session_id = response_create.json()["id"]

    # Initial step = 0
    assert response_create.json()["current_step"] == 0

    # Step 1
    res = client.post(f"/api/cooking/sessions/{session_id}/next")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["current_step"] == 1

    # Step 2
    res = client.post(f"/api/cooking/sessions/{session_id}/next")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["current_step"] == 2

    # Attempt to exceed maximum steps
    for _ in range(total_steps):
        res = client.post(f"/api/cooking/sessions/{session_id}/next")
        assert res.status_code == status.HTTP_200_OK
        
    # Verify current_step stays locked at total_steps - 1
    assert res.json()["current_step"] == total_steps - 1


# 7. Previous step decrements current_step
# 8. Previous step cannot go below zero
def test_previous_step_navigation(client, seeded_db):
    user, recipe = _get_seeded_recipe_and_user(seeded_db)
    
    # Create session
    payload = {"recipe_id": recipe.id}
    response_create = client.post("/api/cooking/sessions", json=payload)
    session_id = response_create.json()["id"]

    # Move to step 2 first
    client.post(f"/api/cooking/sessions/{session_id}/next")
    res_step2 = client.post(f"/api/cooking/sessions/{session_id}/next")
    assert res_step2.json()["current_step"] == 2

    # Go back to step 1
    res = client.post(f"/api/cooking/sessions/{session_id}/previous")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["current_step"] == 1

    # Go back to step 0
    res = client.post(f"/api/cooking/sessions/{session_id}/previous")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["current_step"] == 0

    # Try to go below zero (boundary limit check)
    res = client.post(f"/api/cooking/sessions/{session_id}/previous")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["current_step"] == 0


# 9. Complete session changes status
# 10. Complete session sets completed_at
# 11. Completing an already completed session behaves safely
# 12. Completed session cannot be navigated unexpectedly
def test_complete_session_and_behavior(client, seeded_db):
    user, recipe = _get_seeded_recipe_and_user(seeded_db)
    
    # Create session
    payload = {"recipe_id": recipe.id}
    response_create = client.post("/api/cooking/sessions", json=payload)
    session_id = response_create.json()["id"]

    # Mark completed
    res = client.post(f"/api/cooking/sessions/{session_id}/complete")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None
    first_completion_time = data["completed_at"]

    # Complete again (should behave safely and keep completion timestamp unchanged)
    res_second = client.post(f"/api/cooking/sessions/{session_id}/complete")
    assert res_second.status_code == status.HTTP_200_OK
    assert res_second.json()["status"] == "completed"
    assert res_second.json()["completed_at"] == first_completion_time

    # Navigating next/previous on completed session must return 400 Bad Request
    res_next = client.post(f"/api/cooking/sessions/{session_id}/next")
    assert res_next.status_code == status.HTTP_400_BAD_REQUEST
    assert res_next.json()["error"]["code"] == "SESSION_COMPLETED"

    res_prev = client.post(f"/api/cooking/sessions/{session_id}/previous")
    assert res_prev.status_code == status.HTTP_400_BAD_REQUEST
    assert res_prev.json()["error"]["code"] == "SESSION_COMPLETED"


def test_get_active_cooking_session(client, seeded_db):
    user, recipe = _get_seeded_recipe_and_user(seeded_db)

    # Clean up/complete any pre-existing active sessions in the database for this user
    from app.models.cooking_session import CookingSession
    existing_sessions = seeded_db.query(CookingSession).filter(
        CookingSession.user_id == user.id,
        CookingSession.status == "active"
    ).all()
    for s in existing_sessions:
        s.status = "completed"
    seeded_db.commit()

    # 1. Initially, there should be no active session
    res_empty = client.get("/api/cooking/sessions/active")
    assert res_empty.status_code == status.HTTP_200_OK
    assert res_empty.json() is None

    # 2. Create an active session
    payload = {"recipe_id": recipe.id}
    res_create1 = client.post("/api/cooking/sessions", json=payload)
    assert res_create1.status_code == status.HTTP_201_CREATED
    session1_id = res_create1.json()["id"]

    # 3. GET active session should return this active session
    res_active = client.get("/api/cooking/sessions/active")
    assert res_active.status_code == status.HTTP_200_OK
    assert res_active.json()["id"] == session1_id
    assert res_active.json()["status"] == "active"

    # 4. Multiple active sessions -> should return the most recently started one
    import time
    time.sleep(0.1) # brief pause to guarantee different started_at timestamp ordering
    res_create2 = client.post("/api/cooking/sessions", json=payload)
    session2_id = res_create2.json()["id"]

    res_active_multi = client.get("/api/cooking/sessions/active")
    assert res_active_multi.status_code == status.HTTP_200_OK
    assert res_active_multi.json()["id"] == session2_id # most recently started

    # 5. Complete the session
    client.post(f"/api/cooking/sessions/{session2_id}/complete")

    # Now the first active session becomes the active one since it's still active
    res_active_fallback = client.get("/api/cooking/sessions/active")
    assert res_active_fallback.status_code == status.HTTP_200_OK
    assert res_active_fallback.json()["id"] == session1_id

    # Complete the first one too
    client.post(f"/api/cooking/sessions/{session1_id}/complete")

    # Now no active session exists
    res_none = client.get("/api/cooking/sessions/active")
    assert res_none.status_code == status.HTTP_200_OK
    assert res_none.json() is None
