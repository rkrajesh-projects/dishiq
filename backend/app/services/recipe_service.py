import math
from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import DishIQException
from app.repositories.recipe_repository import RecipeRepository
from app.schemas.recipe import RecipeRead, RecipeDetailRead
from app.schemas.pagination import PaginatedResponse


class RecipeService:
    def __init__(self, db: Session):
        self.repo = RecipeRepository(db)

    def get_recipe_by_id(self, recipe_id: str) -> RecipeDetailRead:
        recipe = self.repo.get_by_id(recipe_id)
        if not recipe:
            raise DishIQException(
                message=f"Recipe with ID '{recipe_id}' not found.",
                code="RECIPE_NOT_FOUND",
                status_code=404
            )
        return RecipeDetailRead.model_validate(recipe)

    def list_recipes(
        self,
        cuisine: Optional[str] = None,
        dietary_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedResponse[RecipeRead]:
        items, total = self.repo.get_list(
            cuisine=cuisine,
            dietary_type=dietary_type,
            page=page,
            page_size=page_size
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        recipe_reads = [RecipeRead.model_validate(item) for item in items]
        
        return PaginatedResponse[RecipeRead](
            items=recipe_reads,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
