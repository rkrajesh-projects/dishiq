from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.grocery_service import GroceryService
from app.schemas.grocery import GroceryStoreRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("", response_model=PaginatedResponse[GroceryStoreRead], summary="List Demonstration Grocery Stores")
def get_stores(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db),
):
    service = GroceryService(db)
    return service.list_stores(page=page, page_size=page_size)
