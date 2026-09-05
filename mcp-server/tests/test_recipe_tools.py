import json
import pytest
import mcp_types as types
from app.errors import (
    BackendUnavailableError,
    BackendValidationFailureError,
    InvalidToolInputError,
)
from app.tools.recipes import (
    execute_search_recipes,
    execute_get_recipe,
    execute_get_recipe_ingredients,
    get_recipe_tools,
)

# ---------------------------------------------------------------------------
# 1. TEST METADATA & SCHEMA DISCOVERY
# ---------------------------------------------------------------------------

def test_recipe_tools_metadata():
    """Verify tool list includes the three recipe tools with proper descriptions."""
    tools = get_recipe_tools()
    assert len(tools) == 3
    
    names = [t.name for t in tools]
    assert "search_recipes" in names
    assert "get_recipe" in names
    assert "get_recipe_ingredients" in names
    search_tool = [t for t in tools if t.name == "search_recipes"][0]
    assert "q" in search_tool.input_schema["properties"]
    assert "cuisine" in search_tool.input_schema["properties"]


# ---------------------------------------------------------------------------
# 2. TEST search_recipes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_recipes_success(mocker):
    """Verify successful recipe search forwarding and response structuring."""
    mock_backend_response = {
        "items": [
            {
                "id": "r1",
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
    
    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_backend_response)

    arguments = {
        "q": "paneer",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "max_cooking_time": 30,
        "available_ingredients": "paneer",
        "limit": 10,
        "offset": 0
    }
    
    res = await execute_search_recipes(arguments)
    assert isinstance(res, types.CallToolResult)
    assert res.is_error is not True
    
    data = json.loads(res.content[0].text)
    assert data["total"] == 1
    assert len(data["recipes"]) == 1
    assert data["recipes"][0]["name"] == "Paneer Bhurji"
    assert data["search_filters"]["q"] == "paneer"


@pytest.mark.asyncio
async def test_search_recipes_empty_result(mocker):
    """Verify search returns empty list when no recipes match."""
    mock_backend_response = {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 10,
        "total_pages": 0
    }
    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_backend_response)

    res = await execute_search_recipes({"q": "non_existent_recipe"})
    data = json.loads(res.content[0].text)
    assert data["total"] == 0
    assert len(data["recipes"]) == 0


@pytest.mark.asyncio
async def test_search_recipes_invalid_inputs():
    """Verify invalid parameters throw tool input errors."""
    with pytest.raises(InvalidToolInputError):
        await execute_search_recipes({"limit": -5})
        
    with pytest.raises(InvalidToolInputError):
        await execute_search_recipes({"offset": -10})

    with pytest.raises(InvalidToolInputError):
        await execute_search_recipes({"max_cooking_time": -1})


@pytest.mark.asyncio
async def test_search_recipes_backend_error(mocker):
    """Verify backend failures are caught and reported as structured errors."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("Backend server offline")
    )

    res = await execute_search_recipes({"q": "paneer"})
    assert res.is_error is True
    assert "Backend server offline" in res.content[0].text


# ---------------------------------------------------------------------------
# 3. TEST get_recipe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_recipe_success(mocker):
    """Verify detailed recipe retrieval."""
    mock_recipe = {
        "id": "r1",
        "name": "Paneer Bhurji",
        "description": "Scrambled paneer...",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "instructions": ["Crumble paneer", "Cook spices"],
        "ingredients": []
    }
    
    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_recipe)
    
    res = await execute_get_recipe({"recipe_id": "r1"})
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    assert data["id"] == "r1"
    assert data["name"] == "Paneer Bhurji"


@pytest.mark.asyncio
async def test_get_recipe_not_found(mocker):
    """Verify 404/Not Found handled gracefully."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("Recipe 'not-found-id' not found.")
    )
    
    res = await execute_get_recipe({"recipe_id": "not-found-id"})
    assert res.is_error is True
    assert "not found" in res.content[0].text.lower()


@pytest.mark.asyncio
async def test_get_recipe_invalid_id():
    """Verify blank recipe_id causes input error."""
    with pytest.raises(InvalidToolInputError):
        await execute_get_recipe({"recipe_id": ""})
        
    with pytest.raises(InvalidToolInputError):
        await execute_get_recipe({})


# ---------------------------------------------------------------------------
# 4. TEST get_recipe_ingredients
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_recipe_ingredients_success(mocker):
    """Verify ingredient retrieval returns parsed normalized metadata."""
    mock_ingredients = {
        "count": 1,
        "results": [
            {
                "raw_text": "500 g fresh paneer",
                "canonical_name": "paneer",
                "quantity": 500.0,
                "unit": "g",
                "preparation_note": "fresh",
                "optional": False,
                "confidence_score": 0.95
            }
        ]
    }
    
    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_ingredients)
    
    res = await execute_get_recipe_ingredients({"recipe_id": "r1"})
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    assert data["count"] == 1
    assert data["results"][0]["canonical_name"] == "paneer"


@pytest.mark.asyncio
async def test_get_recipe_ingredients_not_found(mocker):
    """Verify ingredient retrieval on non-existent recipe is handled."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("Recipe 'not-found-id' not found.")
    )
    
    res = await execute_get_recipe_ingredients({"recipe_id": "not-found-id"})
    assert res.is_error is True
    assert "not found" in res.content[0].text.lower()
