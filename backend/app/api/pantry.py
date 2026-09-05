from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.pantry import PantryItem
from app.models.recipe import Recipe, RecipeIngredient, Ingredient
from app.models.user import User, UserPreference
from app.schemas.pantry import (
    PantryItemCreate,
    PantryItemUpdate,
    PantryItemRead,
    PantryRecipeCheckResponse,
    RecipeIngredientCheck,
)

router = APIRouter(prefix="/pantry", tags=["Pantry Management"])


def get_current_user(db: Session) -> User:
    """
    Get the default current user for DishIQ development environment.
    Creates a demo user if one does not exist.
    """
    user = db.query(User).first()
    if not user:
        user = User(
            email="demo@dishiq.com",
            hashed_password="hashed_password",
            full_name="Demo User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    if not user.preference:
        pref = UserPreference(
            user_id=user.id,
            dietary_type="None",
            weekly_budget=2500.0,
            household_size=4
        )
        db.add(pref)
        db.commit()
        db.refresh(user)
        
    return user


@router.get("", response_model=List[PantryItemRead], summary="Get Pantry Inventory")
def get_pantry(db: Session = Depends(get_db)):
    """Retrieve all pantry items for the current user."""
    user = get_current_user(db)
    items = db.query(PantryItem).filter(PantryItem.user_id == user.id).all()
    
    # Format and populate ingredient names
    results = []
    for item in items:
        results.append(
            PantryItemRead(
                id=item.id,
                ingredient_id=item.ingredient_id,
                ingredient_name=item.ingredient.canonical_name if item.ingredient else "Unknown",
                canonical_name=item.ingredient.canonical_name if item.ingredient else "Unknown",
                quantity=item.quantity,
                unit=item.unit,
                expiration_date=item.expiration_date,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return results


@router.post("", response_model=PantryItemRead, status_code=status.HTTP_201_CREATED, summary="Add Pantry Item")
def add_pantry_item(body: PantryItemCreate, db: Session = Depends(get_db)):
    """Add a new ingredient to the user's pantry."""
    user = get_current_user(db)
    
    # Look up ingredient by name case-insensitively
    clean_name = body.ingredient_name.strip().lower()
    ing = db.query(Ingredient).filter(Ingredient.canonical_name == clean_name).first()
    
    if not ing:
        # Dynamically create custom ingredient if not seeded
        ing = Ingredient(
            canonical_name=clean_name,
            category="Custom",
            default_unit=body.unit
        )
        db.add(ing)
        db.commit()
        db.refresh(ing)
        
    # Check if item already exists in pantry
    existing_item = (
        db.query(PantryItem)
        .filter(PantryItem.user_id == user.id, PantryItem.ingredient_id == ing.id)
        .first()
    )
    
    if existing_item:
        # Increment quantity
        existing_item.quantity += body.quantity
        existing_item.unit = body.unit
        if body.expiration_date:
            existing_item.expiration_date = body.expiration_date
        db.commit()
        db.refresh(existing_item)
        item = existing_item
    else:
        item = PantryItem(
            user_id=user.id,
            ingredient_id=ing.id,
            quantity=body.quantity,
            unit=body.unit,
            expiration_date=body.expiration_date
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    return PantryItemRead(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=ing.canonical_name,
        canonical_name=ing.canonical_name,
        quantity=item.quantity,
        unit=item.unit,
        expiration_date=item.expiration_date,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.patch("/{item_id}", response_model=PantryItemRead, summary="Update Pantry Item")
def update_pantry_item(item_id: str, body: PantryItemUpdate, db: Session = Depends(get_db)):
    """Update details of an existing pantry item."""
    user = get_current_user(db)
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
        item.unit = body.unit
    if body.expiration_date is not None:
        item.expiration_date = body.expiration_date

    db.commit()
    db.refresh(item)
    
    return PantryItemRead(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient.canonical_name if item.ingredient else "Unknown",
        canonical_name=item.ingredient.canonical_name if item.ingredient else "Unknown",
        quantity=item.quantity,
        unit=item.unit,
        expiration_date=item.expiration_date,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove Pantry Item")
def remove_pantry_item(item_id: str, db: Session = Depends(get_db)):
    """Remove an item from the user's pantry."""
    user = get_current_user(db)
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
    db.delete(item)
    db.commit()
    return None


@router.get("/check-recipe/{recipe_id}", response_model=PantryRecipeCheckResponse, summary="Check Pantry against Recipe")
def check_recipe_ingredients(recipe_id: str, db: Session = Depends(get_db)):
    """Check how much of a recipe's ingredients are covered by the current pantry inventory."""
    user = get_current_user(db)
    
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

    # Get user's pantry mapped by ingredient_id
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
            
            # Simple direct unit conversion helper if unit names differ slightly but represent the same
            # e.g., 'grams' vs 'g', 'kg' vs 'grams'
            pantry_converted_qty = pantry_qty
            try:
                p_unit_lower = pantry_unit.lower().rstrip('s')
                r_unit_lower = req_unit.lower().rstrip('s')
                
                if p_unit_lower != r_unit_lower:
                    if p_unit_lower == "kg" and r_unit_lower == "gram":
                        pantry_converted_qty = pantry_qty * 1000.0
                    elif p_unit_lower == "gram" and r_unit_lower == "kg":
                        pantry_converted_qty = pantry_qty / 1000.0
                    elif p_unit_lower == "liter" and r_unit_lower == "ml":
                        pantry_converted_qty = pantry_qty * 1000.0
                    elif p_unit_lower == "ml" and r_unit_lower == "liter":
                        pantry_converted_qty = pantry_qty / 1000.0
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
