import os
import time
import joblib
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger("dishiq")

ARTIFACT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "random_forest_suitability_v1.joblib")
)

class RandomForestSuitability:
    """
    Loads the trained Random Forest pipeline.
    Predicts a proxy suitability score (rating) based on recipe characteristics.
    """
    _instance = None

    def __init__(self):
        self.pipeline = None
        self.loaded = False
        self.metadata: Dict[str, Any] = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "RandomForestSuitability":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        if not os.path.exists(ARTIFACT_PATH):
            logger.warning(f"RF Suitability artifact not found at {ARTIFACT_PATH}. Run training script first.")
            return
            
        try:
            try:
                import sklearn.compose._column_transformer as _ct
                if not hasattr(_ct, "_RemainderColsList"):
                    class _RemainderColsList(list):
                        pass
                    _ct._RemainderColsList = _RemainderColsList
            except Exception:
                pass
            t0 = time.time()
            self.pipeline = joblib.load(ARTIFACT_PATH)
            
            meta_path = ARTIFACT_PATH.replace(".joblib", "_metadata.json")
            if os.path.exists(meta_path):
                import json
                with open(meta_path) as f:
                    self.metadata = json.load(f)
                    
            self.loaded = True
            elapsed = round((time.time() - t0) * 1000, 1)
            logger.info(f"RandomForestSuitability loaded in {elapsed}ms")
        except Exception as e:
            logger.error(f"Failed to load RF Suitability artifact: {e}")
            self.loaded = False

    def predict_suitability(self, recipe_dict: Dict[str, Any]) -> float:
        """
        Predicts suitability (proxy rating) for a single recipe context.
        Input dictionary must contain the basic structure expected by the pipeline:
        cooking_time, ingredients (string or list), instructions, cuisine, diet.
        """
        if not self.loaded or self.pipeline is None:
            return 4.5 # Fallback neutral/high score
            
        # Format for feature extraction
        import json
        
        # safely convert to lists if they aren't already stringified json
        ing = recipe_dict.get("ingredients", [])
        inst = recipe_dict.get("instructions", [])
        if isinstance(ing, list):
            ing = json.dumps(ing)
        if isinstance(inst, list):
            inst = json.dumps(inst)
            
        df = pd.DataFrame([{
            "cooking_time": recipe_dict.get("cooking_time", 0),
            "ingredients": ing,
            "instructions": inst,
            "cuisine": recipe_dict.get("cuisine", "Unknown"),
            "diet": recipe_dict.get("diet", "Unknown")
        }])
        
        # Use exact extract logic
        from ml.training.train_random_forest_v1 import extract_features
        X = extract_features(df)
        
        # Remove target if present
        if 'rating' in X.columns:
            X = X.drop(columns=['rating'])
            
        pred = self.pipeline.predict(X)[0]
        
        # Clip to realistic rating bounds [1.0, 5.0] just in case
        return float(max(1.0, min(5.0, pred)))

    def predict(self, feature_vector: Any) -> float:
        """Predict suitability score for a feature vector or dictionary."""
        if isinstance(feature_vector, dict):
            return self.predict_suitability(feature_vector)
        try:
            from ml.models.suitability_model import SuitabilityModel
            sm = SuitabilityModel.get_instance()
            if sm.loaded:
                return sm.predict(feature_vector)
        except Exception:
            pass
        if not self.loaded or self.pipeline is None:
            return 3.0
        try:
            fv = feature_vector.reshape(1, -1) if hasattr(feature_vector, 'reshape') else [feature_vector]
            pred = self.pipeline.predict(fv)[0]
            return float(max(1.0, min(5.0, pred)))
        except Exception:
            return 3.0

    def predict_batch(self, feature_matrix: Any) -> np.ndarray:
        """Predict suitability scores for batch of feature vectors."""
        try:
            from ml.models.suitability_model import SuitabilityModel
            sm = SuitabilityModel.get_instance()
            if sm.loaded:
                return sm.predict_batch(feature_matrix)
        except Exception:
            pass
        if not self.loaded or self.pipeline is None:
            return np.full(len(feature_matrix), 3.0)
        try:
            preds = self.pipeline.predict(feature_matrix)
            return np.clip(np.round(preds, 2), 1.0, 5.0)
        except Exception:
            return np.full(len(feature_matrix), 3.0)

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": "Random Forest Suitability",
            "algorithm": "RandomForestRegressor Pipeline",
            "loaded": self.loaded,
            "artifact": ARTIFACT_PATH,
            **self.metadata,
        }
