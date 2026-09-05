import os
import time
import joblib
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity

from app.models.recipe import Recipe
from app.core.config import settings
from app.core.recommendation_config import RecommendationSettings, recommendation_settings
from app.core.logging import logger
from ml.utils.feature_engineering import normalize_text


class RecommendationService:
    _model_cache = None

    def __init__(self, db: Session, config: Optional[RecommendationSettings] = None):
        self.db = db
        self.config = config or recommendation_settings
        self._ensure_model_loaded()

    @classmethod
    def _ensure_model_loaded(cls):
        if cls._model_cache is not None:
            return

        artifact_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "artifacts", "recipe_tfidf.joblib")
        )
        
        if os.path.exists(artifact_path):
            try:
                start_t = time.time()
                cls._model_cache = joblib.load(artifact_path)
                load_ms = round((time.time() - start_t) * 1000, 2)
                
                feature_count = cls._model_cache["tfidf_matrix"].shape[1]
                recipe_count = len(cls._model_cache["recipe_ids"])

                logger.info(
                    f"ML Recommender Model loaded successfully ({recipe_count} recipes, {feature_count} features in {load_ms}ms)",
                    extra={
                        "artifact_path": artifact_path,
                        "feature_count": feature_count,
                        "recipe_count": recipe_count,
                        "load_duration_ms": load_ms,
                    }
                )
                return
            except Exception as e:
                logger.error(f"Failed to load ML model artifact from {artifact_path}: {e}")

        cls._model_cache = None

    def get_recommendations(
        self,
        query: Optional[str] = None,
        dietary_type: Optional[str] = None,
        max_time: Optional[int] = None,
        pantry_ingredients: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        start_time = time.time()

        query_recipes = self.db.query(Recipe).all()
        candidate_count = len(query_recipes)

        if candidate_count == 0:
            return []

        pantry_set = {ing.lower().strip() for ing in (pantry_ingredients or []) if ing and ing.strip()}

        results = []

        # Vector similarity scoring if model is cached
        vectorizer = self._model_cache["vectorizer"] if self._model_cache else None
        tfidf_matrix = self._model_cache["tfidf_matrix"] if self._model_cache else None
        recipe_ids = self._model_cache["recipe_ids"] if self._model_cache else []

        query_vector = None
        if vectorizer and query and query.strip():
            norm_q = normalize_text(query)
            query_vector = vectorizer.transform([norm_q])

        cfg = self.config

        for recipe in query_recipes:
            explanations: List[str] = []
            score = cfg.base_score

            # 1. Dietary Filtering & Weight Boost
            if dietary_type and dietary_type.lower() != "none":
                if recipe.dietary_type.lower() != dietary_type.lower():
                    continue
                else:
                    score += cfg.dietary_match_weight
                    explanations.append(f"Matches your {recipe.dietary_type} preference")

            # 2. Cooking Time Penalty / Compatibility
            total_time = recipe.preparation_minutes + recipe.cooking_minutes
            if max_time is not None:
                if total_time > max_time:
                    continue
                else:
                    score += cfg.cooking_time_weight
                    explanations.append(f"Ready within your {max_time} min time limit ({total_time} mins)")
            else:
                explanations.append(f"Quick {total_time} min total time")

            # 3. TF-IDF Text Similarity Score
            if query_vector is not None and tfidf_matrix is not None and recipe.id in recipe_ids:
                idx = recipe_ids.index(recipe.id)
                text_sim = float(cosine_similarity(query_vector, tfidf_matrix[idx:idx+1])[0][0])
                score += text_sim * cfg.cosine_similarity_weight
                if text_sim > 0.3:
                    explanations.append("High query relevance match")

            # 4. Ingredient Overlap Boost
            rec_ingredients = {ri.ingredient.canonical_name.lower() for ri in recipe.ingredients}
            matching_pantry = rec_ingredients.intersection(pantry_set)
            if matching_pantry:
                match_count = len(matching_pantry)
                score += match_count * cfg.ingredient_overlap_weight
                explanations.append(f"{match_count} ingredient(s) already in your pantry")

            # 5. Average Rating Boost
            rating = recipe.average_rating or 4.5
            score += (rating / 5.0) * cfg.rating_weight
            explanations.append(f"Highly rated ({rating:.1f} ★)")

            results.append({
                "recipe": recipe,
                "score": round(score, 3),
                "explanations": list(dict.fromkeys(explanations)),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        final_recommendations = results[:limit]

        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            f"Recommendation query completed: evaluated {candidate_count} recipes, returned {len(final_recommendations)} results in {duration_ms}ms",
            extra={
                "search_query": query,
                "dietary_type": dietary_type,
                "max_time": max_time,
                "candidates_evaluated": candidate_count,
                "recommendations_returned": len(final_recommendations),
                "duration_ms": duration_ms,
            }
        )

        return final_recommendations
