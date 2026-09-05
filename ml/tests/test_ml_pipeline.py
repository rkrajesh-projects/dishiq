import os
import json
import joblib
import pytest
from ml.utils.feature_engineering import create_recipe_feature_document, normalize_text
from ml.training.train_recipe_recommender import train_recommender


def test_feature_engineering_normalizes_text():
    raw_doc = {
        "name": "Paneer Bhurji!",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "description": "Scrambled cottage cheese...",
        "ingredients": ["paneer", "tomato", "onion"]
    }
    doc = create_recipe_feature_document(raw_doc)
    assert "paneer bhurji" in doc
    assert "indian" in doc
    assert "vegetarian" in doc
    assert "!" not in doc


def test_ml_training_generates_enhanced_metadata_and_artifacts():
    train_recommender()
    
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "artifacts"))
    joblib_path = os.path.join(artifacts_dir, "recipe_tfidf.joblib")
    metadata_path = os.path.join(artifacts_dir, "metadata.json")

    assert os.path.exists(joblib_path)
    assert os.path.exists(metadata_path)

    with open(metadata_path) as f:
        metadata = json.load(f)

    assert "model_name" in metadata
    assert "model_version" in metadata
    assert "algorithm" in metadata
    assert "feature_count" in metadata
    assert "dataset_version" in metadata
    assert "training_timestamp" in metadata
    assert "sklearn_version" in metadata
    assert "artifact_filename" in metadata
    assert metadata["artifact_filename"] == "recipe_tfidf.joblib"

    # Test artifact loading
    model_data = joblib.load(joblib_path)
    assert "vectorizer" in model_data
    assert "tfidf_matrix" in model_data
    assert "recipe_ids" in model_data
    assert "recipes" in model_data
