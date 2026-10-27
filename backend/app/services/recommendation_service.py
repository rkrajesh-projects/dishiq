import os
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.recipe import Recipe
from app.core.config import settings
from app.core.recommendation_config import RecommendationSettings, recommendation_settings
from app.core.logging import logger
from app.services.ml_service import MLService


class RecommendationService:
    def __init__(self, db: Session, config: Optional[RecommendationSettings] = None):
        self.db = db
        self.config = config or recommendation_settings
        # Trigger initialization of ml_service on startup
        MLService.get_instance()

    def get_recommendations(
        self,
        query: Optional[str] = None,
        dietary_type: Optional[str] = None,
        max_time: Optional[int] = None,
        pantry_ingredients: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        start_time = time.time()
        ml_svc = MLService.get_instance()

        all_recipes = self.db.query(Recipe).all()
        if not all_recipes:
            return []
            
        # 1. Hard Filtering
        valid_recipes = {}
        for recipe in all_recipes:
            if dietary_type and dietary_type.lower() != "none":
                r_diet = recipe.dietary_type or ""
                if r_diet.lower() != dietary_type.lower():
                    continue
                    
            if max_time is not None:
                total_time = (recipe.preparation_minutes or 0) + (recipe.cooking_minutes or 0)
                if total_time > max_time:
                    continue
                    
            valid_recipes[str(recipe.id)] = recipe

        if not valid_recipes:
            return []

        results = []
        pantry_set = {ing.lower().strip() for ing in (pantry_ingredients or []) if ing and ing.strip()}
        
        # 2. ML Candidate Retrieval
        ml_candidates = {}
        if query and query.strip():
            # Get an appropriately sized pool from hybrid recommender to rank relevant candidates
            hybrid_results = ml_svc.hybrid_query(query.strip(), top_k=250)
            for res in hybrid_results:
                ml_candidates[str(res["recipe_id"])] = res

        cfg = self.config

        for rid, recipe in valid_recipes.items():
            explanations = []
            score = cfg.base_score
            
            ml_stats = ml_candidates.get(rid, {})
            
            matches_text = False
            if query and query.strip():
                q = query.lower().strip()
                name_match = q in (recipe.name or "").lower()
                desc_match = q in (recipe.description or "").lower()
                ing_match = any(
                    q in ri.ingredient.canonical_name.lower()
                    for ri in recipe.ingredients
                    if ri.ingredient and ri.ingredient.canonical_name
                )
                matches_text = name_match or desc_match or ing_match

            # If query provided but recipe wasn't ranked by ML and didn't match text/ingredients, skip it
            if query and query.strip() and not ml_stats and not matches_text:
                continue

            if dietary_type and dietary_type.lower() != "none":
                score += cfg.dietary_match_weight
                explanations.append(f"Matches your {recipe.dietary_type} preference")

            total_time = (recipe.preparation_minutes or 0) + (recipe.cooking_minutes or 0)
            if max_time is not None:
                score += cfg.cooking_time_weight
                explanations.append(f"Ready within your {max_time} min time limit ({total_time} mins)")
            else:
                explanations.append(f"Quick {total_time} min total time")

            rec_ingredients = {ri.ingredient.canonical_name.lower() for ri in recipe.ingredients if ri.ingredient and ri.ingredient.canonical_name}
            matching_pantry = rec_ingredients.intersection(pantry_set)
            if matching_pantry:
                match_count = len(matching_pantry)
                score += match_count * cfg.ingredient_overlap_weight
                explanations.append(f"{match_count} ingredient(s) already in your pantry")

            if ml_stats:
                hybrid_score = ml_stats.get("final_score", 0.0)
                tfidf_score = ml_stats.get("tfidf_score", 0.0)
                semantic_score = ml_stats.get("semantic_score", 0.0)
                rf_suitability = ml_stats.get("suitability_score", 0.0)
                cluster_id = ml_stats.get("cluster_id", -1)
                
                # Big boost based on ML retrieval relevance
                score += (hybrid_score * cfg.cosine_similarity_weight * 10)
                
                if semantic_score > 0.4:
                    explanations.append("High semantic ML relevance")
                elif tfidf_score > 0.3:
                    explanations.append("High text relevance")
                    
                if rf_suitability >= 4.0:
                    explanations.append(f"High generic recipe suitability ({rf_suitability:.1f}/5)")
            else:
                # No ML stats, rely on DB ratings and text match boost
                rating = recipe.average_rating or 4.5
                score += (rating / 5.0) * cfg.rating_weight
                explanations.append(f"Highly rated ({rating:.1f} ★)")
                
                if query and query.strip() and matches_text:
                    score += cfg.cosine_similarity_weight * 5.0
                    explanations.append(f"Matches search query '{query.strip()}'")
                
                rf_suitability = rating
                tfidf_score = 0.5 if matches_text else 0.0
                semantic_score = 0.5 if matches_text else 0.0
                hybrid_score = 0.5 if matches_text else 0.0
                cluster_id = -1
                
            results.append({
                "recipe": recipe,
                "score": round(score, 3),
                "explanations": list(dict.fromkeys(explanations)),
                "tfidf_score": round(tfidf_score, 3),
                "semantic_score": round(semantic_score, 3),
                "suitability_score": round(rf_suitability, 3),
                "cluster_id": cluster_id,
                "hybrid_score": round(hybrid_score, 3)
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        final_recommendations = results[:limit] if limit is not None else results

        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            f"Recommendation query completed: returned {len(final_recommendations)} results in {duration_ms}ms",
            extra={
                "search_query": query,
                "candidates_evaluated": len(all_recipes),
                "recommendations_returned": len(final_recommendations),
            }
        )

        return final_recommendations
