import json
import pytest
import mcp_types as types
from app.errors import (
    BackendUnavailableError,
    BackendValidationFailureError,
    InvalidToolInputError,
)
from app.tools.pantry import (
    get_pantry_tools,
    execute_get_pantry,
    execute_check_missing_ingredients,
    execute_update_pantry,
)

# ---------------------------------------------------------------------------
# 1. TEST METADATA & SCHEMA DISCOVERY
# ---------------------------------------------------------------------------

def test_pantry_tools_metadata():
    """Verify tool list includes the three pantry tools with correct metadata."""
    tools = get_pantry_tools()
    assert len(tools) == 3
    
    names = [t.name for t in tools]
    assert "get_pantry" in names
    assert "check_missing_ingredients" in names
    assert "update_pantry" in names

    update_tool = [t for t in tools if t.name == "update_pantry"][0]
    assert "operation" in update_tool.input_schema["properties"]
    assert "ingredient_name" in update_tool.input_schema["properties"]


# ---------------------------------------------------------------------------
# 2. TEST get_pantry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pantry_success(mocker):
    """Verify successful pantry retrieval."""
    mock_backend_response = [
        {
            "id": "pantry-item-1",
            "ingredient_id": "ing-1",
            "ingredient_name": "paneer",
            "canonical_name": "paneer",
            "quantity": 500.0,
            "unit": "g",
            "expiration_date": "2026-09-01",
            "created_at": "2026-08-09T12:00:00Z",
            "updated_at": "2026-08-09T12:00:00Z"
        }
    ]

    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_backend_response)

    res = await execute_get_pantry({})
    assert isinstance(res, types.CallToolResult)
    assert res.is_error is not True
    
    data = json.loads(res.content[0].text)
    assert len(data) == 1
    assert data[0]["ingredient_name"] == "paneer"
    assert data[0]["quantity"] == 500.0


@pytest.mark.asyncio
async def test_get_pantry_empty(mocker):
    """Verify empty list when user has nothing in pantry."""
    mocker.patch("app.backend_client.BackendClient.get", return_value=[])

    res = await execute_get_pantry({})
    data = json.loads(res.content[0].text)
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_pantry_backend_error(mocker):
    """Verify backend errors map to structured exceptions."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("Backend unavailable")
    )
    res = await execute_get_pantry({})
    assert res.is_error is True
    assert "Backend unavailable" in res.content[0].text


# ---------------------------------------------------------------------------
# 3. TEST check_missing_ingredients
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_missing_ingredients_success(mocker):
    """Verify recipe-to-pantry matching results comparison."""
    mock_backend_response = {
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
            },
            {
                "ingredient_name": "onion",
                "required_quantity": 2.0,
                "required_unit": "pieces",
                "pantry_quantity": 1.0,
                "pantry_unit": "pieces",
                "status": "partially_covered"
            },
            {
                "ingredient_name": "tomato",
                "required_quantity": 2.0,
                "required_unit": "pieces",
                "pantry_quantity": 0.0,
                "pantry_unit": "pieces",
                "status": "missing"
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
        "partially_covered": [
            {
                "ingredient_name": "onion",
                "required_quantity": 2.0,
                "required_unit": "pieces",
                "pantry_quantity": 1.0,
                "pantry_unit": "pieces",
                "status": "partially_covered"
            }
        ],
        "missing_ingredients": [
            {
                "ingredient_name": "tomato",
                "required_quantity": 2.0,
                "required_unit": "pieces",
                "pantry_quantity": 0.0,
                "pantry_unit": "pieces",
                "status": "missing"
            }
        ]
    }

    mocker.patch("app.backend_client.BackendClient.get", return_value=mock_backend_response)

    res = await execute_check_missing_ingredients({"recipe_id": "r1"})
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    
    assert data["recipe_name"] == "Paneer Bhurji"
    assert len(data["required_ingredients"]) == 3
    assert len(data["pantry_covered"]) == 1
    assert len(data["partially_covered"]) == 1
    assert len(data["missing_ingredients"]) == 1


@pytest.mark.asyncio
async def test_check_missing_ingredients_recipe_not_found(mocker):
    """Verify recipe 404 maps to structured error."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("Recipe 'not-found' not found.")
    )
    res = await execute_check_missing_ingredients({"recipe_id": "not-found"})
    assert res.is_error is True
    assert "not found" in res.content[0].text.lower()


# ---------------------------------------------------------------------------
# 4. TEST update_pantry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_pantry_add(mocker):
    """Verify adding item to pantry calls POST /pantry."""
    mock_response = {
        "id": "item-123",
        "ingredient_id": "ing-1",
        "ingredient_name": "paneer",
        "canonical_name": "paneer",
        "quantity": 500.0,
        "unit": "g",
        "expiration_date": "2026-09-01",
        "created_at": "2026-08-09T12:00:00Z",
        "updated_at": "2026-08-09T12:00:00Z"
    }

    mock_post = mocker.patch("app.backend_client.BackendClient.post", return_value=mock_response)

    arguments = {
        "operation": "add",
        "ingredient_name": "paneer",
        "quantity": 500,
        "unit": "g",
        "expiration_date": "2026-09-01"
    }

    res = await execute_update_pantry(arguments)
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    assert data["id"] == "item-123"
    assert data["quantity"] == 500.0

    mock_post.assert_called_once_with(
        "/pantry",
        json={
            "ingredient_name": "paneer",
            "quantity": 500.0,
            "unit": "g",
            "expiration_date": "2026-09-01"
        }
    )


@pytest.mark.asyncio
async def test_update_pantry_update(mocker):
    """Verify updating item calls PATCH /pantry/{item_id}."""
    mock_response = {
        "id": "item-123",
        "ingredient_id": "ing-1",
        "ingredient_name": "paneer",
        "canonical_name": "paneer",
        "quantity": 600.0,
        "unit": "g",
        "expiration_date": "2026-09-01",
        "created_at": "2026-08-09T12:00:00Z",
        "updated_at": "2026-08-09T12:05:00Z"
    }

    mock_request = mocker.patch("app.backend_client.BackendClient.request", return_value=mock_response)

    arguments = {
        "operation": "update",
        "item_id": "item-123",
        "quantity": 600
    }

    res = await execute_update_pantry(arguments)
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    assert data["quantity"] == 600.0

    mock_request.assert_called_once_with(
        "PATCH",
        "/pantry/item-123",
        json={"quantity": 600.0}
    )


@pytest.mark.asyncio
async def test_update_pantry_remove(mocker):
    """Verify removing item calls DELETE /pantry/{item_id}."""
    mock_request = mocker.patch("app.backend_client.BackendClient.request", return_value=None)

    arguments = {
        "operation": "remove",
        "item_id": "item-123"
    }

    res = await execute_update_pantry(arguments)
    assert res.is_error is not True
    data = json.loads(res.content[0].text)
    assert "removed successfully" in data["message"]

    mock_request.assert_called_once_with(
        "DELETE",
        "/pantry/item-123"
    )


@pytest.mark.asyncio
async def test_update_pantry_invalid_inputs():
    """Verify parameter validations."""
    # Invalid operation
    with pytest.raises(InvalidToolInputError):
        await execute_update_pantry({"operation": "invalid_op"})

    # Missing quantity on add
    with pytest.raises(InvalidToolInputError):
        await execute_update_pantry({"operation": "add", "ingredient_name": "paneer", "unit": "g"})

    # Negative quantity
    with pytest.raises(InvalidToolInputError):
        await execute_update_pantry({"operation": "add", "ingredient_name": "paneer", "quantity": -5, "unit": "g"})

    # Invalid expiration date format
    with pytest.raises(InvalidToolInputError):
        await execute_update_pantry({"operation": "add", "ingredient_name": "paneer", "quantity": 1, "unit": "g", "expiration_date": "2026/09/01"})
