from fastapi.testclient import TestClient


def test_get_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["application"] == "DishIQ"


def test_get_recipes_list_paginated(client: TestClient):
    response = client.get("/api/recipes?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data

    assert len(data["items"]) == 5
    assert data["total"] >= 15
    assert data["page"] == 1
    assert data["page_size"] == 5


def test_get_recipes_filtering_by_cuisine_and_diet(client: TestClient):
    # Filter by Indian cuisine
    response = client.get("/api/recipes?cuisine=Indian")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["cuisine"] == "Indian"

    # Filter by Vegetarian
    response_veg = client.get("/api/recipes?dietary_type=Vegetarian")
    assert response_veg.status_code == 200
    data_veg = response_veg.json()
    assert data_veg["total"] > 0
    for item in data_veg["items"]:
        assert item["dietary_type"] == "Vegetarian"


def test_get_recipe_by_id_detail(client: TestClient):
    # Get recipe list first
    list_res = client.get("/api/recipes?page=1&page_size=1")
    first_recipe_id = list_res.json()["items"][0]["id"]

    # Query detail endpoint
    response = client.get(f"/api/recipes/{first_recipe_id}")
    assert response.status_code == 200
    detail = response.json()

    assert detail["id"] == first_recipe_id
    assert "instructions" in detail
    assert isinstance(detail["instructions"], list)
    assert "ingredients" in detail
    assert len(detail["ingredients"]) > 0


def test_get_recipe_not_found_404(client: TestClient):
    response = client.get("/api/recipes/non_existent_id_123")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RECIPE_NOT_FOUND"


def test_get_stores_list(client: TestClient):
    response = client.get("/api/stores")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert len(data["items"]) == 3
    for store in data["items"]:
        assert store["is_demo_store"] is True


def test_get_products_list_and_filtering(client: TestClient):
    # Get all products
    response = client.get("/api/products?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 100
    assert len(data["items"]) == 10

    first_product = data["items"][0]
    assert "prices" in first_product
    assert len(first_product["prices"]) > 0
    assert first_product["prices"][0]["data_source_type"] == "demo"

    # Filter by category Dairy
    dairy_res = client.get("/api/products?category=Dairy")
    assert dairy_res.status_code == 200
    dairy_data = dairy_res.json()
    assert dairy_data["total"] > 0
    for product in dairy_data["items"]:
        assert product["category"] == "Dairy"
