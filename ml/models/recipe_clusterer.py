"""
DishIQ ML — K-Means Recipe Clustering Model (Model 4)

Purpose: Discovers natural groupings of recipes based on their structural characteristics
(cooking time, servings, complexity). This is unsupervised ML — clusters emerge from data.

Cluster names are NOT manually assigned. They are auto-described from centroid statistics.

Algorithm: K-Means (scikit-learn)
"""
import os
import time
import logging
import joblib
import numpy as np
from typing import Optional, Dict, Any, List

logger = logging.getLogger("dishiq")

MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "recipe_kmeans.joblib")
)
SCALER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "recipe_scaler.joblib")
)
METADATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "clustering_metadata.json")
)


class RecipeClusterer:
    """
    Loads the pre-trained K-Means model.
    Assigns each recipe to a discovered cluster.
    Cluster descriptions are auto-generated from centroid values.
    """
    _instance: Optional["RecipeClusterer"] = None

    def __init__(self):
        self.model = None
        self.scaler = None
        self.cluster_labels: List[int] = []      # cluster_id per recipe (positional)
        self.recipe_ids: List[str] = []          # recipe IDs (positional)
        self.cluster_descriptions: Dict[int, str] = {}
        self.n_clusters: int = 0
        self.loaded = False
        self.metadata: Dict[str, Any] = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "RecipeClusterer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        if not os.path.exists(MODEL_PATH):
            logger.warning(f"K-Means model not found at {MODEL_PATH}. Run train_clustering.py first.")
            return
        try:
            t0 = time.time()
            data = joblib.load(MODEL_PATH)
            self.model = data["model"]
            self.cluster_labels = data["cluster_labels"]
            self.recipe_ids = data["recipe_ids"]
            self.cluster_descriptions = data.get("cluster_descriptions", {})
            self.n_clusters = self.model.n_clusters

            if os.path.exists(SCALER_PATH):
                self.scaler = joblib.load(SCALER_PATH)
            if os.path.exists(METADATA_PATH):
                import json
                with open(METADATA_PATH) as f:
                    self.metadata = json.load(f)

            self.loaded = True
            elapsed = round((time.time() - t0) * 1000, 1)
            logger.info(
                f"RecipeClusterer (K-Means, k={self.n_clusters}) loaded: "
                f"{len(self.recipe_ids)} recipes in {elapsed}ms"
            )
        except Exception as e:
            logger.error(f"Failed to load K-Means model: {e}")
            self.loaded = False

    def get_cluster(self, recipe_id: str) -> Optional[int]:
        """Return cluster ID for a given recipe_id, or None if not found."""
        if not self.loaded:
            return None
        try:
            idx = self.recipe_ids.index(recipe_id)
            return int(self.cluster_labels[idx])
        except ValueError:
            return None

    def get_cluster_description(self, cluster_id: int) -> str:
        """Return auto-generated description of a cluster."""
        return self.cluster_descriptions.get(cluster_id, f"Cluster {cluster_id}")

    def get_similar_recipe_ids(self, recipe_id: str, limit: int = 10) -> List[str]:
        """Return other recipe IDs in the same cluster."""
        if not self.loaded:
            return []
        cluster = self.get_cluster(recipe_id)
        if cluster is None:
            return []
        same_cluster = [
            self.recipe_ids[i]
            for i, c in enumerate(self.cluster_labels)
            if c == cluster and self.recipe_ids[i] != recipe_id
        ]
        return same_cluster[:limit]

    def get_all_clusters(self) -> List[Dict[str, Any]]:
        """Return summary of all clusters."""
        if not self.loaded:
            return []
        from collections import Counter
        counts = Counter(self.cluster_labels)
        return [
            {
                "cluster_id": cid,
                "description": self.cluster_descriptions.get(cid, f"Cluster {cid}"),
                "recipe_count": counts.get(cid, 0),
            }
            for cid in range(self.n_clusters)
        ]

    def predict_cluster(self, feature_vector: np.ndarray) -> int:
        """Predict cluster for a new recipe (not in training set)."""
        if not self.loaded or self.model is None:
            return 0
        fv = feature_vector.reshape(1, -1)
        if self.scaler is not None:
            fv = self.scaler.transform(fv)
        return int(self.model.predict(fv)[0])

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": "K-Means Clustering",
            "algorithm": "Unsupervised ML — K-Means",
            "purpose": "Recipe grouping by structural similarity",
            "n_clusters": self.n_clusters,
            "loaded": self.loaded,
            "artifact": MODEL_PATH,
            **self.metadata,
        }
