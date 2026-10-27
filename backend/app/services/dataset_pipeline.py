"""
DishIQ Indian Recipe Dataset Pipeline

Handles provenance, validation, deduplication, and safe import of verified Indian recipes.
Supports extending with multiple source adapters.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.recipe import Recipe, RecipeIngredient, Ingredient


class Provenance(BaseModel):
    source_name: str
    source_url: Optional[str] = None
    source_recipe_id: Optional[str] = None
    source_license: Optional[str] = "UNKNOWN"
    author: Optional[str] = None
    dataset_version: str
    verification_status: str = "UNVERIFIED"
    verification_level: str = "NONE"


class NormalizedIngredient(BaseModel):
    raw_text: str
    canonical_name: str
    quantity: float
    unit: str
    preparation: Optional[str] = None


class ImportedRecipe(BaseModel):
    name: str
    original_name: Optional[str] = None
    original_language: Optional[str] = None
    description: str = ""
    cuisine: str
    dietary_type: str
    region: Optional[str] = None
    state: Optional[str] = None
    is_indian_recipe: bool = True
    preparation_minutes: int = 0
    cooking_minutes: int = 0
    servings: int = 4
    instructions: List[str] = Field(default_factory=list)
    ingredients: List[NormalizedIngredient] = Field(default_factory=list)
    provenance: Provenance


class DatasetPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.manifest = {
            "dataset_version": None,
            "sources": [],
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "duplicates": 0,
            "verified_records": 0,
        }

    def _normalize_ingredient_name(self, name: str) -> str:
        """Basic ingredient normalization (spelling, case)."""
        name = name.lower().strip()
        # Aliases specific to Indian datasets
        aliases = {
            "tomatoes": "tomato",
            "onions": "onion",
            "potatoes": "potato",
            "dhaniya": "coriander leaves",
            "jeera": "cumin seeds",
            "haldi": "turmeric powder",
            "mirchi": "green chilli",
        }
        return aliases.get(name, name)

    def validate_recipe(self, recipe: ImportedRecipe) -> bool:
        """Deterministic validation rules."""
        if not recipe.name or not recipe.name.strip():
            return False
        if not recipe.ingredients:
            return False
        if not recipe.instructions:
            return False
        if not recipe.provenance.source_name:
            return False
        return True

    def is_duplicate(self, recipe: ImportedRecipe) -> bool:
        """Check for duplicates by name or source_recipe_id."""
        query = self.db.query(Recipe)
        if recipe.provenance.source_recipe_id:
            existing = query.filter(Recipe.source_recipe_id == recipe.provenance.source_recipe_id).first()
            if existing:
                return True
                
        # Fuzzy match on name to avoid duplicate regions
        existing_by_name = query.filter(Recipe.name == recipe.name).first()
        if existing_by_name:
            # Check if it's from the same exact source
            if existing_by_name.source_name == recipe.provenance.source_name:
                return True
        return False

    def get_or_create_ingredient(self, canonical_name: str, category: str = "Pantry") -> Ingredient:
        normalized = self._normalize_ingredient_name(canonical_name)
        ing = self.db.query(Ingredient).filter(Ingredient.canonical_name == normalized).first()
        if not ing:
            ing = Ingredient(canonical_name=normalized, category=category)
            self.db.add(ing)
            self.db.flush()
        return ing

    def process_import(self, recipes: List[ImportedRecipe], version: str) -> Dict[str, Any]:
        self.manifest["dataset_version"] = version
        self.manifest["total_records"] = len(recipes)
        
        sources = set()

        try:
            for rec in recipes:
                sources.add(rec.provenance.source_name)
                
                if not self.validate_recipe(rec):
                    self.manifest["invalid_records"] += 1
                    continue
                    
                if self.is_duplicate(rec):
                    self.manifest["duplicates"] += 1
                    continue
                    
                self.manifest["valid_records"] += 1
                if rec.provenance.verification_status in ["VERIFIED", "SOURCE_AUTHORED"]:
                    self.manifest["verified_records"] += 1

                # Insert Recipe
                db_recipe = Recipe(
                    name=rec.name,
                    original_name=rec.original_name,
                    original_language=rec.original_language,
                    description=rec.description,
                    cuisine=rec.cuisine,
                    dietary_type=rec.dietary_type,
                    region=rec.region,
                    state=rec.state,
                    is_indian_recipe=rec.is_indian_recipe,
                    preparation_minutes=rec.preparation_minutes,
                    cooking_minutes=rec.cooking_minutes,
                    servings=rec.servings,
                    instructions=[{"text": step} for step in rec.instructions],
                    source_name=rec.provenance.source_name,
                    source_url=rec.provenance.source_url,
                    source_recipe_id=rec.provenance.source_recipe_id,
                    source_license=rec.provenance.source_license,
                    author=rec.provenance.author,
                    verification_status=rec.provenance.verification_status,
                    verification_level=rec.provenance.verification_level,
                    dataset_version=rec.provenance.dataset_version,
                    collected_at=datetime.now(timezone.utc),
                )
                self.db.add(db_recipe)
                self.db.flush()

                # Insert Ingredients
                for ing_data in rec.ingredients:
                    ing = self.get_or_create_ingredient(ing_data.canonical_name)
                    ri = RecipeIngredient(
                        recipe_id=db_recipe.id,
                        ingredient_id=ing.id,
                        raw_text=ing_data.raw_text,
                        quantity=ing_data.quantity,
                        unit=ing_data.unit,
                        preparation_note=ing_data.preparation
                    )
                    self.db.add(ri)
                    
            self.manifest["sources"] = list(sources)
            self.db.commit()
            return self.manifest
        except Exception:
            self.db.rollback()
            raise
