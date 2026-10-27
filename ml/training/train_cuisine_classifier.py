import os
import joblib
import numpy as np
import logging
from sentence_transformers import SentenceTransformer

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
PRETRAINED_DIR = os.path.join(ML_DIR, "models", "pretrained")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# The target cuisines we want to classify recipes into
TARGET_CUISINES = [
    "American", 
    "Italian", 
    "Mexican", 
    "Indian", 
    "Chinese", 
    "Thai", 
    "Middle Eastern", 
    "French", 
    "Mediterranean", 
    "British", 
    "Greek",
    "Japanese",
    "Korean",
    "Spanish"
]

def train_zero_shot_classifier():
    logger.info("Initializing Zero-Shot Cuisine Classifier...")
    
    # Load the same sentence transformer used for semantic search
    model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=PRETRAINED_DIR)
    
    # Create descriptive prompts to improve embedding quality
    prompts = [f"A traditional {cuisine.lower()} recipe with typical ingredients and authentic flavor" for cuisine in TARGET_CUISINES]
    
    logger.info("Computing centroid embeddings for cuisines...")
    cuisine_embeddings = model.encode(prompts, convert_to_numpy=True)
    
    artifact = {
        "cuisines": TARGET_CUISINES,
        "embeddings": cuisine_embeddings,
        "model_name": "all-MiniLM-L6-v2",
        "description": "Zero-shot centroid embeddings for cuisine classification"
    }
    
    out_path = os.path.join(ARTIFACTS_DIR, "cuisine_classifier_v1.joblib")
    joblib.dump(artifact, out_path)
    logger.info(f"Saved artifact to {out_path}")
    
    print("Done! Centroids generated and saved.")

if __name__ == "__main__":
    train_zero_shot_classifier()
