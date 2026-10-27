"""
DishIQ Phase 9 — Meal Planning & Shopping Lists Automated Test Suite
Tests:
  1. Ingredient quantity scaling based on servings.
  2. Ingredient consolidation with compatible units.
  3. Preservation and separation of incompatible units and distinct forms.
  4. Non-destructive pantry deduction (verifying no inventory mutation).
  5. Persistent shopping list editing, manual item preservation, and idempotent refresh.
  6. API endpoints for meal plans, items, shopping lists, and grocery comparison.
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.recipe import Recipe, RecipeIngredient, Ingredient
from app.models.pantry import PantryItem
from app.models.user import User
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.shopping_list import ShoppingList, ShoppingListItem
from app.services.meal_plan_service import (
    scale_ingredient_quantity,
    detect_form,
    MealPlanService,
)
from app.schemas.meal_plan import MealPlanCreate, MealPlanItemCreate, MealPlanItemUpdate
from app.schemas.shopping_list import ShoppingListItemCreate, ShoppingListItemUpdate


def _get_or_create_user(db: Session) -> User:
    user = db.query(User).first()
    if not user:
        user = User(
            email="phase9_test_user@example.com",
            hashed_password="hashed_pw_test",
            full_name="Phase 9 Test User",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ===========================================================================
# 1. Ingredient Quantity Scaling Unit Tests
# ===========================================================================

def test_scale_ingredient_quantity_normal():
    # 2 servings scaled to 4 servings doubles requirement
    scaled = scale_ingredient_quantity(original_quantity=200.0, original_servings=2, planned_servings=4)
    assert scaled == 400.0


def test_scale_ingredient_quantity_fractional():
    # 4 servings scaled to 3 servings = 75%
    scaled = scale_ingredient_quantity(original_quantity=100.0, original_servings=4, planned_servings=3)
    assert scaled == 75.0


def test_scale_ingredient_quantity_same_servings():
    scaled = scale_ingredient_quantity(original_quantity=250.0, original_servings=4, planned_servings=4)
    assert scaled == 250.0


def test_scale_ingredient_quantity_invalid_servings():
    with pytest.raises(ValueError, match="Planned servings must be positive"):
        scale_ingredient_quantity(original_quantity=100.0, original_servings=4, planned_servings=0)

    with pytest.raises(ValueError, match="Planned servings must be positive"):
        scale_ingredient_quantity(original_quantity=100.0, original_servings=4, planned_servings=-2)

    with pytest.raises(ValueError, match="Original servings must be positive"):
        scale_ingredient_quantity(original_quantity=100.0, original_servings=0, planned_servings=4)


# ===========================================================================
# 2. Form Detection & Unit Compatibility Tests
# ===========================================================================

def test_detect_form_descriptors():
    assert detect_form("coconut milk") == "milk"
    assert detect_form("fresh coconut") is None
    assert detect_form("coriander powder") == "powder"
    assert detect_form("fresh coriander leaves") in ["leaves", "leaf"]
    assert detect_form("coriander seeds") in ["seeds", "seed"]
    assert detect_form("mustard oil") == "oil"
    assert detect_form("tomato puree") == "puree"


# ===========================================================================
# 3. Consolidation Engine Unit Tests
# ===========================================================================

def test_consolidate_ingredients_merges_compatible_mass(seeded_db: Session):
    # Setup two mock recipes with onion requirements
    service = MealPlanService(seeded_db)
    user = seeded_db.query(User).first()

    # Create dummy ingredients and recipes
    ing = seeded_db.query(Ingredient).filter(Ingredient.canonical_name == "onion").first()
    if not ing:
        ing = Ingredient(canonical_name="onion", category="Vegetables", default_unit="g")
        seeded_db.add(ing)
        seeded_db.flush()

    r1 = Recipe(name="Meal Plan Recipe 1", description="R1", cuisine="Indian", dietary_type="Vegetarian", servings=4)
    r2 = Recipe(name="Meal Plan Recipe 2", description="R2", cuisine="Indian", dietary_type="Vegetarian", servings=2)
    seeded_db.add_all([r1, r2])
    seeded_db.flush()

    ri1 = RecipeIngredient(recipe_id=r1.id, ingredient_id=ing.id, raw_text="200g onion", quantity=200.0, unit="g")
    ri2 = RecipeIngredient(recipe_id=r2.id, ingredient_id=ing.id, raw_text="100g onion", quantity=100.0, unit="g")
    seeded_db.add_all([ri1, ri2])
    seeded_db.flush()

    # Create meal plan with r1 planned for 4 servings (200g) and r2 planned for 4 servings (100 * 4/2 = 200g)
    plan = MealPlan(name="Consolidation Test Plan", user_id=user.id if user else None)
    seeded_db.add(plan)
    seeded_db.flush()

    m1 = MealPlanItem(meal_plan_id=plan.id, recipe_id=r1.id, servings=4)
    m2 = MealPlanItem(meal_plan_id=plan.id, recipe_id=r2.id, servings=4)
    seeded_db.add_all([m1, m2])
    seeded_db.commit()

    seeded_db.refresh(plan)
    consolidated = service.consolidate_ingredients(plan)

    # 200g + 200g = 400g
    onion_items = [c for c in consolidated if c["ingredient_name"] == "onion"]
    assert len(onion_items) == 1
    assert onion_items[0]["required_quantity"] == 400.0
    assert onion_items[0]["unit"] == "g"
    assert len(onion_items[0]["source_recipes"]) == 2


def test_consolidate_ingredients_separates_distinct_forms(seeded_db: Session):
    service = MealPlanService(seeded_db)
    user = seeded_db.query(User).first()

    r = Recipe(name="Distinct Form Recipe", description="Desc", cuisine="Indian", dietary_type="Vegetarian", servings=2)
    seeded_db.add(r)
    seeded_db.flush()

    # One ingredient is coconut milk, one is fresh coconut
    ing_milk = Ingredient(canonical_name="coconut milk", category="Pantry", default_unit="ml")
    ing_fresh = Ingredient(canonical_name="fresh coconut", category="Vegetables", default_unit="g")
    seeded_db.add_all([ing_milk, ing_fresh])
    seeded_db.flush()

    ri1 = RecipeIngredient(recipe_id=r.id, ingredient_id=ing_milk.id, raw_text="200ml coconut milk", quantity=200.0, unit="ml")
    ri2 = RecipeIngredient(recipe_id=r.id, ingredient_id=ing_fresh.id, raw_text="100g fresh coconut", quantity=100.0, unit="g")
    seeded_db.add_all([ri1, ri2])
    seeded_db.flush()

    plan = MealPlan(name="Form Separation Plan", user_id=user.id if user else None)
    seeded_db.add(plan)
    seeded_db.flush()

    m = MealPlanItem(meal_plan_id=plan.id, recipe_id=r.id, servings=2)
    seeded_db.add(m)
    seeded_db.commit()

    seeded_db.refresh(plan)
    consolidated = service.consolidate_ingredients(plan)

    names = {c["ingredient_name"] for c in consolidated}
    assert "coconut milk" in names
    assert "fresh coconut" in names
    # Confirm they remained separate
    assert len(consolidated) == 2


# ===========================================================================
# 4. Non-Destructive Pantry Deduction Tests
# ===========================================================================

def test_pantry_deduction_leaves_pantry_records_unmutated(seeded_db: Session):
    service = MealPlanService(seeded_db)
    user = _get_or_create_user(seeded_db)
    assert user is not None

    # Add a pantry item with 500g of paneer
    paneer_ing = seeded_db.query(Ingredient).filter(Ingredient.canonical_name == "paneer").first()
    if not paneer_ing:
        paneer_ing = Ingredient(canonical_name="paneer", category="Dairy", default_unit="g")
        seeded_db.add(paneer_ing)
        seeded_db.flush()

    # Clear prior pantry for this ingredient
    seeded_db.query(PantryItem).filter(
        PantryItem.user_id == user.id, PantryItem.ingredient_id == paneer_ing.id
    ).delete()

    pantry_entry = PantryItem(
        user_id=user.id,
        ingredient_id=paneer_ing.id,
        quantity=500.0,
        unit="g"
    )
    seeded_db.add(pantry_entry)
    seeded_db.commit()

    # Create recipe needing 200g paneer
    r = Recipe(name="Pantry Check Recipe", description="Desc", cuisine="Indian", dietary_type="Vegetarian", servings=4)
    seeded_db.add(r)
    seeded_db.flush()

    ri = RecipeIngredient(recipe_id=r.id, ingredient_id=paneer_ing.id, raw_text="200g paneer", quantity=200.0, unit="g")
    seeded_db.add(ri)
    seeded_db.flush()

    plan = MealPlan(name="Pantry Deduction Test Plan", user_id=user.id)
    seeded_db.add(plan)
    seeded_db.flush()

    m = MealPlanItem(meal_plan_id=plan.id, recipe_id=r.id, servings=4)
    seeded_db.add(m)
    seeded_db.commit()

    # Generate shopping list with pantry deduction
    slist = service.generate_or_refresh_shopping_list(plan.id, user.id, deduct_pantry=True)

    # 1. Required quantity is 200g, pantry has 500g -> quantity to buy = 0.0
    paneer_line = next((it for it in slist.items if it.ingredient_name == "paneer"), None)
    assert paneer_line is not None
    assert paneer_line.required_quantity == 200.0
    assert paneer_line.pantry_quantity == 500.0
    assert paneer_line.quantity_to_buy == 0.0

    # 2. CRITICAL VERIFICATION: Pantry record quantity MUST still be 500.0!
    seeded_db.refresh(pantry_entry)
    assert pantry_entry.quantity == 500.0


def test_pantry_deduction_incompatible_unit_not_deducted(seeded_db: Session):
    service = MealPlanService(seeded_db)
    user = _get_or_create_user(seeded_db)

    garlic_ing = seeded_db.query(Ingredient).filter(Ingredient.canonical_name == "garlic").first()
    if not garlic_ing:
        garlic_ing = Ingredient(canonical_name="garlic", category="Produce", default_unit="piece")
        seeded_db.add(garlic_ing)
        seeded_db.flush()

    seeded_db.query(PantryItem).filter(
        PantryItem.user_id == user.id, PantryItem.ingredient_id == garlic_ing.id
    ).delete()

    # Pantry has 2 "pieces" (COUNT), but recipe requires 50 "g" (MASS) without density
    pantry_entry = PantryItem(
        user_id=user.id,
        ingredient_id=garlic_ing.id,
        quantity=2.0,
        unit="piece"
    )
    seeded_db.add(pantry_entry)
    seeded_db.commit()

    r = Recipe(name="Incompatible Unit Recipe", description="Desc", cuisine="Indian", dietary_type="Vegetarian", servings=2)
    seeded_db.add(r)
    seeded_db.flush()

    ri = RecipeIngredient(recipe_id=r.id, ingredient_id=garlic_ing.id, raw_text="50g garlic", quantity=50.0, unit="g")
    seeded_db.add(ri)
    seeded_db.flush()

    plan = MealPlan(name="Incompatible Unit Plan", user_id=user.id)
    seeded_db.add(plan)
    seeded_db.flush()

    m = MealPlanItem(meal_plan_id=plan.id, recipe_id=r.id, servings=2)
    seeded_db.add(m)
    seeded_db.commit()

    slist = service.generate_or_refresh_shopping_list(plan.id, user.id, deduct_pantry=True)

    garlic_line = next((it for it in slist.items if it.ingredient_name == "garlic"), None)
    assert garlic_line is not None
    # Cannot deduct: quantity_to_buy remains 50.0 g and warning note is recorded
    assert garlic_line.quantity_to_buy == 50.0
    assert "incompatible" in garlic_line.notes.lower()


# ===========================================================================
# 5. Persistent Shopping List Refresh & Manual Item Preservation
# ===========================================================================

def test_refresh_preserves_manual_items_and_checked_status(seeded_db: Session):
    service = MealPlanService(seeded_db)
    user = _get_or_create_user(seeded_db)

    r = Recipe(name="Refresh Recipe", description="Desc", cuisine="Indian", dietary_type="Vegetarian", servings=2)
    seeded_db.add(r)
    seeded_db.flush()

    salt_ing = seeded_db.query(Ingredient).filter(Ingredient.canonical_name == "salt").first()
    if not salt_ing:
        salt_ing = Ingredient(canonical_name="salt", category="Pantry", default_unit="g")
        seeded_db.add(salt_ing)
        seeded_db.flush()

    ri = RecipeIngredient(recipe_id=r.id, ingredient_id=salt_ing.id, raw_text="10g salt", quantity=10.0, unit="g")
    seeded_db.add(ri)
    seeded_db.flush()

    plan = MealPlan(name="Refresh Preservation Plan", user_id=user.id)
    seeded_db.add(plan)
    seeded_db.flush()

    m = MealPlanItem(meal_plan_id=plan.id, recipe_id=r.id, servings=2)
    seeded_db.add(m)
    seeded_db.commit()

    # Step 1: Generate initial list
    slist = service.generate_or_refresh_shopping_list(plan.id, user.id, deduct_pantry=False)
    initial_items_count = len(slist.items)
    salt_item = next(it for it in slist.items if it.ingredient_name == "salt")

    # Step 2: Mark salt item as obtained and set a manual override
    service.update_shopping_list_item(
        slist.id, salt_item.id, user.id,
        ShoppingListItemUpdate(is_obtained=True, user_quantity_override=15.0)
    )

    # Step 3: Add a custom manual item ("dish soap")
    manual_item = service.add_manual_item(
        slist.id, user.id,
        ShoppingListItemCreate(ingredient_name="dish soap", quantity=1.0, unit="bottle")
    )

    # Step 4: Change plan servings from 2 to 4 and refresh
    service.update_planned_meal(plan.id, m.id, user.id, MealPlanItemUpdate(servings=4))
    refreshed_list = service.generate_or_refresh_shopping_list(plan.id, user.id, deduct_pantry=False)

    # Verifications:
    # 1. Manual item still exists
    manual_check = next((it for it in refreshed_list.items if it.ingredient_name == "dish soap"), None)
    assert manual_check is not None
    assert manual_check.is_manual == 1

    # 2. Salt item preserved its ID, checked status, and quantity override
    salt_check = next((it for it in refreshed_list.items if it.ingredient_name == "salt"), None)
    assert salt_check is not None
    assert salt_check.id == salt_item.id
    assert salt_check.is_obtained == 1
    assert salt_check.user_quantity_override == 15.0
    # Required quantity was re-scaled (10g * 4/2 = 20g)
    assert salt_check.required_quantity == 20.0


# ===========================================================================
# 6. Full API Endpoints Integration Tests
# ===========================================================================

def test_api_meal_plan_lifecycle(client: TestClient, seeded_db: Session):
    # Get a recipe from seed
    recipe = seeded_db.query(Recipe).first()
    assert recipe is not None

    # 1. Create a meal plan
    create_payload = {
        "name": "Weekly Test Plan",
        "start_date": "2026-11-01",
        "end_date": "2026-11-07",
        "notes": "Healthy balanced diet",
        "meals": [
            {
                "recipe_id": recipe.id,
                "meal_date": "2026-11-01",
                "meal_type": "lunch",
                "servings": 2,
                "notes": "Extra spicy",
            }
        ]
    }
    r = client.post("/api/meal-plans", json=create_payload)
    assert r.status_code == 201, r.text
    data = r.json()
    plan_id = data["id"]
    assert data["name"] == "Weekly Test Plan"
    assert len(data["meals"]) == 1
    meal_id = data["meals"][0]["id"]
    assert data["meals"][0]["servings"] == 2

    # 2. Update serving count
    update_meal_payload = {"servings": 4}
    r_update = client.put(f"/api/meal-plans/{plan_id}/meals/{meal_id}", json=update_meal_payload)
    assert r_update.status_code == 200
    assert r_update.json()["servings"] == 4

    # 3. Reject negative serving count
    r_bad_servings = client.put(f"/api/meal-plans/{plan_id}/meals/{meal_id}", json={"servings": 0})
    assert r_bad_servings.status_code == 422

    # 4. Generate Shopping List from Plan
    r_gen = client.post(f"/api/meal-plans/{plan_id}/shopping-list", json={"deduct_pantry": False})
    assert r_gen.status_code == 200, r_gen.text
    list_data = r_gen.json()
    list_id = list_data["id"]
    assert list_data["meal_plan_id"] == plan_id
    assert len(list_data["items"]) > 0

    first_item = list_data["items"][0]
    item_id = first_item["id"]

    # 5. Check off an item (mark obtained)
    r_check = client.patch(
        f"/api/shopping-lists/{list_id}/items/{item_id}",
        json={"is_obtained": True}
    )
    assert r_check.status_code == 200
    assert r_check.json()["is_obtained"] is True

    # 6. Add manual custom item
    r_manual = client.post(
        f"/api/shopping-lists/{list_id}/items",
        json={"ingredient_name": "organic honey", "quantity": 1.0, "unit": "bottle"}
    )
    assert r_manual.status_code == 201
    assert r_manual.json()["is_manual"] is True
    manual_id = r_manual.json()["id"]

    # 7. Delete manual item
    r_del = client.delete(f"/api/shopping-lists/{list_id}/items/{manual_id}")
    assert r_del.status_code == 204

    # 8. Request Grocery Comparison for Shopping List
    r_compare = client.get(f"/api/shopping-lists/{list_id}/grocery-comparison")
    assert r_compare.status_code == 200
    compare_data = r_compare.json()
    assert "items" in compare_data
    assert "unmatched_ingredients" in compare_data

    # 9. Clean up / delete meal plan
    r_del_plan = client.delete(f"/api/meal-plans/{plan_id}")
    assert r_del_plan.status_code == 204
