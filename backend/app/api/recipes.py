import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.recipe_service import RecipeService
from app.services.recommendation_service import RecommendationService
from app.schemas.recipe import RecipeRead, RecipeDetailRead
from app.schemas.recommendation import RecommendedRecipeRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/recipes", tags=["Recipes"])


def sanitize_input(value: Optional[str], max_length: int = 250) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Query parameter exceeds maximum length of {max_length} characters."
        )
    return cleaned


@router.get("", response_model=PaginatedResponse[RecipeRead], summary="List Recipes with Pagination & Filtering")
def get_recipes(
    cuisine: Optional[str] = Query(None, description="Filter recipes by cuisine"),
    dietary_type: Optional[str] = Query(None, description="Filter recipes by dietary type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db),
):
    clean_cuisine = sanitize_input(cuisine)
    clean_diet = sanitize_input(dietary_type)
    service = RecipeService(db)
    return service.list_recipes(cuisine=clean_cuisine, dietary_type=clean_diet, page=page, page_size=page_size)


@router.get("/search", response_model=PaginatedResponse[RecommendedRecipeRead], summary="Search & Rank Recipes")
def search_recipes(
    q: Optional[str] = Query(None, description="Search text query"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine"),
    dietary_type: Optional[str] = Query(None, description="Filter by dietary restriction"),
    max_time: Optional[int] = Query(None, ge=1, le=1440, description="Maximum prep + cook time in minutes"),
    ingredient: Optional[str] = Query(None, description="Filter by required ingredient"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db),
):
    clean_q = sanitize_input(q)
    clean_cuisine = sanitize_input(cuisine)
    clean_diet = sanitize_input(dietary_type)
    clean_ingredient = sanitize_input(ingredient)

    rec_service = RecommendationService(db)
    pantry_list = [clean_ingredient] if clean_ingredient else None

    ranked = rec_service.get_recommendations(
        query=clean_q,
        dietary_type=clean_diet,
        max_time=max_time,
        pantry_ingredients=pantry_list,
        limit=100,
    )

    if clean_cuisine:
        ranked = [item for item in ranked if item["recipe"].cuisine.lower() == clean_cuisine.lower()]

    total = len(ranked)
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    paged_items = ranked[offset : offset + page_size]

    recommended_reads = []
    for item in paged_items:
        recipe_obj = item["recipe"]
        base_read = RecipeRead.model_validate(recipe_obj)
        recommended_reads.append(
            RecommendedRecipeRead(
                **base_read.model_dump(),
                score=item["score"],
                explanations=item["explanations"],
            )
        )

    return PaginatedResponse[RecommendedRecipeRead](
        items=recommended_reads,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{recipe_id}", response_model=RecipeDetailRead, summary="Get Recipe Details")
def get_recipe_by_id(recipe_id: str, db: Session = Depends(get_db)):
    clean_id = sanitize_input(recipe_id)
    if not clean_id:
        raise HTTPException(status_code=400, detail="Invalid recipe ID")
    service = RecipeService(db)
    return service.get_recipe_by_id(clean_id)


from app.api.pantry import get_current_user
from app.models.pantry import RecipeFeedback
from app.schemas.feedback import RecipeFeedbackCreate, RecipeFeedbackRead

@router.post("/{recipe_id}/feedback", response_model=RecipeFeedbackRead, status_code=status.HTTP_201_CREATED, summary="Submit Recipe Feedback")
def submit_recipe_feedback(
    recipe_id: str,
    body: RecipeFeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    Submit rating and difficulty feedback for a recipe.
    Associates feedback with the current user and verifies recipe exists.
    Prevents duplicate feedback submissions by the same user.
    """
    user = get_current_user(db)
    
    clean_recipe_id = sanitize_input(recipe_id)
    if not clean_recipe_id:
        raise HTTPException(status_code=400, detail="Invalid recipe ID")

    # 1. Verify recipe exists
    service = RecipeService(db)
    recipe = service.get_recipe_by_id(clean_recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    # 2. Check for duplicate feedback
    existing = db.query(RecipeFeedback).filter_by(user_id=user.id, recipe_id=clean_recipe_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback already submitted for this recipe."
        )
        
    # 3. Create feedback record
    feedback = RecipeFeedback(
        user_id=user.id,
        recipe_id=clean_recipe_id,
        rating=body.rating,
        difficulty=body.difficulty,
        notes=body.notes
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
