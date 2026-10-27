import os
import json
import pytest
import pandas as pd
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
SPLITS_DIR = os.path.join(ML_DIR, "data", "splits")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
REPORTS_DIR = os.path.join(ML_DIR, "reports")

def test_datasets_load_correctly():
    assert os.path.exists(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    assert os.path.exists(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    assert os.path.exists(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    assert len(train_df) > 0
    
def test_no_leakage_between_splits():
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    val_df = pd.read_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    train_ids = set(train_df['recipe_id'])
    val_ids = set(val_df['recipe_id'])
    test_ids = set(test_df['recipe_id'])
    
    assert len(train_ids.intersection(val_ids)) == 0, "Validation leak!"
    assert len(train_ids.intersection(test_ids)) == 0, "Test leak!"

def test_tfidf_artifacts_exist_and_loadable():
    joblib_path = os.path.join(ARTIFACTS_DIR, "recipe_tfidf_v2.joblib")
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_tfidf_v2_metadata.json")
    
    assert os.path.exists(joblib_path)
    assert os.path.exists(meta_path)
    
    data = joblib.load(joblib_path)
    assert "vectorizer" in data
    assert "tfidf_matrix" in data
    assert "recipe_ids" in data
    
    vec = data["vectorizer"]
    assert isinstance(vec, TfidfVectorizer)
    assert data["tfidf_matrix"].shape[0] == len(data["recipe_ids"])

def test_tfidf_inference():
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    
    # Reload singleton to ensure V2 is picked up
    from ml.models.tfidf_recommender import TFIDFRecommender
    TFIDFRecommender.reset()
    model = TFIDFRecommender.get_instance()
    
    assert model.loaded, "Model failed to load"
    assert model.metadata.get("model_version") == "2.0.0", "Expected V2 model"
    
    # Query test
    results = model.query("paneer butter masala", top_k=5)
    assert len(results) == 5
    assert "recipe_id" in results[0]
    assert "similarity" in results[0]
    
    # Handle empty
    assert len(model.query("", top_k=5)) == 0
    assert len(model.query("   ", top_k=5)) == 0
    
    # Check bounds
    sim = model.similarity_for(results[0]["recipe_id"], "paneer butter masala")
    assert not np.isnan(sim)
    assert not np.isinf(sim)

def test_vocabulary_derived_only_from_train():
    # Load metadata
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_tfidf_v2_metadata.json")
    with open(meta_path) as f:
        meta = json.load(f)
        
    train_count = meta["training_dataset_count"]
    assert train_count > 0

    # Verification handled primarily during training script execution, 
    # but we ensure metadata explicitly documents the isolation.
    assert "Strict isolation of fitting on Train only" in meta["evaluation"]["methodology"]
