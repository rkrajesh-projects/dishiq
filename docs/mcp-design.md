# DishIQ Model Context Protocol (MCP) Design

## 1. Overview
DishIQ exposes its core capabilities to LLMs and AI client agents through a dedicated Model Context Protocol (MCP) tool server developed using the **Python MCP SDK**.

The server resides in the `mcp-server/` directory and interfaces cleanly with the DishIQ FastAPI backend services.

---

## 2. MCP Tools Specification

### 2.1 Recipe Tools

#### `search_recipes`
- **Description**: Search DishIQ recipe database using natural language queries and preference filters.
- **Input Schema**:
```json
{
  "query": "string (required, e.g. 'Paneer')",
  "max_prep_time": "integer (optional)",
  "dietary_preference": "string (optional, e.g. 'Vegetarian')"
}
```
- **Output Schema**: Array of ranked recipe objects with prep time, servings, ingredient list, and pantry match indicators.
- **Backend Interaction**: Calls `GET /api/v1/recipes/search`.
- **Error Handling**: Returns structured MCP error object if backend service is unreachable or query yields no matches.

#### `get_recipe_details`
- **Description**: Retrieve detailed recipe steps, nutrition, and normalized ingredient breakdown.
- **Input Schema**: `{ "recipe_id": "string (required)" }`.
- **Output Schema**: Full `Recipe` details schema.

---

### 2.2 Grocery Tools

#### `compare_store_prices`
- **Description**: Compare prices across demonstration grocery stores for a given list of ingredients.
- **Input Schema**:
```json
{
  "ingredients": ["array of strings (required)"],
  "max_stores": "integer (default: 2)"
}
```
- **Output Schema**: Store comparison matrix, price per item, and recommended store selection.
- **Backend Interaction**: Calls `POST /api/v1/grocery/compare`.

#### `optimize_shopping_cart`
- **Description**: Generate the overall lowest-cost shopping plan considering missing pantry items and demo store pricing.
- **Input Schema**: `{ "recipe_id": "string", "user_id": "string" }`.
- **Output Schema**: Optimized cart breakdown per store with total estimated cost.

---

### 2.3 Pantry Tools

#### `get_pantry_inventory`
- **Description**: Fetch active pantry inventory for a user.
- **Input Schema**: `{ "user_id": "string (required)" }`.
- **Output Schema**: List of pantry items with ingredient names, quantities, and expiration dates.

#### `update_pantry_item`
- **Description**: Add or modify quantity of a pantry ingredient.
- **Input Schema**: `{ "ingredient_name": "string", "quantity": "number", "unit": "string" }`.
- **Output Schema**: Updated item confirmation object.

---

## 3. Security & Error Handling Policies

1. **Demonstration Data Notice**: Responses containing product prices explicitly flag `is_demo_data: true` to notify LLM clients that prices derive from demonstration catalogs.
2. **Error Protocols**: Tool handlers sanitize backend exceptions into standard MCP JSON-RPC error codes (`-32603` for internal execution errors, `-32602` for invalid parameters).
