"""
DishIQ Phase 6.1 — Grocery Product Matching Foundation
Package entry points for encoder, matcher, schemas, preprocessing, and caching.
"""

from app.product_matching.encoder import ProductEncoder, get_encoder
from app.product_matching.matcher import ProductMatcher, compute_cosine_similarity
from app.product_matching.schemas import (
    ProductMatchResult,
    MatchIngredientsRequest,
    MatchIngredientsResponse,
)
from app.product_matching.preprocessing import (
    preprocess_ingredient_for_matching,
    preprocess_product_for_matching,
)
from app.product_matching.cache import (
    save_product_embeddings_artifact,
    load_product_embeddings_artifact,
    build_product_embeddings_from_db,
)

__all__ = [
    "ProductEncoder",
    "get_encoder",
    "ProductMatcher",
    "compute_cosine_similarity",
    "ProductMatchResult",
    "MatchIngredientsRequest",
    "MatchIngredientsResponse",
    "preprocess_ingredient_for_matching",
    "preprocess_product_for_matching",
    "save_product_embeddings_artifact",
    "load_product_embeddings_artifact",
    "build_product_embeddings_from_db",
]
