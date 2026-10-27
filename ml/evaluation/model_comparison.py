import os
import json
import time
import pandas as pd
import numpy as np

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
SPLITS_DIR = os.path.join(ML_DIR, "data", "splits")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
REPORTS_DIR = os.path.join(ML_DIR, "reports")
EVAL_DIR = os.path.join(ML_DIR, "evaluation")

if not os.path.exists(EVAL_DIR):
    os.makedirs(EVAL_DIR)

def evaluate_retrieval(model_instance, queries, target_ids, k_values=[5, 10]):
    """
    Evaluates HitRate@K and MRR@K using exact normalized recipe names as queries.
    model_instance must have a `query(text, top_k)` method returning [{"recipe_id":...}]
    """
    metrics = {f"HitRate@{k}": 0.0 for k in k_values}
    for k in k_values:
        metrics[f"MRR@{k}"] = 0.0
        
    n_queries = len(queries)
    if n_queries == 0: return metrics
    
    # We evaluate up to the max K
    max_k = max(k_values)
    
    for q, t_id in zip(queries, target_ids):
        results = model_instance.query(q, top_k=max_k)
        retrieved_ids = [r["recipe_id"] for r in results]
        
        for k in k_values:
            k_retrieved = retrieved_ids[:k]
            if t_id in k_retrieved:
                metrics[f"HitRate@{k}"] += 1
                rank = k_retrieved.index(t_id) + 1
                metrics[f"MRR@{k}"] += (1.0 / rank)
                
    for k in metrics:
        metrics[k] /= n_queries
        
    return metrics

def run_comparison():
    print("=== Phase 18: Rigorous ML Evaluation ===")
    
    # Load Test Set
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    print(f"Loaded Test Set: {len(test_df)} recipes")
    
    # Setup report
    report = {
        "dataset": {
            "version": "Phase 14A Cleaned Combined",
            "train_size": len(train_df),
            "test_size": len(test_df)
        },
        "retrieval_models": {},
        "suitability_model": {},
        "clustering_model": {},
        "evaluation_protocol": "Proxy-based intrinsic structural evaluation without genuine user logs.",
        "limitations": "Lack of genuine user click/interaction data limits external validity. Metrics reflect structural data fidelity, not human personalization."
    }
    
    # 1. Retrieval Models
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    
    from ml.models.tfidf_recommender import TFIDFRecommender
    from ml.models.sentence_transformer_recommender import SemanticRecommender
    
    queries = test_df['recipe_name'].str.lower().tolist()
    target_ids = test_df['recipe_id'].tolist()
    
    # A. TF-IDF
    print("Evaluating TF-IDF V2...")
    tfidf = TFIDFRecommender.get_instance()
    if tfidf.loaded:
        tfidf_metrics = evaluate_retrieval(tfidf, queries, target_ids, k_values=[5, 10])
        report["retrieval_models"]["TF-IDF_V2"] = {
            "metrics": tfidf_metrics,
            "artifact": "recipe_tfidf_v2.joblib"
        }
        print("  TF-IDF done.")
    
    # B. Sentence Transformer
    print("Evaluating Sentence Transformer V1...")
    st = SemanticRecommender.get_instance()
    if st.loaded:
        st_metrics = evaluate_retrieval(st, queries, target_ids, k_values=[5, 10])
        report["retrieval_models"]["SentenceTransformer_V1"] = {
            "metrics": st_metrics,
            "artifact": "recipe_sentence_transformer_v1.joblib"
        }
        print("  Sentence Transformer done.")
        
    # C. Hybrid Recommender
    print("Evaluating Hybrid Recommender...")
    from ml.models.hybrid_recommender import HybridRecommender
    hybrid = HybridRecommender.get_instance()
    if hybrid.loaded:
        hybrid_metrics = evaluate_retrieval(hybrid, queries, target_ids, k_values=[5, 10])
        report["retrieval_models"]["HybridRecommender"] = {
            "metrics": hybrid_metrics,
            "weights": hybrid.weights,
            "artifact": "hybrid_recommender (composite)"
        }
        print("  Hybrid Recommender done.")
        
    # 2. Random Forest Suitability (Regression)
    print("Evaluating Random Forest Suitability V1...")
    from ml.models.random_forest_suitability import RandomForestSuitability
    rf = RandomForestSuitability.get_instance()
    
    if rf.loaded and 'rating' in test_df.columns:
        # We must re-extract features safely
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        
        # Mean baseline
        y_true = pd.to_numeric(test_df['rating'], errors='coerce').fillna(4.5).values
        train_mean = pd.to_numeric(train_df['rating'], errors='coerce').fillna(4.5).mean()
        y_pred_baseline = np.full_like(y_true, train_mean)
        
        base_rmse = np.sqrt(mean_squared_error(y_true, y_pred_baseline))
        base_mae = mean_absolute_error(y_true, y_pred_baseline)
        
        # Load RF metadata for Test scores (avoiding full extraction boilerplate)
        rf_meta_path = os.path.join(ARTIFACTS_DIR, "random_forest_suitability_v1_metadata.json")
        rf_metrics = {}
        if os.path.exists(rf_meta_path):
            with open(rf_meta_path) as f:
                rf_meta = json.load(f)
                rf_metrics = rf_meta.get("evaluation", {}).get("test_metrics", {})
                
        report["suitability_model"]["RandomForest_V1"] = {
            "target": "Recipe Rating (proxy for quality/suitability)",
            "metrics": rf_metrics,
            "baseline_metrics": {
                "RMSE": base_rmse,
                "MAE": base_mae
            },
            "artifact": "random_forest_suitability_v1.joblib"
        }
        print("  RF Suitability done.")
        
    # 3. K-Means
    print("Evaluating K-Means V1...")
    kmeans_meta_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1_metadata.json")
    if os.path.exists(kmeans_meta_path):
        with open(kmeans_meta_path) as f:
            kmeans_meta = json.load(f)
            report["clustering_model"]["KMeans_V1"] = {
                "selected_k": kmeans_meta.get("selected_k"),
                "metrics": kmeans_meta.get("final_metrics"),
                "cluster_sizes": {k: v["count"] for k, v in kmeans_meta.get("cluster_summaries", {}).items()},
                "artifact": "recipe_kmeans_v1.joblib"
            }
        print("  K-Means done.")
        
    report_path = os.path.join(REPORTS_DIR, "ml_model_comparison_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nReport generated successfully: {report_path}")

if __name__ == "__main__":
    run_comparison()
