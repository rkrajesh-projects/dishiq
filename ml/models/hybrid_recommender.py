import os
import time
import json
import logging
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger("dishiq")

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "artifacts"))
CLUSTER_CSV = os.path.join(ARTIFACTS_DIR, "recipe_cluster_assignments.csv")
SUITABILITY_CACHE_JSON = os.path.join(ARTIFACTS_DIR, "recipe_suitability_cache.json")
DATA_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed", "cleaned_combined_dataset.csv"))

class HybridRecommender:
    """
    Combines TF-IDF V2, Sentence Transformer V1, Random Forest Suitability V1,
    and K-Means V1 into a configurable hybrid recommendation foundation.
    
    Uses precomputed cluster assignments and suitability score cache for sub-50ms inference,
    with dynamic fallback for runtime/unknown recipe contexts.
    """
    _instance = None
    
    def __init__(self):
        self.tfidf = None
        self.semantic = None
        self.suitability = None
        self.kmeans = None
        self.cluster_map: Dict[str, int] = {}
        self.suitability_cache: Dict[str, float] = {}
        self.loaded = False
        self._load()
        
        # Configurable weights (can be moved to a config file/db later)
        self.weights = {
            "tfidf": 0.3,
            "semantic": 0.5,
            "suitability": 0.2
        }

    @classmethod
    def get_instance(cls) -> "HybridRecommender":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        try:
            from ml.models.tfidf_recommender import TFIDFRecommender
            from ml.models.sentence_transformer_recommender import SemanticRecommender
            from ml.models.random_forest_suitability import RandomForestSuitability
            from ml.models.kmeans_recipe_clusterer import RecipeKMeansClusterer
            
            t0 = time.time()
            self.tfidf = TFIDFRecommender.get_instance()
            self.semantic = SemanticRecommender.get_instance()
            self.suitability = RandomForestSuitability.get_instance()
            self.kmeans = RecipeKMeansClusterer.get_instance()
            
            # Load precomputed cluster assignments for O(1) lookup
            if os.path.exists(CLUSTER_CSV):
                try:
                    cluster_df = pd.read_csv(CLUSTER_CSV)
                    self.cluster_map = {str(k): int(v) for k, v in zip(cluster_df["recipe_id"], cluster_df["cluster_id"])}
                except Exception as e:
                    logger.warning(f"Failed to load cluster CSV: {e}")

            # Load or build precomputed suitability cache for O(1) lookup
            if os.path.exists(SUITABILITY_CACHE_JSON):
                try:
                    with open(SUITABILITY_CACHE_JSON, "r") as f:
                        self.suitability_cache = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load suitability cache JSON: {e}")
            elif os.path.exists(DATA_CSV) and self.suitability and self.suitability.loaded:
                try:
                    df = pd.read_csv(DATA_CSV)
                    from ml.training.train_random_forest_v1 import extract_features
                    X = extract_features(df)
                    if "rating" in X.columns:
                        X.drop(columns=["rating"], inplace=True)
                    preds = self.suitability.pipeline.predict(X)
                    self.suitability_cache = {str(rid): float(round(p, 4)) for rid, p in zip(df["recipe_id"], preds)}
                except Exception as e:
                    logger.warning(f"Failed to build suitability cache on the fly: {e}")
            
            self.loaded = True
            logger.info(
                f"HybridRecommender loaded underlying models in {(time.time() - t0):.2f}s "
                f"(clusters: {len(self.cluster_map)}, suitability_cache: {len(self.suitability_cache)})"
            )
        except Exception as e:
            logger.error(f"HybridRecommender failed to load: {e}")
            self.loaded = False
            
    def _get_recipe_context(self, recipe_id: str) -> Dict[str, Any]:
        """
        Fallback recipe structural details needed if an unseen recipe is evaluated dynamically.
        """
        return {
            "recipe_id": recipe_id,
            "cooking_time": 30,
            "ingredients": ["salt", "pepper"],
            "cuisine": "Unknown",
            "diet": "Unknown"
        }

    def query(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval pipeline.
        1. Query TF-IDF and Semantic models (pool candidates).
        2. Merge and deduplicate candidates.
        3. Lookup or compute Suitability score.
        4. Lookup or compute Cluster ID.
        5. Calculate weighted final score.
        6. Return Top K sorted by final score.
        """
        if not self.loaded:
            return []
        if not text or not text.strip():
            return []
            
        # 1. Retrieve Candidates
        # Fetch an appropriate pool to re-rank
        pool_size = max(top_k * 2, 50)
        tfidf_results = self.tfidf.query(text, top_k=pool_size) if self.tfidf else []
        semantic_results = self.semantic.query(text, top_k=pool_size) if self.semantic else []
        
        candidates: Dict[str, Dict[str, Any]] = {}
        
        # Merge TF-IDF
        for r in tfidf_results:
            rid = str(r["recipe_id"])
            candidates[rid] = {
                "recipe_id": rid,
                "tfidf_score": float(r.get("similarity", 0.0)),
                "semantic_score": 0.0
            }
            
        # Merge Semantic
        for r in semantic_results:
            rid = str(r["recipe_id"])
            if rid not in candidates:
                candidates[rid] = {
                    "recipe_id": rid,
                    "tfidf_score": 0.0,
                    "semantic_score": float(r.get("similarity", 0.0))
                }
            else:
                candidates[rid]["semantic_score"] = float(r.get("similarity", 0.0))
                
        # 3, 4, 5. Calculate hybrid scores
        results = []
        for rid, stats in candidates.items():
            # Suitability score: fast cache lookup, dynamic predict fallback
            if rid in self.suitability_cache:
                suitability_score = self.suitability_cache[rid]
            elif self.suitability and self.suitability.loaded:
                context = self._get_recipe_context(rid)
                suitability_score = self.suitability.predict_suitability(context)
            else:
                suitability_score = 4.5
                
            # Cluster ID: fast cache lookup, dynamic predict fallback
            if rid in self.cluster_map:
                cluster_id = self.cluster_map[rid]
            elif self.kmeans and self.kmeans.loaded:
                context = self._get_recipe_context(rid)
                cluster_id = self.kmeans.predict_cluster(context)
            else:
                cluster_id = 0
                
            stats["suitability_score"] = suitability_score
            stats["cluster_id"] = cluster_id
            
            # Normalize suitability (1-5 range) to (0-1 range) for weighting
            norm_suitability = (suitability_score - 1.0) / 4.0 if suitability_score >= 1.0 else 0.0
            
            # Weighted final score
            stats["final_score"] = round(
                (stats["tfidf_score"] * self.weights["tfidf"]) +
                (stats["semantic_score"] * self.weights["semantic"]) +
                (norm_suitability * self.weights["suitability"]),
                4
            )
            
            results.append(stats)
            
        # 6. Sort and return
        results.sort(key=lambda x: x["final_score"], reverse=True)
        return results[:top_k]
        
    def get_info(self) -> Dict[str, Any]:
        return {
            "model": "Hybrid Recommender",
            "weights": self.weights,
            "cached_recipes": {
                "clusters": len(self.cluster_map),
                "suitability": len(self.suitability_cache)
            },
            "components_loaded": {
                "tfidf": self.tfidf.loaded if self.tfidf else False,
                "semantic": self.semantic.loaded if self.semantic else False,
                "suitability": self.suitability.loaded if self.suitability else False,
                "kmeans": self.kmeans.loaded if self.kmeans else False,
            }
        }
