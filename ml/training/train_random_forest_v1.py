import os
import json
import time
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timezone

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import sklearn

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
SPLITS_DIR = os.path.join(ML_DIR, "data", "splits")
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

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract structural numeric and categorical features."""
    df_feat = pd.DataFrame()
    
    # Numeric
    df_feat['cooking_time'] = pd.to_numeric(df['cooking_time'], errors='coerce').fillna(0.0)
    df_feat['ingredient_count'] = df['ingredients'].apply(safe_len).astype(float)
    df_feat['instruction_count'] = df['instructions'].apply(safe_len).astype(float)
    
    # Categorical
    df_feat['cuisine'] = df['cuisine'].fillna("Unknown").astype(str)
    df_feat['diet'] = df['diet'].fillna("Unknown").astype(str)
    
    # Target
    if 'rating' in df.columns:
        df_feat['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(4.5)
        
    return df_feat

def run_rf_pipeline():
    print("=== Phase 16: Random Forest Recipe Suitability (Rating Prediction) ===")
    
    # 1. Load Datasets
    train_df = pd.read_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"))
    val_df = pd.read_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"))
    test_df = pd.read_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"))
    
    print(f"Loaded Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # 2. Extract Features
    X_train = extract_features(train_df)
    y_train = X_train.pop('rating').values
    
    X_val = extract_features(val_df)
    y_val = X_val.pop('rating').values
    
    X_test = extract_features(test_df)
    y_test = X_test.pop('rating').values
    
    # 3. Define Preprocessing Pipeline
    numeric_features = ['cooking_time', 'ingredient_count', 'instruction_count']
    categorical_features = ['cuisine', 'diet']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ]
    )
    
    # 4. Validation Configurations (Hyperparameter Search)
    configs = [
        {"n_estimators": 50, "max_depth": 5, "min_samples_split": 5},
        {"n_estimators": 100, "max_depth": 10, "min_samples_split": 5},
        {"n_estimators": 150, "max_depth": 15, "min_samples_split": 10},
    ]
    
    best_config = None
    best_score = float('inf') # We want to minimize RMSE
    val_results = []
    
    print("Running Validation Grid Search...")
    for idx, config in enumerate(configs):
        t0 = time.time()
        
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('model', RandomForestRegressor(
                n_estimators=config["n_estimators"],
                max_depth=config["max_depth"],
                min_samples_split=config["min_samples_split"],
                random_state=42,
                n_jobs=-1
            ))
        ])
        
        # Train
        pipeline.fit(X_train, y_train)
        
        # Predict on Validation
        y_val_pred = pipeline.predict(X_val)
        
        # Evaluate
        mae = mean_absolute_error(y_val, y_val_pred)
        rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
        r2 = r2_score(y_val, y_val_pred)
        
        runtime = time.time() - t0
        val_results.append({
            "config": config,
            "metrics": {"MAE": mae, "RMSE": rmse, "R2": r2},
            "runtime_sec": runtime
        })
        
        print(f"  Config {idx} {config}:")
        print(f"    RMSE: {rmse:.4f} | MAE: {mae:.4f} | R2: {r2:.4f}")
        
        if rmse < best_score:
            best_score = rmse
            best_config = config
            
    print(f"\nSelected Best Config: {best_config}")
    
    # 5. Final Test Evaluation
    final_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', RandomForestRegressor(
            n_estimators=best_config["n_estimators"],
            max_depth=best_config["max_depth"],
            min_samples_split=best_config["min_samples_split"],
            random_state=42,
            n_jobs=-1
        ))
    ])
    
    final_pipeline.fit(X_train, y_train)
    
    y_test_pred = final_pipeline.predict(X_test)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    test_r2 = r2_score(y_test, y_test_pred)
    
    print("\nFinal Test Metrics:")
    print(f"  RMSE: {test_rmse:.4f}")
    print(f"  MAE: {test_mae:.4f}")
    print(f"  R2: {test_r2:.4f}")
    
    # 6. Feature Importances
    model = final_pipeline.named_steps['model']
    preproc = final_pipeline.named_steps['preprocessor']
    
    # Get feature names after one-hot encoding
    cat_encoder = preproc.named_transformers_['cat']
    cat_features = cat_encoder.get_feature_names_out(categorical_features).tolist()
    all_features = numeric_features + cat_features
    
    importances = model.feature_importances_
    feature_importance_dict = {feat: float(imp) for feat, imp in zip(all_features, importances)}
    
    # Sort for JSON
    feature_importance_dict = dict(sorted(feature_importance_dict.items(), key=lambda item: item[1], reverse=True))
    
    with open(os.path.join(REPORTS_DIR, "random_forest_feature_importance.json"), "w") as f:
        json.dump(feature_importance_dict, f, indent=2)
        
    # 7. Save Artifacts
    joblib_path = os.path.join(ARTIFACTS_DIR, "random_forest_suitability_v1.joblib")
    joblib.dump(final_pipeline, joblib_path)
    
    metadata = {
        "model_name": "DishIQ Phase 16 Random Forest Suitability",
        "model_type": "RandomForestRegressor",
        "task_type": "Regression",
        "target": "Recipe Rating (Used as Proxy for Suitability/Quality)",
        "target_source": "Phase 14A dataset 'rating' column",
        "features": numeric_features + categorical_features,
        "preprocessing": "StandardScaler for numeric, OneHotEncoder for categorical",
        "training_dataset_count": len(X_train),
        "validation_dataset_count": len(X_val),
        "test_dataset_count": len(X_test),
        "hyperparameters": best_config,
        "random_seed": 42,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "evaluation": {
            "validation_results": val_results,
            "test_metrics": {
                "MAE": test_mae,
                "RMSE": test_rmse,
                "R2": test_r2
            },
            "limitations": "Rating predictability from basic structural features is naturally low (low R2). Target is a proxy since no direct user personalization feedback exists."
        }
    }
    
    meta_path = os.path.join(ARTIFACTS_DIR, "random_forest_suitability_v1_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    report_path = os.path.join(REPORTS_DIR, "random_forest_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("\nArtifacts saved successfully.")
    print(f"Report saved to: {report_path}")
    print("=== Pipeline Complete ===")

if __name__ == "__main__":
    run_rf_pipeline()
