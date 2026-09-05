"""
DishIQ Phase 7.4–7.5 — Cart API Integration Tests
Tests for POST /api/cart/compare and POST /api/cart/optimize endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestCartCompareAPI:
    """Tests for POST /api/cart/compare endpoint."""

    def test_cart_compare_valid_request(self, client: TestClient):
        """Valid cart compare request returns store breakdowns."""
        response = client.post("/api/cart/compare", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert "stores" in data
        assert "missing_ingredients" in data
        assert data["price_freshness"] == "CACHED"
        assert data["data_source"] == "demo"

    def test_cart_compare_multiple_ingredients(self, client: TestClient):
        """Cart compare with multiple ingredients returns complete baskets."""
        response = client.post("/api/cart/compare", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
                {"ingredient_name": "tomato", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["stores"], list)

    def test_cart_compare_empty_ingredients_rejected(self, client: TestClient):
        """Empty ingredient list returns validation error."""
        response = client.post("/api/cart/compare", json={
            "ingredients": []
        })
        assert response.status_code == 422

    def test_cart_compare_invalid_quantity(self, client: TestClient):
        """Negative quantity returns validation error."""
        response = client.post("/api/cart/compare", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": -1, "required_unit": "g"},
            ]
        })
        assert response.status_code == 422

    def test_cart_compare_store_breakdown_structure(self, client: TestClient):
        """Store breakdown has expected fields."""
        response = client.post("/api/cart/compare", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        if data["stores"]:
            store = data["stores"][0]
            assert "store_name" in store
            assert "selected_products" in store
            assert "subtotal" in store
            assert "delivery_fee" in store
            assert "total" in store
            assert "complete" in store

    def test_cart_compare_no_match_ingredient(self, client: TestClient):
        """Unmatched ingredient appears in missing_ingredients."""
        response = client.post("/api/cart/compare", json={
            "ingredients": [
                {"ingredient_name": "dragonfruitxyz999", "required_quantity": 1, "required_unit": "piece"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        # Either no stores or missing ingredients reported
        has_missing = len(data["missing_ingredients"]) > 0
        no_stores = len(data["stores"]) == 0
        assert has_missing or no_stores


class TestCartOptimizeAPI:
    """Tests for POST /api/cart/optimize endpoint."""

    def test_cart_optimize_valid_request(self, client: TestClient):
        """Valid optimization returns a recommended strategy."""
        response = client.post("/api/cart/optimize", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert "recommended_strategy" in data
        assert "recommended_cart" in data
        assert "total_cost" in data
        assert "explanation" in data
        assert data["price_freshness"] == "CACHED"
        assert data["data_source"] == "demo"

    def test_cart_optimize_multiple_ingredients(self, client: TestClient):
        """Optimization with multiple ingredients returns complete result."""
        response = client.post("/api/cart/optimize", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
                {"ingredient_name": "tomato", "required_quantity": 500, "required_unit": "g"},
                {"ingredient_name": "onion", "required_quantity": 300, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["recommended_strategy"] in [
            "cheapest_single_store", "cheapest_split_cart",
            "fastest_available", "none_available"
        ]
        assert data["total_cost"] >= 0
        assert "stores_used" in data

    def test_cart_optimize_alternatives_present(self, client: TestClient):
        """Optimization includes alternative strategies."""
        response = client.post("/api/cart/optimize", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert "alternatives" in data
        assert isinstance(data["alternatives"], list)

    def test_cart_optimize_no_fabricated_delivery_time(self, client: TestClient):
        """No strategy should contain fabricated delivery ETAs."""
        response = client.post("/api/cart/optimize", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        explanation = data["explanation"].lower()
        assert "minutes" not in explanation or "availability" in explanation

    def test_cart_optimize_empty_ingredients_rejected(self, client: TestClient):
        """Empty ingredient list returns validation error."""
        response = client.post("/api/cart/optimize", json={
            "ingredients": []
        })
        assert response.status_code == 422

    def test_cart_optimize_demo_data_safety(self, client: TestClient):
        """Optimization result preserves demo data markers."""
        response = client.post("/api/cart/optimize", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["price_freshness"] == "CACHED"
        assert data["data_source"] == "demo"
        # Check recommended cart products
        for store in data["recommended_cart"].get("stores", []):
            for product in store.get("selected_products", []):
                assert product["price_freshness"] == "CACHED"
                assert product["data_source_type"] == "demo"

    def test_cart_optimize_inr_currency(self, client: TestClient):
        """All monetary values use INR currency."""
        response = client.post("/api/cart/optimize", json={
            "ingredients": [
                {"ingredient_name": "paneer", "required_quantity": 500, "required_unit": "g"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("currency", "INR") == "INR"
