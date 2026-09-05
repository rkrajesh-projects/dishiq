"""
DishIQ Phase 6.2 — Grocery Product Matching API Tests
Tests for GET /api/grocery/match and GET /api/products/match endpoints.
"""
import pytest
from fastapi.testclient import TestClient


def test_grocery_match_valid_ingredient(client: TestClient):
    response = client.get("/api/grocery/match?ingredient=paneer")
    assert response.status_code == 200
    data = response.json()

    assert data["ingredient_text"] == "paneer"
    assert data["canonical_name"] == "paneer"
    assert "threshold" in data
    assert "total_matches" in data
    assert "results" in data

    results = data["results"]
    assert len(results) > 0

    # Verify required fields in result objects
    first = results[0]
    assert "product_id" in first
    assert "product_name" in first
    assert "similarity_score" in first
    assert "match_status" in first
    assert "rank" in first
    assert "price" in first
    assert "paneer" in first["product_name"].lower()


def test_grocery_match_sorted_descending(client: TestClient):
    response = client.get("/api/grocery/match?ingredient=tomatoes")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) > 1

    scores = [r["similarity_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_grocery_match_limit_parameter(client: TestClient):
    response = client.get("/api/grocery/match?ingredient=paneer&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) <= 2


def test_grocery_match_threshold_parameter(client: TestClient):
    # High threshold (0.95) should filter out less exact matches
    resp_high = client.get("/api/grocery/match?ingredient=paneer&threshold=0.95")
    assert resp_high.status_code == 200
    data_high = resp_high.json()

    # Low threshold (0.20) should include more matches
    resp_low = client.get("/api/grocery/match?ingredient=paneer&threshold=0.20")
    assert resp_low.status_code == 200
    data_low = resp_low.json()

    assert data_high["total_matches"] <= data_low["total_matches"]


def test_grocery_match_no_match_ingredient(client: TestClient):
    response = client.get("/api/grocery/match?ingredient=dragonfruitxyz")
    assert response.status_code == 200
    data = response.json()

    assert data["ingredient_text"] == "dragonfruitxyz"
    assert data["total_matches"] == 0
    assert data["results"] == []


def test_grocery_match_missing_ingredient(client: TestClient):
    response = client.get("/api/grocery/match")
    assert response.status_code == 422


def test_grocery_match_whitespace_ingredient(client: TestClient):
    response = client.get("/api/grocery/match?ingredient=%20%20")
    assert response.status_code == 422


def test_products_match_alias_endpoint(client: TestClient):
    response = client.get("/api/products/match?ingredient=paneer")
    assert response.status_code == 200
    data = response.json()
    assert data["canonical_name"] == "paneer"


def test_existing_grocery_products_api_continues_working(client: TestClient):
    response = client.get("/api/products?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_existing_grocery_stores_api_continues_working(client: TestClient):
    response = client.get("/api/stores?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
