import os
import json
import pytest
import pandas as pd
import numpy as np
import joblib

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
PROCESSED_DIR = os.path.join(ML_DIR, "data", "processed")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
REPORTS_DIR = os.path.join(ML_DIR, "reports")

def test_kmeans_artifacts_exist_and_loadable():
    joblib_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1.joblib")
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1_metadata.json")
    report_path = os.path.join(REPORTS_DIR, "kmeans_evaluation_report.json")
    
    assert os.path.exists(joblib_path)
    assert os.path.exists(meta_path)
    assert os.path.exists(report_path)
    
    data = joblib.load(joblib_path)
    assert "kmeans_model" in data
    assert "tfidf_vectorizer" in data
    assert "scaler" in data
    assert "cluster_stats" in data
    assert "recipe_ids" in data
    assert "cluster_labels" in data

def test_kmeans_cluster_assignments_valid():
    assignments_csv = os.path.join(ARTIFACTS_DIR, "recipe_cluster_assignments.csv")
    assert os.path.exists(assignments_csv)
    
    df = pd.read_csv(assignments_csv)
    assert len(df) == 2005
    assert "recipe_id" in df.columns
    assert "cluster_id" in df.columns
    
    # Check for duplicates
    assert len(df["recipe_id"].unique()) == 2005
    
    # Check cluster ranges
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1_metadata.json")
    with open(meta_path) as f:
        meta = json.load(f)
        
    k = meta["selected_k"]
    valid_ids = set(range(k))
    
    assigned_ids = set(df["cluster_id"].unique())
    assert assigned_ids.issubset(valid_ids)

def test_kmeans_inference():
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    
    from ml.models.kmeans_recipe_clusterer import RecipeKMeansClusterer
    RecipeKMeansClusterer.reset()
    model = RecipeKMeansClusterer.get_instance()
    
    assert model.loaded, "Model failed to load"
    assert model.kmeans_model is not None
    
    # Valid Recipe Context
    recipe_dict = {
        "cooking_time": 30,
        "ingredients": ["paneer", "onion", "tomato", "spices"],
    }
    
    cluster_id = model.predict_cluster(recipe_dict)
    assert isinstance(cluster_id, int)
    assert 0 <= cluster_id < model.kmeans_model.n_clusters
    
    # Test description
    summary = model.get_cluster_summary(cluster_id)
    assert "Cluster" in summary
    assert "Recipes" in summary

def test_kmeans_metadata_valid():
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1_metadata.json")
    with open(meta_path) as f:
        meta = json.load(f)
        
    assert meta["model_type"] == "KMeans" or meta["algorithm"] == "KMeans"
    assert "selected_k" in meta
    assert "final_metrics" in meta
    assert "Silhouette" in meta["final_metrics"]
    assert "limitations" in meta
