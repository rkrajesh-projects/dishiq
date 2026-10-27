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
        assert data["price_freshness"] == "DEMO"
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
        assert data["price_freshness"] == "DEMO"
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
        assert data["price_freshness"] == "DEMO"
        assert data["data_source"] == "demo"
        # Check recommended cart products
        for store in data["recommended_cart"].get("stores", []):
            for product in store.get("selected_products", []):
                assert product["price_freshness"] == "DEMO"
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


class TestCartOptimizationResilience:
    """
    Focused regression tests for cart optimization timeout prevention,
    ingredient query deduplication, bounded concurrency, and partial failure resilience.
    """

    def test_cart_optimize_deduplicates_identical_ingredients(self, client: TestClient):
        """Identical ingredient queries within one request are only searched once."""
        from unittest.mock import patch
        from app.services.grocery_service import GroceryService

        searched_ingredients = []
        original_match = GroceryService.match_products_for_ingredient

        def spy_match(self, ingredient, *args, **kwargs):
            searched_ingredients.append(ingredient.strip().lower())
            return original_match(self, ingredient, *args, **kwargs)

        with patch.object(GroceryService, "match_products_for_ingredient", side_effect=spy_match, autospec=True):
            response = client.post("/api/cart/optimize", json={
                "ingredients": [
                    {"ingredient_name": "paneer", "required_quantity": 200, "required_unit": "g"},
                    {"ingredient_name": "Paneer", "required_quantity": 300, "required_unit": "g"},
                    {"ingredient_name": " paneer ", "required_quantity": 100, "required_unit": "g"},
                ]
            })

        assert response.status_code == 200
        data = response.json()
        assert data["recommended_strategy"] in [
            "cheapest_single_store", "cheapest_split_cart", "fastest_available", "none_available"
        ]
        # "paneer" must only have been queried ONCE instead of 3 times
        assert searched_ingredients.count("paneer") == 1

    def test_cart_optimize_handles_live_provider_timeout_gracefully(self, client: TestClient):
        """When a live provider times out, the optimizer returns partial results without crashing or exceeding timeout."""
        from unittest.mock import patch
        from app.services.grocery_service import GroceryService

        def timeout_match(self, ingredient, *args, **kwargs):
            raise TimeoutError("Swiggy Instamart provider connection timed out after 4.0s")

        with patch.object(GroceryService, "match_products_for_ingredient", side_effect=timeout_match):
            response = client.post("/api/cart/optimize?live_mode=true", json={
                "ingredients": [
                    {"ingredient_name": "paneer", "required_quantity": 200, "required_unit": "g"},
                ]
            })

        # Endpoint returns HTTP 200 with missing ingredients reported gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["data_source"] == "live"
        assert len(data["missing_ingredients"]) == 1
        missing = data["missing_ingredients"][0]
        assert missing["ingredient_name"] == "paneer"
        assert "timed out" in missing["reason"].lower() or "timeout" in missing["reason"].lower()

    def test_cart_optimize_partial_search_failure_resilience(self, client: TestClient):
        """When some ingredients fail/timeout and others succeed, available ingredients are still optimized."""
        from unittest.mock import patch
        from app.services.grocery_service import GroceryService
        from app.product_matching.schemas import MatchIngredientsResponse, ProductMatchResult

        original_match = GroceryService.match_products_for_ingredient

        def partial_match(self, ingredient, *args, **kwargs):
            if "fail" in ingredient.lower():
                raise TimeoutError("Provider timed out for failing ingredient")
            return original_match(self, ingredient, *args, **kwargs)

        with patch.object(GroceryService, "match_products_for_ingredient", side_effect=partial_match, autospec=True):
            response = client.post("/api/cart/optimize?live_mode=false", json={
                "ingredients": [
                    {"ingredient_name": "paneer", "required_quantity": 200, "required_unit": "g"},
                    {"ingredient_name": "fail_ingredient_xyz", "required_quantity": 100, "required_unit": "g"},
                ]
            })

        assert response.status_code == 200
        data = response.json()
        # The failing ingredient is marked in missing_ingredients
        missing_names = [m["ingredient_name"] for m in data["missing_ingredients"]]
        assert "fail_ingredient_xyz" in missing_names
        # Paneer was matched and included
        assert data["recommended_strategy"] is not None

    def test_cart_optimize_preserves_stock_checks(self, client: TestClient):
        """Out of stock products (availability=False) must never be selected in cart optimization."""
        from unittest.mock import patch
        from app.services.grocery_service import GroceryService
        from app.product_matching.schemas import MatchIngredientsResponse, ProductMatchResult

        # Mock match returning an unavailable product
        mock_response = MatchIngredientsResponse(
            ingredient_text="paneer",
            canonical_name="paneer",
            total_matches=1,
            threshold=0.4,
            results=[
                ProductMatchResult(
                    product_id="prod_out_of_stock",
                    product_name="Out of Stock Paneer",
                    store_id="store_1",
                    store_name="Store 1",
                    brand="BrandX",
                    price=50.0,
                    package_quantity=200.0,
                    package_unit="g",
                    match_score=0.95,
                    similarity_score=0.95,
                    matched_text="paneer",
                    match_status="matched",
                    rank=1,
                    availability=False,  # EXPLICITLY UNAVAILABLE
                    price_freshness="PROVIDER_LIVE",
                )
            ],
            best_option=None,
            comparison_mode=None,
            price_freshness="PROVIDER_LIVE",
            data_source="live",
        )

        with patch.object(GroceryService, "match_products_for_ingredient", return_value=mock_response):
            response = client.post("/api/cart/optimize?live_mode=true", json={
                "ingredients": [
                    {"ingredient_name": "paneer", "required_quantity": 200, "required_unit": "g"},
                ]
            })

        assert response.status_code == 200
        data = response.json()
        assert data["data_source"] == "live"
        # Product must NOT be selected because availability is False
        for store in data["recommended_cart"].get("stores", []):
            for prod in store.get("selected_products", []):
                assert prod["product_id"] != "prod_out_of_stock"

    def test_cart_optimize_never_silently_replaces_live_with_demo_prices(self, client: TestClient):
        """In live mode, missing products must not be silently replaced with demo data."""
        from unittest.mock import patch
        from app.services.grocery_service import GroceryService
        from app.product_matching.schemas import MatchIngredientsResponse

        # Return empty matches in live mode (as if live provider returned nothing)
        empty_response = MatchIngredientsResponse(
            ingredient_text="coriander",
            canonical_name="coriander",
            total_matches=0,
            threshold=0.4,
            results=[],
            best_option=None,
            comparison_mode=None,
            price_freshness="UNKNOWN",
            data_source="live",
        )

        with patch.object(GroceryService, "match_products_for_ingredient", return_value=empty_response):
            response = client.post("/api/cart/optimize?live_mode=true", json={
                "ingredients": [
                    {"ingredient_name": "coriander", "required_quantity": 100, "required_unit": "g"},
                ]
            })

        assert response.status_code == 200
        data = response.json()
        assert data["data_source"] == "live"
        assert len(data["missing_ingredients"]) == 1
        assert data["missing_ingredients"][0]["ingredient_name"] == "coriander"
        # Ensure no demo products were injected
        assert data["recommended_cart"]["stores_used"] == 0

