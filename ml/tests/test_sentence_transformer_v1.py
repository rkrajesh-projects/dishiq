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

def test_st_artifacts_exist_and_loadable():
    joblib_path = os.path.join(ARTIFACTS_DIR, "recipe_sentence_transformer_v1.joblib")
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_sentence_transformer_v1_metadata.json")
    
    assert os.path.exists(joblib_path)
    assert os.path.exists(meta_path)
    
    data = joblib.load(joblib_path)
    assert "embeddings" in data
    assert "recipe_ids" in data
    
    assert data["embeddings"].shape[0] == len(data["recipe_ids"])
    assert data["embeddings"].shape[1] == 384  # MiniLM-L6 dimension

def test_no_leakage_between_splits():
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    val_df = pd.read_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    train_ids = set(train_df['recipe_id'])
    val_ids = set(val_df['recipe_id'])
    test_ids = set(test_df['recipe_id'])
    
    assert len(train_ids.intersection(val_ids)) == 0, "Validation leak!"
    assert len(train_ids.intersection(test_ids)) == 0, "Test leak!"

def test_semantic_inference():
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    
    from ml.models.sentence_transformer_recommender import SemanticRecommender
    SemanticRecommender.reset()
    model = SemanticRecommender.get_instance()
    
    assert model.loaded, "Model failed to load"
    assert model.model is not None
    
    # Query test
    results = model.query("spicy south indian", top_k=5)
    assert len(results) == 5
    assert "recipe_id" in results[0]
    assert "similarity" in results[0]
    
    # Handle empty
    assert len(model.query("", top_k=5)) == 0
    assert len(model.query("   ", top_k=5)) == 0
    
    # Check bounds
    sim = results[0]["similarity"]
    assert not np.isnan(sim)
    assert not np.isinf(sim)
    assert -1.0 <= sim <= 1.0001
    
    # Check bounds limit
    assert len(model.query("test", top_k=50000)) == len(model.recipe_ids)

def test_st_metadata_valid():
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_sentence_transformer_v1_metadata.json")
    with open(meta_path) as f:
        meta = json.load(f)
        
    assert meta["model_type"] == "SentenceTransformer"
    assert meta["embedding_dimension"] == 384
    assert meta["pretrained_model"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert "No fine-tuning" in meta["evaluation"]["methodology"]
