"""
DishIQ Phase 6.1 — Grocery Product Matching
Embedding Storage & Cache module.

Provides joblib-based serialization/deserialization for precomputed product embeddings.
Prevents re-encoding entire product catalogs on every match request.
"""
import os
import time
from typing import Dict, Any, Optional, List
import joblib
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.grocery import GroceryProduct
from app.product_matching.encoder import get_encoder, ProductEncoder
from app.product_matching.preprocessing import preprocess_product_for_matching


def save_product_embeddings_artifact(
    embeddings_data: Dict[str, Any],
    artifact_path: Optional[str] = None,
) -> str:
    """
    Save precomputed product embeddings dictionary to a joblib artifact file.
    """
    target_path = artifact_path or settings.PRODUCT_EMBEDDINGS_ARTIFACT_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    joblib.dump(embeddings_data, target_path, compress=3)
    logger.info(
        f"Saved product embeddings artifact to [{target_path}] "
        f"({len(embeddings_data.get('products', {}))} products)"
    )
    return target_path


def load_product_embeddings_artifact(
    artifact_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Load precomputed product embeddings from joblib artifact file.
    Returns None if file does not exist or is corrupted.
    """
    target_path = artifact_path or settings.PRODUCT_EMBEDDINGS_ARTIFACT_PATH
    if not os.path.exists(target_path):
        return None

    try:
        data = joblib.load(target_path)
        if isinstance(data, dict) and "products" in data:
            return data
    except Exception as e:
        logger.error(f"Failed to load product embeddings artifact from {target_path}: {e}")
    return None


def build_product_embeddings_from_db(
    db: Session,
    encoder: Optional[ProductEncoder] = None,
) -> Dict[str, Any]:
    """
    Query all GroceryProduct records in the database, compute their embeddings,
    and return a precomputed artifact dictionary structure.
    """
    enc = encoder or get_encoder()
    products: List[GroceryProduct] = db.query(GroceryProduct).all()

    if not products:
        return {
            "model_name": enc.model_name,
            "created_at": time.time(),
            "products": {},
        }

    texts = [
        preprocess_product_for_matching(p.name, p.brand, p.category)
        for p in products
    ]

    embeddings = enc.encode_texts(texts)

    products_dict: Dict[str, Dict[str, Any]] = {}
    for idx, p in enumerate(products):
        products_dict[p.id] = {
            "product_id": p.id,
            "product_name": p.name,
            "name": p.name,
            "brand": p.brand,
            "category": p.category,
            "store_id": p.store_id,
            "store_name": p.store.name if p.store else None,
            "price": p.prices[0].price if p.prices else None,
            "package_quantity": p.package_quantity,
            "package_unit": p.package_unit,
            "matched_text": texts[idx],
            "embedding": embeddings[idx],
        }

    return {
        "model_name": enc.model_name,
        "created_at": time.time(),
        "products": products_dict,
    }
