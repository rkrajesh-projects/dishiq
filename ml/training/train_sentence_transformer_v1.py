import os
import sys
import json
import time
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
SPLITS_DIR = os.path.join(ML_DIR, "data", "splits")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
REPORTS_DIR = os.path.join(ML_DIR, "reports")
MODELS_DIR = os.path.join(ML_DIR, "models")
PRETRAINED_DIR = os.path.join(MODELS_DIR, "pretrained")

def build_text_feature(row):
    """
    Deterministically build a single text document representing the recipe.
    Must be identical to Phase 14B TF-IDF logic for fair comparison.
    """
    parts = []
    if pd.notna(row.get('recipe_name')) and row['recipe_name']:
        parts.extend([str(row['recipe_name'])] * 2)
    if pd.notna(row.get('cuisine')) and row['cuisine']:
        parts.append(str(row['cuisine']))
    if pd.notna(row.get('diet')) and row['diet']:
        parts.append(str(row['diet']))
    if pd.notna(row.get('description')) and row['description']:
        parts.append(str(row['description']))
    if pd.notna(row.get('ingredients')) and row['ingredients']:
        import json
        try:
            ing_list = json.loads(row['ingredients'])
            parts.extend([str(i) for i in ing_list])
        except:
            parts.append(str(row['ingredients']))
            
    text = " ".join(parts).lower()
    import re
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def evaluate_retrieval(model, embeddings_matrix, query_texts, target_indices, k_values=[5, 10], normalize=True):
    """
    Evaluates semantic retrieval using 'Exact Name' as the query proxy.
    """
    q_vecs = model.encode(query_texts, convert_to_numpy=True, normalize_embeddings=normalize)
    scores = cosine_similarity(q_vecs, embeddings_matrix)
    
    metrics = {f"HitRate@{k}": 0.0 for k in k_values}
    for i, target_idx in enumerate(target_indices):
        top_indices = scores[i].argsort()[::-1]
        for k in k_values:
            if target_idx in top_indices[:k]:
                metrics[f"HitRate@{k}"] += 1
                
    for k in k_values:
        metrics[f"HitRate@{k}"] /= len(query_texts)
    return metrics

def run_semantic_pipeline():
    print("=== Phase 15: Sentence Transformer Semantic Retrieval ===")
    
    # 1. Load Pretrained Model Metadata
    registry_path = os.path.join(PRETRAINED_DIR, "pretrained_registry.json")
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Missing {registry_path}. Run Phase 14A first.")
        
    with open(registry_path, "r") as f:
        registry = json.load(f)
        
    model_name = registry["model_name"]
    cache_loc = registry["cache_location"]
    
    # 2. Load Pretrained Model (Frozen Weights)
    print(f"Loading pretrained model: {model_name}...")
    t0 = time.time()
    model = SentenceTransformer(model_name, cache_folder=cache_loc)
    load_time = time.time() - t0
    print(f"Model loaded in {load_time:.2f}s")
    
    # 3. Load Datasets
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    val_df = pd.read_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    print(f"Loaded Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # 4. Build Text Features
    train_texts = train_df.apply(build_text_feature, axis=1).tolist()
    val_texts = val_df.apply(build_text_feature, axis=1).tolist()
    test_texts = test_df.apply(build_text_feature, axis=1).tolist()
    
    # 5. Validation Configuration
    # We will test L2 Normalization True vs False
    configs = [
        {"normalize_embeddings": True},
        {"normalize_embeddings": False}
    ]
    
    val_queries = val_df['recipe_name'].str.lower().tolist()
    val_target_indices = [len(train_texts) + i for i in range(len(val_texts))]
    
    best_config = None
    best_score = -1
    val_results = []
    
    print("Running Validation Configuration...")
    for idx, config in enumerate(configs):
        norm = config["normalize_embeddings"]
        
        # We don't 'fit', we just encode.
        combined_texts = train_texts + val_texts
        t1 = time.time()
        combined_embeddings = model.encode(combined_texts, convert_to_numpy=True, normalize_embeddings=norm)
        enc_time = time.time() - t1
        
        metrics = evaluate_retrieval(model, combined_embeddings, val_queries, val_target_indices, normalize=norm)
        metrics["config_id"] = idx
        metrics["encoding_time_sec"] = enc_time
        val_results.append({
            "config": config,
            "metrics": metrics
        })
        
        print(f"  Config {idx} (Normalize={norm}):")
        print(f"    HitRate@5: {metrics['HitRate@5']:.4f} | HitRate@10: {metrics['HitRate@10']:.4f}")
        
        if metrics['HitRate@5'] > best_score:
            best_score = metrics['HitRate@5']
            best_config = config
            
    print(f"\nSelected Best Config: {best_config}")
    
    # 6. Final Test Evaluation
    norm = best_config["normalize_embeddings"]
    final_combined_texts = train_texts + test_texts
    t2 = time.time()
    final_matrix = model.encode(final_combined_texts, convert_to_numpy=True, normalize_embeddings=norm)
    test_enc_time = time.time() - t2
    
    test_queries = test_df['recipe_name'].str.lower().tolist()
    test_target_indices = [len(train_texts) + i for i in range(len(test_texts))]
    test_metrics = evaluate_retrieval(model, final_matrix, test_queries, test_target_indices, normalize=norm)
    
    print("\nFinal Test Metrics:")
    for k, v in test_metrics.items():
        print(f"  {k}: {v:.4f}")
        
    # 7. Generate Full Artifact
    all_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
    all_texts = train_texts + val_texts + test_texts
    t3 = time.time()
    production_matrix = model.encode(all_texts, convert_to_numpy=True, normalize_embeddings=norm)
    gen_time = time.time() - t3
    
    # Load TF-IDF report for comparison
    tfidf_report_path = os.path.join(REPORTS_DIR, "tfidf_evaluation_report.json")
    tfidf_metrics = {}
    if os.path.exists(tfidf_report_path):
        with open(tfidf_report_path, "r") as f:
            tfidf_report = json.load(f)
            tfidf_metrics = tfidf_report.get("evaluation", {}).get("test_metrics", {})
            
    # 8. Run Qualitative Examples
    example_queries = [
        "healthy Indian breakfast",
        "quick paneer dinner",
        "spicy South Indian vegetarian food",
        "easy chicken curry",
        "light vegetable meal"
    ]
    
    qualitative_results = {}
    for eq in example_queries:
        q_vec = model.encode([eq.lower()], convert_to_numpy=True, normalize_embeddings=norm)
        scores = cosine_similarity(q_vec, production_matrix).flatten()
        top_idx = scores.argsort()[::-1][:5]
        
        matches = []
        for i in top_idx:
            matches.append({
                "recipe_id": all_df.iloc[i]['recipe_id'],
                "recipe_name": all_df.iloc[i]['recipe_name'],
                "similarity": float(scores[i])
            })
        qualitative_results[eq] = matches

    # 9. Save Artifacts
    joblib_path = os.path.join(ARTIFACTS_DIR, "recipe_sentence_transformer_v1.joblib")
    joblib.dump({
        "embeddings": production_matrix,
        "recipe_ids": all_df['recipe_id'].tolist(),
        "recipe_sources": all_df['dataset_source'].tolist()
    }, joblib_path)
    
    metadata = {
        "model_name": "DishIQ Phase 15 Sentence Transformer Recommender",
        "pretrained_model": model_name,
        "model_type": "SentenceTransformer",
        "embedding_dimension": production_matrix.shape[1],
        "training_dataset_count": len(train_texts),
        "validation_dataset_count": len(val_texts),
        "test_dataset_count": len(test_texts),
        "total_matrix_size": production_matrix.shape[0],
        "normalization_strategy": "L2_Norm" if norm else "None",
        "feature_fields": ["recipe_name", "cuisine", "diet", "description", "ingredients"],
        "random_seed": 42,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "performance": {
            "model_load_time_sec": load_time,
            "full_corpus_generation_time_sec": gen_time
        },
        "evaluation": {
            "validation_results": val_results,
            "test_metrics": test_metrics,
            "methodology": "Exact Normalized Recipe Name Retrieval Proxy. No fine-tuning.",
            "limitations": "No legitimate user click/ground-truth labels exist.",
            "comparison_tfidf_v2_metrics": tfidf_metrics
        },
        "qualitative_test_queries": qualitative_results
    }
    
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_sentence_transformer_v1_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    report_path = os.path.join(REPORTS_DIR, "sentence_transformer_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("\nArtifacts saved successfully.")
    print(f"Matrix shape: {production_matrix.shape}")
    print(f"Report saved to: {report_path}")
    print("=== Pipeline Complete ===")

if __name__ == "__main__":
    run_semantic_pipeline()
