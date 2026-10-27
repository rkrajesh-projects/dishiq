"""
DishIQ ML — TF-IDF Recipe Recommender (clean model class)
Wraps the existing TF-IDF artifact for clean inference.
"""
import os
import time
import joblib
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("dishiq")

ARTIFACT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "recipe_tfidf.joblib")
)


class TFIDFRecommender:
    """
    Loads the pre-trained TF-IDF vectorizer + recipe matrix.
    Provides cosine-similarity ranking for free-text recipe queries.
    
    Algorithm: Classical NLP / Information Retrieval (NOT a neural network).
    """
    _instance: Optional["TFIDFRecommender"] = None

    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.recipe_ids: List[str] = []
        self.recipes: List[Dict] = []
        self.loaded = False
        self.metadata: Dict[str, Any] = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "TFIDFRecommender":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        v2_path = ARTIFACT_PATH.replace("recipe_tfidf.joblib", "recipe_tfidf_v2.joblib")
        target_path = v2_path if os.path.exists(v2_path) else ARTIFACT_PATH
        
        if not os.path.exists(target_path):
            logger.warning(f"TF-IDF artifact not found at {target_path}. Run training script first.")
            return
        try:
            t0 = time.time()
            data = joblib.load(target_path)
            self.vectorizer = data["vectorizer"]
            self.tfidf_matrix = data["tfidf_matrix"]
            self.recipe_ids = data["recipe_ids"]
            self.recipes = data.get("recipes", [])
            self.loaded = True

            # Load metadata if available
            meta_path = target_path.replace(".joblib", "_metadata.json")
            if os.path.exists(meta_path):
                import json
                with open(meta_path) as f:
                    self.metadata = json.load(f)

            elapsed = round((time.time() - t0) * 1000, 1)
            logger.info(
                f"TFIDFRecommender loaded (artifact={os.path.basename(target_path)}): "
                f"{len(self.recipe_ids)} recipes, {self.tfidf_matrix.shape[1]} features, {elapsed}ms"
            )
        except Exception as e:
            logger.error(f"Failed to load TF-IDF artifact: {e}")
            self.loaded = False

    def query(self, text: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Given a free-text query, return top_k recipes sorted by cosine similarity.
        Returns: [{"recipe_id": str, "similarity": float}, ...]
        """
        if not self.loaded or self.vectorizer is None:
            return []
        if not text or not text.strip():
            return []

        from ml.utils.feature_engineering import normalize_text
        norm = normalize_text(text)
        q_vec = self.vectorizer.transform([norm])
        scores = cosine_similarity(q_vec, self.tfidf_matrix).flatten()

        top_idx = scores.argsort()[::-1][:top_k]
        results = []
        for idx in top_idx:
            results.append({
                "recipe_id": self.recipe_ids[idx],
                "similarity": float(round(scores[idx], 4)),
            })
        return results

    def similarity_for(self, recipe_id: str, query_text: str) -> float:
        """Return cosine similarity score for a specific recipe_id and query."""
        if not self.loaded or recipe_id not in self.recipe_ids:
            return 0.0
        results = {r["recipe_id"]: r["similarity"] for r in self.query(query_text, top_k=len(self.recipe_ids))}
        return results.get(recipe_id, 0.0)

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": "TF-IDF + Cosine Similarity",
            "algorithm": "Classical NLP / Information Retrieval",
            "loaded": self.loaded,
            "recipe_count": len(self.recipe_ids),
            "feature_count": int(self.tfidf_matrix.shape[1]) if self.loaded else 0,
            "artifact": ARTIFACT_PATH,
            **self.metadata,
        }
