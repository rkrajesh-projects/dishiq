"""
DishIQ ML — Random Forest Recipe Suitability Model (Model 3)

Purpose: Predicts a suitability score (1-5) for a recipe based on its structural features.

Training data: Food.com interactions dataset (real user ratings).
IMPORTANT: The Food.com users are different from DishIQ users. This model acts as a
*general recipe quality predictor* — it learns which recipe characteristics correlate
with higher ratings, independent of a specific user. It is NOT a personalized 
user-preference model (that requires more DishIQ-specific interaction data).

Algorithm: RandomForestRegressor (scikit-learn)
"""
import os
import time
import logging
import joblib
import numpy as np
from typing import Optional, Dict, Any, List

logger = logging.getLogger("dishiq")

MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "suitability_rf_model.joblib")
)
PREPROCESSOR_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "suitability_preprocessor.joblib")
)
METADATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "artifacts", "suitability_metadata.json")
)


class SuitabilityModel:
    """
    Loads the pre-trained Random Forest Regressor.
    Predicts recipe suitability score in range [1.0, 5.0].
    """
    _instance: Optional["SuitabilityModel"] = None

    def __init__(self):
        self.model = None
        self.scaler = None
        self.loaded = False
        self.metadata: Dict[str, Any] = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "SuitabilityModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _load(self):
        if not os.path.exists(MODEL_PATH):
            logger.warning(f"RF suitability model not found at {MODEL_PATH}. Run train_suitability.py first.")
            return
        try:
            t0 = time.time()
            self.model = joblib.load(MODEL_PATH)
            if os.path.exists(PREPROCESSOR_PATH):
                self.scaler = joblib.load(PREPROCESSOR_PATH)
            if os.path.exists(METADATA_PATH):
                import json
                with open(METADATA_PATH) as f:
                    self.metadata = json.load(f)
            self.loaded = True
            elapsed = round((time.time() - t0) * 1000, 1)
            logger.info(f"SuitabilityModel (RF) loaded in {elapsed}ms")
        except Exception as e:
            logger.error(f"Failed to load RF suitability model: {e}")
            self.loaded = False

    def predict(self, feature_vector: np.ndarray) -> float:
        """
        Predict suitability score for a single recipe.
        
        Args:
            feature_vector: 1D numpy array of shape (n_features,)
            
        Returns:
            Predicted score in [1.0, 5.0]. Returns 3.0 (neutral) if model unavailable.
        """
        if not self.loaded or self.model is None:
            return 3.0  # neutral fallback, not a fake prediction

        fv = feature_vector.reshape(1, -1)
        if self.scaler is not None:
            fv = self.scaler.transform(fv)

        pred = float(self.model.predict(fv)[0])
        return float(np.clip(round(pred, 2), 1.0, 5.0))

    def predict_batch(self, feature_matrix: np.ndarray) -> np.ndarray:
        """Predict suitability scores for multiple recipes."""
        if not self.loaded or self.model is None:
            return np.full(len(feature_matrix), 3.0)

        X = feature_matrix
        if self.scaler is not None:
            X = self.scaler.transform(X)

        preds = self.model.predict(X)
        return np.clip(np.round(preds, 2), 1.0, 5.0)

    def get_feature_importances(self) -> Dict[str, float]:
        """Return feature importances from the trained RF model."""
        from ml.preprocessing.recipe_features import SUITABILITY_FEATURE_NAMES
        if not self.loaded or not hasattr(self.model, "feature_importances_"):
            return {}
        return dict(zip(SUITABILITY_FEATURE_NAMES, self.model.feature_importances_.tolist()))

    def get_info(self) -> Dict[str, Any]:
        return {
            "model": "RandomForestRegressor",
            "algorithm": "Supervised ML — Ensemble of Decision Trees",
            "purpose": "General recipe suitability prediction (NOT user-personalized)",
            "loaded": self.loaded,
            "artifact": MODEL_PATH,
            **self.metadata,
        }
