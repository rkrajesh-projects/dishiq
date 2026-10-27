"""
DishIQ Phase 9 — Shopping Lists API Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.meal_plan_service import MealPlanService
from app.schemas.shopping_list import (
    ShoppingListRead,
    ShoppingListCreate,
    ShoppingListItemRead,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListGroceryComparisonResponse,
)

router = APIRouter(prefix="/shopping-lists", tags=["Shopping Lists"])


def _format_shopping_item(item) -> ShoppingListItemRead:
    effective_qty = (
        item.user_quantity_override
        if item.user_quantity_override is not None
        else item.quantity_to_buy
    )
    return ShoppingListItemRead(
        id=item.id,
        shopping_list_id=item.shopping_list_id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient_name,
        required_quantity=item.required_quantity,
        unit=item.unit,
        pantry_quantity=item.pantry_quantity,
        quantity_to_buy=item.quantity_to_buy,
        user_quantity_override=item.user_quantity_override,
        effective_quantity=effective_qty,
        is_obtained=bool(item.is_obtained),
        is_manual=bool(item.is_manual),
        source_recipes=item.source_recipes or [],
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _format_shopping_list(slist) -> ShoppingListRead:
    items = [_format_shopping_item(it) for it in slist.items]
    obtained = sum(1 for it in items if it.is_obtained)
    return ShoppingListRead(
        id=slist.id,
        user_id=slist.user_id,
        meal_plan_id=slist.meal_plan_id,
        name=slist.name,
        status=slist.status,
        items=items,
        total_items=len(items),
        obtained_items=obtained,
        created_at=slist.created_at,
        updated_at=slist.updated_at,
    )


@router.get("", response_model=List[ShoppingListRead], summary="List User Shopping Lists")
def list_shopping_lists(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    lists = service.list_shopping_lists(user.id)
    return [_format_shopping_list(s) for s in lists]


@router.post("", response_model=ShoppingListRead, status_code=status.HTTP_201_CREATED, summary="Create Shopping List")
def create_shopping_list(
    body: ShoppingListCreate = ShoppingListCreate(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    slist = service.create_shopping_list(user.id, body.name, body.meal_plan_id)
    return _format_shopping_list(slist)


@router.get("/{list_id}", response_model=ShoppingListRead, summary="Get Shopping List Details")
def get_shopping_list(
    list_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    slist = service.get_shopping_list(list_id, user.id)
    return _format_shopping_list(slist)


@router.post("/{list_id}/items", response_model=ShoppingListItemRead, status_code=status.HTTP_201_CREATED, summary="Add Manual Item to Shopping List")
def add_manual_item(
    list_id: str,
    body: ShoppingListItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    item = service.add_manual_item(list_id, user.id, body)
    return _format_shopping_item(item)


@router.patch("/{list_id}/items/{item_id}", response_model=ShoppingListItemRead, summary="Update Item Status or Override")
def update_shopping_list_item(
    list_id: str,
    item_id: str,
    body: ShoppingListItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    item = service.update_shopping_list_item(list_id, item_id, user.id, body)
    return _format_shopping_item(item)


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove Item from Shopping List")
def delete_shopping_list_item(
    list_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    service.delete_shopping_list_item(list_id, item_id, user.id)
    return None


@router.get("/{list_id}/grocery-comparison", response_model=ShoppingListGroceryComparisonResponse, summary="Compare Shopping List Against Grocery Catalog")
def compare_shopping_list_grocery(
    list_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    return service.compare_shopping_list_grocery(list_id, user.id)
