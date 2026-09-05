import pytest
from fastapi.testclient import TestClient
from app.core.recommendation_config import RecommendationSettings
from app.services.recommendation_service import RecommendationService


def test_search_recipes_whitespace_query_handled(client: TestClient):
    response = client.get("/api/recipes/search?q=%20%20%20")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0


def test_search_recipes_oversized_query_returns_422(client: TestClient):
    long_q = "a" * 300
    response = client.get(f"/api/recipes/search?q={long_q}")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_422"


def test_search_recipes_invalid_pagination_returns_422(client: TestClient):
    response = client.get("/api/recipes/search?page=0")
    assert response.status_code == 422

    response_oversized_page = client.get("/api/recipes/search?page_size=100")
    assert response_oversized_page.status_code == 422


def test_recommendation_config_custom_weights(seeded_db):
    custom_cfg = RecommendationSettings(
        base_score=1.0,
        dietary_match_weight=0.5,
        rating_weight=0.2,
    )
    assert custom_cfg.base_score == 1.0
    assert custom_cfg.dietary_match_weight == 0.5

    # Pass custom configuration instance explicitly to recommendation service
    service = RecommendationService(seeded_db, config=custom_cfg)
    recs = service.get_recommendations(query="Paneer", dietary_type="Vegetarian", limit=2)
    assert len(recs) > 0
    # Custom base_score 1.0 + dietary 0.5 + rating boost ~0.19 = score ~1.69 > 1.0
    assert recs[0]["score"] > 1.0
