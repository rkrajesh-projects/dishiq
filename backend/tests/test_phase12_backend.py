"""
DishIQ Phase 12.2 — Backend and API Integration Unit Tests
Protects user isolation, pantry-cart quantity math, cooking step boundaries,
and personalized recommendation ranking factors.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.pantry import PantryItem
from app.models.recipe import Recipe, RecipeIngredient, Ingredient
from app.models.cooking_session import CookingSession
from app.api.pantry import get_current_user
from app.services.recommendation_service import RecommendationService
from app.services.cooking_session_service import CookingSessionService


@pytest.fixture
def mock_users(seeded_db: Session):
    """Fixture to create two distinct users for isolation testing."""
    # Delete existing users/pantry/sessions to ensure clean state
    seeded_db.query(CookingSession).delete()
    seeded_db.query(PantryItem).delete()
    seeded_db.query(User).delete()
    seeded_db.commit()

    user_a = User(
        email="usera@dishiq.com",
        hashed_password="hashed_password",
        full_name="User A"
    )
    user_b = User(
        email="userb@dishiq.com",
        hashed_password="hashed_password",
        full_name="User B"
    )
    seeded_db.add_all([user_a, user_b])
    seeded_db.commit()
    seeded_db.refresh(user_a)
    seeded_db.refresh(user_b)
    return user_a, user_b


def test_user_isolation_pantry(client: TestClient, seeded_db: Session, mock_users, monkeypatch):
    """Verify that User B cannot read, update, or delete User A's pantry items."""
    user_a, user_b = mock_users

    # Setup monkeypatching for get_current_user to return dynamic mock user
    current_user_holder = [user_a]
    def mock_get_current_user(db):
        return current_user_holder[0]

    monkeypatch.setattr("app.api.pantry.get_current_user", mock_get_current_user)
    import app.api.cooking as cooking_mod
    monkeypatch.setattr(cooking_mod, "get_current_user", mock_get_current_user)
    import app.api.recipes as recipes_mod
    monkeypatch.setattr(recipes_mod, "get_current_user", mock_get_current_user)
    import app.api.profile as profile_mod
    monkeypatch.setattr(profile_mod, "get_current_user", mock_get_current_user)

    # 1. Add pantry item as User A
    payload = {
        "ingredient_name": "Paneer",
        "quantity": 500.0,
        "unit": "g",
    }
    r_add = client.post("/api/pantry", json=payload)
    assert r_add.status_code == 201
    item_id = r_add.json()["id"]

    # Verify User A can retrieve it
    r_get_a = client.get("/api/pantry")
    assert any(x["id"] == item_id for x in r_get_a.json())

    # 2. Switch to User B
    current_user_holder[0] = user_b

    # Verify User B does NOT see User A's pantry item
    r_get_b = client.get("/api/pantry")
    assert not any(x["id"] == item_id for x in r_get_b.json())

    # Verify User B cannot update User A's pantry item (returns 404)
    r_patch = client.patch(f"/api/pantry/{item_id}", json={"quantity": 100.0})
    assert r_patch.status_code == 404

    # Verify User B cannot delete User A's pantry item (returns 404)
    r_delete = client.delete(f"/api/pantry/{item_id}")
    assert r_delete.status_code == 404


def test_pantry_recipe_check_deduction(client: TestClient, seeded_db: Session, mock_users, monkeypatch):
    """
    Verify pantry check status & quantity math:
    - Full pantry coverage -> covered status
    - Partial pantry coverage -> partially_covered status
    - No pantry coverage -> missing status
    """
    user_a, _ = mock_users
    
    current_user_holder = [user_a]
    def mock_get_current_user(db):
        return current_user_holder[0]

    monkeypatch.setattr("app.api.pantry.get_current_user", mock_get_current_user)

    # Create a test recipe with one ingredient
    ing = Ingredient(canonical_name="test_paneer_phase12", category="Dairy", default_unit="g")
    seeded_db.add(ing)
    seeded_db.commit()
    seeded_db.refresh(ing)

    recipe = Recipe(
        name="Paneer Test Dish",
        cuisine="Indian",
        dietary_type="Vegetarian",
        description="Test description",
        instructions=["Step 1"],
        preparation_minutes=5,
        cooking_minutes=5,
        servings=2,
    )
    seeded_db.add(recipe)
    seeded_db.commit()
    seeded_db.refresh(recipe)

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ing.id,
        quantity=500.0,
        unit="g",
        raw_text="500g paneer"
    )
    seeded_db.add(ri)
    seeded_db.commit()

    # Case 1: No pantry availability (missing)
    r_check1 = client.get(f"/api/pantry/check-recipe/{recipe.id}")
    assert r_check1.status_code == 200
    data1 = r_check1.json()
    assert len(data1["missing_ingredients"]) == 1
    assert data1["missing_ingredients"][0]["status"] == "missing"
    assert data1["missing_ingredients"][0]["pantry_quantity"] == 0.0

    # Case 2: Partial pantry availability (partially_covered)
    pantry_item = PantryItem(
        user_id=user_a.id,
        ingredient_id=ing.id,
        quantity=300.0,
        unit="g"
    )
    seeded_db.add(pantry_item)
    seeded_db.commit()

    r_check2 = client.get(f"/api/pantry/check-recipe/{recipe.id}")
    assert r_check2.status_code == 200
    data2 = r_check2.json()
    assert len(data2["partially_covered"]) == 1
    assert data2["partially_covered"][0]["status"] == "partially_covered"
    assert data2["partially_covered"][0]["pantry_quantity"] == 300.0
    assert data2["partially_covered"][0]["required_quantity"] == 500.0

    # Case 3: Full pantry availability (covered)
    pantry_item.quantity = 600.0
    seeded_db.commit()

    r_check3 = client.get(f"/api/pantry/check-recipe/{recipe.id}")
    assert r_check3.status_code == 200
    data3 = r_check3.json()
    assert len(data3["pantry_covered"]) == 1
    assert data3["pantry_covered"][0]["status"] == "covered"
    assert data3["pantry_covered"][0]["pantry_quantity"] == 600.0


def test_cooking_session_step_boundaries(client: TestClient, seeded_db: Session, mock_users, monkeypatch):
    """Verify cooking session step boundary logic, persistence, and completion status."""
    user_a, _ = mock_users
    
    current_user_holder = [user_a]
    def mock_get_current_user(db):
        return current_user_holder[0]

    monkeypatch.setattr("app.api.cooking.get_current_user", mock_get_current_user)

    # Retrieve a seeded recipe
    recipe = seeded_db.query(Recipe).first()
    if not recipe:
        # Fallback recipe if seeded_db was cleared
        recipe = Recipe(
            name="Seeded Dish",
            cuisine="Indian",
            dietary_type="Vegetarian",
            description="Test",
            instructions=["Step 1", "Step 2", "Step 3"],
            preparation_minutes=5,
            cooking_minutes=5,
            servings=2,
        )
        seeded_db.add(recipe)
        seeded_db.commit()
        seeded_db.refresh(recipe)

    # Start session
    r_start = client.post("/api/cooking/sessions", json={"recipe_id": recipe.id, "notes": "Test session"})
    assert r_start.status_code == 201
    session_id = r_start.json()["id"]

    # Verify initial step is 0
    assert r_start.json()["current_step"] == 0
    assert r_start.json()["status"] == "active"

    # Move previous (should stay at step 0)
    r_prev = client.post(f"/api/cooking/sessions/{session_id}/previous")
    assert r_prev.status_code == 200
    assert r_prev.json()["current_step"] == 0

    # Navigate to final step
    total_steps = len(recipe.instructions)
    for _ in range(total_steps + 2):
        r_next = client.post(f"/api/cooking/sessions/{session_id}/next")
        assert r_next.status_code == 200

    # Should cap at max step (total_steps - 1)
    assert r_next.json()["current_step"] == max(0, total_steps - 1)

    # Complete session
    r_comp = client.post(f"/api/cooking/sessions/{session_id}/complete")
    assert r_comp.status_code == 200
    assert r_comp.json()["status"] == "completed"
    assert r_comp.json()["completed_at"] is not None


def test_recommendation_personalized_factors(seeded_db: Session):
    """Verify recommendation service scores candidate recipes based on multi-factor inputs."""
    # Ensure there is at least one recipe in db
    recipe = seeded_db.query(Recipe).first()
    if not recipe:
        recipe = Recipe(
            name="Seeded Boost Dish",
            cuisine="Indian",
            dietary_type="Vegetarian",
            description="Test",
            instructions=["Step 1"],
            preparation_minutes=5,
            cooking_minutes=5,
            servings=2,
        )
        seeded_db.add(recipe)
        seeded_db.commit()
        seeded_db.refresh(recipe)

    service = RecommendationService(seeded_db)

    # Fetch recommendations with empty pantry & no preferences
    recs_empty = service.get_recommendations(limit=5)
    assert len(recs_empty) > 0

    # Verify that pantry matching boosts score
    pantry_ing = []
    if recipe.ingredients:
        pantry_ing = [ri.ingredient.canonical_name for ri in recipe.ingredients[:2]]
    else:
        # If no ingredients exist, make a custom one
        ing = Ingredient(canonical_name="boost_ingredient", category="Custom")
        seeded_db.add(ing)
        seeded_db.commit()
        ri = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=1.0, unit="pieces", raw_text="1 piece")
        seeded_db.add(ri)
        seeded_db.commit()
        pantry_ing = ["boost_ingredient"]

    recs_pantry = service.get_recommendations(pantry_ingredients=pantry_ing, limit=5)
    # Find if explanations contains pantry boost message
    explanations = [item["explanations"] for item in recs_pantry]
    has_pantry_boost = any(any("pantry" in exp for exp in item_exps) for item_exps in explanations)
    assert has_pantry_boost
