from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse, RecommendedRecipeRead
from app.schemas.recipe import RecipeRead

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post(
    "/recipes",
    response_model=RecommendationResponse,
    summary="Get Multi-Factor AI Recipe Recommendations",
    description="Calculates TF-IDF similarity, ingredient overlap, dietary filters, and rating boosts to recommend dishes.",
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
                score=item["score"],
                explanations=item["explanations"],
            )
        )

    return RecommendationResponse(
        recommendations=recommended_reads,
        total=len(recommended_reads),
    )
