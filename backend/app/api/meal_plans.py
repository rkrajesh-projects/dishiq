"""
DishIQ Phase 9 — Meal Planning API Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.meal_plan_service import MealPlanService
from app.schemas.meal_plan import (
    MealPlanCreate,
    MealPlanUpdate,
    MealPlanRead,
    MealPlanItemCreate,
    MealPlanItemUpdate,
    MealPlanItemRead,
)
from app.schemas.shopping_list import ShoppingListRead, ShoppingListGenerateRequest

router = APIRouter(prefix="/meal-plans", tags=["Meal Planning"])


def _format_meal_item(meal) -> MealPlanItemRead:
    recipe_servings = meal.recipe.servings if meal.recipe and meal.recipe.servings else 4
    return MealPlanItemRead(
        id=meal.id,
        meal_plan_id=meal.meal_plan_id,
        recipe_id=meal.recipe_id,
        recipe_name=meal.recipe.name if meal.recipe else "Unknown Recipe",
        recipe_cuisine=meal.recipe.cuisine if meal.recipe else None,
        meal_date=meal.meal_date,
        meal_type=meal.meal_type,
        servings=meal.servings,
        original_servings=recipe_servings,
        notes=meal.notes,
        created_at=meal.created_at,
        updated_at=meal.updated_at,
    )


def _format_meal_plan(plan) -> MealPlanRead:
    return MealPlanRead(
        id=plan.id,
        user_id=plan.user_id,
        name=plan.name,
        start_date=plan.start_date,
        end_date=plan.end_date,
        notes=plan.notes,
        meals=[_format_meal_item(m) for m in plan.meals],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("", response_model=MealPlanRead, status_code=status.HTTP_201_CREATED, summary="Create Meal Plan")
def create_meal_plan(
    body: MealPlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    plan = service.create_meal_plan(user.id, body)
    return _format_meal_plan(plan)


@router.get("", response_model=List[MealPlanRead], summary="List Meal Plans")
def list_meal_plans(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    plans = service.list_meal_plans(user.id)
    return [_format_meal_plan(p) for p in plans]


@router.get("/{plan_id}", response_model=MealPlanRead, summary="Get Meal Plan Details")
def get_meal_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    plan = service.get_meal_plan(plan_id, user.id)
    return _format_meal_plan(plan)


@router.put("/{plan_id}", response_model=MealPlanRead, summary="Update Meal Plan")
def update_meal_plan(
    plan_id: str,
    body: MealPlanUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    plan = service.update_meal_plan(plan_id, user.id, body)
    return _format_meal_plan(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Meal Plan")
def delete_meal_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    service.delete_meal_plan(plan_id, user.id)
    return None


@router.post("/{plan_id}/meals", response_model=MealPlanItemRead, status_code=status.HTTP_201_CREATED, summary="Add Recipe to Meal Plan")
def add_meal_to_plan(
    plan_id: str,
    body: MealPlanItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    meal = service.add_meal_to_plan(plan_id, user.id, body)
    return _format_meal_item(meal)


@router.put("/{plan_id}/meals/{meal_id}", response_model=MealPlanItemRead, summary="Update Planned Meal Servings & Details")
def update_planned_meal(
    plan_id: str,
    meal_id: str,
    body: MealPlanItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    meal = service.update_planned_meal(plan_id, meal_id, user.id, body)
    return _format_meal_item(meal)


@router.delete("/{plan_id}/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove Planned Meal")
def remove_planned_meal(
    plan_id: str,
    meal_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MealPlanService(db)
    service.remove_planned_meal(plan_id, meal_id, user.id)
    return None


@router.post("/{plan_id}/shopping-list", response_model=ShoppingListRead, summary="Generate or Refresh Shopping List")
def generate_shopping_list(
    plan_id: str,
    body: ShoppingListGenerateRequest = ShoppingListGenerateRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.api.shopping_lists import _format_shopping_list
    service = MealPlanService(db)
    slist = service.generate_or_refresh_shopping_list(
        plan_id=plan_id,
        user_id=user.id,
        deduct_pantry=body.deduct_pantry,
        custom_name=body.name,
    )
    return _format_shopping_list(slist)
