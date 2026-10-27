import os
import sys
import joblib
import numpy as np
import logging
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from app.db.session import SessionLocal
from app.models.recipe import Recipe

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def auto_tag_cuisines():
    logger.info("Starting Cuisine Auto-Tagging Process...")
    
    artifact_path = os.path.join(PROJECT_ROOT, "ml", "artifacts", "cuisine_classifier_v1.joblib")
    if not os.path.exists(artifact_path):
        logger.error(f"Classifier artifact not found: {artifact_path}")
        return
        
    classifier = joblib.load(artifact_path)
    cuisines = classifier["cuisines"]
    cuisine_embeddings = classifier["embeddings"]
    
    pretrained_dir = os.path.join(PROJECT_ROOT, "ml", "models", "pretrained")
    model = SentenceTransformer(classifier["model_name"], cache_folder=pretrained_dir)
    
    db: Session = SessionLocal()
    
    try:
        # Find recipes with 'Unknown' cuisine or empty
        unknown_recipes = db.query(Recipe).filter(
            (Recipe.cuisine == 'Unknown') | 
            (Recipe.cuisine == None) | 
            (Recipe.cuisine == '')
        ).all()
        
        logger.info(f"Found {len(unknown_recipes)} recipes requiring cuisine classification.")
        if len(unknown_recipes) == 0:
            return
            
        updated_count = 0
        batch_texts = []
        recipes_batch = []
        
        for i, recipe in enumerate(unknown_recipes):
            ingredients_text = " ".join([ri.ingredient.canonical_name for ri in recipe.ingredients])
            text = f"{recipe.name} {ingredients_text}"
            
            batch_texts.append(text)
            recipes_batch.append(recipe)
            
            # Process in batches of 64
            if len(batch_texts) == 64 or i == len(unknown_recipes) - 1:
                embs = model.encode(batch_texts, convert_to_numpy=True)
                sims = cosine_similarity(embs, cuisine_embeddings)
                
                for j, sim_scores in enumerate(sims):
                    best_idx = np.argmax(sim_scores)
                    best_cuisine = cuisines[best_idx]
                    best_score = sim_scores[best_idx]
                    
                    if best_score > 0.15:
                        recipes_batch[j].cuisine = best_cuisine
                        updated_count += 1
                        
                db.commit()
                logger.info(f"Processed {i+1}/{len(unknown_recipes)} recipes...")
                
                batch_texts = []
                recipes_batch = []
                
        logger.info(f"Successfully auto-tagged {updated_count} recipes!")
        
    finally:
        db.close()

if __name__ == "__main__":
    auto_tag_cuisines()
