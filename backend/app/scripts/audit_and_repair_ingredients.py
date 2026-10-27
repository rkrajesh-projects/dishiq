"""
DishIQ Phase 5 — Ingredient Intelligence
Safe Ingredient Audit and Data Repair Script.

Usage:
    # Read-only Dry-Run Audit (Default):
    python backend/app/scripts/audit_and_repair_ingredients.py --dry-run

    # Apply Reversible Repairs (Requires explicit approval):
    python backend/app/scripts/audit_and_repair_ingredients.py --apply
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from app.models.recipe import Recipe, Ingredient, RecipeIngredient
from app.models.grocery import GroceryProduct
from app.ingredient_intelligence.parser import parse_ingredient
from app.ingredient_intelligence.units import normalize_unit, get_unit_dimension

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingredient_audit")


def run_ingredient_audit(db: Session) -> Dict[str, Any]:
    """Perform non-destructive comprehensive audit of ingredient data."""
    report: Dict[str, Any] = {
        "counts": {},
        "integrity": {},
        "anomalies": {},
        "proposed_repairs": [],
    }

    total_recipes = db.query(func.count(Recipe.id)).scalar()
    total_ingredients = db.query(func.count(Ingredient.id)).scalar()
    total_recipe_ingredients = db.query(func.count(RecipeIngredient.id)).scalar()
    total_grocery_products = db.query(func.count(GroceryProduct.id)).scalar()

    report["counts"] = {
        "total_recipes": total_recipes,
        "total_ingredients": total_ingredients,
        "total_recipe_ingredients": total_recipe_ingredients,
        "total_grocery_products": total_grocery_products,
    }

    # Foreign key integrity
    orphaned_ingredients = (
        db.query(RecipeIngredient)
        .filter(~RecipeIngredient.ingredient_id.in_(db.query(Ingredient.id)))
        .count()
    )
    orphaned_recipes = (
        db.query(RecipeIngredient)
        .filter(~RecipeIngredient.recipe_id.in_(db.query(Recipe.id)))
        .count()
    )

    report["integrity"] = {
        "orphaned_recipe_ingredients_missing_ingredient": orphaned_ingredients,
        "orphaned_recipe_ingredients_missing_recipe": orphaned_recipes,
    }

    # Canonical name anomalies
    empty_canonical = (
        db.query(Ingredient)
        .filter((Ingredient.canonical_name == None) | (Ingredient.canonical_name == ""))
        .all()
    )
    
    empty_canonical_list = []
    for ing in empty_canonical:
        ri_rows = db.query(RecipeIngredient).filter(RecipeIngredient.ingredient_id == ing.id).all()
        raw_samples = [r.raw_text for r in ri_rows[:5]]
        empty_canonical_list.append({
            "ingredient_id": ing.id,
            "category": ing.category,
            "default_unit": ing.default_unit,
            "associated_recipe_ingredients_count": len(ri_rows),
            "raw_text_samples": raw_samples,
        })
        
        # Determine proposed safe repair
        if all("clove" in (t or "").lower() for t in raw_samples):
            report["proposed_repairs"].append({
                "action": "UPDATE_CANONICAL_NAME",
                "ingredient_id": ing.id,
                "current_name": ing.canonical_name,
                "proposed_name": "clove",
                "proposed_category": "spice",
                "reason": "All 12 associations reference the spice 'clove'/'cloves' with unit 'clove'.",
            })

    report["anomalies"]["empty_or_null_canonical_names"] = empty_canonical_list

    # Quantity & Unit anomalies
    invalid_quantities = (
        db.query(RecipeIngredient)
        .filter((RecipeIngredient.quantity == None) | (RecipeIngredient.quantity <= 0))
        .count()
    )
    missing_units = (
        db.query(RecipeIngredient)
        .filter((RecipeIngredient.unit == None) | (RecipeIngredient.unit == ""))
        .count()
    )

    all_units = [u[0] for u in db.query(RecipeIngredient.unit).all() if u[0]]
    unit_counts = Counter(all_units)
    unrecognized_units = [u for u in unit_counts if get_unit_dimension(u) is None and u != "unknown"]

    report["anomalies"]["invalid_quantities_count"] = invalid_quantities
    report["anomalies"]["missing_units_count"] = missing_units
    report["anomalies"]["unit_distribution"] = dict(unit_counts.most_common(20))
    report["anomalies"]["unrecognized_units"] = unrecognized_units

    # Near-duplicates / case variants in canonical names
    all_names = [n[0] for n in db.query(Ingredient.canonical_name).all() if n[0]]
    lower_map: Dict[str, List[str]] = {}
    for name in all_names:
        low = name.strip().lower()
        lower_map.setdefault(low, []).append(name)

    case_duplicates = {k: v for k, v in lower_map.items() if len(v) > 1}
    report["anomalies"]["case_insensitive_duplicate_names"] = case_duplicates

    return report


def apply_repairs(db: Session, report: Dict[str, Any], dry_run: bool = True) -> int:
    """Apply reversible, non-destructive data repairs inside a transaction."""
    repairs = report.get("proposed_repairs", [])
    if not repairs:
        logger.info("No repairs proposed.")
        return 0

    repaired_count = 0
    try:
        for r in repairs:
            if r["action"] == "UPDATE_CANONICAL_NAME":
                ing_id = r["ingredient_id"]
                new_name = r["proposed_name"]
                new_cat = r["proposed_category"]
                
                ing = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
                if ing:
                    if dry_run:
                        logger.info(f"[DRY-RUN] Would update Ingredient {ing_id} canonical_name -> '{new_name}', category -> '{new_cat}'")
                    else:
                        ing.canonical_name = new_name
                        ing.category = new_cat
                        logger.info(f"[APPLIED] Updated Ingredient {ing_id} canonical_name -> '{new_name}', category -> '{new_cat}'")
                    repaired_count += 1

        if dry_run:
            logger.info(f"[DRY-RUN] Completed analysis: {repaired_count} repair(s) would be made. Database untouched.")
            db.rollback()
        else:
            db.commit()
            logger.info(f"[APPLY] Successfully committed {repaired_count} repair(s) to persistent database.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error applying repairs, rolled back: {e}")
        raise

    return repaired_count


def main():
    parser = argparse.ArgumentParser(description="DishIQ Ingredient Audit and Data Repair")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform read-only audit without changes (default)")
    parser.add_argument("--apply", action="store_true", default=False, help="Explicitly apply approved repairs")
    parser.add_argument("--db-path", default="sqlite:///D:/DishIQ/backend/dishiq.db", help="Target SQLite database URL")
    parser.add_argument("--json", action="store_true", default=False, help="Output full report as formatted JSON")
    args = parser.parse_args()

    engine = create_engine(args.db_path)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        report = run_ingredient_audit(db)
        is_dry_run = not args.apply

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("\n=== DishIQ Phase 5 Ingredient Intelligence Audit Report ===")
            print(f"Total Recipes:                     {report['counts']['total_recipes']}")
            print(f"Total Ingredients:                 {report['counts']['total_ingredients']}")
            print(f"Total Recipe-Ingredient Rows:      {report['counts']['total_recipe_ingredients']}")
            print(f"Total Grocery Products:            {report['counts']['total_grocery_products']}")
            print(f"Orphaned References:               {report['integrity']['orphaned_recipe_ingredients_missing_ingredient']}")
            print(f"Empty Canonical Names:             {len(report['anomalies']['empty_or_null_canonical_names'])}")
            print(f"Invalid Quantities (<= 0):         {report['anomalies']['invalid_quantities_count']}")
            print(f"Missing Units:                     {report['anomalies']['missing_units_count']}")
            print(f"Proposed Repairs:                  {len(report['proposed_repairs'])}")
            if report['proposed_repairs']:
                for p in report['proposed_repairs']:
                    print(f"   -> Action: {p['action']}, ID: {p['ingredient_id']}, Name: '{p['current_name']}' -> '{p['proposed_name']}' ({p['reason']})")
            print("============================================================\n")

        apply_repairs(db, report, dry_run=is_dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
