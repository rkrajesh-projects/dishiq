"""
DishIQ Indian Recipe Dataset Importer
Run from repo root: python backend/scripts/import_indian_recipes.py
"""
import os
import sys
import csv
import json
from datetime import datetime

# Path setup
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_DIR = os.path.join(REPO_ROOT, 'backend')
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, BACKEND_DIR)

# Change working directory so sqlite:///dishiq.db works
os.chdir(BACKEND_DIR)

from app.db.session import SessionLocal
from app.services.dataset_pipeline import DatasetPipeline, ImportedRecipe, NormalizedIngredient, Provenance

DATASET_PATH = os.path.join(REPO_ROOT, "dataset", "sample_indian_recipes.csv")
DATASET_VERSION = "indian-recipes-v1-sample"

def parse_dataset(file_path: str) -> list[ImportedRecipe]:
    recipes = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Parse ingredients JSON
                raw_ingr = json.loads(row.get("ingredients_json", "[]"))
                ingredients = []
                for ri in raw_ingr:
                    ingredients.append(NormalizedIngredient(
                        raw_text=ri.get("raw", ""),
                        canonical_name=ri.get("name", ""),
                        quantity=float(ri.get("qty", 1.0)),
                        unit=ri.get("unit", "unknown")
                    ))
                
                # Parse instructions JSON
                instructions = json.loads(row.get("instructions_json", "[]"))
                
                prov = Provenance(
                    source_name=row.get("source_name", "UNKNOWN"),
                    source_url=row.get("source_url") or None,
                    source_recipe_id=row.get("source_recipe_id") or None,
                    source_license=row.get("source_license") or "UNKNOWN",
                    author=row.get("author") or None,
                    dataset_version=DATASET_VERSION,
                    verification_status=row.get("verification_status", "UNVERIFIED"),
                    verification_level=row.get("verification_level", "NONE")
                )
                
                rec = ImportedRecipe(
                    name=row["name"],
                    original_name=row.get("original_name") or None,
                    original_language=row.get("original_language") or None,
                    cuisine=row["cuisine"],
                    dietary_type=row["dietary_type"],
                    region=row.get("region") or None,
                    state=row.get("state") or None,
                    is_indian_recipe=True,
                    preparation_minutes=int(row.get("prep_time", 0)),
                    cooking_minutes=int(row.get("cook_time", 0)),
                    servings=int(row.get("servings", 4)),
                    instructions=instructions,
                    ingredients=ingredients,
                    provenance=prov
                )
                recipes.append(rec)
            except Exception as e:
                print(f"Skipping row {row.get('source_recipe_id')} due to error: {e}")
    return recipes

def main():
    print(f"=== DishIQ Indian Recipe Import ({DATASET_VERSION}) ===")
    if not os.path.exists(DATASET_PATH):
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        sys.exit(1)
        
    recipes = parse_dataset(DATASET_PATH)
    print(f"Parsed {len(recipes)} recipes from CSV.")
    
    db = SessionLocal()
    try:
        pipeline = DatasetPipeline(db)
        manifest = pipeline.process_import(recipes, DATASET_VERSION)
        
        print("\n=== IMPORT MANIFEST ===")
        print(json.dumps(manifest, indent=2))
        print("=======================")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
