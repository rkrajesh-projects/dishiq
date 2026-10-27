import os
import json
import pytest
import pandas as pd
from sentence_transformers import SentenceTransformer

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
DATA_DIR = os.path.join(ML_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
REPORTS_DIR = os.path.join(ML_DIR, "reports")
MODELS_DIR = os.path.join(ML_DIR, "models")
PRETRAINED_DIR = os.path.join(MODELS_DIR, "pretrained")

def test_pipeline_generated_artifacts():
    # Check reports
    assert os.path.exists(os.path.join(REPORTS_DIR, "dataset_report.json"))
    assert os.path.exists(os.path.join(REPORTS_DIR, "duplicate_analysis.json"))
    
    # Check datasets
    assert os.path.exists(os.path.join(PROCESSED_DIR, "cleaned_combined_dataset.csv"))
    assert os.path.exists(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    assert os.path.exists(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    assert os.path.exists(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    # Check pretrained model registry
    assert os.path.exists(os.path.join(PRETRAINED_DIR, "pretrained_registry.json"))

def test_no_data_leakage_and_splits_logic():
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    val_df = pd.read_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    train_ids = set(train_df['recipe_id'])
    val_ids = set(val_df['recipe_id'])
    test_ids = set(test_df['recipe_id'])
    
    # Leakage tests
    assert len(train_ids.intersection(val_ids)) == 0, "Leakage between train and validation"
    assert len(train_ids.intersection(test_ids)) == 0, "Leakage between train and test"
    assert len(val_ids.intersection(test_ids)) == 0, "Leakage between val and test"
    
    # Stable IDs and source check
    assert 'recipe_id' in train_df.columns
    assert 'dataset_source' in train_df.columns
    assert len(train_df['recipe_id'].dropna()) == len(train_df)
    
    # Check stratification (Both sources should be in all splits if large enough)
    assert set(train_df['dataset_source'].unique()) == {'foodcom', 'archanas_kitchen'}
    assert set(val_df['dataset_source'].unique()) == {'foodcom', 'archanas_kitchen'}
    assert set(test_df['dataset_source'].unique()) == {'foodcom', 'archanas_kitchen'}
    
    # Empty/Null handling (description might be empty, but ID/name/source should not be null)
    assert train_df['recipe_id'].isnull().sum() == 0
    assert train_df['recipe_name'].isnull().sum() == 0
    assert train_df['dataset_source'].isnull().sum() == 0

def test_duplicate_analysis_report():
    with open(os.path.join(REPORTS_DIR, "duplicate_analysis.json"), 'r') as f:
        report = json.load(f)
    
    assert "total_recipes_before_cleaning" in report
    assert "exact_duplicates_removed" in report
    assert "recipes_retained" in report
    
    # Make sure we didn't wipe everything aggressively
    assert report["recipes_retained"] > 0
    assert report["foodcom_retained_count"] > 0
    assert report["archanas_kitchen_retained_count"] > 0

def test_pretrained_model_registry_and_load():
    with open(os.path.join(PRETRAINED_DIR, "pretrained_registry.json"), 'r') as f:
        registry = json.load(f)
    
    assert registry["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert registry["embedding_dimension"] == 384
    
    # Ensure it loads from cache successfully (it won't download if cached)
    model = SentenceTransformer(registry["model_name"], cache_folder=registry["cache_location"])
    assert model is not None
