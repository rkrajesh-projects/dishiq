import json
import pytest
import mcp_types as types
from app.errors import (
    BackendUnavailableError,
    RequestTimeoutError,
    BackendValidationFailureError,
    InvalidToolInputError,
    UnexpectedBackendResponseError,
)
from app.server import list_tools_handler, call_tool_handler

# ---------------------------------------------------------------------------
# 1. TOOL DISCOVERY VERIFICATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_discovery_e2e():
    """Verify all 10 MCP tools are registered and discoverable with valid schemas."""
    res = await list_tools_handler(None, None)
    assert isinstance(res, types.ListToolsResult)
    assert len(res.tools) == 10

    expected_names = {
        "health",
        "search_recipes",
        "get_recipe",
        "get_recipe_ingredients",
        "search_grocery_products",
        "compare_recipe_cart",
        "get_store_prices",
        "get_pantry",
        "check_missing_ingredients",
        "update_pantry"
    }

    tool_names = {t.name for t in res.tools}
    assert tool_names == expected_names

    # Check descriptions and schemas
    for tool in res.tools:
        assert tool.description is not None
        assert tool.input_schema is not None
        assert "type" in tool.input_schema
        assert tool.input_schema["type"] == "object"


# ---------------------------------------------------------------------------
# 2. RECIPE END-TO-END FLOW
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recipe_e2e_flow(mocker):
    """Verify recipe search, retrieval, and ingredient listing end-to-end flow."""
    # 1. Mock search response
    mock_search = {
        "items": [
            {
                "id": "recipe-uuid-1",
                "name": "Paneer Bhurji",
                "cuisine": "Indian",
                "dietary_type": "Vegetarian",
                "preparation_minutes": 10,
                "cooking_minutes": 15,
                "servings": 4,
                "average_rating": 4.8
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 10,
        "total_pages": 1
    }
    
    # 2. Mock detail response
    mock_detail = {
        "id": "recipe-uuid-1",
        "name": "Paneer Bhurji",
        "description": "Scrambled paneer...",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 10,
        "cooking_minutes": 15,
        "servings": 4,
        "instructions": ["Step 1", "Step 2"]
    }

    # 3. Mock ingredients response
    mock_ingredients = {
        "count": 1,
        "results": [
            {
                "raw_text": "250g paneer",
                "display_name": "Paneer",
                "canonical_name": "paneer",
                "quantity": 250.0,
                "unit": "grams",
                "category": "Dairy",
                "confidence_score": 0.95
            }
        ]
    }

    # Setup mocker
    mock_get = mocker.patch("app.backend_client.BackendClient.get")
    mock_get.side_effect = [mock_search, mock_detail, mock_ingredients]

    # Step A: Search recipe
    search_res = await call_tool_handler(None, types.CallToolRequestParams(
        name="search_recipes",
        arguments={"q": "paneer"}
    ))
    assert not search_res.is_error
    search_data = json.loads(search_res.content[0].text)
    assert len(search_data["recipes"]) == 1
    recipe_id = search_data["recipes"][0]["id"]
    assert recipe_id == "recipe-uuid-1"

    # Step B: Get recipe detail
    detail_res = await call_tool_handler(None, types.CallToolRequestParams(
        name="get_recipe",
        arguments={"recipe_id": recipe_id}
    ))
    assert not detail_res.is_error
    detail_data = json.loads(detail_res.content[0].text)
    assert detail_data["name"] == "Paneer Bhurji"

    # Step C: Get recipe ingredients
    ing_res = await call_tool_handler(None, types.CallToolRequestParams(
        name="get_recipe_ingredients",
        arguments={"recipe_id": recipe_id}
    ))
    assert not ing_res.is_error
    ing_data = json.loads(ing_res.content[0].text)
    assert ing_data["count"] == 1
    assert ing_data["results"][0]["canonical_name"] == "paneer"


# ---------------------------------------------------------------------------
# 3. GROCERY END-TO-END FLOW (WITH DATA SAFETY CHECKS)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grocery_e2e_flow_with_safety_assertions(mocker):
    """Verify grocery search, cost compare, store pricing, and price freshness safety flags."""
    # 1. Mock grocery match
    mock_match = {
        "ingredient_text": "paneer",
        "canonical_name": "paneer",
        "threshold": 0.4,
        "total_matches": 1,
        "results": [
            {
                "product_id": "p1",
                "product_name": "Paneer 200g",
                "brand": "Amul",
                "category": "Dairy",
                "store_name": "Demo QuickMart",
                "price": 90.0,
                "currency": "INR",
                "package_quantity": 200.0,
                "package_unit": "g",
                "similarity_score": 0.95,
                "match_status": "matched",
                "rank": 1
            }
        ],
        "best_option": None,
        "comparison_mode": "unit_price"
    }

    # 2. Mock cart comparison
    mock_cart = {
        "stores": [
            {
                "store_id": "s1",
                "store_name": "Demo QuickMart",
                "subtotal": 180.0,
                "delivery_fee": 30.0,
                "total": 210.0,
                "complete": True,
                "selected_products": [
                    {
                        "product_id": "p1",
                        "product_name": "Paneer 200g",
                        "quantity_to_buy": 2,
                        "unit_price": 0.45,
                        "line_cost": 180.0,
                        "price_freshness": "CACHED",
                        "data_source_type": "demo"
                    }
                ],
                "missing_ingredients": []
            }
        ],
        "missing_ingredients": [],
        "data_source": "demo",
        "price_freshness": "CACHED"
    }

    # 3. Mock store prices
    mock_prices = {
        "ingredient_text": "paneer",
        "canonical_name": "paneer",
        "results": [
            {"product_name": "Paneer 200g", "price": 90.0, "store_name": "Demo QuickMart"}
        ]
    }

    mocker.patch("app.backend_client.BackendClient.get", side_effect=[mock_match, mock_prices])
    mocker.patch("app.backend_client.BackendClient.post", return_value=mock_cart)

    # Step A: Search grocery products
    search_res = await call_tool_handler(None, types.CallToolRequestParams(
        name="search_grocery_products",
        arguments={"query": "paneer"}
    ))
    assert not search_res.is_error
    search_data = json.loads(search_res.content[0].text)
    assert search_data["results"][0]["product_name"] == "Paneer 200g"
    
    # Step B: Compare recipe cart
    cart_res = await call_tool_handler(None, types.CallToolRequestParams(
        name="compare_recipe_cart",
        arguments={
            "ingredients": [{"name": "paneer", "quantity": 400.0, "unit": "g"}]
        }
    ))
    assert not cart_res.is_error
    cart_data = json.loads(cart_res.content[0].text)
    assert len(cart_data["stores"]) == 1
    assert cart_data["stores"][0]["total"] == 210.0

    # Step C: Get store prices
    prices_res = await call_tool_handler(None, types.CallToolRequestParams(
        name="get_store_prices",
        arguments={"ingredient": "paneer"}
    ))
    assert not prices_res.is_error
    prices_data = json.loads(prices_res.content[0].text)
    assert len(prices_data["results"]) == 1

    # --- REGRESSION ASSERTION FOR DATA SAFETY ---
    # Ensure all demonstration/cached fields are marked as CACHED / demo and NEVER LIVE.
    for res_item in search_data["results"]:
        assert res_item["price_freshness"] != "LIVE", "Demonstration data must not be labeled as LIVE."
        assert res_item["price_freshness"] == "CACHED"
        assert res_item["data_source_type"] == "demo"
    assert search_data["price_freshness"] == "CACHED"

    for store in cart_data["stores"]:
        for prod in store["selected_products"]:
            assert prod["price_freshness"] != "LIVE", "Demonstration data must not be labeled as LIVE."
            assert prod["price_freshness"] == "CACHED"
            assert prod["data_source_type"] == "demo"
    assert cart_data["price_freshness"] == "CACHED"
    assert cart_data["data_source"] == "demo"


# ---------------------------------------------------------------------------
# 4. PANTRY END-TO-END FLOW
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pantry_e2e_flow(mocker):
    """Verify pantry add, get, update, and ingredient checking flow."""
    # 1. get_pantry (initial empty)
    mock_get_pantry_empty = []

    # 2. update_pantry (add paneer)
    mock_add_pantry = {
        "id": "pantry-id-1",
        "ingredient_id": "ing-1",
        "ingredient_name": "paneer",
        "canonical_name": "paneer",
        "quantity": 500.0,
        "unit": "g",
        "expiration_date": "2026-12-31",
        "created_at": "2026-08-09T12:00:00Z",
        "updated_at": "2026-08-09T12:00:00Z"
    }

    # 3. get_pantry (post add)
    mock_get_pantry_filled = [mock_add_pantry]

    # 4. check_missing_ingredients
    mock_check_recipe = {
        "recipe_id": "r1",
        "recipe_name": "Paneer Bhurji",
        "required_ingredients": [
            {
                "ingredient_name": "paneer",
                "required_quantity": 250.0,
                "required_unit": "grams",
                "pantry_quantity": 500.0,
                "pantry_unit": "g",
                "status": "covered"
            }
        ],
        "pantry_covered": [
            {
                "ingredient_name": "paneer",
                "required_quantity": 250.0,
                "required_unit": "grams",
                "pantry_quantity": 500.0,
                "pantry_unit": "g",
                "status": "covered"
            }
        ],
        "partially_covered": [],
        "missing_ingredients": []
    }

    mocker.patch("app.backend_client.BackendClient.get", side_effect=[
        mock_get_pantry_empty,
        mock_get_pantry_filled,
        mock_check_recipe
    ])
    mocker.patch("app.backend_client.BackendClient.post", return_value=mock_add_pantry)

    # A. Initial get_pantry
    res_empty = await call_tool_handler(None, types.CallToolRequestParams(name="get_pantry", arguments={}))
    assert not res_empty.is_error
    data_empty = json.loads(res_empty.content[0].text)
    assert len(data_empty) == 0

    # B. Add pantry item
    res_add = await call_tool_handler(None, types.CallToolRequestParams(
        name="update_pantry",
        arguments={
            "operation": "add",
            "ingredient_name": "paneer",
            "quantity": 500.0,
            "unit": "g",
            "expiration_date": "2026-12-31"
        }
    ))
    assert not res_add.is_error
    data_add = json.loads(res_add.content[0].text)
    assert data_add["ingredient_name"] == "paneer"
    assert data_add["quantity"] == 500.0

    # C. Get pantry (now filled)
    res_filled = await call_tool_handler(None, types.CallToolRequestParams(name="get_pantry", arguments={}))
    assert not res_filled.is_error
    data_filled = json.loads(res_filled.content[0].text)
    assert len(data_filled) == 1
    assert data_filled[0]["ingredient_name"] == "paneer"

    # D. Check missing ingredients for a recipe
    res_check = await call_tool_handler(None, types.CallToolRequestParams(
        name="check_missing_ingredients",
        arguments={"recipe_id": "r1"}
    ))
    assert not res_check.is_error
    data_check = json.loads(res_check.content[0].text)
    assert data_check["recipe_name"] == "Paneer Bhurji"
    assert len(data_check["pantry_covered"]) == 1


# ---------------------------------------------------------------------------
# 5. STRUCTURED RESPONSE & BACKEND ERROR CONVERSION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backend_error_handling_and_exception_filtering(mocker):
    """Verify backend errors map to structured error responses without leaking tracebacks/credentials."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("FastAPI Backend connection refused")
    )

    res = await call_tool_handler(None, types.CallToolRequestParams(name="get_pantry", arguments={}))
    assert res.is_error
    assert len(res.content) == 1
    
    msg = res.content[0].text
    # Ensure error is descriptive
    assert "FastAPI Backend connection refused" in msg
    # Verify no credentials, DB connections, or stack traces leak out
    assert "password" not in msg.lower()
    assert "db_connection" not in msg.lower()
    assert "traceback" not in msg.lower()
