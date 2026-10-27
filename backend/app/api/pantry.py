import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.pantry import PantryItem, PantryConsumptionLog
from app.models.recipe import Recipe, RecipeIngredient, Ingredient
from app.models.user import User
from app.ingredient_intelligence.units import convert_quantity, are_units_compatible, normalize_unit
from app.schemas.pantry import (
    PantryItemCreate,
    PantryItemUpdate,
    PantryItemRead,
    PantryRecipeCheckResponse,
    RecipeIngredientCheck,
    ConsumptionPreviewRequest,
    ConsumptionPreviewResponse,
    ConsumptionPreviewItem,
    ConsumptionConfirmRequest,
    ConsumptionConfirmResponse,
)

router = APIRouter(prefix="/pantry", tags=["Pantry Management"])


def _item_to_read(item: PantryItem) -> PantryItemRead:
    ing_name = item.ingredient.canonical_name if item.ingredient else "Unknown"
    return PantryItemRead(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.custom_name or ing_name,
        canonical_name=ing_name,
        quantity=item.quantity,
        unit=item.unit,
        expiration_date=item.expiration_date,
        custom_name=item.custom_name,
        location=item.location,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=List[PantryItemRead], summary="Get Pantry Inventory")
def get_pantry(
    search: Optional[str] = Query(None, description="Search by ingredient name or custom name"),
    location: Optional[str] = Query(None, description="Filter by storage location"),
    expiring_within_days: Optional[int] = Query(None, description="Filter items expiring within N days"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Retrieve all pantry items for the current user with optional search and filters."""
    query = (
        db.query(PantryItem)
        .join(PantryItem.ingredient)
        .filter(PantryItem.user_id == user.id)
    )

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            (Ingredient.canonical_name.ilike(term)) | (PantryItem.custom_name.ilike(term))
        )

    if location and location.strip():
        query = query.filter(PantryItem.location.ilike(location.strip()))

    if expiring_within_days is not None and expiring_within_days >= 0:
        today = date.today()
        target = today + timedelta(days=expiring_within_days)
        query = query.filter(PantryItem.expiration_date.isnot(None), PantryItem.expiration_date <= target)

    items = query.order_by(PantryItem.created_at.desc()).all()
    return [_item_to_read(item) for item in items]


@router.post("", response_model=PantryItemRead, status_code=status.HTTP_201_CREATED, summary="Add Pantry Item")
def add_pantry_item(body: PantryItemCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Add a new ingredient to the user's pantry."""
    clean_name = body.ingredient_name.strip().lower()
    raw_unit = body.unit.strip()

    ing = db.query(Ingredient).filter(Ingredient.canonical_name == clean_name).first()
    try:
        if not ing:
            ing = Ingredient(
                canonical_name=clean_name,
                category="Custom",
                default_unit=raw_unit,
            )
            db.add(ing)
            db.flush()

        existing_item = (
            db.query(PantryItem)
            .filter(PantryItem.user_id == user.id, PantryItem.ingredient_id == ing.id)
            .first()
        )

        if existing_item:
            existing_item.quantity += body.quantity
            existing_item.unit = raw_unit
            if body.expiration_date:
                existing_item.expiration_date = body.expiration_date
            if body.custom_name:
                existing_item.custom_name = body.custom_name.strip()
            if body.location:
                existing_item.location = body.location.strip()
            if body.notes:
                existing_item.notes = body.notes.strip()
            db.commit()
            db.refresh(existing_item)
            item = existing_item
        else:
            item = PantryItem(
                user_id=user.id,
                ingredient_id=ing.id,
                quantity=body.quantity,
                unit=raw_unit,
                expiration_date=body.expiration_date,
                custom_name=body.custom_name.strip() if body.custom_name else None,
                location=body.location.strip() if body.location else None,
                notes=body.notes.strip() if body.notes else None,
            )
            db.add(item)
            db.commit()
            db.refresh(item)
    except Exception:
        db.rollback()
        raise

    return _item_to_read(item)


@router.patch("/{item_id}", response_model=PantryItemRead, summary="Update Pantry Item")
def update_pantry_item(item_id: str, body: PantryItemUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Update details of an existing pantry item."""
    item = (
        db.query(PantryItem)
        .filter(PantryItem.id == item_id, PantryItem.user_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pantry item '{item_id}' not found."
        )

    if body.quantity is not None:
        item.quantity = body.quantity
    if body.unit is not None:
        item.unit = body.unit.strip()
    if body.expiration_date is not None:
        item.expiration_date = body.expiration_date
    if body.custom_name is not None:
        item.custom_name = body.custom_name.strip() if body.custom_name else None
    if body.location is not None:
        item.location = body.location.strip() if body.location else None
    if body.notes is not None:
        item.notes = body.notes.strip() if body.notes else None

    try:
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        raise

    return _item_to_read(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove Pantry Item")
def remove_pantry_item(item_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Remove an item from the user's pantry."""
    item = (
        db.query(PantryItem)
        .filter(PantryItem.id == item_id, PantryItem.user_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pantry item '{item_id}' not found."
        )
    try:
        db.delete(item)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return None


@router.get("/check-recipe/{recipe_id}", response_model=PantryRecipeCheckResponse, summary="Check Pantry against Recipe")
def check_recipe_ingredients(recipe_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Check how much of a recipe's ingredients are covered by the current pantry inventory."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe '{recipe_id}' not found."
        )

    recipe_ingredients = (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )

    pantry_items = {
        item.ingredient_id: item
        for item in db.query(PantryItem).filter(PantryItem.user_id == user.id).all()
    }

    required_checks = []
    pantry_covered = []
    partially_covered = []
    missing_ingredients = []

    for ri in recipe_ingredients:
        pantry_item = pantry_items.get(ri.ingredient_id)
        req_qty = ri.quantity
        req_unit = ri.unit
        pantry_qty = 0.0
        pantry_unit = req_unit

        if pantry_item:
            pantry_qty = pantry_item.quantity
            pantry_unit = pantry_item.unit
            pantry_converted_qty = pantry_qty
            try:
                if pantry_unit and req_unit and pantry_unit.strip().lower() != req_unit.strip().lower():
                    converted, _ = convert_quantity(pantry_qty, pantry_unit, req_unit)
                    if converted is not None:
                        pantry_converted_qty = converted
            except Exception:
                pass

            if pantry_converted_qty >= req_qty:
                status_str = "covered"
            elif pantry_converted_qty > 0.0:
                status_str = "partially_covered"
            else:
                status_str = "missing"
        else:
            status_str = "missing"

        check_item = RecipeIngredientCheck(
            ingredient_name=ri.ingredient.canonical_name if ri.ingredient else "Unknown",
            required_quantity=req_qty,
            required_unit=req_unit,
            pantry_quantity=pantry_qty,
            pantry_unit=pantry_unit,
            status=status_str
        )

        required_checks.append(check_item)
        if status_str == "covered":
            pantry_covered.append(check_item)
        elif status_str == "partially_covered":
            partially_covered.append(check_item)
        else:
            missing_ingredients.append(check_item)

    return PantryRecipeCheckResponse(
        recipe_id=recipe_id,
        recipe_name=recipe.name,
        required_ingredients=required_checks,
        pantry_covered=pantry_covered,
        partially_covered=partially_covered,
        missing_ingredients=missing_ingredients
    )


# ---------------------------------------------------------------------------
# Phase 11 — Explicit Pantry Consumption Workflow
# ---------------------------------------------------------------------------

@router.post("/preview-consumption", response_model=ConsumptionPreviewResponse, summary="Preview Pantry Consumption")
def preview_pantry_consumption(
    body: ConsumptionPreviewRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Preview the proposed pantry deductions before making any changes.
    Evaluates unit compatibility and stock availability.
    Strictly read-only; never mutates database stock.
    """
    pantry_items = {
        item.ingredient_id: item
        for item in db.query(PantryItem).filter(PantryItem.user_id == user.id).all()
        if item.ingredient_id
    }

    raw_items = []
    if body.recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == body.recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe '{body.recipe_id}' not found.")

        base_servings = recipe.servings if recipe.servings and recipe.servings > 0 else 4
        target_servings = body.servings if body.servings and body.servings > 0 else base_servings
        scale_factor = target_servings / base_servings

        for ri in (recipe.ingredients or []):
            if ri.quantity is not None and ri.quantity > 0:
                raw_items.append({
                    "ingredient_id": ri.ingredient_id,
                    "ingredient_name": ri.ingredient.canonical_name if ri.ingredient else (ri.raw_text or "Unknown"),
                    "required_quantity": round(ri.quantity * scale_factor, 3),
                    "required_unit": ri.unit or "pieces",
                })
    elif body.items:
        for item in body.items:
            raw_items.append({
                "ingredient_id": item.get("ingredient_id"),
                "ingredient_name": item.get("ingredient_name", "Unknown"),
                "required_quantity": float(item.get("required_quantity", 1.0)),
                "required_unit": item.get("required_unit", "pieces"),
            })
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'recipe_id' or a non-empty 'items' list must be provided."
        )

    preview_items = []
    has_issues = False

    for item in raw_items:
        ing_id = item.get("ingredient_id")
        req_qty = item["required_quantity"]
        req_unit = item["required_unit"]
        ing_name = item["ingredient_name"]

        pantry_match = pantry_items.get(ing_id) if ing_id else None

        if not pantry_match:
            preview_items.append(ConsumptionPreviewItem(
                ingredient_id=ing_id,
                ingredient_name=ing_name,
                required_quantity=req_qty,
                required_unit=req_unit,
                status="missing",
                can_deduct=False,
                reason="Not in pantry stock"
            ))
            continue

        p_unit = pantry_match.unit
        p_qty = pantry_match.quantity

        # Check unit compatibility
        compatible = are_units_compatible(req_unit, p_unit)
        if not compatible:
            has_issues = True
            preview_items.append(ConsumptionPreviewItem(
                ingredient_id=ing_id,
                ingredient_name=ing_name,
                required_quantity=req_qty,
                required_unit=req_unit,
                pantry_item_id=pantry_match.id,
                pantry_quantity=p_qty,
                pantry_unit=p_unit,
                is_compatible=False,
                can_deduct=False,
                status="incompatible_unit",
                reason=f"Unit '{req_unit}' cannot be converted to pantry unit '{p_unit}' without density"
            ))
            continue

        # Convert required quantity to pantry's unit
        converted_req_qty, _ = convert_quantity(req_qty, req_unit, p_unit)
        if converted_req_qty is None:
            has_issues = True
            preview_items.append(ConsumptionPreviewItem(
                ingredient_id=ing_id,
                ingredient_name=ing_name,
                required_quantity=req_qty,
                required_unit=req_unit,
                pantry_item_id=pantry_match.id,
                pantry_quantity=p_qty,
                pantry_unit=p_unit,
                is_compatible=False,
                can_deduct=False,
                status="uncertain_match",
                reason="Conversion factor unavailable"
            ))
            continue

        # Compare with available stock
        if p_qty >= converted_req_qty:
            deduct_qty = round(converted_req_qty, 3)
            remaining = round(p_qty - converted_req_qty, 3)
            item_status = "fully_covered"
        else:
            deduct_qty = round(p_qty, 3)
            remaining = 0.0
            item_status = "partially_covered"

        preview_items.append(ConsumptionPreviewItem(
            ingredient_id=ing_id,
            ingredient_name=ing_name,
            required_quantity=req_qty,
            required_unit=req_unit,
            pantry_item_id=pantry_match.id,
            pantry_quantity=p_qty,
            pantry_unit=p_unit,
            converted_deduct_quantity=deduct_qty,
            remaining_stock=remaining,
            is_compatible=True,
            can_deduct=deduct_qty > 0,
            status=item_status,
        ))

    total_deductible = sum(1 for p in preview_items if p.can_deduct)
    preview_token = str(uuid.uuid4())

    return ConsumptionPreviewResponse(
        preview_token=preview_token,
        recipe_id=body.recipe_id,
        cooking_session_id=body.cooking_session_id,
        items=preview_items,
        total_deductible_items=total_deductible,
        has_incompatible_or_uncertain=has_issues,
    )


@router.post("/consume", response_model=ConsumptionConfirmResponse, summary="Confirm Explicit Pantry Consumption")
def confirm_pantry_consumption(
    body: ConsumptionConfirmRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Execute confirmed pantry deduction inside an atomic database transaction.
    Guarantees idempotency via preview_token verification.
    """
    if not body.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No items provided for consumption."
        )

    # Check for duplicate submission
    existing_log = (
        db.query(PantryConsumptionLog)
        .filter(PantryConsumptionLog.token == body.preview_token)
        .first()
    )
    if existing_log:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate submission: This consumption token has already been processed."
        )

    deductions_applied = []

    try:
        for item in body.items:
            pantry_item = (
                db.query(PantryItem)
                .filter(PantryItem.id == item.pantry_item_id, PantryItem.user_id == user.id)
                .first()
            )
            if not pantry_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pantry item '{item.pantry_item_id}' not found for user."
                )

            deduct = round(item.deduct_quantity, 4)
            prev_qty = pantry_item.quantity
            new_qty = max(0.0, round(prev_qty - deduct, 4))
            pantry_item.quantity = new_qty
            pantry_item.updated_at = datetime.now(timezone.utc)

            deductions_applied.append({
                "pantry_item_id": pantry_item.id,
                "ingredient_name": pantry_item.ingredient.canonical_name if pantry_item.ingredient else "Unknown",
                "previous_quantity": prev_qty,
                "deducted_quantity": deduct,
                "new_quantity": new_qty,
                "unit": pantry_item.unit,
            })

        # Save audit log
        log_entry = PantryConsumptionLog(
            user_id=user.id,
            token=body.preview_token,
            recipe_id=body.recipe_id,
            cooking_session_id=body.cooking_session_id,
            items=deductions_applied,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return ConsumptionConfirmResponse(
        success=True,
        deducted_count=len(deductions_applied),
        message=f"Successfully deducted {len(deductions_applied)} pantry items.",
        deductions=deductions_applied,
    )
