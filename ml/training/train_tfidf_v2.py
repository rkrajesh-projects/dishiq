import os
import sys
import json
import time
import joblib
import pandas as pd
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timezone

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
SPLITS_DIR = os.path.join(ML_DIR, "data", "splits")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
REPORTS_DIR = os.path.join(ML_DIR, "reports")

def build_text_feature(row):
    """
    Deterministically build a single text document representing the recipe.
    Fields used: recipe_name, description, ingredients, cuisine, diet.
    """
    parts = []
    
    if pd.notna(row.get('recipe_name')) and row['recipe_name']:
        # Repeat name slightly to give it weight against a huge ingredient list
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
            
    # Normalize by converting to lower and stripping
    text = " ".join(parts).lower()
    import re
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def evaluate_retrieval(vectorizer, tfidf_matrix, query_texts, target_indices, k_values=[5, 10]):
    """
    Evaluates retrieval using 'Exact Name' as the query.
    This is a proxy evaluation since we lack ground-truth user click labels.
    """
    q_vecs = vectorizer.transform(query_texts)
    scores = cosine_similarity(q_vecs, tfidf_matrix)
    
    metrics = {f"HitRate@{k}": 0.0 for k in k_values}
    
    for i, target_idx in enumerate(target_indices):
        # Sort indices by score descending
        top_indices = scores[i].argsort()[::-1]
        
        for k in k_values:
            if target_idx in top_indices[:k]:
                metrics[f"HitRate@{k}"] += 1
                
    for k in k_values:
        metrics[f"HitRate@{k}"] /= len(query_texts)
        
    return metrics

def train_and_evaluate():
    print("=== Phase 14B: TF-IDF Content-Based Retrieval ===")
    
    # 1. Load Data
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    val_df = pd.read_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    print(f"Loaded Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # 2. Build Text Features
    train_texts = train_df.apply(build_text_feature, axis=1).tolist()
    val_texts = val_df.apply(build_text_feature, axis=1).tolist()
    test_texts = test_df.apply(build_text_feature, axis=1).tolist()
    
    # Validation Queries: Use recipe_names to see if we can retrieve them from the matrix
    # Note: We must combine Train and Val into the search index to evaluate Val properly
    # However, to STRICTLY prevent leakage in fitting, we FIT only on train_texts.
    # We will build the searchable matrix by transforming both train and val.
    
    # 3. Validation Grid Search
    configs = [
        {"ngram_range": (1, 1), "max_features": 2000, "min_df": 2, "max_df": 0.95},
        {"ngram_range": (1, 2), "max_features": 5000, "min_df": 2, "max_df": 0.95},
        {"ngram_range": (1, 2), "max_features": 10000, "min_df": 2, "max_df": 0.95},
    ]
    
    val_queries = val_df['recipe_name'].str.lower().tolist()
    val_target_indices = [len(train_texts) + i for i in range(len(val_texts))] # Indices in the combined (Train+Val) matrix
    
    best_config = None
    best_score = -1
    val_results = []
    
    print("Running Validation Grid Search...")
    for idx, config in enumerate(configs):
        t0 = time.time()
        
        vec = TfidfVectorizer(
            ngram_range=config["ngram_range"],
            max_features=config["max_features"],
            min_df=config["min_df"],
            max_df=config["max_df"],
            stop_words="english",
            sublinear_tf=True
        )
        
        # FIT ONLY ON TRAIN
        vec.fit(train_texts)
        
        # Transform Train and Val to build the searchable corpus
        combined_texts = train_texts + val_texts
        combined_matrix = vec.transform(combined_texts)
        
        # Evaluate
        metrics = evaluate_retrieval(vec, combined_matrix, val_queries, val_target_indices)
        metrics["config_id"] = idx
        metrics["runtime_sec"] = time.time() - t0
        val_results.append({
            "config": config,
            "metrics": metrics
        })
        
        print(f"  Config {idx}: {config}")
        print(f"    HitRate@5: {metrics['HitRate@5']:.4f} | HitRate@10: {metrics['HitRate@10']:.4f}")
        
        if metrics['HitRate@5'] > best_score:
            best_score = metrics['HitRate@5']
            best_config = config
            
    print(f"\nSelected Best Config: {best_config}")
    
    # 4. Final Test Evaluation
    # Re-fit vectorizer strictly on train with best config
    final_vec = TfidfVectorizer(
        ngram_range=best_config["ngram_range"],
        max_features=best_config["max_features"],
        min_df=best_config["min_df"],
        max_df=best_config["max_df"],
        stop_words="english",
        sublinear_tf=True
    )
    
    t0 = time.time()
    final_vec.fit(train_texts)
    train_time = time.time() - t0
    
    # Build final test corpus matrix (Train + Test)
    final_combined_texts = train_texts + test_texts
    final_matrix = final_vec.transform(final_combined_texts)
    
    test_queries = test_df['recipe_name'].str.lower().tolist()
    test_target_indices = [len(train_texts) + i for i in range(len(test_texts))]
    
    t1 = time.time()
    test_metrics = evaluate_retrieval(final_vec, final_matrix, test_queries, test_target_indices)
    eval_time = time.time() - t1
    
    print("\nFinal Test Metrics:")
    for k, v in test_metrics.items():
        print(f"  {k}: {v:.4f}")
        
    # 5. Save Artifacts (V2)
    # The actual production matrix should just be the Train matrix for now, 
    # but practically we would transform the entire LIVE database.
    # To keep the ML artifacts self-contained for Phase 14, we will store the Train + Val + Test combined matrix 
    # so the API can search across all known 2005 recipes using the TF-IDF vocabulary learned ONLY on Train.
    
    all_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
    all_texts = train_texts + val_texts + test_texts
    production_matrix = final_vec.transform(all_texts)
    
    joblib_path = os.path.join(ARTIFACTS_DIR, "recipe_tfidf_v2.joblib")
    joblib.dump({
        "vectorizer": final_vec,
        "tfidf_matrix": production_matrix,
        "recipe_ids": all_df['recipe_id'].tolist(),
        "recipe_sources": all_df['dataset_source'].tolist()
    }, joblib_path)
    
    metadata = {
        "model_name": "DishIQ Phase 14B TF-IDF Recommender",
        "model_version": "2.0.0",
        "algorithm": "TF-IDF + Cosine Similarity",
        "training_dataset_count": len(train_texts),
        "validation_dataset_count": len(val_texts),
        "test_dataset_count": len(test_texts),
        "total_matrix_size": production_matrix.shape[0],
        "feature_count": production_matrix.shape[1],
        "vocabulary_size": len(final_vec.vocabulary_),
        "tf_idf_parameters": best_config,
        "feature_fields": ["recipe_name", "cuisine", "diet", "description", "ingredients"],
        "random_seed": 42,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "evaluation": {
            "validation_results": val_results,
            "test_metrics": test_metrics,
            "methodology": "Proxy retrieval using exact normalized recipe names. Strict isolation of fitting on Train only.",
            "limitations": "No legitimate user click/ground-truth labels exist. Evaluation uses exact name retrieval as a proxy for structural soundness."
        }
    }
    
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_tfidf_v2_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    report_path = os.path.join(REPORTS_DIR, "tfidf_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"\nArtifacts saved successfully.")
    print(f"Matrix shape: {production_matrix.shape}")
    print(f"Metadata saved to: {meta_path}")
    print("=== Pipeline Complete ===")

if __name__ == "__main__":
    train_and_evaluate()
