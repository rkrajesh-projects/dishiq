import os
import sys
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import ast

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, init_db, engine
from app.db.base import Base
from app.models.recipe import Recipe, Ingredient, RecipeIngredient
from app.ingredient_intelligence.parser import parse_ingredient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dishiq.dataset_import")

_host_path = backend_dir.parent / "dataset" / "RAW_recipes.csv"
_docker_path = backend_dir / "dataset" / "RAW_recipes.csv"
DATASET_PATH = _docker_path if _docker_path.exists() else _host_path

def get_or_create_ingredient(db: Session, canonical_name: str, category: str = "Unknown") -> Ingredient:
    ing = db.query(Ingredient).filter(Ingredient.canonical_name == canonical_name).first()
    if not ing:
        ing = Ingredient(
            canonical_name=canonical_name,
            category=category or "Unknown",
            default_unit="grams"
        )
        db.add(ing)
        db.flush()
    return ing

def import_recipes(limit: int = 100):
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found at {DATASET_PATH}")
        return

    logger.info(f"Starting dataset import from {DATASET_PATH} (limit: {limit})")
    
    db: Session = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        
        current_count = db.query(Recipe).count()
        logger.info(f"Current recipe count: {current_count}")
        
        with open(DATASET_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            recipes_added = 0
            for row in reader:
                if recipes_added >= limit:
                    break
                    
                try:
                    name = row["name"].strip()
                    if not name:
                        continue
                        
                    # Normalize title - Title Case
                    name = name.title()
                        
                    exists = db.query(Recipe).filter(Recipe.name == name).first()
                    if exists:
                        continue
                    
                    try:
                        steps = ast.literal_eval(row["steps"])
                    except:
                        steps = []
                        
                    try:
                        tags = ast.literal_eval(row["tags"])
                    except:
                        tags = []
                    
                    cuisine = "Unknown"
                    dietary_type = "Standard"
                    
                    if "vegetarian" in tags:
                        dietary_type = "Vegetarian"
                    if "vegan" in tags:
                        dietary_type = "Vegan"
                        
                    recipe = Recipe(
                        name=name,
                        description=row["description"] or "",
                        cuisine=cuisine,
                        dietary_type=dietary_type,
                        preparation_minutes=0,
                        cooking_minutes=int(row["minutes"]) if row["minutes"].isdigit() else 0,
                        servings=4,
                        instructions=steps,
                        source_name="Food.com Dataset",
                        source_url=f"https://www.food.com/recipe/{row['id']}"
                    )
                    db.add(recipe)
                    db.flush()
                    
                    try:
                        raw_ingredients = ast.literal_eval(row["ingredients"])
                    except:
                        raw_ingredients = []
                        
                    for raw_ing in raw_ingredients:
                        parsed = parse_ingredient(raw_ing)
                        
                        ing_model = get_or_create_ingredient(
                            db, 
                            parsed.canonical_name, 
                            parsed.category
                        )
                        
                        qty = parsed.quantity if parsed.quantity is not None else 1.0
                        unit = parsed.unit if parsed.unit is not None else ing_model.default_unit
                        
                        ri = RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_id=ing_model.id,
                            raw_text=raw_ing,
                            quantity=qty,
                            unit=unit,
                            preparation_note=parsed.preparation_note
                        )
                        db.add(ri)
                    
                    recipes_added += 1
                    
                    if recipes_added % 100 == 0:
                        db.commit()
                        logger.info(f"Imported {recipes_added} recipes...")
                        
                except Exception as e:
                    logger.warning(f"Error processing row {row.get('id')}: {e}")
                    db.rollback()
            
            db.commit()
            logger.info(f"Import completed. Added {recipes_added} recipes.")
            
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    import_recipes(limit=limit)
