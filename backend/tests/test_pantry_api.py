"""
Backend tests for the Pantry API endpoints.
Phase 11.1 — PantryPage Live API Integration
"""
from fastapi.testclient import TestClient


def test_get_pantry_returns_list(client: TestClient):
    """GET /api/pantry should return a list (empty or populated)."""
    response = client.get("/api/pantry")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_add_pantry_item(client: TestClient):
    """POST /api/pantry should add a new pantry item and return PantryItemRead."""
    payload = {
        "ingredient_name": "test_tomato_phase11",
        "quantity": 1.5,
        "unit": "kg",
        "expiration_date": "2099-12-31",
    }
    response = client.post("/api/pantry", json=payload)
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["ingredient_name"] == "test_tomato_phase11"
    assert data["quantity"] == 1.5
    assert data["unit"] == "kg"
    assert data["expiration_date"] == "2099-12-31"
    assert "id" in data


def test_add_pantry_item_increments_existing(client: TestClient):
    """Adding the same ingredient twice should increment quantity."""
    payload = {
        "ingredient_name": "test_onion_phase11",
        "quantity": 1.0,
        "unit": "kg",
    }
    r1 = client.post("/api/pantry", json=payload)
    assert r1.status_code == 201
    initial_qty = r1.json()["quantity"]

    r2 = client.post("/api/pantry", json=payload)
    assert r2.status_code == 201
    # Quantity should be incremented
    assert r2.json()["quantity"] == initial_qty + 1.0


def test_add_pantry_item_without_expiry(client: TestClient):
    """POST /api/pantry without expiration_date should succeed with null expiry."""
    payload = {
        "ingredient_name": "test_spinach_phase11",
        "quantity": 200.0,
        "unit": "grams",
    }
    response = client.post("/api/pantry", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["expiration_date"] is None


def test_add_pantry_item_validation_zero_quantity(client: TestClient):
    """POST /api/pantry with quantity=0 should return 422 Unprocessable Entity."""
    payload = {
        "ingredient_name": "bad_item",
        "quantity": 0.0,
        "unit": "pieces",
    }
    response = client.post("/api/pantry", json=payload)
    assert response.status_code == 422


def test_add_pantry_item_validation_empty_name(client: TestClient):
    """POST /api/pantry with empty ingredient_name should return 422."""
    payload = {
        "ingredient_name": "",
        "quantity": 1.0,
        "unit": "pieces",
    }
    response = client.post("/api/pantry", json=payload)
    assert response.status_code == 422


def test_update_pantry_item(client: TestClient):
    """PATCH /api/pantry/:id should update quantity and unit."""
    # First add an item to update
    add_payload = {
        "ingredient_name": "test_paneer_phase11",
        "quantity": 100.0,
        "unit": "grams",
    }
    add_res = client.post("/api/pantry", json=add_payload)
    assert add_res.status_code == 201
    item_id = add_res.json()["id"]

    # Now update it
    update_payload = {"quantity": 250.0, "unit": "grams"}
    update_res = client.patch(f"/api/pantry/{item_id}", json=update_payload)
    assert update_res.status_code == 200

    data = update_res.json()
    assert data["id"] == item_id
    assert data["quantity"] == 250.0
    assert data["unit"] == "grams"


def test_update_pantry_item_expiry(client: TestClient):
    """PATCH /api/pantry/:id should be able to set expiration_date."""
    add_res = client.post("/api/pantry", json={
        "ingredient_name": "test_butter_phase11",
        "quantity": 50.0,
        "unit": "grams",
    })
    assert add_res.status_code == 201
    item_id = add_res.json()["id"]

    update_res = client.patch(f"/api/pantry/{item_id}", json={"expiration_date": "2099-06-30"})
    assert update_res.status_code == 200
    assert update_res.json()["expiration_date"] == "2099-06-30"


def test_update_pantry_item_not_found(client: TestClient):
    """PATCH /api/pantry/:id with unknown id should return 404."""
    response = client.patch("/api/pantry/nonexistent-id-xyz", json={"quantity": 1.0})
    assert response.status_code == 404


def test_delete_pantry_item(client: TestClient):
    """DELETE /api/pantry/:id should remove the item (204)."""
    add_res = client.post("/api/pantry", json={
        "ingredient_name": "test_egg_phase11",
        "quantity": 6.0,
        "unit": "pieces",
    })
    assert add_res.status_code == 201
    item_id = add_res.json()["id"]

    del_res = client.delete(f"/api/pantry/{item_id}")
    assert del_res.status_code == 204

    # Verify deleted item is gone from list
    list_res = client.get("/api/pantry")
    ids = [item["id"] for item in list_res.json()]
    assert item_id not in ids


def test_delete_pantry_item_not_found(client: TestClient):
    """DELETE /api/pantry/:id with unknown id should return 404."""
    response = client.delete("/api/pantry/nonexistent-id-abc")
    assert response.status_code == 404


def test_get_pantry_returns_added_items(client: TestClient):
    """GET /api/pantry after additions should list all added items."""
    client.post("/api/pantry", json={
        "ingredient_name": "test_garlic_phase11",
        "quantity": 5.0,
        "unit": "pieces",
    })
    list_res = client.get("/api/pantry")
    assert list_res.status_code == 200
    names = [item["ingredient_name"] for item in list_res.json()]
    assert "test_garlic_phase11" in names


def test_pantry_item_read_schema_fields(client: TestClient):
    """Each PantryItemRead must contain all required schema fields."""
    add_res = client.post("/api/pantry", json={
        "ingredient_name": "test_schema_check_phase11",
        "quantity": 1.0,
        "unit": "pieces",
    })
    item = add_res.json()
    required_fields = {
        "id", "ingredient_id", "ingredient_name", "canonical_name",
        "quantity", "unit", "expiration_date", "created_at", "updated_at",
    }
    assert required_fields.issubset(item.keys()), f"Missing fields: {required_fields - item.keys()}"
