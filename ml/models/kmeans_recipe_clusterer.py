import os
import json
import time
import joblib
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

logger = logging.getLogger("dishiq")

ARTIFACT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "recipe_kmeans_v1.joblib")
)
METADATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "recipe_kmeans_v1_metadata.json")
)

class RecipeKMeansClusterer:
    """
    Loads the trained Phase 17 K-Means pipeline.
    Predicts the assigned cluster for a recipe based on its structural characteristics.
    """
    _instance = None

    def __init__(self):
        self.kmeans_model = None
        self.tfidf_vectorizer = None
        self.scaler = None
        self.cluster_stats = {}
        self.loaded = False
        self.metadata = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "RecipeKMeansClusterer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        if not os.path.exists(ARTIFACT_PATH):
            logger.warning(f"K-Means artifact not found at {ARTIFACT_PATH}. Run training script first.")
            return
            
        try:
            t0 = time.time()
            data = joblib.load(ARTIFACT_PATH)
            
            self.kmeans_model = data["kmeans_model"]
            self.tfidf_vectorizer = data["tfidf_vectorizer"]
            self.scaler = data["scaler"]
            self.cluster_stats = data.get("cluster_stats", {})
            
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, "r") as f:
                    self.metadata = json.load(f)
                    
            self.loaded = True
            elapsed = round((time.time() - t0) * 1000, 1)
            logger.info(f"RecipeKMeansClusterer loaded in {elapsed}ms (K={self.kmeans_model.n_clusters})")
        except Exception as e:
            logger.error(f"Failed to load KMeans artifact: {e}")
            self.loaded = False

    def predict_cluster(self, recipe_dict: Dict[str, Any]) -> int:
        """
        Predicts the cluster ID for a recipe context.
        Input dictionary must contain: cooking_time, ingredients (string or list).
        """
        if not self.loaded or self.kmeans_model is None:
            return 0 # Fallback cluster
            
        # 1. Format input
        from ml.training.train_kmeans_v1 import extract_ingredients_text, safe_len
        
        ingredients = recipe_dict.get("ingredients", [])
        if isinstance(ingredients, list):
            ingredients = json.dumps(ingredients)
            
        cooking_time = float(recipe_dict.get("cooking_time", 0.0))
        
        ing_text = extract_ingredients_text(ingredients).lower()
        ing_count = float(safe_len(ingredients))
        
        # 2. Preprocess
        X_tfidf = self.tfidf_vectorizer.transform([ing_text])
        
        # Must mirror training precisely: log1p, DataFrame with feature names, and * 0.5
        log_cooking_time = np.log1p(cooking_time)
        log_ing_count = np.log1p(ing_count)
        
        num_df = pd.DataFrame(
            [[log_cooking_time, log_ing_count]], 
            columns=['log_cooking_time', 'log_ingredient_count']
        )
        X_num = self.scaler.transform(num_df)
        X_num = X_num * 0.5
        
        # 3. Combine
        from scipy.sparse import hstack
        X_combined = hstack([X_tfidf, X_num])
        
        # 4. Predict
        cluster_id = int(self.kmeans_model.predict(X_combined)[0])
        return cluster_id

    def get_cluster(self, recipe_id: str) -> Optional[int]:
        """Return cluster ID for a recipe_id, or None if not found."""
        if hasattr(self, "recipe_ids") and self.recipe_ids and recipe_id in self.recipe_ids:
            idx = self.recipe_ids.index(recipe_id)
            return int(self.cluster_labels[idx])
        try:
            from ml.models.recipe_clusterer import RecipeClusterer
            rc = RecipeClusterer.get_instance()
            if rc.loaded:
                return rc.get_cluster(recipe_id)
        except Exception:
            pass
        return None

    def get_cluster_description(self, cluster_id: int) -> str:
        """Returns the human-readable description of a cluster."""
        try:
            from ml.models.recipe_clusterer import RecipeClusterer
            rc = RecipeClusterer.get_instance()
            if rc.loaded:
                return rc.get_cluster_description(cluster_id)
        except Exception:
            pass
        return self.get_cluster_summary(cluster_id)

    def get_similar_recipe_ids(self, recipe_id: str, limit: int = 10) -> List[str]:
        """Return other recipe IDs in the same cluster."""
        try:
            from ml.models.recipe_clusterer import RecipeClusterer
            rc = RecipeClusterer.get_instance()
            if rc.loaded:
                return rc.get_similar_recipe_ids(recipe_id, limit=limit)
        except Exception:
            pass
        if hasattr(self, "recipe_ids") and self.recipe_ids and recipe_id in self.recipe_ids:
            idx = self.recipe_ids.index(recipe_id)
            cid = self.cluster_labels[idx]
            same = [self.recipe_ids[i] for i, c in enumerate(self.cluster_labels) if c == cid and self.recipe_ids[i] != recipe_id]
            return same[:limit]
        return []

    def get_all_clusters(self) -> List[Dict[str, Any]]:
        """Return summary of all clusters."""
        try:
            from ml.models.recipe_clusterer import RecipeClusterer
            rc = RecipeClusterer.get_instance()
            if rc.loaded:
                clusters = rc.get_all_clusters()
                if clusters:
                    return clusters
        except Exception:
            pass
        if not self.loaded or self.kmeans_model is None:
            return []
        n_clusters = getattr(self.kmeans_model, 'n_clusters', 2)
        clusters = []
        for cid in range(n_clusters):
            cid_str = str(cid)
            desc = self.get_cluster_summary(cid)
            count = 0
            if cid_str in self.cluster_stats:
                count = self.cluster_stats[cid_str].get("count", 0)
            elif cid in self.cluster_stats:
                count = self.cluster_stats[cid].get("count", 0)
            clusters.append({
                "cluster_id": cid,
                "description": desc,
                "recipe_count": count,
            })
        return clusters

    def get_cluster_summary(self, cluster_id: int) -> str:
        """Returns the human-readable text summary of the cluster."""
        # Convert to string just in case keys were loaded as strings
        cid_str = str(cluster_id)
        if cid_str in self.cluster_stats:
            return self.cluster_stats[cid_str].get("text_description", "No description available.")
            
        # Fallback integer lookup
        if cluster_id in self.cluster_stats:
            return self.cluster_stats[cluster_id].get("text_description", "No description available.")
            
        return f"Cluster {cluster_id} (No description generated)"

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": "K-Means Recipe Clustering",
            "algorithm": "KMeans Pipeline (TF-IDF + Numeric Scaler)",
            "loaded": self.loaded,
            "artifact": ARTIFACT_PATH,
            **self.metadata,
        }

