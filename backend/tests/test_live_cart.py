import pytest
from unittest.mock import patch, AsyncMock
from app.grocery_sources.models import NormalizedGroceryProduct
from app.schemas.cart import CartCompareRequest, CartIngredientRequest
from app.api.cart import _match_all_ingredients
from app.grocery_sources.registry import clear_grocery_cache
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def reset_cache():
    clear_grocery_cache()
    yield
    clear_grocery_cache()

# ---------------------------------------------------------------------------
# MOCKS
# ---------------------------------------------------------------------------
def get_mock_live_product(name="Fresh Tomato 1kg", price=50.0):
    return NormalizedGroceryProduct(
        source_platform="Mock Live Store",
        source_product_id="live_123",
        store_name="Mock Live Store",
        product_name=name,
        brand="Fresh",
        category="Vegetables",
        package_quantity=1000,
        package_unit="g",
        price=price,
        currency="INR",
        availability=True,
        product_url="http://mock",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="PROVIDER_LIVE"
    )

# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

def test_live_mode_false_uses_demo(seeded_db):
    """A. live_mode=false -> demo products remain available, metadata is demo/CACHED."""
    req = CartCompareRequest(ingredients=[
        CartIngredientRequest(ingredient_name="tomato", required_quantity=500, required_unit="g")
    ])
    matched, missing = _match_all_ingredients(req, seeded_db, live_mode=False)
    assert not missing
    matches = matched.get("tomato", [])
    assert len(matches) > 0
    # The matches should be from demo provider
    for m in matches:
        assert m.data_source_type == "demo"
        # Demo uses DEMO or CACHED (updated to DEMO in codebase)
        assert m.price_freshness == "DEMO"

@patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.search_products")
@patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.is_configured", new_callable=lambda: True)
def test_live_mode_true_valid_product(mock_is_conf, mock_search, seeded_db, client):
    """B. live_mode=true with valid live product -> reaches cart, metadata is LIVE/provider-derived."""
    mock_search.return_value = [get_mock_live_product("Fresh Tomato 1kg", 60.0)]
    
    # We use client to test the full response (including cart optimization logic)
    response = client.post("/api/cart/compare?live_mode=true", json={
        "ingredients": [
            {"ingredient_name": "tomato", "required_quantity": 500, "required_unit": "g"}
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["data_source"] == "live"
    assert data["price_freshness"] == "PROVIDER_LIVE"
    
    stores = data["stores"]
    assert len(stores) == 1
    store = stores[0]
    assert store["store_name"] == "Mock Live Store"
    
    products = store["selected_products"]
    assert len(products) == 1
    p = products[0]
    assert p["product_name"] == "Fresh Tomato 1kg"
    assert p["data_source_type"] == "Mock Live Store"
    assert p["price_freshness"] == "PROVIDER_LIVE"
    assert p["package_price"] == 60.0

@patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.search_products")
@patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.is_configured", new_callable=lambda: True)
def test_live_mode_true_irrelevant_product(mock_is_conf, mock_search, seeded_db, client):
    """C. live_mode=true with irrelevant product -> rejected, demo NOT substituted."""
    # Return batteries when asking for tomato
    mock_search.return_value = [get_mock_live_product("Ultra Alkaline AA Batteries", 200.0)]
    
    response = client.post("/api/cart/compare?live_mode=true", json={
        "ingredients": [
            {"ingredient_name": "tomato", "required_quantity": 500, "required_unit": "g"}
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["data_source"] == "live"
    assert data["price_freshness"] == "UNKNOWN"
    
    # Cart should be empty, missing ingredients should be populated
    assert len(data["stores"]) == 0
    assert len(data["missing_ingredients"]) == 1
    assert data["missing_ingredients"][0]["ingredient_name"] == "tomato"

@patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.search_products")
@patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.is_configured", new_callable=lambda: True)
def test_live_mode_true_provider_failure(mock_is_conf, mock_search, seeded_db, client):
    """D. live_mode=true with provider failure -> handled safely, no demo fallback."""
    mock_search.side_effect = Exception("API Timeout")
    
    response = client.post("/api/cart/compare?live_mode=true", json={
        "ingredients": [
            {"ingredient_name": "tomato", "required_quantity": 500, "required_unit": "g"}
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["data_source"] == "live"
    assert data["price_freshness"] == "UNKNOWN"
    
    # Cart should be empty, provider isolated
    assert len(data["stores"]) == 0
    assert len(data["missing_ingredients"]) == 1
    assert data["missing_ingredients"][0]["ingredient_name"] == "tomato"
