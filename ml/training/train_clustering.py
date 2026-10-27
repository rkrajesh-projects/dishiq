"""
DishIQ ML — Training Script: K-Means Recipe Clustering
Run from repository root: python ml/training/train_clustering.py

Discovers natural recipe groupings from structural features.
Clusters are NOT manually named — descriptions are auto-generated from centroid statistics.

Algorithm: K-Means (scikit-learn)
Evaluation: Silhouette Score
"""
import os
import sys
import json
import time
import logging

import numpy as np
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# Path setup
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'backend'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dishiq.train_clustering")

ARTIFACTS_DIR  = os.path.join(REPO_ROOT, 'ml', 'artifacts')
MODEL_PATH     = os.path.join(ARTIFACTS_DIR, 'recipe_kmeans.joblib')
SCALER_PATH    = os.path.join(ARTIFACTS_DIR, 'recipe_scaler.joblib')
METADATA_PATH  = os.path.join(ARTIFACTS_DIR, 'clustering_metadata.json')

RANDOM_SEED = 42
K_CANDIDATES = [4, 5, 6]  # Try these K values, pick best silhouette


def auto_describe_cluster(centroid: np.ndarray, feature_names: list) -> str:
    """
    Auto-generate a human-readable cluster description based on centroid values.
    No manual label assignment — derived purely from the centroid statistics.
    """
    feat = dict(zip(feature_names, centroid))
    total_time = feat.get("total_time", 0)
    servings   = feat.get("servings", 4)
    n_ing      = feat.get("ingredient_count", 5)
    rating     = feat.get("avg_rating", 4.5)

    parts = []

    # Time-based description
    if total_time <= 20:
        parts.append("Very quick")
    elif total_time <= 40:
        parts.append("Quick")
    elif total_time <= 70:
        parts.append("Moderate time")
    else:
        parts.append("Long cooking")

    # Servings
    if servings <= 2:
        parts.append("small servings")
    elif servings <= 4:
        parts.append("medium servings")
    else:
        parts.append("large servings")

    # Complexity by ingredient count
    if n_ing <= 5:
        parts.append("few ingredients")
    elif n_ing <= 10:
        parts.append("moderate complexity")
    else:
        parts.append("many ingredients")

    # Rating
    if rating >= 4.5:
        parts.append("highly rated")

    return ", ".join(parts).capitalize()


def load_recipe_features():
    from app.db.session import SessionLocal
    from ml.preprocessing.recipe_features import (
        extract_recipe_features_from_db,
        get_clustering_feature_matrix,
        CLUSTERING_FEATURE_NAMES
    )
    db = SessionLocal()
    try:
        df = extract_recipe_features_from_db(db)
        logger.info(f"Loaded {len(df)} recipes from database")
        X = get_clustering_feature_matrix(df)
        return df, X, CLUSTERING_FEATURE_NAMES
    finally:
        db.close()


def select_best_k(X_scaled: np.ndarray) -> tuple:
    """Try multiple K values and select based on Silhouette Score."""
    results = {}
    for k in K_CANDIDATES:
        km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10, max_iter=300)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        results[k] = {"model": km, "labels": labels, "silhouette": round(float(score), 4)}
        logger.info(f"  K={k}: Silhouette={score:.4f}")

    best_k = max(results, key=lambda k: results[k]["silhouette"])
    logger.info(f"Best K={best_k} (Silhouette={results[best_k]['silhouette']})")
    return best_k, results[best_k]["model"], results[best_k]["labels"], results[best_k]["silhouette"], results


def main():
    logger.info("=== DishIQ — Training K-Means Recipe Clustering ===")

    df, X_raw, feature_names = load_recipe_features()

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    logger.info(f"Feature matrix: {X_scaled.shape} | Features: {feature_names}")

    # Select best K
    logger.info(f"Trying K values: {K_CANDIDATES}")
    best_k, best_model, labels, best_silhouette, all_results = select_best_k(X_scaled)

    # Auto-describe clusters from centroids
    centroids_unscaled = scaler.inverse_transform(best_model.cluster_centers_)
    cluster_descriptions = {}
    for cid in range(best_k):
        desc = auto_describe_cluster(centroids_unscaled[cid], feature_names)
        cluster_descriptions[cid] = desc
        count = int((labels == cid).sum())
        logger.info(f"  Cluster {cid}: '{desc}' — {count} recipes")

    # Save artifacts
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    joblib.dump({
        "model": best_model,
        "cluster_labels": labels.tolist(),
        "recipe_ids": df["recipe_id"].tolist(),
        "cluster_descriptions": cluster_descriptions,
    }, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    logger.info(f"K-Means model saved to {MODEL_PATH}")

    # Save silhouette scores for all K values
    silhouette_by_k = {k: v["silhouette"] for k, v in all_results.items()}

    metadata = {
        "model_name": "DishIQ Recipe Clusterer — K-Means",
        "model_version": "1.0.0",
        "algorithm": "K-Means (sklearn)",
        "purpose": "Unsupervised recipe grouping by structural characteristics",
        "best_k": best_k,
        "best_silhouette_score": best_silhouette,
        "silhouette_by_k": silhouette_by_k,
        "k_candidates_tried": K_CANDIDATES,
        "n_recipes": len(df),
        "feature_names": feature_names,
        "cluster_descriptions": cluster_descriptions,
        "cluster_sizes": {
            str(cid): int((labels == cid).sum()) for cid in range(best_k)
        },
        "random_seed": RANDOM_SEED,
        "training_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved to {METADATA_PATH}")

    logger.info("=== Clustering Complete ===")
    logger.info(f"Best K={best_k}, Silhouette Score={best_silhouette}")
    for cid, desc in cluster_descriptions.items():
        count = int((labels == cid).sum())
        logger.info(f"  Cluster {cid}: '{desc}' — {count} recipes")


if __name__ == "__main__":
    main()
