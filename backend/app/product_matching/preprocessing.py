"""
DishIQ Phase 6.1 — Grocery Product Matching
Text Preprocessing & Ingredient Compatibility module.

Reuses the Phase 5.2 Ingredient Intelligence engine (parse_ingredient, normalize_ingredient)
to prepare clean semantic text for embedding and validate ingredient compatibility.
"""
import re
from typing import Optional, Tuple
from app.ingredient_intelligence.parser import parse_ingredient, normalize_ingredient


def preprocess_ingredient_for_matching(raw_text: str) -> Tuple[str, str]:
    """
    Preprocess an input ingredient text string for semantic embedding matching.
    
    Reuses Phase 5.2 parse_ingredient to extract the canonical_name and clean display_name.
    
    Returns:
        (text_for_embedding, canonical_name)
    """
    if not raw_text or not raw_text.strip():
        return "", ""

    parsed = parse_ingredient(raw_text)
    canonical = parsed.canonical_name.strip().lower()

    # Construct clean embedding target: combine display name and canonical name if different
    display = parsed.display_name.strip()
    if display.lower() != canonical:
        text_for_embedding = f"{display} {canonical}".strip()
    else:
        text_for_embedding = canonical

    return text_for_embedding, canonical


def preprocess_product_for_matching(
    product_name: str,
    brand: Optional[str] = None,
    category: Optional[str] = None,
) -> str:
    """
    Preprocess a grocery product's title and metadata for semantic embedding.
    """
    if not product_name or not product_name.strip():
        return ""

    cleaned_name = product_name.strip()
    # Normalize extra spaces and common weight/pack noise tokens for embedding focus
    cleaned_name = re.sub(r"\s+", " ", cleaned_name)

    parts = [cleaned_name]
    if brand and brand.strip() and brand.lower() not in cleaned_name.lower():
        parts.append(brand.strip())
    if category and category.strip() and category.lower() not in cleaned_name.lower():
        parts.append(category.strip())

    return " ".join(parts).strip()


def extract_canonical_from_product_name(product_name: str) -> Optional[str]:
    """
    Extract the canonical ingredient name from a grocery product's title/name.
    Reuses Phase 5.2 parse_ingredient and normalize_ingredient.
    """
    if not product_name:
        return None

    # First, try direct parse_ingredient
    parsed = parse_ingredient(product_name)
    if parsed.normalization_source == "dictionary":
        return parsed.canonical_name.strip().lower()

    # If store name or brand prefix prevented direct match, search words using normalize_ingredient
    clean_name = product_name.lower()

    words = re.findall(r"[a-z]+", clean_name)
    for i in range(len(words)):
        for j in range(len(words), i, -1):
            phrase = " ".join(words[i:j])
            norm = normalize_ingredient(phrase)
            if norm.normalization_source == "dictionary":
                return norm.canonical_name.strip().lower()

    return None


def validate_ingredient_compatibility(
    raw_query: str,
    query_canonical: str,
    query_normalization_source: str,
    product_name: str,
) -> bool:
    """
    Validates whether a product is semantically and lexically compatible
    with a query ingredient.
    
    1. For unknown ingredients (normalization_source == 'unknown'):
       Requires the raw query string to lexically overlap with the product name.
    
    2. For known ingredients (normalization_source == 'dictionary'):
       Parses the product title using Phase 5.2 engine. If the product is recognized
       as a different canonical ingredient (e.g. 'potato' vs 'tomato'), rejects the match.
    """
    if not product_name or not product_name.strip():
        return False

    clean_prod_name = product_name.strip().lower()

    # 1. Unknown query ingredient
    if query_normalization_source == "unknown":
        clean_raw_query = raw_query.strip().lower()
        if not clean_raw_query:
            return False
        tokens = [t for t in re.findall(r"[a-z]+", clean_raw_query) if len(t) > 2]
        if not tokens:
            return clean_raw_query in clean_prod_name
        return any(t in clean_prod_name for t in tokens)

    # 2. Known query canonical ingredient
    clean_query_canonical = query_canonical.strip().lower()
    prod_canonical = extract_canonical_from_product_name(product_name)

    if prod_canonical:
        # Both query and product have known canonical ingredients
        # If they differ (e.g. "tomato" != "potato"), reject
        if clean_query_canonical != prod_canonical:
            return False
        return True
    else:
        # Product canonical ingredient could not be extracted from dictionary -> check token overlap
        query_tokens = set(re.findall(r"[a-z]+", clean_query_canonical))
        prod_tokens = set(re.findall(r"[a-z]+", clean_prod_name))
        return bool(query_tokens and query_tokens.issubset(prod_tokens))
