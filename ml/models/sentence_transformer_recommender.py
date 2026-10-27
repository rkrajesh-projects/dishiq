import os
import time
import joblib
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import json

logger = logging.getLogger("dishiq")

ARTIFACT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "recipe_sentence_transformer_v1.joblib")
)
REGISTRY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "pretrained", "pretrained_registry.json")
)

class SemanticRecommender:
    """
    Loads the pretrained Sentence Transformer and the generated recipe embedding matrix.
    Provides semantic cosine-similarity ranking for natural language queries.
    """
    _instance: Optional["SemanticRecommender"] = None

    def __init__(self):
        self.model = None
        self.embeddings = None
        self.recipe_ids: List[str] = []
        self.loaded = False
        self.metadata: Dict[str, Any] = {}
        self.normalize = True
        self._load()

    @classmethod
    def get_instance(cls) -> "SemanticRecommender":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        if not os.path.exists(ARTIFACT_PATH):
            logger.warning(f"Semantic artifact not found at {ARTIFACT_PATH}. Run training script first.")
            return
            
        if not os.path.exists(REGISTRY_PATH):
            logger.warning(f"Pretrained registry not found at {REGISTRY_PATH}.")
            return
            
        try:
            t0 = time.time()
            # 1. Load Data
            data = joblib.load(ARTIFACT_PATH)
            self.embeddings = data["embeddings"]
            self.recipe_ids = data["recipe_ids"]
            
            # 2. Load Model
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            cache_dir = os.path.dirname(REGISTRY_PATH)
            if os.path.exists(REGISTRY_PATH):
                try:
                    with open(REGISTRY_PATH, "r") as f:
                        registry = json.load(f)
                    model_name = registry.get("model_name", model_name)
                    custom_cache = registry.get("cache_location")
                    if custom_cache and os.path.exists(custom_cache):
                        cache_dir = custom_cache
                except Exception:
                    pass

            try:
                self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
            except Exception as e:
                logger.warning(f"Failed to load cached SentenceTransformer from {cache_dir}, falling back to default download: {e}")
                self.model = SentenceTransformer(model_name)
            
            # 3. Load Metadata
            meta_path = ARTIFACT_PATH.replace(".joblib", "_metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    self.metadata = json.load(f)
                    
            self.normalize = self.metadata.get("normalization_strategy") == "L2_Norm"
            self.loaded = True

            elapsed = round((time.time() - t0) * 1000, 1)
            logger.info(
                f"SemanticRecommender loaded: {len(self.recipe_ids)} recipes, "
                f"{self.embeddings.shape[1]} dimensions, {elapsed}ms"
            )
        except Exception as e:
            logger.error(f"Failed to load Semantic artifact: {e}")
            self.loaded = False

    def query(self, text: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Given a free-text query, return top_k recipes sorted by semantic similarity.
        """
        if not self.loaded or self.model is None or self.embeddings is None:
            return []
            
        text = text.strip().lower()
        if not text:
            return []

        # Encode query
        q_vec = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=self.normalize)
        
        # Calculate similarity
        scores = cosine_similarity(q_vec, self.embeddings).flatten()

        # Handle NaNs safely
        scores = np.nan_to_num(scores)
        
        top_k = min(top_k, len(self.recipe_ids))
        if top_k <= 0:
            return []
            
        top_idx = scores.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_idx:
            results.append({
                "recipe_id": self.recipe_ids[idx],
                "similarity": float(round(scores[idx], 4)),
            })
        return results

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": "Sentence Transformer Semantic Retrieval",
            "algorithm": "Dense Embeddings + Cosine Similarity",
            "loaded": self.loaded,
            "recipe_count": len(self.recipe_ids),
            "feature_count": int(self.embeddings.shape[1]) if self.loaded else 0,
            "artifact": ARTIFACT_PATH,
            **self.metadata,
        }
