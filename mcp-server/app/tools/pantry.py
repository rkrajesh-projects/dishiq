from __future__ import annotations
import json
import logging
import mcp_types as types
from typing import Any, Dict, Optional
from datetime import datetime
from app.backend_client import BackendClient
from app.errors import MCPBaseError, InvalidToolInputError

logger = logging.getLogger("mcp-server.tools.pantry")

backend_client = BackendClient()

def get_pantry_tools() -> list[types.Tool]:
    """
    Return the definition of the pantry tools.
    """
    return [
        types.Tool(
            name="get_pantry",
            description="Retrieve the pantry inventory available to the current DishIQ user.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="check_missing_ingredients",
            description="Check which ingredients for a DishIQ recipe are already available, partially available, or missing from the pantry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "The unique ID of the recipe to compare against the pantry"
                    }
                },
                "required": ["recipe_id"]
            }
        ),
        types.Tool(
            name="update_pantry",
            description="Add, update, or remove pantry inventory using DishIQ's pantry services.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation type: 'add', 'update', or 'remove'",
                        "enum": ["add", "update", "remove"]
                    },
                    "ingredient_name": {
                        "type": "string",
                        "description": "Name of the ingredient (required for 'add' operation)"
                    },
                    "item_id": {
                        "type": "string",
                        "description": "The unique ID of the pantry item (required for 'update' and 'remove')"
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Ingredient quantity (positive number, required for 'add' or 'update')"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Measurement unit (required for 'add')"
                    },
                    "expiration_date": {
                        "type": "string",
                        "description": "Optional expiration date in YYYY-MM-DD format"
                    }
                },
                "required": ["operation"]
            }
        )
    ]


async def execute_get_pantry(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute get_pantry tool."""
    try:
        data = await backend_client.get("/pantry")
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        )
    except MCPBaseError as e:
        return types.CallToolResult(
            is_error=True,
            content=[
                types.TextContent(
                    type="text",
                    text=f"Error retrieving pantry: {e.message} (Code: {e.code})"
                )
            ]
        )


async def execute_check_missing_ingredients(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute check_missing_ingredients tool."""
    recipe_id = arguments.get("recipe_id")
    if not recipe_id:
        raise InvalidToolInputError("recipe_id parameter is required.")

    recipe_id_str = str(recipe_id).strip()
    if not recipe_id_str:
        raise InvalidToolInputError("recipe_id parameter cannot be empty.")

    try:
        data = await backend_client.get(f"/pantry/check-recipe/{recipe_id_str}")
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        )
    except MCPBaseError as e:
        return types.CallToolResult(
            is_error=True,
            content=[
                types.TextContent(
                    type="text",
                    text=f"Error checking missing ingredients: {e.message} (Code: {e.code})"
                )
            ]
        )


async def execute_update_pantry(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute update_pantry tool."""
    operation = arguments.get("operation")
    if not operation:
        raise InvalidToolInputError("operation parameter is required.")

    operation_str = str(operation).strip().lower()
    if operation_str not in ["add", "update", "remove"]:
        raise InvalidToolInputError("operation must be one of: 'add', 'update', 'remove'.")

    # Common validation helper for expiry date
    expiration_date = arguments.get("expiration_date")
    if expiration_date:
        try:
            datetime.strptime(str(expiration_date).strip(), "%Y-%m-%d")
        except ValueError:
            raise InvalidToolInputError("expiration_date must be in YYYY-MM-DD format.")

    try:
        if operation_str == "add":
            ing_name = arguments.get("ingredient_name")
            if not ing_name:
                raise InvalidToolInputError("ingredient_name is required for 'add' operation.")
            ing_name_str = str(ing_name).strip()
            if not ing_name_str:
                raise InvalidToolInputError("ingredient_name cannot be empty.")

            qty = arguments.get("quantity")
            if qty is None:
                raise InvalidToolInputError("quantity is required for 'add' operation.")
            try:
                qty_val = float(qty)
                if qty_val <= 0:
                    raise ValueError()
            except ValueError:
                raise InvalidToolInputError("quantity must be a positive number.")

            unit = arguments.get("unit")
            if not unit:
                raise InvalidToolInputError("unit is required for 'add' operation.")
            unit_str = str(unit).strip()
            if not unit_str:
                raise InvalidToolInputError("unit cannot be empty.")

            payload = {
                "ingredient_name": ing_name_str,
                "quantity": qty_val,
                "unit": unit_str
            }
            if expiration_date:
                payload["expiration_date"] = str(expiration_date).strip()

            data = await backend_client.post("/pantry", json=payload)

        elif operation_str == "update":
            item_id = arguments.get("item_id")
            if not item_id:
                raise InvalidToolInputError("item_id is required for 'update' operation.")
            item_id_str = str(item_id).strip()
            if not item_id_str:
                raise InvalidToolInputError("item_id cannot be empty.")

            payload = {}
            qty = arguments.get("quantity")
            if qty is not None:
                try:
                    qty_val = float(qty)
                    if qty_val <= 0:
                        raise ValueError()
                    payload["quantity"] = qty_val
                except ValueError:
                    raise InvalidToolInputError("quantity must be a positive number.")

            unit = arguments.get("unit")
            if unit is not None:
                unit_str = str(unit).strip()
                if not unit_str:
                    raise InvalidToolInputError("unit cannot be empty.")
                payload["unit"] = unit_str

            if expiration_date:
                payload["expiration_date"] = str(expiration_date).strip()

            if not payload:
                raise InvalidToolInputError("At least one parameter (quantity, unit, or expiration_date) must be provided to update.")

            # PATCH /api/pantry/{item_id}
            data = await backend_client.request("PATCH", f"/pantry/{item_id_str}", json=payload)

        else:  # remove
            item_id = arguments.get("item_id")
            if not item_id:
                raise InvalidToolInputError("item_id is required for 'remove' operation.")
            item_id_str = str(item_id).strip()
            if not item_id_str:
                raise InvalidToolInputError("item_id cannot be empty.")

            # DELETE /api/pantry/{item_id}
            await backend_client.request("DELETE", f"/pantry/{item_id_str}")
            data = {"status": "success", "message": f"Pantry item '{item_id_str}' removed successfully."}

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )
            ]
        )
    except InvalidToolInputError:
        raise
    except MCPBaseError as e:
        return types.CallToolResult(
            is_error=True,
            content=[
                types.TextContent(
                    type="text",
                    text=f"Error performing pantry {operation_str}: {e.message} (Code: {e.code})"
                )
            ]
        )
