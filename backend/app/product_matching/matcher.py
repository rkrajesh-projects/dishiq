"""
DishIQ Phase 6.1 â€” Grocery Product Matching
Product Matcher module.

Calculates cosine similarity between ingredient embeddings and grocery product embeddings,
ranks products by semantic similarity, applies configurable match thresholds, and returns
typed ProductMatchResult objects.
"""
from typing import List, Dict, Any, Optional, Union
import numpy as np

from app.core.config import settings
from app.models.grocery import GroceryProduct
from app.product_matching.encoder import get_encoder, ProductEncoder
from app.product_matching.preprocessing import (
    preprocess_ingredient_for_matching,
    preprocess_product_for_matching,
    validate_ingredient_compatibility,
)
from app.ingredient_intelligence.parser import parse_ingredient
from app.product_matching.schemas import ProductMatchResult, MatchIngredientsResponse


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate normalized cosine similarity between two 1D numerical vectors.
    Handles zero vectors safely without division by zero.
    
    Returns a score bounded in [0.0, 1.0].
    """
    if vec1 is None or vec2 is None:
        return 0.0

    v1 = np.asarray(vec1, dtype=np.float32)
    v2 = np.asarray(vec2, dtype=np.float32)

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    sim = float(np.dot(v1, v2) / (norm1 * norm2))
    return max(0.0, min(1.0, round(sim, 4)))


class ProductMatcher:
    """
    Semantic Product Matcher leveraging SentenceTransformer embeddings.
    """

    def __init__(
        self,
        encoder: Optional[ProductEncoder] = None,
        default_threshold: Optional[float] = None,
    ):
        self.encoder = encoder or get_encoder()
        self.default_threshold = (
            default_threshold
            if default_threshold is not None
            else settings.PRODUCT_MATCH_THRESHOLD
        )

    def match_products(
        self,
        ingredient_text: str,
        products: List[Union[GroceryProduct, Dict[str, Any]]],
        threshold: Optional[float] = None,
        top_k: Optional[int] = None,
        include_unmatched: bool = False,
    ) -> MatchIngredientsResponse:
        """
        Rank a list of grocery products by semantic similarity to an ingredient.

        Args:
            ingredient_text: Raw or clean ingredient name (e.g. "200g paneer", "tomato")
            products: List of GroceryProduct OR product dicts (optionally with 'embedding')
            threshold: Similarity score threshold (defaults to self.default_threshold)
            top_k: Maximum ranked matches to return
            include_unmatched: If True, include low_confidence/unmatched items in results

        Returns:
            MatchIngredientsResponse with sorted ProductMatchResult items
        """
        active_threshold = threshold if threshold is not None else self.default_threshold

        # Preprocess ingredient text via Phase 5.2 engine
        embed_text, canonical_name = preprocess_ingredient_for_matching(ingredient_text)
        query_parsed = parse_ingredient(ingredient_text)

        # Handle empty/invalid ingredient text safely
        if not embed_text:
            return MatchIngredientsResponse(
                ingredient_text=ingredient_text or "",
                canonical_name=canonical_name or "",
                threshold=active_threshold,
                total_matches=0,
                results=[],
            )

        # Handle empty products list safely
        if not products:
            return MatchIngredientsResponse(
                ingredient_text=ingredient_text,
                canonical_name=canonical_name,
                threshold=active_threshold,
                total_matches=0,
                results=[],
            )

        # Encode query ingredient
        ing_vec = self.encoder.encode_text(embed_text)

        scored_results: List[ProductMatchResult] = []

        for p in products:
            if isinstance(p, dict):
                p_id = str(p.get("product_id") or p.get("id") or "")
                p_name = str(p.get("product_name") or p.get("name") or "")
                brand = p.get("brand")
                category = p.get("category")
                store_id = p.get("store_id")
                store_name = p.get("store_name")
                price = p.get("price")
                pkg_qty = p.get("package_quantity")
                pkg_unit = p.get("package_unit")
                p_vec = p.get("embedding")
                source_platform = p.get("source_platform")
                price_freshness = p.get("price_freshness")
                mrp = p.get("mrp")
                discount = p.get("discount")
                location = p.get("location")
                availability = p.get("availability", True)
            elif isinstance(p, GroceryProduct):
                p_id = str(p.id)
                p_name = str(p.name)
                brand = p.brand
                category = p.category
                store_id = str(p.store_id)
                store_name = p.store.name if p.store else None
                price = p.prices[0].price if p.prices else None
                pkg_qty = p.package_quantity
                pkg_unit = p.package_unit
                p_vec = getattr(p, "embedding", None)
                source_platform = "demo"
                price_freshness = "CACHED"
                mrp = getattr(p, "mrp", None)
                discount = getattr(p, "discount", None)
                location = getattr(p, "location", None)
                availability = getattr(p, "availability", True)
            else:
                continue

            if not p_name.strip():
                continue

            matched_text = preprocess_product_for_matching(p_name, brand, category)

            # Generate embedding dynamically if not precomputed
            if p_vec is None:
                p_vec = self.encoder.encode_text(matched_text)

            sim_score = compute_cosine_similarity(ing_vec, p_vec)

            # Validate ingredient compatibility (lexical / canonical guard)
            is_compatible = validate_ingredient_compatibility(
                raw_query=ingredient_text,
                query_canonical=canonical_name,
                query_normalization_source=query_parsed.normalization_source,
                product_name=p_name,
            )

            status = "matched" if (sim_score >= active_threshold and is_compatible) else "low_confidence"

            scored_results.append(
                ProductMatchResult(
                    product_id=p_id,
                    product_name=p_name,
                    brand=brand,
                    category=category,
                    store_id=store_id,
                    store_name=store_name,
                    price=price,
                    currency="INR",
                    package_quantity=pkg_qty,
                    package_unit=pkg_unit,
                    mrp=mrp,
                    discount=discount,
                    location=location,
                    availability=availability,
                    similarity_score=sim_score,
                    matched_text=matched_text,
                    match_status=status,
                    rank=1,  # Temporary, updated after sorting
                    data_source_type=source_platform,
                    price_freshness=price_freshness,
                )
            )

        # Sort results descending by similarity score
        scored_results.sort(key=lambda r: r.similarity_score, reverse=True)

        if include_unmatched:
            target_results = scored_results
        else:
            target_results = [r for r in scored_results if r.match_status == "matched"]

        # Update ranks
        for idx, res in enumerate(target_results):
            res.rank = idx + 1

        matches_above_threshold = sum(1 for r in scored_results if r.match_status == "matched")

        final_results = target_results[:top_k] if top_k is not None else target_results

        return MatchIngredientsResponse(
            ingredient_text=ingredient_text,
            canonical_name=canonical_name,
            threshold=active_threshold,
            total_matches=matches_above_threshold,
            results=final_results,
        )

