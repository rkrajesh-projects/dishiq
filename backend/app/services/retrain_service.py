import os
import time
import json
import joblib
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sentence_transformers import SentenceTransformer
from scipy.sparse import hstack

from app.models.recipe import Recipe
from app.services.ml_service import MLService
from ml.utils.feature_engineering import create_recipe_feature_document
from ml.training.train_random_forest_v1 import extract_features as rf_extract_features
from ml.training.train_kmeans_v1 import extract_ingredients_text, safe_len, generate_cluster_descriptions

logger = logging.getLogger("dishiq.retrain")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "ml", "artifacts")


def run_retrain_pipeline(db: Session):
    """
    Pulls the latest database state, retrains TF-IDF, Semantic, RF, and K-Means,
    saves the updated joblib artifacts exactly as the original training scripts did,
    and triggers MLService hot reload.
    """
    logger.info("Starting Full Production ML Retraining Pipeline...")
    t_start = time.time()
    
    recipes = db.query(Recipe).all()
    if not recipes:
        logger.error("No recipes in DB to train on!")
        return False
        
    recipe_ids = [str(r.id) for r in recipes]
    logger.info(f"Loaded {len(recipes)} recipes from DB.")
    
    # Pre-extract unified dictionaries for feature generation
    unified_recipes = []
    for r in recipes:
        unified_recipes.append({
            'recipe_id': str(r.id),
            'name': r.name or "Unknown Recipe",
            'description': r.description or "",
            'cuisine': (r.cuisine or 'Unknown').strip(),
            'dietary_type': (r.dietary_type or 'Standard').strip(),
            'diet': (r.dietary_type or 'Standard').strip(), # For RF
            'ingredients': [ri.ingredient.canonical_name for ri in r.ingredients],
            'instructions': r.legacy_instructions,
            'cooking_time': (r.preparation_minutes or 0) + (r.cooking_minutes or 0),
            'rating': r.average_rating or 4.5
        })

    # --- 1. TF-IDF V2 Retrain ---
    logger.info("Retraining TF-IDF...")
    texts = [create_recipe_feature_document(r) for r in unified_recipes]
    
    tfidf_vec = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=10000,
        min_df=2 if len(texts) > 2 else 1, # Prevent crash on tiny datasets
        max_df=0.95,
        stop_words="english",
        sublinear_tf=True
    )
    
    tfidf_matrix = tfidf_vec.fit_transform(texts)
    
    tfidf_path = os.path.join(ARTIFACTS_DIR, "recipe_tfidf_v2.joblib")
    joblib.dump({
        "vectorizer": tfidf_vec,
        "tfidf_matrix": tfidf_matrix,
        "recipe_ids": recipe_ids,
        "recipe_sources": ["DB"] * len(recipes)
    }, tfidf_path)
    logger.info("TF-IDF saved.")

    # --- 2. Sentence Transformer Retrain ---
    logger.info("Retraining Sentence Transformer (generating embeddings)...")
    model_name = 'all-MiniLM-L6-v2'
    pretrained_dir = os.path.join(PROJECT_ROOT, "ml", "models", "pretrained")
    st_model = SentenceTransformer(model_name, cache_folder=pretrained_dir)
    
    embeddings = st_model.encode(texts, convert_to_numpy=True)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings_normalized = np.divide(embeddings, norms, out=np.zeros_like(embeddings), where=norms!=0)
    
    st_path = os.path.join(ARTIFACTS_DIR, "recipe_sentence_transformer_v1.joblib")
    joblib.dump({
        "embeddings": embeddings_normalized,
        "recipe_ids": recipe_ids
    }, st_path)
    logger.info("Semantic embeddings saved.")
    
    # --- 3. Random Forest Retrain ---
    logger.info("Retraining Random Forest Suitability...")
    df_raw = pd.DataFrame([{
        'cooking_time': r['cooking_time'],
        'ingredients': json.dumps(r['ingredients']),
        'instructions': json.dumps(r['instructions']),
        'cuisine': r['cuisine'],
        'diet': r['diet'],
        'rating': r['rating']
    } for r in unified_recipes])
    
    df_rf = rf_extract_features(df_raw)
    y_rf = df_rf.pop('rating').values
    
    numeric_features = ['cooking_time', 'ingredient_count', 'instruction_count']
    categorical_features = ['cuisine', 'diet']
    
    # CRITICAL FIX: sparse_output=False required for RandomForestRegressor
    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
    ])
    
    rf_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42))
    ])
    
    rf_pipeline.fit(df_rf, y_rf)
    
    rf_path = os.path.join(ARTIFACTS_DIR, "random_forest_suitability_v1.joblib")
    joblib.dump(rf_pipeline, rf_path)
    logger.info("Random Forest saved.")

    # --- 4. K-Means Clustering Retrain ---
    logger.info("Retraining K-Means Clustering...")
    df_km = pd.DataFrame([{
        'recipe_id': r['recipe_id'],
        'cooking_time': r['cooking_time'],
        'ingredients': json.dumps(r['ingredients']),
        'cuisine': r['cuisine'],
        'diet': r['diet']
    } for r in unified_recipes])
    
    df_km['cooking_time'] = pd.to_numeric(df_km['cooking_time'], errors='coerce').fillna(0.0)
    df_km['ingredient_count'] = df_km['ingredients'].apply(safe_len).astype(float)
    df_km['ingredients_text'] = df_km['ingredients'].apply(extract_ingredients_text).str.lower()
    
    df_km['log_cooking_time'] = np.log1p(df_km['cooking_time'])
    df_km['log_ingredient_count'] = np.log1p(df_km['ingredient_count'])
    
    kmeans_tfidf = TfidfVectorizer(max_features=200, stop_words='english')
    X_tfidf = kmeans_tfidf.fit_transform(df_km['ingredients_text'])
    
    scaler = StandardScaler()
    X_num = scaler.fit_transform(df_km[['log_cooking_time', 'log_ingredient_count']])
    X_num = X_num * 0.5
    
    # CRITICAL FIX: The training script stacked X_tfidf THEN X_num
    X_combined = hstack([X_tfidf, X_num])
    
    n_clusters = min(5, max(2, len(recipes) // 20)) # Adaptive K, at least 2
    if n_clusters < 2:
        n_clusters = 2
        
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_combined)
    
    cluster_stats = generate_cluster_descriptions(df_km, cluster_labels, n_clusters, kmeans_tfidf, X_tfidf)
    
    kmeans_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1.joblib")
    joblib.dump({
        "kmeans_model": kmeans,
        "scaler": scaler,
        "tfidf_vectorizer": kmeans_tfidf,
        "cluster_stats": cluster_stats,
        "recipe_ids": df_km["recipe_id"].tolist(),
        "cluster_labels": cluster_labels.tolist()
    }, kmeans_path)
    logger.info(f"K-Means saved (K={n_clusters}).")

    # --- 5. Reload MLService ---
    logger.info("Triggering MLService reload...")
    MLService.reset()
    MLService.get_instance()
    
    logger.info(f"Retraining complete in {time.time() - t_start:.2f}s!")
    return True
