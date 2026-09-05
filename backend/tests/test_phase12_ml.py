import pytest
import asyncio
from typing import List

from app.services.recommendation_service import RecommendationService
from app.product_matching.matcher import ProductMatcher
from app.grocery_sources.demo_provider import DemoGroceryProvider
from app.models.recipe import Recipe
from app.models.grocery import GroceryProduct
from sqlalchemy.orm import Session

# -------------------------------------------------------------------
# 1. Recipe Recommendation Tests
# -------------------------------------------------------------------
def test_recipe_recommendation_dietary_and_pantry(seeded_db: Session):
    """
    Verify that the ML recommender correctly prioritizes recipes based on
    semantic query relevance, dietary constraints, and pantry overlap boosts.
    """
    service = RecommendationService(db=seeded_db)
    
    # User searches for 'paneer' with 'Vegetarian' preference and 'paneer' in pantry
    recs = service.get_recommendations(
        query="paneer", 
        dietary_type="Vegetarian", 
        pantry_ingredients=["paneer", "tomato"],
        limit=5
    )
    
    assert len(recs) > 0, "Should return at least one recommendation"
    top_rec = recs[0]
    
    # Verify dietary filter worked
    assert top_rec["recipe"].dietary_type.lower() == "vegetarian"
    
    # Verify explanation strings contain expected reasoning
    explanations = "".join(top_rec["explanations"]).lower()
    assert "vegetarian preference" in explanations, "Should explain dietary match"
    assert "pantry" in explanations, "Should explain pantry overlap boost"

def test_recipe_recommendation_time_penalty(seeded_db: Session):
    """
    Verify that max_time limits filter out long recipes and boost quick ones.
    """
    service = RecommendationService(db=seeded_db)
    
    # Search with a strict 15-minute time limit
    recs = service.get_recommendations(
        query="", 
        max_time=15, 
        limit=10
    )
    
    for rec in recs:
        recipe: Recipe = rec["recipe"]
        total_time = recipe.preparation_minutes + recipe.cooking_minutes
        assert total_time <= 15, f"Recipe {recipe.name} exceeded time limit"

def test_recommender_handles_empty_query(seeded_db: Session):
    """
    Empty or nonsense queries should not crash the system.
    """
    service = RecommendationService(db=seeded_db)
    recs = service.get_recommendations(query="   ", limit=2)
    assert isinstance(recs, list)
    # Should fallback to baseline scoring (dietary, rating, time)

# -------------------------------------------------------------------
# 2. Product Matching Tests (Sentence Transformer)
# -------------------------------------------------------------------
def test_product_matcher_semantic_filtering():
    """
    Verify the semantic matcher correctly identifies pure ingredients vs
    derivatives/mixes (e.g., 'Paneer' vs 'Paneer Masala Mix').
    """
    matcher = ProductMatcher()
    
    mock_products = [
        {"product_id": "1", "name": "Fresh Paneer 200g", "brand": "Amul", "category": "Dairy"},
        {"product_id": "2", "name": "Paneer Tikka Masala Mix", "brand": "Suhana", "category": "Spices"},
        {"product_id": "3", "name": "Tomato Ketchup", "brand": "Heinz", "category": "Pantry"}
    ]
    
    result = matcher.match_products(ingredient_text="paneer", products=mock_products)
    
    # The pure paneer product should rank highest
    assert len(result.results) > 0
    top_match = result.results[0]
    assert top_match.product_id == "1"
    
    # The ketchup should definitely not be matched
    matched_ids = [r.product_id for r in result.results]
    assert "3" not in matched_ids

# -------------------------------------------------------------------
# 3. Embedding Cache Regression Test
# -------------------------------------------------------------------
def test_demo_provider_cache_resilience(seeded_db: Session):
    """
    Verify Phase 12.2 fix: the provider correctly handles precomputed
    caches alongside fresh database products.
    """
    provider = DemoGroceryProvider(db=seeded_db)
    
    # Search for paneer using the async provider method
    results = asyncio.run(provider.search_products("paneer"))
    
    assert isinstance(results, list)
    # Depending on seed data, should return normalized grocery products
    if len(results) > 0:
        assert hasattr(results[0], "product_name")
        assert results[0].currency == "INR"
