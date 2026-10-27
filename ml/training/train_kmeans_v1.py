import os
import json
import time
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timezone

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
PROCESSED_DIR = os.path.join(ML_DIR, "data", "processed")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
REPORTS_DIR = os.path.join(ML_DIR, "reports")

def safe_len(val):
    if pd.isna(val) or not val:
        return 0
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return len(parsed)
    except:
        pass
    return 1

def extract_ingredients_text(val):
    if pd.isna(val) or not val:
        return ""
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return " ".join([str(x) for x in parsed])
    except:
        pass
    return str(val)

def generate_cluster_descriptions(df, cluster_labels, k, tfidf_vectorizer, X_tfidf):
    descriptions = {}
    feature_names = tfidf_vectorizer.get_feature_names_out()
    
    for cluster_id in range(k):
        mask = (cluster_labels == cluster_id)
        cluster_df = df[mask]
        
        count = len(cluster_df)
        pct = (count / len(df)) * 100
        
        avg_time = cluster_df['cooking_time'].mean()
        avg_ing_count = cluster_df['ingredient_count'].mean()
        
        dom_cuisine = cluster_df['cuisine'].mode()[0] if not cluster_df['cuisine'].mode().empty else "Unknown"
        dom_diet = cluster_df['diet'].mode()[0] if not cluster_df['diet'].mode().empty else "Unknown"
        
        cluster_tfidf = X_tfidf[mask].mean(axis=0)
        cluster_tfidf_array = np.array(cluster_tfidf).flatten()
        top_indices = cluster_tfidf_array.argsort()[::-1][:5]
        top_ingredients = [feature_names[i] for i in top_indices]
        
        cuisine_text = f"{dom_cuisine} " if dom_cuisine and dom_cuisine.lower() != "unknown" else ""
        diet_text = f"{dom_diet} " if dom_diet and dom_diet.lower() != "unknown" else ""
        prefix = f"{diet_text}{cuisine_text}".strip()
        if not prefix:
            prefix = "recipes"
        else:
            prefix += " recipes"
            
        desc = (
            f"Cluster {cluster_id}\n"
            f"Recipes: {count} ({pct:.1f}%)\n"
            f"Average cooking time: {avg_time:.1f} minutes\n"
            f"Average ingredient count: {avg_ing_count:.1f}\n"
            f"Common ingredients: {', '.join(top_ingredients)}\n\n"
            f"Description:\n"
            f"Statistical recipe group representing {prefix} with an average cooking time of "
            f"{avg_time:.0f} minutes and approximately {avg_ing_count:.0f} ingredients. "
            f"Common ingredient terms include {', '.join(top_ingredients)}."
        )
        descriptions[cluster_id] = {
            "count": int(count),
            "percentage": float(pct),
            "dominant_cuisine": str(dom_cuisine),
            "dominant_diet": str(dom_diet),
            "avg_cooking_time": float(avg_time),
            "avg_ingredient_count": float(avg_ing_count),
            "top_ingredients": top_ingredients,
            "text_description": desc
        }
    return descriptions

def run_kmeans_pipeline():
    print("=== Phase 17: K-Means Recipe Clustering (Robust Features) ===")
    
    dataset_path = os.path.join(PROCESSED_DIR, "cleaned_combined_dataset.csv")
    df = pd.read_csv(dataset_path)
    print(f"Loaded Dataset: {len(df)} recipes")
    
    df['cooking_time'] = pd.to_numeric(df['cooking_time'], errors='coerce').fillna(0.0)
    df['ingredient_count'] = df['ingredients'].apply(safe_len).astype(float)
    df['ingredients_text'] = df['ingredients'].apply(extract_ingredients_text).str.lower()
    
    # We apply log1p to numeric features to suppress extreme outliers (e.g. 16-day cooking times)
    df['log_cooking_time'] = np.log1p(df['cooking_time'])
    df['log_ingredient_count'] = np.log1p(df['ingredient_count'])
    
    tfidf = TfidfVectorizer(max_features=200, stop_words='english')
    print("Building Feature Matrix...")
    t0 = time.time()
    
    X_tfidf = tfidf.fit_transform(df['ingredients_text'])
    
    scaler = StandardScaler()
    X_num = scaler.fit_transform(df[['log_cooking_time', 'log_ingredient_count']])
    
    # Reduce numeric weight so culinary text dominates over structural shape,
    # preventing "Unknown" bias from overwhelming the ingredients
    X_num = X_num * 0.5 
    
    from scipy.sparse import hstack
    X_combined = hstack([X_tfidf, X_num])
    
    print(f"Feature matrix built in {time.time() - t0:.2f}s. Shape: {X_combined.shape}")
    
    k_range = range(2, 11)
    k_metrics = {}
    best_k = 2
    best_score = -1
    
    print("Evaluating K values (2 to 10)...")
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_combined)
        
        sil_score = silhouette_score(X_combined, labels)
        ch_score = calinski_harabasz_score(X_combined.toarray(), labels)
        db_score = davies_bouldin_score(X_combined.toarray(), labels)
        
        k_metrics[k] = {
            "Silhouette": float(sil_score),
            "Calinski_Harabasz": float(ch_score),
            "Davies_Bouldin": float(db_score)
        }
        print(f"  K={k} -> Silhouette: {sil_score:.4f} | CH: {ch_score:.1f} | DB: {db_score:.4f}")
        
        # In text-heavy sparse spaces, Silhouette naturally drops. We want culinary clusters, 
        # so K=2 might be structurally tight but useless (e.g., "fast vs slow").
        # If K=5 is reasonable, we will just take the highest silhouette >= 4 if possible,
        # but let's strictly follow the "highest silhouette" logic, UNLESS it's just 2.
        # Let's just track the max score.
        if sil_score > best_score:
            best_score = sil_score
            best_k = k
            
    # Force a more meaningful K if K=2 is just an artifact of the TF-IDF sparsity
    # Often K=5 or K=6 are more human-readable. Let's see what the highest score is.
    print(f"\nSelected K = {best_k} (Highest Silhouette Score: {best_score:.4f})")
    
    final_kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    final_labels = final_kmeans.fit_predict(X_combined)
    
    cluster_stats = generate_cluster_descriptions(df, final_labels, best_k, tfidf, X_tfidf)
    for cid, stats in cluster_stats.items():
        print(f"\n{stats['text_description']}")
        
    assignments_df = pd.DataFrame({
        "recipe_id": df["recipe_id"],
        "cluster_id": final_labels
    })
    assignments_csv = os.path.join(ARTIFACTS_DIR, "recipe_cluster_assignments.csv")
    assignments_df.to_csv(assignments_csv, index=False)
    
    pipeline_data = {
        "kmeans_model": final_kmeans,
        "tfidf_vectorizer": tfidf,
        "scaler": scaler,
        "cluster_stats": cluster_stats,
        "recipe_ids": df["recipe_id"].tolist(),
        "cluster_labels": final_labels.tolist()
    }
    
    joblib_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1.joblib")
    joblib.dump(pipeline_data, joblib_path)
    
    metadata = {
        "model_name": "DishIQ Phase 17 Unsupervised Recipe Clusterer",
        "model_version": "1.0.1",
        "algorithm": "KMeans",
        "selected_k": best_k,
        "feature_representation": "TF-IDF(ingredients, max 200) + LogScaled(cooking_time, ingredient_count)*0.5",
        "preprocessing": "StandardScaler for numerics, Log1p for outliers",
        "training_recipe_count": len(df),
        "random_seed": 42,
        "metrics_evaluated": k_metrics,
        "final_metrics": k_metrics[best_k],
        "cluster_summaries": cluster_stats,
        "limitations": (
            "K-Means is unsupervised; no classification accuracy is reported. "
            "Numeric outliers heavily skewed early testing, so log transforms were applied. "
            "Clusters represent statistical groupings of ingredients."
        )
    }
    
    meta_path = os.path.join(ARTIFACTS_DIR, "recipe_kmeans_v1_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    report_path = os.path.join(REPORTS_DIR, "kmeans_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("\nArtifacts saved successfully.")
    print(f"Cluster assignments CSV saved: {assignments_csv}")
    print("=== Pipeline Complete ===")

if __name__ == "__main__":
    run_kmeans_pipeline()
