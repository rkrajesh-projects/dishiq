from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.grocery import GroceryStore, GroceryProduct


class GroceryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_stores(self, page: int = 1, page_size: int = 10) -> Tuple[List[GroceryStore], int]:
        query = self.db.query(GroceryStore)
        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(GroceryStore.name.asc()).offset(offset).limit(page_size).all()
        return items, total

    def get_products(
        self,
        store_id: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[GroceryProduct], int]:
        query = self.db.query(GroceryProduct)
        
        if store_id:
            query = query.filter(GroceryProduct.store_id == store_id)
        if category:
            query = query.filter(func.lower(GroceryProduct.category) == category.lower())

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(GroceryProduct.name.asc()).offset(offset).limit(page_size).all()
        
        return items, total

    def get_all_products(self) -> List[GroceryProduct]:
        """Retrieve all in-stock grocery products for matching."""
        return self.db.query(GroceryProduct).filter(GroceryProduct.in_stock == True).all()
