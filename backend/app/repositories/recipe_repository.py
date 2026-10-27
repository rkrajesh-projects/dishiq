from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.recipe import Recipe


class RecipeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, recipe_id: str) -> Optional[Recipe]:
        return self.db.query(Recipe).filter(Recipe.id == recipe_id).first()

    def get_by_exact_name(self, name: str) -> Optional[Recipe]:
        return self.db.query(Recipe).filter(func.lower(Recipe.name) == name.lower()).first()

    def get_list(

        self,
        cuisine: Optional[str] = None,
        dietary_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Recipe], int]:
        query = self.db.query(Recipe)
        
        if cuisine:
            clean_c = cuisine.strip().lower()
            base_c = clean_c[:-8].strip() if clean_c.endswith(" recipes") else clean_c
            query = query.filter(
                func.lower(Recipe.cuisine).in_([clean_c, base_c, f"{base_c} recipes"])
            )
        if dietary_type:
            query = query.filter(func.lower(Recipe.dietary_type) == dietary_type.lower())

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(Recipe.name.asc()).offset(offset).limit(page_size).all()
        
        return items, total
