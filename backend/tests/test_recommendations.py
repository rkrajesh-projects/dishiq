from fastapi.testclient import TestClient


def test_recipe_search_endpoint_with_query(client: TestClient):
    response = client.get("/api/recipes/search?q=Paneer")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    first = data["items"][0]
    assert "score" in first
    assert "explanations" in first
    assert isinstance(first["explanations"], list)


def test_recipe_search_filtering_by_dietary_type(client: TestClient):
    response = client.get("/api/recipes/search?dietary_type=Vegetarian")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["dietary_type"] == "Vegetarian"


def test_post_recommendations_recipes_endpoint(client: TestClient):
    payload = {
        "query": "Paneer",
        "dietary_type": "Vegetarian",
        "max_time": 30,
        "pantry_ingredients": ["tomato", "onion"],
        "limit": 5
    }
    response = client.post("/api/recommendations/recipes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0
    top_rec = data["recommendations"][0]
    assert top_rec["dietary_type"] == "Vegetarian"
    assert len(top_rec["explanations"]) > 0
