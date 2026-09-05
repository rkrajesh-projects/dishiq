from __future__ import annotations
import json
import logging
import mcp_types as types
from typing import Any, Dict, Optional
from app.backend_client import BackendClient
from app.errors import MCPBaseError, InvalidToolInputError

logger = logging.getLogger("mcp-server.tools.recipes")

backend_client = BackendClient()

def get_recipe_tools() -> list[types.Tool]:
    """
    Return the definition of the recipe tools.
    """
    return [
        types.Tool(
            name="search_recipes",
            description="Search DishIQ recipes using name query, cuisine, dietary restriction, max cooking time, or ingredient filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Search query text (e.g. 'paneer bhurji')"
                    },
                    "cuisine": {
                        "type": "string",
                        "description": "Cuisine type (e.g. 'Indian', 'Italian')"
                    },
                    "dietary_type": {
                        "type": "string",
                        "description": "Dietary restriction (e.g. 'Vegetarian', 'Vegan')"
                    },
                    "max_cooking_time": {
                        "type": "integer",
                        "description": "Maximum cook + prep time in minutes"
                    },
                    "available_ingredients": {
                        "type": "string",
                        "description": "A required ingredient that must be present in the recipe"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of records to return (page size)"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset count for pagination"
                    }
                }
            }
        ),
        types.Tool(
            name="get_recipe",
            description="Retrieve detailed instructions, metadata, and serving size of a specific DishIQ recipe by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "The unique ID of the recipe (UUID or string representation)"
                    }
                },
                "required": ["recipe_id"]
            }
        ),
        types.Tool(
            name="get_recipe_ingredients",
            description="Retrieve the stored raw ingredient lines for a recipe, parsed and normalized by DishIQ.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "The unique ID of the recipe (UUID or string representation)"
                    }
                },
                "required": ["recipe_id"]
            }
        )
    ]


async def execute_search_recipes(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute search_recipes tool."""
    # Parameter mapping and parsing
    q = arguments.get("q")
    cuisine = arguments.get("cuisine")
    dietary_type = arguments.get("dietary_type")
    max_cooking_time = arguments.get("max_cooking_time")
    available_ingredients = arguments.get("available_ingredients")
    limit = arguments.get("limit", 10)
    offset = arguments.get("offset", 0)

    # Validate numeric parameters
    if limit is not None:
        try:
            limit = int(limit)
            if limit < 1 or limit > 50:
                raise ValueError()
        except ValueError:
            raise InvalidToolInputError("Limit parameter must be an integer between 1 and 50.")

    if offset is not None:
        try:
            offset = int(offset)
            if offset < 0:
                raise ValueError()
        except ValueError:
            raise InvalidToolInputError("Offset parameter must be a non-negative integer.")

    if max_cooking_time is not None:
        try:
            max_cooking_time = int(max_cooking_time)
            if max_cooking_time < 1:
                raise ValueError()
        except ValueError:
            raise InvalidToolInputError("max_cooking_time must be a positive integer.")

    # Convert limit/offset to page/page_size for backend API
    page_size = limit
    page = (offset // limit) + 1 if limit > 0 else 1

    params = {}
    if q:
        params["q"] = q
    if cuisine:
        params["cuisine"] = cuisine
    if dietary_type:
        params["dietary_type"] = dietary_type
    if max_cooking_time:
        params["max_time"] = max_cooking_time
    if available_ingredients:
        params["ingredient"] = available_ingredients
    
    params["page"] = page
    params["page_size"] = page_size

    try:
        data = await backend_client.get("/recipes/search", params=params)
        
        # Structure output to contain recipes and pagination details
        formatted_result = {
            "recipes": data.get("items", []),
            "total": data.get("total", 0),
            "page": data.get("page", 1),
            "page_size": data.get("page_size", 10),
            "total_pages": data.get("total_pages", 0),
            "search_filters": {
                "q": q,
                "cuisine": cuisine,
                "dietary_type": dietary_type,
                "max_cooking_time": max_cooking_time,
                "available_ingredients": available_ingredients
            }
        }
        
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps(formatted_result, indent=2)
                )
            ]
        )
    except MCPBaseError as e:
        return types.CallToolResult(
            is_error=True,
            content=[
                types.TextContent(
                    type="text",
                    text=f"Error searching recipes: {e.message} (Code: {e.code})"
                )
            ]
        )


async def execute_get_recipe(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute get_recipe tool."""
    recipe_id = arguments.get("recipe_id")
    if not recipe_id:
        raise InvalidToolInputError("recipe_id parameter is required.")

    # Convert recipe_id to string (if integer was passed, coercion handles it)
    recipe_id_str = str(recipe_id).strip()
    if not recipe_id_str:
        raise InvalidToolInputError("recipe_id parameter cannot be blank.")

    try:
        data = await backend_client.get(f"/recipes/{recipe_id_str}")
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
                    text=f"Error retrieving recipe: {e.message} (Code: {e.code})"
                )
            ]
        )


async def execute_get_recipe_ingredients(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute get_recipe_ingredients tool."""
    recipe_id = arguments.get("recipe_id")
    if not recipe_id:
        raise InvalidToolInputError("recipe_id parameter is required.")

    recipe_id_str = str(recipe_id).strip()
    if not recipe_id_str:
        raise InvalidToolInputError("recipe_id parameter cannot be blank.")

    try:
        data = await backend_client.get(f"/recipes/{recipe_id_str}/ingredients")
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
                    text=f"Error retrieving recipe ingredients: {e.message} (Code: {e.code})"
                )
            ]
        )
