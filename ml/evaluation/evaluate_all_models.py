"""
DishIQ ML — Full Model Evaluation Pipeline
Run from repo root: python ml/evaluation/evaluate_all_models.py

Evaluates all 4 ML components and saves results to ml/artifacts/evaluation_report.json
All metrics are computed from REAL data. No values are fabricated.
"""
import sys, os, json, time, sqlite3
import numpy as np
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, r'd:\DishIQ')
sys.path.insert(0, r'd:\DishIQ\backend')

ARTIFACTS_DIR = r'd:\DishIQ\ml\artifacts'
DB_PATH = r'd:\DishIQ\backend\dishiq.db'

print("=" * 60)
print("DishIQ — ML Model Evaluation Report")
print("=" * 60)

report = {
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "models": {}
}

# ─────────────────────────────────────────────
# MODEL 1: TF-IDF Recommender
# ─────────────────────────────────────────────
print("\n[1] TF-IDF Recipe Recommender")
tfidf_path = os.path.join(ARTIFACTS_DIR, "recipe_tfidf.joblib")

if os.path.exists(tfidf_path):
    data = joblib.load(tfidf_path)
    vectorizer = data["vectorizer"]
    tfidf_matrix = data["tfidf_matrix"]
    recipe_ids = data["recipe_ids"]
    recipes = data["recipes"]

    from ml.utils.feature_engineering import normalize_text

    # --- Self-retrieval accuracy (sanity check)
    correct = 0
    sample = min(100, len(recipes))
    for i in range(sample):
        r = recipes[i]
        q_vec = vectorizer.transform([normalize_text(r["name"])])
        scores = cosine_similarity(q_vec, tfidf_matrix).flatten()
        if scores.argsort()[::-1][0] == i:
            correct += 1
    self_retrieval = round(correct / sample, 4)

    # --- Precision@5 with labeled test queries
    # 20 hand-curated queries with known expected top result (recipe name substring)
    labeled_queries = [
        ("paneer", "paneer"),
        ("chicken curry", "chicken"),
        ("pasta italian", "pasta"),
        ("dal lentil", "dal"),
        ("dosa south indian", "dosa"),
        ("biryani", "biryani"),
        ("vegan", "vegan"),
        ("soup", "soup"),
        ("rice", "rice"),
        ("butter chicken", "butter chicken"),
        ("vegetarian", "vegetarian"),
        ("masala", "masala"),
        ("egg", "egg"),
        ("mushroom", "mushroom"),
        ("noodles", "noodles"),
        ("salad", "salad"),
        ("bread", "bread"),
        ("cake", "cake"),
        ("sandwich", "sandwich"),
        ("tacos", "taco"),
    ]

    recipe_names_lower = [r["name"].lower() for r in recipes]
    hits_at_5 = 0
    sim_scores_top1 = []

    for query, keyword in labeled_queries:
        q_vec = vectorizer.transform([normalize_text(query)])
        scores = cosine_similarity(q_vec, tfidf_matrix).flatten()
        top5_idx = scores.argsort()[::-1][:5]
        sim_scores_top1.append(float(scores[top5_idx[0]]))
        # Hit if keyword appears in any of top-5 recipe names
        hit = any(keyword.lower() in recipe_names_lower[i] for i in top5_idx)
        if hit:
            hits_at_5 += 1

    precision_at_5 = round(hits_at_5 / len(labeled_queries), 4)
    avg_top1_sim = round(float(np.mean(sim_scores_top1)), 4)

    print(f"  Self-retrieval accuracy (top-100 recipes): {self_retrieval*100:.1f}%")
    print(f"  Precision@5 (20 labeled queries): {precision_at_5*100:.1f}%")
    print(f"  Avg top-1 similarity score: {avg_top1_sim}")
    print(f"  Vocabulary size: {len(vectorizer.vocabulary_)}")
    print(f"  Recipes indexed: {len(recipe_ids)}")

    report["models"]["tfidf_recommender"] = {
        "model": "TF-IDF + Cosine Similarity",
        "algorithm_type": "Classical NLP / Information Retrieval",
        "recipes_indexed": len(recipe_ids),
        "vocabulary_size": len(vectorizer.vocabulary_),
        "self_retrieval_accuracy_pct": round(self_retrieval * 100, 1),
        "precision_at_5_pct": round(precision_at_5 * 100, 1),
        "avg_top1_similarity": avg_top1_sim,
        "n_test_queries": len(labeled_queries),
        "hits_at_5": hits_at_5,
    }
else:
    print("  ARTIFACT NOT FOUND — run ml/training/train_recipe_recommender.py")
    report["models"]["tfidf_recommender"] = {"status": "artifact_missing"}

# ─────────────────────────────────────────────
# MODEL 2: SentenceTransformer Product Matcher
# ─────────────────────────────────────────────
print("\n[2] SentenceTransformer Product Matcher")
embeddings_path = os.path.join(ARTIFACTS_DIR, "product_embeddings.joblib")

if os.path.exists(embeddings_path):
    # Test semantic match pairs
    test_pairs = [
        ("paneer", "Mother Dairy Paneer 200g", True),
        ("paneer", "Amul Fresh Paneer 500g", True),
        ("paneer", "Tomato 1kg", False),
        ("onion", "Red Onion 1kg", True),
        ("onion", "Mango Juice 1L", False),
        ("tomato", "Tomato 500g", True),
        ("chicken", "Chicken Breast 500g", True),
        ("rice", "Basmati Rice 1kg", True),
        ("rice", "Apple Juice 1L", False),
        ("butter", "Amul Butter 500g", True),
    ]
    try:
        sys.path.insert(0, r'd:\DishIQ\backend')
        from app.product_matching.encoder import get_encoder
        encoder = get_encoder()

        correct = 0
        sim_scores = []
        THRESHOLD = 0.40

        for ing, product, expected_match in test_pairs:
            v1 = encoder.encode_text(ing)
            v2 = encoder.encode_text(product)
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            sim = float(np.dot(v1, v2) / (norm1 * norm2)) if norm1 > 0 and norm2 > 0 else 0.0
            sim = max(0.0, min(1.0, sim))
            predicted_match = sim >= THRESHOLD
            sim_scores.append(sim)
            if predicted_match == expected_match:
                correct += 1

        match_accuracy = round(correct / len(test_pairs), 4)
        avg_sim = round(float(np.mean(sim_scores)), 4)

        print(f"  Model: all-MiniLM-L6-v2 | Embedding dim: {encoder.get_embedding_dimension()}")
        print(f"  Match accuracy (10 test pairs): {match_accuracy*100:.1f}%")
        print(f"  Avg similarity across all pairs: {avg_sim}")
        print(f"  Match threshold: {THRESHOLD}")

        report["models"]["sentence_transformer_matcher"] = {
            "model": "all-MiniLM-L6-v2 (SentenceTransformer)",
            "algorithm_type": "Pre-trained transformer — semantic similarity",
            "embedding_dimension": encoder.get_embedding_dimension(),
            "match_threshold": THRESHOLD,
            "n_test_pairs": len(test_pairs),
            "match_accuracy_pct": round(match_accuracy * 100, 1),
            "avg_similarity": avg_sim,
            "note": "Pre-trained HuggingFace model — not fine-tuned on DishIQ data",
        }
    except Exception as e:
        print(f"  Encoder evaluation error: {e}")
        report["models"]["sentence_transformer_matcher"] = {"status": "evaluation_error", "error": str(e)}
else:
    print("  Product embeddings not found")
    report["models"]["sentence_transformer_matcher"] = {"status": "embeddings_missing"}

# ─────────────────────────────────────────────
# MODEL 3: Random Forest Suitability
# ─────────────────────────────────────────────
print("\n[3] Random Forest Suitability Model")
rf_path = os.path.join(ARTIFACTS_DIR, "suitability_rf_model.joblib")
rf_meta_path = os.path.join(ARTIFACTS_DIR, "suitability_metadata.json")

if os.path.exists(rf_path) and os.path.exists(rf_meta_path):
    with open(rf_meta_path) as f:
        rf_meta = json.load(f)
    print(f"  Algorithm: {rf_meta['algorithm']}")
    print(f"  Training samples: {rf_meta['n_training_samples']}")
    print(f"  Validation — MAE={rf_meta['validation_metrics']['MAE']}, RMSE={rf_meta['validation_metrics']['RMSE']}, R²={rf_meta['validation_metrics']['R2']}")
    print(f"  Test       — MAE={rf_meta['test_metrics']['MAE']}, RMSE={rf_meta['test_metrics']['RMSE']}, R²={rf_meta['test_metrics']['R2']}")
    top_feat = sorted(rf_meta["feature_importances"].items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  Top features: {top_feat}")
    print(f"  Note: {rf_meta['proxy_label_note'][:80]}...")
    report["models"]["random_forest_suitability"] = {
        "model": "RandomForestRegressor",
        "algorithm_type": "Supervised ML — Ensemble of Decision Trees",
        **rf_meta
    }
else:
    print("  ARTIFACT NOT FOUND — run ml/training/train_suitability.py")
    report["models"]["random_forest_suitability"] = {"status": "artifact_missing"}

# ─────────────────────────────────────────────
# MODEL 4: K-Means Clustering
# ─────────────────────────────────────────────
print("\n[4] K-Means Recipe Clustering")
km_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans.joblib")
km_meta_path = os.path.join(ARTIFACTS_DIR, "clustering_metadata.json")

if os.path.exists(km_path) and os.path.exists(km_meta_path):
    with open(km_meta_path) as f:
        km_meta = json.load(f)
    print(f"  Algorithm: K-Means | Best K={km_meta['best_k']}")
    print(f"  Silhouette scores by K: {km_meta['silhouette_by_k']}")
    print(f"  Best Silhouette Score: {km_meta['best_silhouette_score']}")
    print(f"  Clusters:")
    for cid, desc in km_meta["cluster_descriptions"].items():
        size = km_meta["cluster_sizes"].get(str(cid), "?")
        print(f"    Cluster {cid}: '{desc}' — {size} recipes")
    report["models"]["kmeans_clustering"] = {
        "model": "K-Means",
        "algorithm_type": "Unsupervised ML — Clustering",
        **km_meta
    }
else:
    print("  ARTIFACT NOT FOUND — run ml/training/train_clustering.py")
    report["models"]["kmeans_clustering"] = {"status": "artifact_missing"}

# ─────────────────────────────────────────────
# SAVE REPORT
# ─────────────────────────────────────────────
report_path = os.path.join(ARTIFACTS_DIR, "evaluation_report.json")
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)

print("\n" + "=" * 60)
print(f"Evaluation report saved to: {report_path}")
print("=" * 60)
