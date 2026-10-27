"""
Tests for the DishIQ ML Service Layer and new ML API endpoints.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── MLService unit tests ──────────────────────────────────────────────────────

def test_ml_service_singleton():
    """MLService must return the same instance on repeated calls."""
    from app.services.ml_service import MLService
    MLService.reset()
    svc1 = MLService.get_instance()
    svc2 = MLService.get_instance()
    assert svc1 is svc2
    MLService.reset()


def test_ml_service_get_model_info():
    """get_model_info() returns a dict with expected keys."""
    from app.services.ml_service import MLService
    MLService.reset()
    svc = MLService.get_instance()
    info = svc.get_model_info()
    assert isinstance(info, dict)
    assert "tfidf_recommender" in info
    assert "rf_suitability" in info
    assert "kmeans_clusterer" in info
    assert "sentence_transformer" in info
    MLService.reset()


def test_ml_service_tfidf_query_returns_list():
    """tfidf_query must return a list (empty or populated)."""
    from app.services.ml_service import MLService
    MLService.reset()
    svc = MLService.get_instance()
    result = svc.tfidf_query("chicken curry", top_k=5)
    assert isinstance(result, list)
    if result:
        assert "recipe_id" in result[0]
        assert "similarity" in result[0]
        assert 0.0 <= result[0]["similarity"] <= 1.0
    MLService.reset()


def test_ml_service_predict_suitability_range():
    """predict_suitability must return a score in [1.0, 5.0] or 3.0 fallback."""
    from app.services.ml_service import MLService
    MLService.reset()
    svc = MLService.get_instance()
    fv = np.array([15, 20, 35, 4, 8, 4.5, 1, 0, 0, 0, 0], dtype=np.float32)
    score = svc.predict_suitability(fv)
    assert isinstance(score, float)
    assert 1.0 <= score <= 5.0
    MLService.reset()


def test_ml_service_suitability_fallback():
    """predict_suitability returns 3.0 when model is not loaded."""
    from app.services.ml_service import MLService
    MLService.reset()
    svc = MLService.get_instance()
    # Force model to appear unloaded
    original_loaded = svc._suitability.loaded if svc._suitability else False
    if svc._suitability:
        svc._suitability.loaded = False
    fv = np.array([15, 20, 35, 4, 8, 4.5, 1, 0, 0, 0, 0], dtype=np.float32)
    score = svc.predict_suitability(fv)
    assert score == 3.0
    if svc._suitability:
        svc._suitability.loaded = original_loaded
    MLService.reset()


def test_ml_service_get_clusters_list():
    """get_all_clusters returns a list of dicts."""
    from app.services.ml_service import MLService
    MLService.reset()
    svc = MLService.get_instance()
    clusters = svc.get_all_clusters()
    assert isinstance(clusters, list)
    if clusters:
        assert "cluster_id" in clusters[0]
        assert "description" in clusters[0]
        assert "recipe_count" in clusters[0]
    MLService.reset()


def test_ml_service_tfidf_empty_query():
    """Empty query returns empty list, not an error."""
    from app.services.ml_service import MLService
    MLService.reset()
    svc = MLService.get_instance()
    result = svc.tfidf_query("", top_k=5)
    assert result == []
    MLService.reset()


# ── API endpoint tests ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_ml_model_info_endpoint(client):
    """GET /api/ml/model-info should return 200 with model metadata."""
    response = client.get("/api/ml/model-info")
    assert response.status_code == 200
    data = response.json()
    assert "tfidf_recommender" in data
    assert "rf_suitability" in data
    assert "kmeans_clusterer" in data


def test_ml_clusters_endpoint(client):
    """GET /api/ml/clusters should return 200 with cluster list."""
    response = client.get("/api/ml/clusters")
    assert response.status_code == 200
    data = response.json()
    assert "clusters" in data
    assert "model" in data
    assert isinstance(data["clusters"], list)


def test_ml_suitability_endpoint(client):
    """POST /api/ml/suitability should return a score in [1.0, 5.0]."""
    payload = {
        "recipe_id": "test-recipe-001",
        "prep_time": 15,
        "cook_time": 30,
        "servings": 4,
        "ingredient_count": 8,
        "avg_rating": 4.5,
        "dietary_type": "Vegetarian",
        "cuisine": "Indian",
    }
    response = client.post("/api/ml/suitability", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "suitability_score" in data
    assert 1.0 <= data["suitability_score"] <= 5.0
    assert data["recipe_id"] == "test-recipe-001"


def test_ml_similar_recipes_endpoint(client):
    """GET /api/ml/similar-recipes/{id} should return 200."""
    response = client.get("/api/ml/similar-recipes/nonexistent-recipe")
    assert response.status_code == 200
    data = response.json()
    assert "similar_recipe_ids" in data
    assert isinstance(data["similar_recipe_ids"], list)


def test_existing_recommendation_endpoint_unchanged(client):
    """POST /api/recommendations/recipes should still work — no regression."""
    payload = {
        "query": "paneer",
        "dietary_type": None,
        "max_time": None,
        "pantry_ingredients": [],
        "limit": 5,
    }
    response = client.post("/api/recommendations/recipes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "total" in data
    assert isinstance(data["recommendations"], list)
