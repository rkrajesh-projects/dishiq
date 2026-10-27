"""
DishIQ ML — Unit tests for Suitability Model and Recipe Clusterer
Run from repo root: pytest ml/tests/
"""
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'artifacts'))


# ── Suitability Model Tests ───────────────────────────────────────────────────

def test_suitability_model_loads():
    """SuitabilityModel should load without errors if artifact exists."""
    from ml.models.suitability_model import SuitabilityModel
    SuitabilityModel.reset()
    model = SuitabilityModel.get_instance()
    # Either loaded (artifact exists) or not loaded (missing) — both are valid states
    assert isinstance(model.loaded, bool)
    SuitabilityModel.reset()


def test_suitability_predict_range():
    """predict() must return a float in [1.0, 5.0]."""
    from ml.models.suitability_model import SuitabilityModel
    SuitabilityModel.reset()
    model = SuitabilityModel.get_instance()
    fv = np.array([15, 20, 35, 4, 8, 4.5, 1, 0, 0, 0, 0], dtype=np.float32)
    score = model.predict(fv)
    assert isinstance(score, float)
    assert 1.0 <= score <= 5.0
    SuitabilityModel.reset()


def test_suitability_fallback_when_unloaded():
    """Returns 3.0 when model is not loaded."""
    from ml.models.suitability_model import SuitabilityModel
    SuitabilityModel.reset()
    model = SuitabilityModel.get_instance()
    original = model.loaded
    model.loaded = False
    fv = np.array([10, 15, 25, 2, 5, 4.0, 0, 0, 1, 0, 0], dtype=np.float32)
    score = model.predict(fv)
    assert score == 3.0
    model.loaded = original
    SuitabilityModel.reset()


def test_suitability_batch_predict():
    """predict_batch() returns array of same length as input."""
    from ml.models.suitability_model import SuitabilityModel
    SuitabilityModel.reset()
    model = SuitabilityModel.get_instance()
    X = np.random.rand(5, 11).astype(np.float32) * 5
    scores = model.predict_batch(X)
    assert len(scores) == 5
    assert all(1.0 <= s <= 5.0 for s in scores)
    SuitabilityModel.reset()


def test_suitability_feature_importances_when_loaded():
    """Feature importances should be a dict with expected feature names."""
    from ml.models.suitability_model import SuitabilityModel
    SuitabilityModel.reset()
    model = SuitabilityModel.get_instance()
    if model.loaded:
        importances = model.get_feature_importances()
        assert isinstance(importances, dict)
        assert "avg_rating" in importances
        assert "ingredient_count" in importances
    SuitabilityModel.reset()


# ── K-Means Clusterer Tests ───────────────────────────────────────────────────

def test_clusterer_loads():
    """RecipeClusterer should load without errors."""
    from ml.models.recipe_clusterer import RecipeClusterer
    RecipeClusterer.reset()
    model = RecipeClusterer.get_instance()
    assert isinstance(model.loaded, bool)
    RecipeClusterer.reset()


def test_clusterer_n_clusters():
    """If loaded, n_clusters should be between 2 and 10."""
    from ml.models.recipe_clusterer import RecipeClusterer
    RecipeClusterer.reset()
    model = RecipeClusterer.get_instance()
    if model.loaded:
        assert 2 <= model.n_clusters <= 10
    RecipeClusterer.reset()


def test_clusterer_get_all_clusters_format():
    """get_all_clusters() returns list of dicts with expected keys."""
    from ml.models.recipe_clusterer import RecipeClusterer
    RecipeClusterer.reset()
    model = RecipeClusterer.get_instance()
    clusters = model.get_all_clusters()
    assert isinstance(clusters, list)
    if clusters:
        c = clusters[0]
        assert "cluster_id" in c
        assert "description" in c
        assert "recipe_count" in c
    RecipeClusterer.reset()


def test_clusterer_unknown_recipe_returns_none():
    """get_cluster() returns None for unknown recipe_id."""
    from ml.models.recipe_clusterer import RecipeClusterer
    RecipeClusterer.reset()
    model = RecipeClusterer.get_instance()
    result = model.get_cluster("totally-fake-recipe-id-xyz-999")
    assert result is None
    RecipeClusterer.reset()


def test_clusterer_similar_recipes_for_unknown():
    """get_similar_recipe_ids() returns [] for unknown recipe_id."""
    from ml.models.recipe_clusterer import RecipeClusterer
    RecipeClusterer.reset()
    model = RecipeClusterer.get_instance()
    result = model.get_similar_recipe_ids("totally-fake-recipe-id-xyz-999", limit=10)
    assert result == []
    RecipeClusterer.reset()


def test_clusterer_get_info():
    """get_info() returns a dict with expected keys."""
    from ml.models.recipe_clusterer import RecipeClusterer
    RecipeClusterer.reset()
    model = RecipeClusterer.get_instance()
    info = model.get_info()
    assert "model" in info
    assert "algorithm" in info
    assert "loaded" in info
    RecipeClusterer.reset()


# ── TF-IDF Recommender Tests ──────────────────────────────────────────────────

def test_tfidf_loads():
    """TFIDFRecommender should load without errors."""
    from ml.models.tfidf_recommender import TFIDFRecommender
    TFIDFRecommender.reset()
    model = TFIDFRecommender.get_instance()
    assert isinstance(model.loaded, bool)
    TFIDFRecommender.reset()


def test_tfidf_query_format():
    """query() returns a list of dicts with recipe_id and similarity."""
    from ml.models.tfidf_recommender import TFIDFRecommender
    TFIDFRecommender.reset()
    model = TFIDFRecommender.get_instance()
    results = model.query("chicken masala", top_k=3)
    assert isinstance(results, list)
    if results:
        assert "recipe_id" in results[0]
        assert "similarity" in results[0]
        assert 0.0 <= results[0]["similarity"] <= 1.0
    TFIDFRecommender.reset()


def test_tfidf_empty_query_returns_empty():
    """Empty string query returns [], not an error."""
    from ml.models.tfidf_recommender import TFIDFRecommender
    TFIDFRecommender.reset()
    model = TFIDFRecommender.get_instance()
    assert model.query("") == []
    TFIDFRecommender.reset()


def test_tfidf_get_info():
    """get_info() returns a dict with expected keys."""
    from ml.models.tfidf_recommender import TFIDFRecommender
    TFIDFRecommender.reset()
    model = TFIDFRecommender.get_instance()
    info = model.get_info()
    assert "model" in info
    assert "loaded" in info
    TFIDFRecommender.reset()
