"""
DishIQ ML — Shared Feature Extraction
Extracts structured numeric/categorical features from recipe DB records.
Used by both the Random Forest suitability model and the K-Means clustering model.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session


CUISINE_LIST = [
    "Indian", "South Indian", "Italian", "Mexican", "Asian",
    "Mediterranean", "Continental", "Unknown"
]

DIETARY_LIST = [
    "Vegetarian", "Vegan", "Non-Vegetarian", "Standard"
]


def extract_recipe_features_from_db(db: Session) -> pd.DataFrame:
    """
    Query all recipes from the database and build a feature DataFrame.

    Columns returned:
        recipe_id, name, cuisine, dietary_type,
        prep_time, cook_time, total_time, servings,
        ingredient_count, avg_rating,
        is_vegetarian, is_vegan, is_non_vegetarian, is_standard,
        cuisine_encoded
    """
    from app.models.recipe import Recipe, RecipeIngredient
    from sqlalchemy import func

    # Base recipe info
    recipes = db.query(Recipe).all()

    # Ingredient count per recipe
    ing_counts = dict(
        db.query(RecipeIngredient.recipe_id, func.count(RecipeIngredient.id))
        .group_by(RecipeIngredient.recipe_id)
        .all()
    )

    rows = []
    for r in recipes:
        total_time = (r.preparation_minutes or 0) + (r.cooking_minutes or 0)
        diet = (r.dietary_type or "Standard").strip()
        cuisine = (r.cuisine or "Unknown").strip()

        rows.append({
            "recipe_id": r.id,
            "name": r.name,
            "cuisine": cuisine,
            "dietary_type": diet,
            "prep_time": r.preparation_minutes or 0,
            "cook_time": r.cooking_minutes or 0,
            "total_time": total_time,
            "servings": r.servings or 4,
            "ingredient_count": ing_counts.get(r.id, 0),
            "avg_rating": r.average_rating or 4.5,
            "is_vegetarian": int(diet == "Vegetarian"),
            "is_vegan": int(diet == "Vegan"),
            "is_non_vegetarian": int(diet == "Non-Vegetarian"),
            "is_standard": int(diet == "Standard"),
            "cuisine_encoded": CUISINE_LIST.index(cuisine) if cuisine in CUISINE_LIST else len(CUISINE_LIST),
        })

    df = pd.DataFrame(rows)
    return df


def get_clustering_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    Returns the numeric feature matrix used for K-Means clustering.
    Features: prep_time, cook_time, total_time, servings, ingredient_count, avg_rating
    """
    cols = ["prep_time", "cook_time", "total_time", "servings", "ingredient_count", "avg_rating"]
    return df[cols].fillna(0).values.astype(np.float32)


def get_suitability_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    Returns the feature matrix used for Random Forest suitability prediction.
    """
    cols = [
        "prep_time", "cook_time", "total_time", "servings",
        "ingredient_count", "avg_rating",
        "is_vegetarian", "is_vegan", "is_non_vegetarian", "is_standard",
        "cuisine_encoded"
    ]
    return df[cols].fillna(0).values.astype(np.float32)


SUITABILITY_FEATURE_NAMES = [
    "prep_time", "cook_time", "total_time", "servings",
    "ingredient_count", "avg_rating",
    "is_vegetarian", "is_vegan", "is_non_vegetarian", "is_standard",
    "cuisine_encoded"
]

CLUSTERING_FEATURE_NAMES = [
    "prep_time", "cook_time", "total_time", "servings", "ingredient_count", "avg_rating"
]
