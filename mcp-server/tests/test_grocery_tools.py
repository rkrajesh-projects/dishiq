import json
import pytest
import mcp_types as types
from app.errors import (
    BackendUnavailableError,
    BackendValidationFailureError,
    InvalidToolInputError,
)
from app.tools.grocery import (
    get_grocery_tools,
    execute_search_grocery_products,
    execute_compare_recipe_cart,
    execute_get_store_prices,
)

# ---------------------------------------------------------------------------
# 1. TEST METADATA & SCHEMA DISCOVERY
# ---------------------------------------------------------------------------

def test_grocery_tools_metadata():
    """Verify tool list includes the three grocery tools with correct metadata."""
    tools = get_grocery_tools()
    assert len(tools) == 3
    
    names = [t.name for t in tools]
    assert "search_grocery_products" in names
    assert "compare_recipe_cart" in names
    assert "get_store_prices" in names

    search_tool = [t for t in tools if t.name == "search_grocery_products"][0]
    assert "query" in search_tool.input_schema["properties"]
    assert "limit" in search_tool.input_schema["properties"]


# ---------------------------------------------------------------------------
# 2. TEST search_grocery_products
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_grocery_products_success(mocker):
    """Verify successful product matching forwarding and CACHED freshness markers."""
    mock_backend_response = {
        "ingredient_text": "paneer",
        "canonical_name": "paneer",
        "threshold": 0.40,
        "total_matches": 1,
        "results": [
            {
                "product_id": "p1",
                "product_name": "Amul Paneer 200g",
                "brand": "Amul",
                "category": "Dairy",
                "store_id": "s1",
                "store_name": "Demo QuickMart",
                "price": 90.25,
                "currency": "INR",
                "package_quantity": 200.0,
                "package_unit": "g",
                "unit_price": 0.451,
                "base_unit": "g",
                "similarity_score": 0.95,
                "matched_text": "paneer",
                "match_status": "matched",
                "rank": 1
            }
        ],
        "best_option": {
            "product_id": "p1",
            "product_name": "Amul Paneer 200g",
            "store_name": "Demo QuickMart",
            "price": 90.25,
            "currency": "INR",
            "package_quantity": 200.0,
            "package_unit": "g",
            "unit_price": 0.451,
            "base_unit": "g",
            "similarity_score": 0.95
        },
        "comparison_mode": "unit_price"
    }

    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_backend_response)

    arguments = {"query": "paneer", "limit": 10, "threshold": 0.4}
    res = await execute_search_grocery_products(arguments)
    
    assert isinstance(res, types.CallToolResult)
    assert res.is_error is not True
    
    data = json.loads(res.content[0].text)
    assert data["total_matches"] == 1
    assert data["results"][0]["product_name"] == "Amul Paneer 200g"
    # Ensure CACHED freshness and demo data type markers are correctly preserved
    assert data["results"][0]["price_freshness"] == "CACHED"
    assert data["results"][0]["data_source_type"] == "demo"
    assert data["price_freshness"] == "CACHED"
    assert data["data_source"] == "demo"


@pytest.mark.asyncio
async def test_search_grocery_products_empty(mocker):
    """Verify empty matches list handled cleanly."""
    mock_backend_response = {
        "ingredient_text": "dragonfruitxyz",
        "canonical_name": "dragonfruitxyz",
        "threshold": 0.40,
        "total_matches": 0,
        "results": [],
        "best_option": None,
        "comparison_mode": None
    }
    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_backend_response)

    res = await execute_search_grocery_products({"query": "dragonfruitxyz"})
    data = json.loads(res.content[0].text)
    assert data["total_matches"] == 0
    assert len(data["results"]) == 0


@pytest.mark.asyncio
async def test_search_grocery_products_invalid_inputs():
    """Verify bounds and validation checks."""
    with pytest.raises(InvalidToolInputError):
        await execute_search_grocery_products({"query": ""})
        
    with pytest.raises(InvalidToolInputError):
        await execute_search_grocery_products({"query": "paneer", "limit": 100})

    with pytest.raises(InvalidToolInputError):
        await execute_search_grocery_products({"query": "paneer", "threshold": -0.5})


@pytest.mark.asyncio
async def test_search_grocery_products_backend_error(mocker):
    """Verify HTTP failures map to structured errors."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("Backend unavailable")
    )
    res = await execute_search_grocery_products({"query": "paneer"})
    assert res.is_error is True
    assert "Backend unavailable" in res.content[0].text


# ---------------------------------------------------------------------------
# 3. TEST compare_recipe_cart
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compare_recipe_cart_success(mocker):
    """Verify successful cart comparison forwarding and totals/delivery calculation."""
    mock_cart_response = {
        "stores": [
            {
                "store_id": "s1",
                "store_name": "Demo QuickMart",
                "subtotal": 180.0,
                "delivery_fee": 30.0,
                "total": 210.0,
                "complete": True,
                "selected_products": [],
                "missing_ingredients": []
            }
        ],
        "missing_ingredients": [],
        "data_source": "demo",
        "price_freshness": "CACHED"
    }

    mocker.patch("app.backend_client.BackendClient.post", return_value=mock_cart_response)

    arguments = {
        "ingredients": [
            {"name": "paneer", "quantity": 500, "unit": "g"}
        ]
    }

    res = await execute_compare_recipe_cart(arguments)
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    
    assert len(data["stores"]) == 1
    assert data["stores"][0]["store_name"] == "Demo QuickMart"
    assert data["stores"][0]["total"] == 210.0
    assert data["price_freshness"] == "CACHED"
    assert data["data_source"] == "demo"


@pytest.mark.asyncio
async def test_compare_recipe_cart_validation_error():
    """Verify cart compare checks nested array schemas and throws input errors."""
    with pytest.raises(InvalidToolInputError):
        await execute_compare_recipe_cart({"ingredients": []})

    with pytest.raises(InvalidToolInputError):
        await execute_compare_recipe_cart({"ingredients": [{"name": "paneer", "quantity": -10, "unit": "g"}]})

    with pytest.raises(InvalidToolInputError):
        await execute_compare_recipe_cart({"ingredients": [{"name": "", "quantity": 500, "unit": "g"}]})


@pytest.mark.asyncio
async def test_compare_recipe_cart_backend_unavailable(mocker):
    """Verify connection errors are handled."""
    mocker.patch(
        "app.backend_client.BackendClient.post",
        side_effect=BackendUnavailableError("Backend server offline")
    )
    arguments = {
        "ingredients": [{"name": "paneer", "quantity": 500, "unit": "g"}]
    }
    res = await execute_compare_recipe_cart(arguments)
    assert res.is_error is True
    assert "Backend server offline" in res.content[0].text


# ---------------------------------------------------------------------------
# 4. TEST get_store_prices
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_store_prices_by_ingredient(mocker):
    """Verify price retrieval by ingredient calls /grocery/compare."""
    mock_compare_response = {
        "ingredient_text": "paneer",
        "canonical_name": "paneer",
        "results": [
            {"product_name": "Paneer", "price": 90.0, "store_name": "Demo QuickMart"}
        ]
    }
    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_compare_response)

    res = await execute_get_store_prices({"ingredient": "paneer"})
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    assert data["ingredient_text"] == "paneer"
    assert data["results"][0]["price"] == 90.0


@pytest.mark.asyncio
async def test_get_store_prices_by_store_and_category(mocker):
    """Verify listing catalog products filters by store_id and category and calls /products."""
    mock_products_response = {
        "items": [
            {"name": "Paneer", "store_id": "s1", "category": "Dairy"}
        ],
        "total": 1
    }
    mock_get = mocker.patch("app.backend_client.BackendClient.get", return_value=mock_products_response)

    res = await execute_get_store_prices({"store_id": "s1", "category": "Dairy", "limit": 5})
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Paneer"
    
    # Check correct parameters were forwarded
    mock_get.assert_called_once_with("/products", params={"store_id": "s1", "category": "Dairy", "page_size": 5, "page": 1})


@pytest.mark.asyncio
async def test_get_store_prices_invalid_input():
    """Verify bounds check on limit parameter."""
    with pytest.raises(InvalidToolInputError):
        await execute_get_store_prices({"limit": 100})
