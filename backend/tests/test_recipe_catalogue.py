import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.recipe import Recipe, RecipeIngredient, Ingredient


def test_recipe_detail_provenance_fields(client: TestClient, seeded_db: Session):
    """Verify RecipeDetailRead includes all required provenance and attribution fields."""
    recipe = Recipe(
        name="Authentic Hyderabadi Biryani",
        description="A traditional celebratory rice dish from Hyderabad.",
        cuisine="Indian",
        dietary_type="Non-Vegetarian",
        preparation_minutes=30,
        cooking_minutes=45,
        servings=6,
        source_name="Archana's Kitchen",
        source_url="https://archanaskitchen.com/hyderabadi-biryani",
        author="Archana Doshi",
        source_license="CC-BY-NC-SA 4.0",
        region="South India",
        state="Telangana",
        original_name="Kacchi Biryani",
        is_indian_recipe=1,
        verification_status="VERIFIED",
        instructions=["Marinate meat", "Layer parboiled rice", "Dum cook on low flame"],
    )
    seeded_db.add(recipe)
    seeded_db.commit()
    seeded_db.refresh(recipe)

    response = client.get(f"/api/recipes/{recipe.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == recipe.id
    assert data["name"] == "Authentic Hyderabadi Biryani"
    assert data["author"] == "Archana Doshi"
    assert data["source_license"] == "CC-BY-NC-SA 4.0"
    assert data["region"] == "South India"
    assert data["state"] == "Telangana"
    assert data["original_name"] == "Kacchi Biryani"
    assert data["is_indian_recipe"] is True
    assert data["verification_status"] == "VERIFIED"
    assert data["source_url"] == "https://archanaskitchen.com/hyderabadi-biryani"
    assert len(data["instructions"]) == 3


def test_recipe_detail_structured_instructions(client: TestClient, seeded_db: Session):
    """Verify structured instructions are properly parsed and exposed alongside legacy instructions."""
    structured_steps = [
        {
            "step_number": 1,
            "text": "Whisk eggs with a pinch of salt and pepper.",
            "action_type": "WHISK",
            "timing_minutes": 2,
            "temperature": None,
            "equipment": ["whisk", "bowl"],
            "ingredients": ["eggs", "salt", "black pepper"],
        },
        {
            "step_number": 2,
            "text": "Melt butter in skillet over medium-low heat.",
            "action_type": "HEAT",
            "timing_minutes": 1,
            "temperature": "Medium-low",
            "equipment": ["skillet", "spatula"],
            "ingredients": ["butter"],
        },
    ]

    recipe = Recipe(
        name="Soft Scrambled Eggs",
        description="Creamy, gently scrambled eggs.",
        cuisine="American",
        dietary_type="Vegetarian",
        preparation_minutes=2,
        cooking_minutes=5,
        servings=2,
        instructions=structured_steps,
    )
    seeded_db.add(recipe)
    seeded_db.commit()
    seeded_db.refresh(recipe)

    response = client.get(f"/api/recipes/{recipe.id}")
    assert response.status_code == 200
    data = response.json()

    # Legacy instructions should extract plain string step texts
    assert data["instructions"] == [
        "Whisk eggs with a pinch of salt and pepper.",
        "Melt butter in skillet over medium-low heat.",
    ]
    # Structured instructions should contain detailed step data
    assert data["structured_instructions"] is not None
    assert len(data["structured_instructions"]) == 2
    assert data["structured_instructions"][0]["action_type"] == "WHISK"
    assert data["structured_instructions"][0]["timing_minutes"] == 2
    assert data["structured_instructions"][1]["temperature"] == "Medium-low"


def test_recipe_filters_normalization(client: TestClient, seeded_db: Session):
    """Verify /api/recipes/filters cleans trailing ' Recipes' and eliminates duplicates."""
    r1 = Recipe(
        name="Filter Test Recipe 1",
        description="Desc",
        cuisine="Bengali",
        dietary_type="Vegetarian",
        instructions=["Step 1"],
    )
    r2 = Recipe(
        name="Filter Test Recipe 2",
        description="Desc",
        cuisine="Bengali Recipes",
        dietary_type="Vegetarian",
        instructions=["Step 1"],
    )
    seeded_db.add_all([r1, r2])
    seeded_db.commit()

    response = client.get("/api/recipes/filters")
    assert response.status_code == 200
    data = response.json()

    assert "cuisines" in data
    assert "dietary_types" in data
    # "Bengali" must appear, and "Bengali Recipes" should not be a separate duplicate entry
    assert "Bengali" in data["cuisines"]
    assert "Bengali Recipes" not in data["cuisines"]
    assert len([c for c in data["cuisines"] if c == "Bengali"]) == 1


def test_recipe_search_by_cuisine_alias(client: TestClient, seeded_db: Session):
    """Verify search endpoint correctly matches cuisine when queried with or without 'Recipes' suffix."""
    r = Recipe(
        name="Alias Test Curry",
        description="Flavorful curry.",
        cuisine="Goan",
        dietary_type="Non-Vegetarian",
        instructions=["Cook curry"],
    )
    seeded_db.add(r)
    seeded_db.commit()

    # Query with exact cuisine
    res1 = client.get("/api/recipes/search?cuisine=Goan")
    assert res1.status_code == 200
    names1 = [item["name"] for item in res1.json()["items"]]
    assert "Alias Test Curry" in names1

    # Query with suffix alias
    res2 = client.get("/api/recipes/search?cuisine=Goan%20Recipes")
    assert res2.status_code == 200
    names2 = [item["name"] for item in res2.json()["items"]]
    assert "Alias Test Curry" in names2


def test_recipe_list_by_cuisine_alias(client: TestClient, seeded_db: Session):
    """Verify /api/recipes list endpoint filters by cuisine with or without suffix."""
    r = Recipe(
        name="Maharashtrian Poha",
        description="Flattened rice breakfast.",
        cuisine="Maharashtrian",
        dietary_type="Vegetarian",
        instructions=["Rinse poha", "Saute peanuts and mustard seeds"],
    )
    seeded_db.add(r)
    seeded_db.commit()

    res1 = client.get("/api/recipes?cuisine=Maharashtrian")
    assert res1.status_code == 200
    items1 = [i["name"] for i in res1.json()["items"]]
    assert "Maharashtrian Poha" in items1

    res2 = client.get("/api/recipes?cuisine=Maharashtrian%20Recipes")
    assert res2.status_code == 200
    items2 = [i["name"] for i in res2.json()["items"]]
    assert "Maharashtrian Poha" in items2


def test_recipe_not_found(client: TestClient):
    """Verify non-existent recipe ID returns 404."""
    response = client.get("/api/recipes/non-existent-uuid-999")
    assert response.status_code == 404
    data = response.json()
    assert ("detail" in data) or ("message" in data) or ("error" in data and data["error"]["code"] == "RECIPE_NOT_FOUND")
