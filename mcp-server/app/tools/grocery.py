from __future__ import annotations
import json
import logging
import mcp_types as types
from typing import Any, Dict, List, Optional
from app.backend_client import BackendClient
from app.errors import MCPBaseError, InvalidToolInputError

logger = logging.getLogger("mcp-server.tools.grocery")

backend_client = BackendClient()

def get_grocery_tools() -> list[types.Tool]:
    """
    Return the definition of the grocery tools.
    """
    return [
        types.Tool(
            name="search_grocery_products",
            description="Search DishIQ grocery products using the existing backend product matching and grocery catalogue services.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Ingredient name or search query (e.g. 'paneer', 'spinach')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of ranked matches to return (1-50, default 10)"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Optional similarity score threshold filter (0.0 to 1.0)"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="compare_recipe_cart",
            description="Compare the cost of a multi-ingredient recipe cart across available DishIQ grocery stores using the existing cart comparison service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ingredients": {
                        "type": "array",
                        "description": "List of recipe ingredients with quantities and units to compare",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Ingredient name (e.g. 'paneer')"
                                },
                                "quantity": {
                                    "type": "number",
                                    "description": "Required numeric quantity (e.g. 500.0)"
                                },
                                "unit": {
                                    "type": "string",
                                    "description": "Measurement unit (e.g. 'g', 'kg', 'ml', 'piece')"
                                }
                            },
                            "required": ["name", "quantity", "unit"]
                        }
                    }
                },
                "required": ["ingredients"]
            }
        ),
        types.Tool(
            name="get_store_prices",
            description="Retrieve recorded grocery prices and availability for products/stores from DishIQ's configured grocery providers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ingredient": {
                        "type": "string",
                        "description": "Optional ingredient to compare prices for (e.g. 'paneer')"
                    },
                    "store_id": {
                        "type": "string",
                        "description": "Optional store ID to filter catalog products"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. 'Dairy', 'Produce')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items to return (1-50, default 10)"
                    }
                }
            }
        )
    ]


async def execute_search_grocery_products(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute search_grocery_products tool."""
    query = arguments.get("query")
    if not query:
        raise InvalidToolInputError("query parameter is required.")

    query_str = str(query).strip()
    if not query_str:
        raise InvalidToolInputError("query parameter cannot be empty or whitespace-only.")

    limit = arguments.get("limit", 10)
    if limit is not None:
        try:
            limit = int(limit)
            if limit < 1 or limit > 50:
                raise ValueError()
        except ValueError:
            raise InvalidToolInputError("limit parameter must be an integer between 1 and 50.")

    threshold = arguments.get("threshold")
    if threshold is not None:
        try:
            threshold = float(threshold)
            if threshold < 0.0 or threshold > 1.0:
                raise ValueError()
        except ValueError:
            raise InvalidToolInputError("threshold parameter must be a float between 0.0 and 1.0.")

    params = {"ingredient": query_str, "limit": limit}
    if threshold is not None:
        params["threshold"] = threshold

    try:
        data = await backend_client.get("/grocery/match", params=params)
        
        # Preserving demo/cached data source identifiers
        results_formatted = []
        for res in data.get("results", []):
            results_formatted.append({
                "product_id": res.get("product_id"),
                "product_name": res.get("product_name"),
                "brand": res.get("brand"),
                "category": res.get("category"),
                "store_name": res.get("store_name"),
                "store_id": res.get("store_id"),
                "price": res.get("price"),
                "currency": res.get("currency", "INR"),
                "package_quantity": res.get("package_quantity"),
                "package_unit": res.get("package_unit"),
                "unit_price": res.get("unit_price"),
                "base_unit": res.get("base_unit"),
                "similarity_score": res.get("similarity_score"),
                "match_status": res.get("match_status"),
                "data_source_type": "demo",
                "price_freshness": "CACHED"
            })

        best_option = None
        if data.get("best_option"):
            bo = data["best_option"]
            best_option = {
                "product_id": bo.get("product_id"),
                "product_name": bo.get("product_name"),
                "store_name": bo.get("store_name"),
                "price": bo.get("price"),
                "currency": bo.get("currency", "INR"),
                "package_quantity": bo.get("package_quantity"),
                "package_unit": bo.get("package_unit"),
                "unit_price": bo.get("unit_price"),
                "base_unit": bo.get("base_unit"),
                "similarity_score": bo.get("similarity_score"),
                "data_source_type": "demo",
                "price_freshness": "CACHED"
            }

        formatted_response = {
            "query": data.get("ingredient_text"),
            "canonical_name": data.get("canonical_name"),
            "threshold": data.get("threshold"),
            "total_matches": data.get("total_matches"),
            "results": results_formatted,
            "best_option": best_option,
            "comparison_mode": data.get("comparison_mode"),
            "data_source": "demo",
            "price_freshness": "CACHED"
        }

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps(formatted_response, indent=2)
                )
            ]
        )
    except MCPBaseError as e:
        return types.CallToolResult(
            is_error=True,
            content=[
                types.TextContent(
                    type="text",
                    text=f"Error searching grocery products: {e.message} (Code: {e.code})"
                )
            ]
        )


async def execute_compare_recipe_cart(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute compare_recipe_cart tool."""
    ingredients = arguments.get("ingredients")
    if not ingredients or not isinstance(ingredients, list):
        raise InvalidToolInputError("ingredients parameter is required and must be an array.")

    mapped_ingredients = []
    for idx, ing in enumerate(ingredients):
        if not isinstance(ing, dict):
            raise InvalidToolInputError(f"Ingredient at index {idx} must be an object.")
        
        name = ing.get("name")
        if not name:
            raise InvalidToolInputError(f"Ingredient at index {idx} is missing a required name parameter.")
        name_str = str(name).strip()
        if not name_str:
            raise InvalidToolInputError(f"Ingredient name at index {idx} cannot be empty.")

        quantity = ing.get("quantity")
        if quantity is None:
            raise InvalidToolInputError(f"Ingredient '{name_str}' is missing a required quantity parameter.")
        try:
            qty_val = float(quantity)
            if qty_val <= 0:
                raise ValueError()
        except ValueError:
            raise InvalidToolInputError(f"Ingredient '{name_str}' quantity must be a positive number.")

        unit = ing.get("unit")
        if not unit:
            raise InvalidToolInputError(f"Ingredient '{name_str}' is missing a required unit parameter.")
        unit_str = str(unit).strip()
        if not unit_str:
            raise InvalidToolInputError(f"Ingredient '{name_str}' unit cannot be empty.")

        mapped_ingredients.append({
            "ingredient_name": name_str,
            "required_quantity": qty_val,
            "required_unit": unit_str
        })

    payload = {"ingredients": mapped_ingredients}

    try:
        # Call the existing Phase 7 endpoint POST /api/cart/compare
        data = await backend_client.post("/cart/compare", json=payload)
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
                    text=f"Error comparing recipe cart: {e.message} (Code: {e.code})"
                )
            ]
        )


async def execute_get_store_prices(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Execute get_store_prices tool."""
    ingredient = arguments.get("ingredient")
    store_id = arguments.get("store_id")
    category = arguments.get("category")
    limit = arguments.get("limit", 10)

    if limit is not None:
        try:
            limit = int(limit)
            if limit < 1 or limit > 50:
                raise ValueError()
        except ValueError:
            raise InvalidToolInputError("limit parameter must be an integer between 1 and 50.")

    # If ingredient is provided, we run the price comparison endpoint
    if ingredient:
        ingredient_str = str(ingredient).strip()
        if not ingredient_str:
            raise InvalidToolInputError("ingredient parameter cannot be whitespace-only.")

        params = {"ingredient": ingredient_str, "limit": limit}
        try:
            # Query /grocery/compare
            data = await backend_client.get("/grocery/compare", params=params)
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
                        text=f"Error getting store prices: {e.message} (Code: {e.code})"
                    )
                ]
            )
    else:
        # General store/product listing endpoint from backend
        params = {"page_size": limit, "page": 1}
        if store_id:
            params["store_id"] = str(store_id)
        if category:
            params["category"] = str(category)

        try:
            # Query /products
            data = await backend_client.get("/products", params=params)
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
                        text=f"Error getting store products: {e.message} (Code: {e.code})"
                    )
                ]
            )
