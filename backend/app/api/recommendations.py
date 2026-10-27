"""
DishIQ API — Recommendations + ML Endpoints

Existing endpoints (UNCHANGED):
  POST /api/recommendations/recipes   — multi-factor recommendation

New ML endpoints (ADDED):
  POST /api/ml/suitability            — RF suitability score for a recipe
  GET  /api/ml/clusters               — all K-Means clusters
  GET  /api/ml/similar-recipes/{id}   — recipes in same cluster
  GET  /api/ml/model-info             — metadata for all loaded models
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse, RecommendedRecipeRead
from app.schemas.recipe import RecipeRead

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
ml_router = APIRouter(prefix="/ml", tags=["ML"])


# ──────────────────────────────────────────────────────────────────
# EXISTING ENDPOINT — unchanged
# ──────────────────────────────────────────────────────────────────
@router.post(
    "/recipes",
    response_model=RecommendationResponse,
    summary="Get Multi-Factor AI Recipe Recommendations",
    description=(
        "Calculates TF-IDF cosine similarity, ingredient overlap, dietary filters, "
        "rating boosts, and Random Forest suitability to recommend dishes."
    ),
)
def get_recipe_recommendations(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
):
    service = RecommendationService(db)
    ranked_results = service.get_recommendations(
        query=payload.query,
        dietary_type=payload.dietary_type,
        max_time=payload.max_time,
        pantry_ingredients=payload.pantry_ingredients,
        limit=payload.limit,
    )

    recommended_reads = []
    for item in ranked_results:
        recipe_obj = item["recipe"]
        base_read = RecipeRead.model_validate(recipe_obj)
        recommended_reads.append(
            RecommendedRecipeRead(
                **base_read.model_dump(),
                score=item.get("score", 0.0),
                explanations=item.get("explanations", []),
                tfidf_score=item.get("tfidf_score"),
                semantic_score=item.get("semantic_score"),
                suitability_score=item.get("suitability_score"),
                cluster_id=item.get("cluster_id"),
                hybrid_score=item.get("hybrid_score"),
            )
        )

    return RecommendationResponse(
        recommendations=recommended_reads,
        total=len(recommended_reads),
    )


# ──────────────────────────────────────────────────────────────────
# NEW ML ENDPOINTS
# ──────────────────────────────────────────────────────────────────

class SuitabilityRequest(BaseModel):
    recipe_id: str
    prep_time: int = 0
    cook_time: int = 0
    servings: int = 4
    ingredient_count: int = 5
    avg_rating: float = 4.5
    dietary_type: str = "Vegetarian"
    cuisine: str = "Indian"


class SuitabilityResponse(BaseModel):
    recipe_id: str
    suitability_score: float
    model: str
    note: str


@ml_router.post(
    "/suitability",
    response_model=SuitabilityResponse,
    summary="Predict Recipe Suitability Score",
    description=(
        "Uses the trained RandomForestRegressor to predict a general suitability/quality score "
        "[1.0–5.0] for a recipe based on its structural features. "
        "Score is NOT user-personalized — it reflects general recipe quality patterns. "
        "Returns 3.0 (neutral fallback) if model artifact is unavailable."
    ),
)
def predict_suitability(payload: SuitabilityRequest):
    import numpy as np
    from app.services.ml_service import get_ml_service

    CUISINE_LIST = ["Indian", "South Indian", "Italian", "Mexican", "Asian",
                    "Mediterranean", "Continental", "Unknown"]
    diet = payload.dietary_type.strip()
    cuisine = payload.cuisine.strip()
    total_time = payload.prep_time + payload.cook_time

    feature_vector = np.array([
        payload.prep_time,
        payload.cook_time,
        total_time,
        payload.servings,
        payload.ingredient_count,
        payload.avg_rating,
        int(diet == "Vegetarian"),
        int(diet == "Vegan"),
        int(diet == "Non-Vegetarian"),
        int(diet == "Standard"),
        CUISINE_LIST.index(cuisine) if cuisine in CUISINE_LIST else len(CUISINE_LIST),
    ], dtype=np.float32)

    ml = get_ml_service()
    score = ml.predict_suitability(feature_vector)

    return SuitabilityResponse(
        recipe_id=payload.recipe_id,
        suitability_score=score,
        model="RandomForestRegressor",
        note=(
            "General recipe quality score based on structural features. "
            "Not user-personalized. Returns 3.0 (neutral) if model unavailable."
        ),
    )


class ClusterInfo(BaseModel):
    cluster_id: int
    description: str
    recipe_count: int


class ClustersResponse(BaseModel):
    clusters: List[ClusterInfo]
    model: str
    algorithm: str
    silhouette_score: Optional[float] = None


@ml_router.get(
    "/clusters",
    response_model=ClustersResponse,
    summary="Get All Recipe Clusters",
    description="Returns K-Means discovered recipe clusters with auto-generated descriptions.",
)
def get_clusters():
    import json, os
    from app.services.ml_service import get_ml_service

    ml = get_ml_service()
    clusters_raw = ml.get_all_clusters()

    clusters = [
        ClusterInfo(
            cluster_id=c["cluster_id"],
            description=c["description"],
            recipe_count=c["recipe_count"],
        )
        for c in clusters_raw
    ]

    silhouette = None
    meta_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "artifacts", "clustering_metadata.json")
    )
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        silhouette = meta.get("best_silhouette_score")

    return ClustersResponse(
        clusters=clusters,
        model="K-Means",
        algorithm="Unsupervised ML — K-Means Clustering",
        silhouette_score=silhouette,
    )


class SimilarRecipesResponse(BaseModel):
    recipe_id: str
    cluster_id: Optional[int]
    cluster_description: str
    similar_recipe_ids: List[str]
    model: str


@ml_router.get(
    "/similar-recipes/{recipe_id}",
    response_model=SimilarRecipesResponse,
    summary="Get Similar Recipes by Cluster",
    description="Returns recipes in the same K-Means cluster as the given recipe.",
)
def get_similar_recipes(recipe_id: str, limit: int = 10):
    from app.services.ml_service import get_ml_service

    ml = get_ml_service()
    cluster_id = ml.get_recipe_cluster(recipe_id)
    description = ml.get_cluster_description(cluster_id) if cluster_id is not None else ""
    similar_ids = ml.get_similar_recipe_ids(recipe_id, limit=limit)

    return SimilarRecipesResponse(
        recipe_id=recipe_id,
        cluster_id=cluster_id,
        cluster_description=description,
        similar_recipe_ids=similar_ids,
        model="K-Means Clustering",
    )


@ml_router.get(
    "/model-info",
    summary="Get ML Model Metadata",
    description="Returns metadata for all loaded ML models: TF-IDF, RF, K-Means, SentenceTransformer.",
)
def get_model_info():
    from app.services.ml_service import get_ml_service
    ml = get_ml_service()
    return ml.get_model_info()

from fastapi import BackgroundTasks

@ml_router.post(
    "/retrain",
    summary="Trigger Automated ML Retraining",
    description="Fetches all recipes from the DB and retrains TF-IDF, Semantic, RF, and K-Means models in the background."
)
def trigger_retrain(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from app.services.retrain_service import run_retrain_pipeline
    
    # We must not pass the request-scoped DB session to the background task because it closes after the response.
    # We will instantiate a new session inside the task wrapper.
    def bg_task():
        from app.db.session import SessionLocal
        bg_db = SessionLocal()
        try:
            run_retrain_pipeline(bg_db)
        finally:
            bg_db.close()
            
    background_tasks.add_task(bg_task)
    return {"message": "ML Retraining Pipeline triggered in background."}
