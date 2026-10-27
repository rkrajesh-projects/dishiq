from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.recipe import RecipeRead


class RecommendationRequest(BaseModel):
    query: Optional[str] = None
    dietary_type: Optional[str] = None
    max_time: Optional[int] = None
    pantry_ingredients: Optional[List[str]] = None
    limit: int = 10


class RecommendedRecipeRead(RecipeRead):
    score: float
    explanations: List[str]
    tfidf_score: Optional[float] = None
    semantic_score: Optional[float] = None
    suitability_score: Optional[float] = None
    cluster_id: Optional[int] = None
    hybrid_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    recommendations: List[RecommendedRecipeRead]
    total: int
