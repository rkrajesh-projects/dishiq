import os
import sys
import json
import joblib
import sklearn
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.utils.feature_engineering import create_recipe_feature_document
from backend.app.db.seed import RECIPE_SEED_DATA


def get_training_recipes():
    try:
        from backend.app.db.session import SessionLocal
        from backend.app.models.recipe import Recipe
        
        db = SessionLocal()
        db_recipes = db.query(Recipe).all()
        
        if db_recipes:
            recipes_data = []
            for r in db_recipes:
                ing_list = [ri.ingredient.canonical_name for ri in r.ingredients]
                recipes_data.append({
                    "id": r.id,
                    "name": r.name,
                    "cuisine": r.cuisine,
                    "dietary_type": r.dietary_type,
                    "description": r.description,
                    "preparation_minutes": r.preparation_minutes,
                    "cooking_minutes": r.cooking_minutes,
                    "average_rating": r.average_rating,
                    "ingredients": ing_list,
                })
            db.close()
            return recipes_data
    except Exception as e:
        print(f"Database fetch skipped, using seed dataset fallback: {e}")

    recipes_data = []
    for idx, r in enumerate(RECIPE_SEED_DATA):
        ing_list = [i["canonical"] for i in r["ingredients"]]
        recipes_data.append({
            "id": f"rec_{idx + 1}",
            "name": r["name"],
            "cuisine": r["cuisine"],
            "dietary_type": r["dietary_type"],
            "description": r["description"],
            "preparation_minutes": r["preparation_minutes"],
            "cooking_minutes": r["cooking_minutes"],
            "average_rating": 4.7,
            "ingredients": ing_list,
        })
    return recipes_data


def train_recommender():
    print("=== Training DishIQ TF-IDF Recipe Recommender Model ===")
    recipes = get_training_recipes()
    print(f"Loaded {len(recipes)} recipes for training.")

    documents = [create_recipe_feature_document(r) for r in recipes]
    recipe_ids = [r["id"] for r in recipes]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", max_features=500)
    tfidf_matrix = vectorizer.fit_transform(documents)

    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "artifacts"))
    os.makedirs(artifacts_dir, exist_ok=True)

    joblib_filename = "recipe_tfidf.joblib"
    joblib_path = os.path.join(artifacts_dir, joblib_filename)
    joblib.dump({
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "recipe_ids": recipe_ids,
        "recipes": recipes,
    }, joblib_path)

    metadata = {
        "model_name": "DishIQ Recipe TF-IDF Recommender",
        "model_version": "1.1.0",
        "algorithm": "TF-IDF + Cosine Similarity",
        "algorithm_type": "Classical NLP / Information Retrieval (NOT a neural network)",
        "feature_count": int(tfidf_matrix.shape[1]),
        "ngram_range": [1, 2],
        "stop_words": "english",
        "max_features": 500,
        "dataset_version": "1.0.0",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "artifact_filename": joblib_filename,
        "total_recipes": len(recipes),
        "artifact_path": joblib_path,
    }

    metadata_path = os.path.join(artifacts_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Companion metadata for TFIDFRecommender model class
    companion_path = os.path.join(artifacts_dir, "recipe_tfidf_metadata.json")
    with open(companion_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model successfully saved to {joblib_path}")
    print(f"Metadata saved to {metadata_path}")
    print(f"Total recipes: {len(recipes)} | Features: {tfidf_matrix.shape[1]}")


if __name__ == "__main__":
    train_recommender()
