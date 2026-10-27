import os
import json
import pytest
import pandas as pd
import numpy as np
import joblib

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
SPLITS_DIR = os.path.join(ML_DIR, "data", "splits")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")

def test_rf_artifacts_exist_and_loadable():
    joblib_path = os.path.join(ARTIFACTS_DIR, "random_forest_suitability_v1.joblib")
    meta_path = os.path.join(ARTIFACTS_DIR, "random_forest_suitability_v1_metadata.json")
    
    assert os.path.exists(joblib_path)
    assert os.path.exists(meta_path)
    
    try:
        import sklearn.compose._column_transformer as _ct
        if not hasattr(_ct, "_RemainderColsList"):
            class _RemainderColsList(list):
                pass
            _ct._RemainderColsList = _RemainderColsList
    except Exception:
        pass
    pipeline = joblib.load(joblib_path)
    assert hasattr(pipeline, "predict")
    
def test_no_leakage_between_splits():
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    val_df = pd.read_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    train_ids = set(train_df['recipe_id'])
    val_ids = set(val_df['recipe_id'])
    test_ids = set(test_df['recipe_id'])
    
    assert len(train_ids.intersection(val_ids)) == 0, "Validation leak!"
    assert len(train_ids.intersection(test_ids)) == 0, "Test leak!"

def test_rf_inference():
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    
    from ml.models.random_forest_suitability import RandomForestSuitability
    RandomForestSuitability.reset()
    model = RandomForestSuitability.get_instance()
    
    assert model.loaded, "Model failed to load"
    assert model.pipeline is not None
    
    # Valid Recipe Context
    recipe_dict = {
        "cooking_time": 30,
        "ingredients": ["onion", "garlic", "tomato"],
        "instructions": ["chop", "fry", "eat"],
        "cuisine": "Indian",
        "diet": "Vegetarian"
    }
    
    score = model.predict_suitability(recipe_dict)
    assert isinstance(score, float)
    assert not np.isnan(score)
    assert not np.isinf(score)
    assert 1.0 <= score <= 5.0
    
    # Missing values context (should handle via pipeline gracefully)
    empty_dict = {}
    score_empty = model.predict_suitability(empty_dict)
    assert isinstance(score_empty, float)
    assert 1.0 <= score_empty <= 5.0

def test_rf_metadata_valid():
    meta_path = os.path.join(ARTIFACTS_DIR, "random_forest_suitability_v1_metadata.json")
    with open(meta_path) as f:
        meta = json.load(f)
        
    assert meta["model_type"] == "RandomForestRegressor"
    assert meta["task_type"] == "Regression"
    assert "target" in meta
    assert "features" in meta
    
def test_feature_importances_exist():
    fi_path = os.path.join(ML_DIR, "reports", "random_forest_feature_importance.json")
    assert os.path.exists(fi_path)
    with open(fi_path) as f:
        importances = json.load(f)
    assert len(importances) > 0
    assert sum(importances.values()) == pytest.approx(1.0, 0.001)
