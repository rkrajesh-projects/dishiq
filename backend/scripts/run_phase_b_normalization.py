import os
import sys
import logging
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.recipe import Recipe
from app.services.recipe_quality_service import RecipeQualityAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dishiq.phase_b")

def run_normalization():
    db: Session = SessionLocal()
    try:
        recipes = db.query(Recipe).all()
        logger.info(f"Found {len(recipes)} recipes to normalize.")
        
        normalized_count = 0
        for recipe in recipes:
            if RecipeQualityAnalyzer.normalize_instructions(recipe):
                normalized_count += 1
                
        db.commit()
        logger.info(f"Successfully normalized instructions for {normalized_count} recipes.")
    except Exception as e:
        logger.error(f"Error during normalization: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_normalization()
