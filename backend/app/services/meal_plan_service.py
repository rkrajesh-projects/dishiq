"""
DishIQ Phase 9 — Meal Planning & Shopping List Service
Handles:
  1. Ingredient quantity scaling based on planned vs original recipe servings.
  2. Safe consolidation across meals with canonical identity, unit compatibility, and form separation.
  3. Non-destructive pantry deduction (read-only against pantry stock).
  4. Shopping list persistence, manual item preservation, and idempotent refresh.
  5. Grocery comparison integration with price freshness and missing-item disclosure.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.shopping_list import ShoppingList, ShoppingListItem
from app.models.recipe import Recipe, RecipeIngredient, Ingredient
from app.models.pantry import PantryItem
from app.ingredient_intelligence.units import (
    normalize_unit,
    get_unit_dimension,
    are_units_compatible,
    convert_quantity,
    UnitDimension,
)
from app.services.grocery_service import GroceryService
from app.schemas.meal_plan import (
    MealPlanCreate,
    MealPlanUpdate,
    MealPlanItemCreate,
    MealPlanItemUpdate,
)
from app.schemas.shopping_list import (
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListGroceryComparisonResponse,
    ShoppingListGroceryItemMatch,
)

FORM_KEYWORDS = [
    "powder", "ground", "milk", "oil", "paste", "flour",
    "leaves", "leaf", "seeds", "seed", "puree", "flakes"
]


def detect_form(name: str, raw_text: Optional[str] = None) -> Optional[str]:
    """Detect specific culinary form from ingredient name and raw text."""
    combined = f"{name} {raw_text or ''}".lower()
    for kw in FORM_KEYWORDS:
        # Match whole word
        if re.search(r"\b" + re.escape(kw) + r"\b", combined):
            return kw
    return None


def scale_ingredient_quantity(
    original_quantity: float,
    original_servings: int,
    planned_servings: int,
) -> float:
    """
    Scale ingredient quantity proportionally based on servings.
    Required Quantity = Original Quantity * (Planned Servings / Original Servings)
    """
    if original_servings <= 0:
        raise ValueError("Original servings must be positive")
    if planned_servings <= 0:
        raise ValueError("Planned servings must be positive")
    if original_quantity < 0:
        raise ValueError("Original quantity cannot be negative")

    scaled = original_quantity * (float(planned_servings) / float(original_servings))
    return round(scaled, 4)


class MealPlanService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Meal Plan CRUD
    # -------------------------------------------------------------------------

    def create_meal_plan(self, user_id: Optional[str], payload: MealPlanCreate) -> MealPlan:
        """Create a new meal plan with optional initial meals."""
        plan = MealPlan(
            user_id=user_id,
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            notes=payload.notes,
        )
        self.db.add(plan)
        self.db.flush()

        if payload.meals:
            for m in payload.meals:
                self.add_meal_to_plan(plan.id, user_id, m)

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_meal_plan(self, plan_id: str, user_id: Optional[str]) -> MealPlan:
        """Retrieve meal plan with ownership validation."""
        query = self.db.query(MealPlan).filter(MealPlan.id == plan_id)
        if user_id:
            query = query.filter(MealPlan.user_id == user_id)
        else:
            query = query.filter(MealPlan.user_id.is_(None))
        plan = query.first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meal plan '{plan_id}' not found.",
            )
        return plan

    def list_meal_plans(self, user_id: Optional[str]) -> List[MealPlan]:
        """List meal plans owned by the user (or unowned if unauthenticated)."""
        query = self.db.query(MealPlan)
        if user_id:
            query = query.filter(MealPlan.user_id == user_id)
        else:
            query = query.filter(MealPlan.user_id.is_(None))
        return query.order_by(MealPlan.created_at.desc()).all()

    def update_meal_plan(self, plan_id: str, user_id: Optional[str], payload: MealPlanUpdate) -> MealPlan:
        """Update meal plan metadata."""
        plan = self.get_meal_plan(plan_id, user_id)
        if payload.name is not None:
            plan.name = payload.name
        if payload.start_date is not None:
            plan.start_date = payload.start_date
        if payload.end_date is not None:
            plan.end_date = payload.end_date
        if payload.notes is not None:
            plan.notes = payload.notes

        plan.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def delete_meal_plan(self, plan_id: str, user_id: Optional[str]) -> None:
        """Delete a meal plan and cascading items."""
        plan = self.get_meal_plan(plan_id, user_id)
        self.db.delete(plan)
        self.db.commit()

    # -------------------------------------------------------------------------
    # Planned Meals CRUD & Serving Adjustments
    # -------------------------------------------------------------------------

    def add_meal_to_plan(
        self, plan_id: str, user_id: Optional[str], payload: MealPlanItemCreate
    ) -> MealPlanItem:
        """Add a recipe as a planned meal with custom servings."""
        plan = self.get_meal_plan(plan_id, user_id)

        recipe = self.db.query(Recipe).filter(Recipe.id == payload.recipe_id).first()
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe '{payload.recipe_id}' not found.",
            )

        if payload.servings <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Servings count must be greater than 0.",
            )

        item = MealPlanItem(
            meal_plan_id=plan.id,
            recipe_id=recipe.id,
            meal_date=payload.meal_date,
            meal_type=payload.meal_type or "dinner",
            servings=payload.servings,
            notes=payload.notes,
        )
        self.db.add(item)
        plan.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_planned_meal(
        self, plan_id: str, meal_id: str, user_id: Optional[str], payload: MealPlanItemUpdate
    ) -> MealPlanItem:
        """Update serving count, date, or notes on a planned meal."""
        plan = self.get_meal_plan(plan_id, user_id)
        meal = (
            self.db.query(MealPlanItem)
            .filter(MealPlanItem.id == meal_id, MealPlanItem.meal_plan_id == plan.id)
            .first()
        )
        if not meal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planned meal '{meal_id}' not found in plan '{plan_id}'.",
            )

        if payload.servings is not None:
            if payload.servings <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Servings count must be greater than 0.",
                )
            meal.servings = payload.servings

        if payload.meal_date is not None:
            meal.meal_date = payload.meal_date
        if payload.meal_type is not None:
            meal.meal_type = payload.meal_type
        if payload.notes is not None:
            meal.notes = payload.notes

        meal.updated_at = datetime.now(timezone.utc)
        plan.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(meal)
        return meal

    def remove_planned_meal(self, plan_id: str, meal_id: str, user_id: Optional[str]) -> None:
        """Remove a planned meal from the plan."""
        plan = self.get_meal_plan(plan_id, user_id)
        meal = (
            self.db.query(MealPlanItem)
            .filter(MealPlanItem.id == meal_id, MealPlanItem.meal_plan_id == plan.id)
            .first()
        )
        if not meal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planned meal '{meal_id}' not found in plan '{plan_id}'.",
            )
        self.db.delete(meal)
        plan.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    # -------------------------------------------------------------------------
    # Ingredient Consolidation & Serving Scaling Engine
    # -------------------------------------------------------------------------

    def consolidate_ingredients(self, plan: MealPlan) -> List[Dict[str, Any]]:
        """
        Consolidates ingredient requirements across all planned meals:
        - Scales each recipe ingredient by (planned_servings / recipe_servings).
        - Groups by (canonical_ingredient_id / name, normalized_unit_dimension, form).
        - Separates incompatible units (e.g. g vs ml) and incompatible forms (e.g. milk vs whole).
        - Sums compatible quantities into canonical units.
        - Preserves source recipe references.
        """
        raw_items: List[Dict[str, Any]] = []

        for meal in plan.meals:
            recipe = meal.recipe
            if not recipe:
                continue

            recipe_servings = recipe.servings if recipe.servings and recipe.servings > 0 else 4
            planned_servings = meal.servings

            for ri in recipe.ingredients:
                orig_qty = ri.quantity
                orig_unit = ri.unit or "piece"
                scaled_qty = scale_ingredient_quantity(orig_qty, recipe_servings, planned_servings)

                ing_name = (
                    ri.ingredient.canonical_name
                    if ri.ingredient and ri.ingredient.canonical_name
                    else ri.raw_text.strip()
                )
                ing_id = ri.ingredient_id

                form = detect_form(ing_name, ri.raw_text)
                norm_unit = normalize_unit(orig_unit) or orig_unit.strip().lower()
                dimension = get_unit_dimension(norm_unit) or UnitDimension.COUNT

                raw_items.append({
                    "ingredient_id": ing_id,
                    "ingredient_name": ing_name,
                    "quantity": scaled_qty,
                    "unit": norm_unit,
                    "dimension": dimension,
                    "form": form,
                    "source": {
                        "recipe_id": recipe.id,
                        "recipe_name": recipe.name,
                        "quantity": scaled_qty,
                        "unit": norm_unit,
                    },
                })

        # Group compatible items
        # Key: (ingredient_id or name.lower(), dimension, form)
        groups: Dict[Tuple[str, str, Optional[str]], Dict[str, Any]] = {}

        for item in raw_items:
            key_id = item["ingredient_id"] or item["ingredient_name"].strip().lower()
            key_dim = item["dimension"].value if hasattr(item["dimension"], "value") else str(item["dimension"])
            key_form = item["form"]
            group_key = (str(key_id), key_dim, key_form)

            if group_key not in groups:
                groups[group_key] = {
                    "ingredient_id": item["ingredient_id"],
                    "ingredient_name": item["ingredient_name"],
                    "dimension": item["dimension"],
                    "form": item["form"],
                    "quantities_and_units": [(item["quantity"], item["unit"])],
                    "source_recipes": [item["source"]],
                }
            else:
                groups[group_key]["quantities_and_units"].append((item["quantity"], item["unit"]))
                groups[group_key]["source_recipes"].append(item["source"])

        # Consolidate each group's quantities
        consolidated: List[Dict[str, Any]] = []

        for group in groups.values():
            dim = group["dimension"]
            pairs = group["quantities_and_units"]

            # Standard base units:
            # MASS -> g; if >= 1000g -> kg
            # VOLUME -> ml; if >= 1000ml -> l
            # COUNT -> piece
            if dim == UnitDimension.MASS:
                total_g = 0.0
                for q, u in pairs:
                    g_val, _ = convert_quantity(q, u, "g")
                    if g_val is not None:
                        total_g += g_val
                    else:
                        total_g += q  # fallback

                if total_g >= 1000.0:
                    final_qty = round(total_g / 1000.0, 3)
                    final_unit = "kg"
                else:
                    final_qty = round(total_g, 1)
                    final_unit = "g"

            elif dim == UnitDimension.VOLUME:
                total_ml = 0.0
                for q, u in pairs:
                    ml_val, _ = convert_quantity(q, u, "ml")
                    if ml_val is not None:
                        total_ml += ml_val
                    else:
                        total_ml += q

                if total_ml >= 1000.0:
                    final_qty = round(total_ml / 1000.0, 3)
                    final_unit = "l"
                else:
                    final_qty = round(total_ml, 1)
                    final_unit = "ml"

            elif dim == UnitDimension.COUNT:
                total_count = sum(q for q, _ in pairs)
                final_qty = round(total_count, 2)
                final_unit = pairs[0][1] if pairs else "piece"

            else:  # Descriptive
                # If units match, sum; else take first unit
                first_unit = pairs[0][1]
                if all(u == first_unit for _, u in pairs):
                    final_qty = round(sum(q for q, _ in pairs), 2)
                    final_unit = first_unit
                else:
                    final_qty = round(pairs[0][0], 2)
                    final_unit = first_unit

            consolidated.append({
                "ingredient_id": group["ingredient_id"],
                "ingredient_name": group["ingredient_name"],
                "required_quantity": final_qty,
                "unit": final_unit,
                "source_recipes": group["source_recipes"],
                "form": group["form"],
            })

        # Sort deterministically by ingredient name
        consolidated.sort(key=lambda x: x["ingredient_name"].lower())
        return consolidated

    # -------------------------------------------------------------------------
    # Non-Destructive Pantry Integration
    # -------------------------------------------------------------------------

    def apply_pantry_deductions(
        self, items: List[Dict[str, Any]], user_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Check pantry inventory against required quantities.
        Deducts available quantities ONLY when units are compatible.
        CRITICAL: Never mutates actual pantry inventory records.
        """
        if not user_id:
            for item in items:
                item["pantry_quantity"] = 0.0
                item["quantity_to_buy"] = item["required_quantity"]
                item["notes"] = None
            return items

        # Load user's pantry
        pantry_items = (
            self.db.query(PantryItem)
            .filter(PantryItem.user_id == user_id)
            .all()
        )

        pantry_by_ing_id = {pi.ingredient_id: pi for pi in pantry_items if pi.ingredient_id}
        pantry_by_name = {
            pi.ingredient.canonical_name.lower(): pi
            for pi in pantry_items
            if pi.ingredient and pi.ingredient.canonical_name
        }

        for item in items:
            matched_pantry: Optional[PantryItem] = None
            if item.get("ingredient_id") and item["ingredient_id"] in pantry_by_ing_id:
                matched_pantry = pantry_by_ing_id[item["ingredient_id"]]
            elif item["ingredient_name"].lower() in pantry_by_name:
                matched_pantry = pantry_by_name[item["ingredient_name"].lower()]

            if matched_pantry and matched_pantry.quantity > 0:
                p_unit = matched_pantry.unit or item["unit"]
                p_qty = matched_pantry.quantity

                if are_units_compatible(p_unit, item["unit"]):
                    converted_p_qty, _ = convert_quantity(p_qty, p_unit, item["unit"])
                    if converted_p_qty is not None:
                        deducted_qty = min(item["required_quantity"], converted_p_qty)
                        needed_qty = max(0.0, round(item["required_quantity"] - converted_p_qty, 4))

                        item["pantry_quantity"] = round(converted_p_qty, 4)
                        item["quantity_to_buy"] = needed_qty

                        if needed_qty == 0.0:
                            item["notes"] = f"Fulfilled by pantry ({p_qty} {p_unit} in stock)"
                        else:
                            item["notes"] = f"Partially covered by pantry ({p_qty} {p_unit} in stock)"
                        continue

                # Incompatible unit dimension: do not deduct
                item["pantry_quantity"] = 0.0
                item["quantity_to_buy"] = item["required_quantity"]
                item["notes"] = f"Pantry has {p_qty} {p_unit}, but unit is incompatible for automatic deduction"
            else:
                item["pantry_quantity"] = 0.0
                item["quantity_to_buy"] = item["required_quantity"]
                item["notes"] = None

        return items

    # -------------------------------------------------------------------------
    # Persistent Shopping List Generation & Refresh
    # -------------------------------------------------------------------------

    def generate_or_refresh_shopping_list(
        self,
        plan_id: str,
        user_id: Optional[str],
        deduct_pantry: bool = True,
        custom_name: Optional[str] = None,
    ) -> ShoppingList:
        """
        Generate or idempotently refresh a persistent shopping list from a meal plan.
        Preserves:
        - All manual items added by the user (is_manual=True).
        - Checked items (is_obtained=True).
        - User quantity overrides (user_quantity_override).
        - Stable item identifiers where ingredients continue to be needed.
        """
        plan = self.get_meal_plan(plan_id, user_id)

        # 1. Consolidate current ingredient requirements
        consolidated = self.consolidate_ingredients(plan)

        # 2. Apply pantry deductions if requested
        if deduct_pantry:
            consolidated = self.apply_pantry_deductions(consolidated, user_id)
        else:
            for item in consolidated:
                item["pantry_quantity"] = 0.0
                item["quantity_to_buy"] = item["required_quantity"]
                item["notes"] = None

        # 3. Find or create ShoppingList record
        shopping_list = (
            self.db.query(ShoppingList)
            .filter(ShoppingList.meal_plan_id == plan.id)
            .first()
        )

        if not shopping_list:
            list_name = custom_name or f"{plan.name} — Shopping List"
            shopping_list = ShoppingList(
                user_id=user_id,
                meal_plan_id=plan.id,
                name=list_name,
                status="active",
            )
            self.db.add(shopping_list)
            self.db.flush()

        # 4. Map existing items by (ingredient_name.lower(), unit.lower())
        existing_items = list(shopping_list.items)
        existing_by_key = {
            (ei.ingredient_name.strip().lower(), ei.unit.strip().lower()): ei
            for ei in existing_items
            if not ei.is_manual
        }
        retained_item_ids = set()

        # Update or insert generated requirements
        for c in consolidated:
            key = (c["ingredient_name"].strip().lower(), c["unit"].strip().lower())
            if key in existing_by_key:
                # Update existing generated item in-place (preserving id, override, and checked status)
                existing_item = existing_by_key[key]
                existing_item.required_quantity = c["required_quantity"]
                existing_item.pantry_quantity = c["pantry_quantity"]
                existing_item.quantity_to_buy = c["quantity_to_buy"]
                existing_item.source_recipes = c["source_recipes"]
                existing_item.updated_at = datetime.now(timezone.utc)
                if c.get("notes") and not existing_item.notes:
                    existing_item.notes = c["notes"]
                retained_item_ids.add(existing_item.id)
            else:
                # Create new item
                new_item = ShoppingListItem(
                    shopping_list_id=shopping_list.id,
                    ingredient_id=c.get("ingredient_id"),
                    ingredient_name=c["ingredient_name"],
                    required_quantity=c["required_quantity"],
                    unit=c["unit"],
                    pantry_quantity=c["pantry_quantity"],
                    quantity_to_buy=c["quantity_to_buy"],
                    is_obtained=0,
                    is_manual=0,
                    source_recipes=c["source_recipes"],
                    notes=c.get("notes"),
                )
                self.db.add(new_item)
                self.db.flush()
                retained_item_ids.add(new_item.id)

        # 5. Clean up obsolete items:
        # Delete only generated items that are no longer needed AND have not been checked off.
        for ei in existing_items:
            if not ei.is_manual and ei.id not in retained_item_ids:
                if not ei.is_obtained:
                    self.db.delete(ei)

        shopping_list.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(shopping_list)
        return shopping_list

    # -------------------------------------------------------------------------
    # Shopping List Items CRUD & Manual Additions
    # -------------------------------------------------------------------------

    def create_shopping_list(
        self,
        user_id: Optional[str],
        name: str = "My Shopping List",
        meal_plan_id: Optional[str] = None,
    ) -> ShoppingList:
        """Create a standalone or plan-associated shopping list."""
        slist = ShoppingList(
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            name=name,
            status="active",
        )
        self.db.add(slist)
        self.db.commit()
        self.db.refresh(slist)
        return slist

    def get_shopping_list(self, list_id: str, user_id: Optional[str]) -> ShoppingList:
        """Retrieve shopping list with ownership validation."""
        query = self.db.query(ShoppingList).filter(ShoppingList.id == list_id)
        if user_id:
            query = query.filter(ShoppingList.user_id == user_id)
        else:
            query = query.filter(ShoppingList.user_id.is_(None))
        slist = query.first()
        if not slist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shopping list '{list_id}' not found.",
            )
        return slist

    def list_shopping_lists(self, user_id: Optional[str]) -> List[ShoppingList]:
        """List user's shopping lists."""
        query = self.db.query(ShoppingList)
        if user_id:
            query = query.filter(ShoppingList.user_id == user_id)
        else:
            query = query.filter(ShoppingList.user_id.is_(None))
        return query.order_by(ShoppingList.created_at.desc()).all()

    def add_manual_item(
        self, list_id: str, user_id: Optional[str], payload: ShoppingListItemCreate
    ) -> ShoppingListItem:
        """Add a custom user item to an existing shopping list."""
        slist = self.get_shopping_list(list_id, user_id)

        item = ShoppingListItem(
            shopping_list_id=slist.id,
            ingredient_name=payload.ingredient_name,
            required_quantity=payload.quantity,
            unit=payload.unit,
            pantry_quantity=0.0,
            quantity_to_buy=payload.quantity,
            is_obtained=0,
            is_manual=1,
            source_recipes=[],
            notes=payload.notes,
        )
        self.db.add(item)
        slist.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_shopping_list_item(
        self, list_id: str, item_id: str, user_id: Optional[str], payload: ShoppingListItemUpdate
    ) -> ShoppingListItem:
        """Update an item's checked status, manual quantity override, or notes."""
        slist = self.get_shopping_list(list_id, user_id)
        item = (
            self.db.query(ShoppingListItem)
            .filter(
                ShoppingListItem.id == item_id,
                ShoppingListItem.shopping_list_id == slist.id,
            )
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item '{item_id}' not found in shopping list '{list_id}'.",
            )

        if payload.is_obtained is not None:
            item.is_obtained = 1 if payload.is_obtained else 0
        if payload.user_quantity_override is not None:
            item.user_quantity_override = payload.user_quantity_override
        if payload.notes is not None:
            item.notes = payload.notes

        item.updated_at = datetime.now(timezone.utc)
        slist.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_shopping_list_item(
        self, list_id: str, item_id: str, user_id: Optional[str]
    ) -> None:
        """Delete an item from the shopping list."""
        slist = self.get_shopping_list(list_id, user_id)
        item = (
            self.db.query(ShoppingListItem)
            .filter(
                ShoppingListItem.id == item_id,
                ShoppingListItem.shopping_list_id == slist.id,
            )
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item '{item_id}' not found in shopping list '{list_id}'.",
            )
        self.db.delete(item)
        slist.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    # -------------------------------------------------------------------------
    # Grocery Comparison Integration
    # -------------------------------------------------------------------------

    def compare_shopping_list_grocery(
        self, list_id: str, user_id: Optional[str]
    ) -> ShoppingListGroceryComparisonResponse:
        """
        Integrates shopping list items with the Phase 8 price comparison & grocery matching engine.
        Returns product matches, standardized unit prices, savings, in-stock status, and discloses
        unmatched items without fabricating full-basket completion.
        """
        slist = self.get_shopping_list(list_id, user_id)
        grocery_service = GroceryService(self.db)

        item_matches: List[ShoppingListGroceryItemMatch] = []
        unmatched: List[str] = []
        total_estimated_cost: float = 0.0
        all_matched = True

        for item in slist.items:
            # Determine effective quantity needed
            qty_needed = (
                item.user_quantity_override
                if item.user_quantity_override is not None
                else item.quantity_to_buy
            )

            # Skip items that are already obtained or have 0 quantity needed
            if item.is_obtained or qty_needed <= 0.0:
                continue

            try:
                match_response = grocery_service.match_products_for_ingredient(
                    ingredient=item.ingredient_name,
                    limit=5,
                    sort_by="total_price",
                )
                products = [p.model_dump() for p in match_response.results]
                best_prod = products[0] if products else None

                if best_prod and best_prod.get("price") is not None:
                    # Calculate estimated cost for this line
                    pkg_price = float(best_prod["price"])
                    total_estimated_cost += pkg_price
                else:
                    all_matched = False
                    unmatched.append(item.ingredient_name)

                item_matches.append(
                    ShoppingListGroceryItemMatch(
                        item_id=item.id,
                        ingredient_name=item.ingredient_name,
                        quantity_needed=qty_needed,
                        unit=item.unit,
                        matched_products=products,
                        best_product=best_prod,
                        missing_reason=None if products else "No matching products found in grocery catalog",
                    )
                )
            except Exception as e:
                all_matched = False
                unmatched.append(item.ingredient_name)
                item_matches.append(
                    ShoppingListGroceryItemMatch(
                        item_id=item.id,
                        ingredient_name=item.ingredient_name,
                        quantity_needed=qty_needed,
                        unit=item.unit,
                        matched_products=[],
                        best_product=None,
                        missing_reason=f"Error matching product: {str(e)}",
                    )
                )

        return ShoppingListGroceryComparisonResponse(
            shopping_list_id=slist.id,
            items=item_matches,
            store_baskets=[],
            unmatched_ingredients=unmatched,
            total_estimated_cost=round(total_estimated_cost, 2) if total_estimated_cost > 0 else None,
            is_complete=all_matched and len(unmatched) == 0 and len(item_matches) > 0,
            notes="Estimated total cost reflects best available product per ingredient line. Unmatched items are excluded from total."
            if unmatched
            else None,
        )
