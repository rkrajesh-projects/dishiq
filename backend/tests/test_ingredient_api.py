"""
DishIQ Phase 5.2 — Ingredient Intelligence API Tests
Tests for POST /api/ingredients/parse and GET /api/recipes/{id}/ingredients.
"""

from typing import Dict, Any


def test_parse_endpoint_metadata(client):
    response = client.post(
        "/api/ingredients/parse",
        json={"ingredients": ["2 large onions, finely chopped", "500 g paneer", "mystery herb xyz"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    results = data["results"]

    # Onion
    onion = results[0]
    assert onion["canonical_name"] == "onion"
    assert onion["category"] == "vegetable"
    assert onion["matched_alias"] is not None
    assert onion["normalization_source"] == "dictionary"
    assert onion["parser_version"] == "1.0"

    # Paneer
    paneer = results[1]
    assert paneer["canonical_name"] == "paneer"
    assert paneer["category"] == "dairy"
    assert paneer["normalization_source"] == "dictionary"
    assert paneer["parser_version"] == "1.0"

    # Unknown
    unknown = results[2]
    assert unknown["category"] is None
    assert unknown["matched_alias"] is None
    assert unknown["normalization_source"] == "unknown"
    assert unknown["parser_version"] == "1.0"


def test_parse_paneer_standalone_api(client):
    response = client.post(
        "/api/ingredients/parse",
        json={"ingredients": ["paneer"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    p = data["results"][0]
    assert p["canonical_name"] == "paneer"
    assert p["normalization_source"] == "dictionary"
    assert p["matched_alias"] == "paneer"


def test_recipe_ingredients_metadata(client):
    recipes_resp = client.get("/api/recipes/search?page_size=1")
    assert recipes_resp.status_code == 200
    items = recipes_resp.json()["items"]
    if items:
        recipe_id = items[0]["id"]
        resp = client.get(f"/api/recipes/{recipe_id}/ingredients")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "results" in data
        if data["count"] > 0:
            first_ing = data["results"][0]
            assert "display_name" in first_ing
            assert "canonical_name" in first_ing
            assert "normalization_source" in first_ing
            assert "parser_version" in first_ing
