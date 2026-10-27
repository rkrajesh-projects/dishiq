"""
DishIQ Backend — Unified ML Service Layer

Loads all trained ML model artifacts once at startup (class-level singletons).
Provides a single clean interface for the recommendation system and API endpoints.

Fallback behavior:
- If any model artifact is missing, that model's methods return neutral/empty defaults.
- The application NEVER crashes due to a missing ML model.
- Fallback behavior is clearly logged — not silently swapped for fake predictions.
"""
import os
import logging
import numpy as np
from typing import List, Optional, Dict, Any

logger = logging.getLogger("dishiq")

# Artifact paths — relative to repo root
from app.core.config import _find_project_root
_REPO_ROOT = os.path.abspath(os.path.join(_find_project_root(), "ml", "artifacts"))


class MLService:
    """
    Unified service that loads and exposes all DishIQ ML models.
    Use MLService.get_instance() — do not instantiate directly per request.
    """
    _instance: Optional["MLService"] = None

    def __init__(self):
        self._tfidf = None
        self._suitability = None
        self._clusterer = None
        self._loaded = False
        self._load_all()

    @classmethod
    def get_instance(cls) -> "MLService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Force reload on next access (call after retraining models)."""
        cls._instance = None

    def _load_all(self):
        errors = []

        try:
            import sys
            import os
            from app.core.config import _find_project_root
            repo_root = _find_project_root()
            if repo_root not in sys.path:
                sys.path.insert(0, repo_root)
            from ml.models.hybrid_recommender import HybridRecommender
            
            self._hybrid = HybridRecommender.get_instance()
            
            # The hybrid recommender loads TF-IDF, Semantic, RF, and KMeans internally.
            if self._hybrid.loaded:
                import logging
                logger = logging.getLogger("dishiq")
                logger.info("MLService: Hybrid Recommender loaded successfully.")
                self._tfidf = self._hybrid.tfidf
                self._suitability = self._hybrid.suitability
                self._clusterer = self._hybrid.kmeans
            else:
                import logging
                logger = logging.getLogger("dishiq")
                logger.warning("MLService: Hybrid Recommender not fully loaded.")
        except Exception as e:
            import logging
            logger = logging.getLogger("dishiq")
            logger.error(f"MLService: Hybrid Recommender load error: {e}")
            errors.append(f"hybrid_recommender: {e}")

        self._loaded = True
        if errors:
            import logging
            logger = logging.getLogger("dishiq")
            logger.warning(f"MLService initialized with {len(errors)} model error(s): {errors}")
        else:
            import logging
            logger = logging.getLogger("dishiq")
            logger.info("MLService: All models loaded successfully")

    def hybrid_query(self, query: str, top_k: int = 20):
        if not hasattr(self, '_hybrid') or not self._hybrid or not self._hybrid.loaded:
            return []
        return self._hybrid.query(query, top_k=top_k)


    # ── TF-IDF Interface ────────────────────────────────────────────
    def tfidf_query(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Returns top_k recipe matches for a text query using TF-IDF cosine similarity.
        Returns [] if model unavailable (NOT fake predictions).
        """
        if not self._tfidf or not self._tfidf.loaded:
            return []
        return self._tfidf.query(query, top_k=top_k)

    def tfidf_similarity(self, recipe_id: str, query: str) -> float:
        """Get cosine similarity score for a specific recipe_id + query."""
        if not self._tfidf or not self._tfidf.loaded:
            return 0.0
        return self._tfidf.similarity_for(recipe_id, query)

    # ── Random Forest Interface ─────────────────────────────────────
    def predict_suitability(self, recipe_features: Any) -> float:
        """
        Predict recipe suitability score [1.0, 5.0] using Random Forest.
        Returns 3.0 (neutral) if model unavailable.
        """
        if not self._suitability or not self._suitability.loaded:
            return 3.0
        if hasattr(self._suitability, "predict"):
            return self._suitability.predict(recipe_features)
        if hasattr(self._suitability, "predict_suitability") and isinstance(recipe_features, dict):
            return self._suitability.predict_suitability(recipe_features)
        return 3.0

    def predict_suitability_batch(self, feature_matrix: Any) -> np.ndarray:
        """Batch prediction for multiple recipes."""
        if not self._suitability or not self._suitability.loaded:
            return np.full(len(feature_matrix), 3.0)
        if hasattr(self._suitability, "predict_batch"):
            return self._suitability.predict_batch(feature_matrix)
        return np.full(len(feature_matrix), 3.0)

    def get_feature_importances(self) -> Dict[str, float]:
        if not self._suitability or not self._suitability.loaded:
            return {}
        return self._suitability.get_feature_importances()

    # ── K-Means Interface ───────────────────────────────────────────
    def get_recipe_cluster(self, recipe_id: str) -> Optional[int]:
        """Return cluster ID for a recipe (None if model unavailable)."""
        if not self._clusterer or not self._clusterer.loaded:
            return None
        if hasattr(self._clusterer, "get_cluster"):
            return self._clusterer.get_cluster(recipe_id)
        return None

    def get_cluster_description(self, cluster_id: int) -> str:
        if not self._clusterer or not self._clusterer.loaded:
            return ""
        if hasattr(self._clusterer, "get_cluster_description"):
            return self._clusterer.get_cluster_description(cluster_id)
        if hasattr(self._clusterer, "get_cluster_summary"):
            return self._clusterer.get_cluster_summary(cluster_id)
        return ""

    def get_similar_recipe_ids(self, recipe_id: str, limit: int = 10) -> List[str]:
        """Return recipe_ids in the same cluster as the given recipe."""
        if not self._clusterer or not self._clusterer.loaded:
            return []
        if hasattr(self._clusterer, "get_similar_recipe_ids"):
            return self._clusterer.get_similar_recipe_ids(recipe_id, limit=limit)
        return []

    def get_all_clusters(self) -> List[Dict[str, Any]]:
        if not self._clusterer or not self._clusterer.loaded:
            return []
        if hasattr(self._clusterer, "get_all_clusters"):
            return self._clusterer.get_all_clusters()
        return []

    # ── Status ──────────────────────────────────────────────────────
    def get_model_info(self) -> Dict[str, Any]:
        """Return metadata for all loaded models."""
        return {
            "tfidf_recommender": self._tfidf.get_info() if self._tfidf else {"loaded": False},
            "rf_suitability": self._suitability.get_info() if self._suitability else {"loaded": False},
            "kmeans_clusterer": self._clusterer.get_info() if self._clusterer else {"loaded": False},
            "sentence_transformer": {
                "model": "all-MiniLM-L6-v2",
                "algorithm_type": "Pre-trained transformer — semantic similarity",
                "note": "Used for product matching (see product_matching module)",
            },
        }


def get_ml_service() -> MLService:
    """FastAPI dependency — returns the shared MLService singleton."""
    return MLService.get_instance()
