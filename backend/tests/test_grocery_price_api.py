"""
DishIQ Phase 6.3 — Grocery Price Comparison API Tests
Tests for GET /api/grocery/compare endpoint and price response metadata.
"""
import pytest
from fastapi.testclient import TestClient


def test_grocery_compare_valid_ingredient(client: TestClient):
    response = client.get("/api/grocery/compare?ingredient=paneer")
    assert response.status_code == 200
    data = response.json()

    assert data["ingredient_text"] == "paneer"
    assert data["canonical_name"] == "paneer"
    assert "best_option" in data
    assert data["best_option"] is not None

    best = data["best_option"]
    assert "product_id" in best
    assert "product_name" in best
    assert "store_name" in best
    assert "price" in best
    assert best["currency"] == "INR"
    assert best["price"] > 0

    results = data["results"]
    assert len(results) > 0

    # Ensure results in /compare are sorted by price (ascending)
    valid_prices = [r["price"] for r in results if r["price"] is not None]
    assert valid_prices == sorted(valid_prices)


def test_grocery_compare_diff_package_sizes(client: TestClient):
    # Tomatoes has 500g and 1kg products in seed data
    response = client.get("/api/grocery/compare?ingredient=tomatoes")
    assert response.status_code == 200
    data = response.json()

    best = data["best_option"]
    assert best is not None
    assert "tomato" in best["product_name"].lower()
    assert best["currency"] == "INR"


def test_grocery_compare_no_match(client: TestClient):
    response = client.get("/api/grocery/compare?ingredient=dragonfruitxyz")
    assert response.status_code == 200
    data = response.json()

    assert data["total_matches"] == 0
    assert data["results"] == []
    assert data["best_option"] is None


def test_grocery_compare_missing_ingredient(client: TestClient):
    response = client.get("/api/grocery/compare")
    assert response.status_code == 422


def test_grocery_compare_whitespace_ingredient(client: TestClient):
    response = client.get("/api/grocery/compare?ingredient=%20%20")
    assert response.status_code == 422


def test_existing_grocery_match_enriched_with_best_option(client: TestClient):
    response = client.get("/api/grocery/match?ingredient=paneer")
    assert response.status_code == 200
    data = response.json()

    assert "best_option" in data
    assert data["best_option"] is not None
    assert data["best_option"]["currency"] == "INR"
