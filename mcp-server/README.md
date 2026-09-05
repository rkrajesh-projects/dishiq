# DishIQ MCP Server Foundation

This directory contains the Model Context Protocol (MCP) server foundation for the DishIQ kitchen and grocery manager application.

---

## 1. Purpose
The DishIQ MCP server bridges any MCP-compatible LLM host (such as Claude Desktop or Cursor) with the DishIQ system. It exposes tools and resources enabling the AI assistant to search recipes, compare grocery costs, and manage pantry storage directly using standard protocol schemas.

---

## 2. Architecture & Design Principles
- **No Duplicate Business Logic**: The MCP server acts strictly as a lightweight translation layer. All operations (e.g. database queries, grocery matching, cart optimizations, recipe recommendations) are delegated to the existing FastAPI backend service.
- **Robust Error Handling**: Communication timeouts, backend unavailability, validation issues, and bad response formats are mapped directly to standard JSON-RPC structured error responses.
- **Secure Configuration**: The server uses environment variables for config. No credentials or secrets are committed.

---

## 3. Configuration & Environment Variables

Create a `.env` file based on `.env.example` in this folder:

| Variable | Description | Default |
|---|---|---|
| `DISHIQ_BACKEND_URL` | Base URL of the DishIQ FastAPI backend API. | `http://127.0.0.1:8000/api` |
| `DISHIQ_REQUEST_TIMEOUT` | Timeout limit for backend HTTP requests. | `10.0` |
| `DISHIQ_MCP_SERVER_NAME` | Display name of the MCP server. | `DishIQ-MCP` |
| `DISHIQ_MCP_SERVER_VERSION` | Version string of the MCP server. | `1.0.0` |

---

## 4. Installation & Setup

### Prerequisites
- Python 3.10 or higher (due to Model Context Protocol SDK requirements).

### Install Dependencies
To install the required SDK and HTTP components in your environment:
```bash
pip install -r requirements.txt
```

---

## 5. Testing
Run the MCP foundation tests using pytest in this directory:
```bash
python -m pytest -v
```

---

## 6. How it Connects to DishIQ
Hosts communicate with the MCP server over standard input/output (**stdio**) transport.

### Claude Desktop Integration Configuration
Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "dishiq-mcp": {
      "command": "C:\\Users\\rajeshkumar\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": [
        "D:\\DishIQ\\mcp-server\\app\\server.py"
      ],
      "env": {
        "DISHIQ_BACKEND_URL": "http://127.0.0.1:8000/api"
      }
    }
  }
}
```
*Note: Make sure the DishIQ FastAPI backend server is running in parallel on `http://127.0.0.1:8000`.*

---

## 7. Recipe Tools
The Model Context Protocol (MCP) server acts strictly as an interface layer over DishIQ backend services. All recipe business logic (searching, ranking, sorting, and ingredient parsing) remains in the backend.

The following recipe-related tools are available:

### 1. `search_recipes`
- **Purpose**: Search DishIQ recipes using dish name and optional cuisine, dietary, cooking-time, and ingredient filters.
- **Parameters**:
  - `q` (string, optional): Search query text (e.g. `"paneer"`)
  - `cuisine` (string, optional): Cuisine type (e.g. `"Indian"`)
  - `dietary_type` (string, optional): Dietary restriction (e.g. `"Vegetarian"`)
  - `max_cooking_time` (integer, optional): Maximum cook + prep time in minutes
  - `available_ingredients` (string, optional): A required ingredient in the recipe
  - `limit` (integer, optional): Page size (default: `10`)
  - `offset` (integer, optional): Offset count for pagination (default: `0`)
- **Example Request**:
  ```json
  {
    "name": "search_recipes",
    "arguments": {
      "q": "paneer",
      "cuisine": "Indian"
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "recipes": [
      {
        "id": "recipe-id-123",
        "name": "Paneer Bhurji",
        "description": "Scrambled cottage cheese cooked with chopped onions, tomatoes, and aromatic Indian spices.",
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
    "total_pages": 1,
    "search_filters": {
      "q": "paneer",
      "cuisine": "Indian",
      "dietary_type": null,
      "max_cooking_time": null,
      "available_ingredients": null
    }
  }
  ```

### 2. `get_recipe`
- **Purpose**: Retrieve detailed instructions, metadata, and serving size of a specific DishIQ recipe by ID.
- **Parameters**:
  - `recipe_id` (string, required): The unique ID of the recipe
- **Example Request**:
  ```json
  {
    "name": "get_recipe",
    "arguments": {
      "recipe_id": "recipe-id-123"
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "id": "recipe-id-123",
    "name": "Paneer Bhurji",
    "description": "Scrambled cottage cheese cooked with chopped onions, tomatoes, and aromatic Indian spices.",
    "cuisine": "Indian",
    "dietary_type": "Vegetarian",
    "preparation_minutes": 10,
    "cooking_minutes": 15,
    "servings": 4,
    "instructions": [
      "Crumble paneer finely in a bowl.",
      "Heat oil and butter in a pan, add cumin seeds and green chilies.",
      "Sauté onions until golden brown, then add ginger-garlic paste and chopped tomatoes."
    ]
  }
  ```

### 3. `get_recipe_ingredients`
- **Purpose**: Retrieve the stored raw ingredient lines for a recipe, parsed and normalized by DishIQ.
- **Parameters**:
  - `recipe_id` (string, required): The unique ID of the recipe
- **Example Request**:
  ```json
  {
    "name": "get_recipe_ingredients",
    "arguments": {
      "recipe_id": "recipe-id-123"
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "count": 2,
    "results": [
      {
        "raw_text": "200 g paneer",
        "display_name": "Paneer",
        "canonical_name": "paneer",
        "category": "dairy",
        "quantity": 200.0,
        "unit": "g",
        "preparation_note": null,
        "optional": false,
        "confidence_score": 0.95
      }
    ]
  }
  ```

---

## 8. Grocery Tools
The Model Context Protocol (MCP) server acts strictly as an interface layer over DishIQ backend services. All product matching, price comparison, unit pricing, package calculation, and cart optimization logic remains in the backend.

### Important Data-Safety Notice
All prices, delivery fees, and stock statuses currently provided are **demonstration data** and are marked as `CACHED` or `demo`. The MCP server does not claim real-time live market access and strictly forwards cached/demo statuses exactly as received from the backend to preserve transparency.

The following grocery-related tools are available:

### 1. `search_grocery_products`
- **Purpose**: Search DishIQ's grocery product catalog and semantic matching system for suitable products matching a given query.
- **Parameters**:
  - `query` (string, required): Ingredient name or search query (e.g. `"paneer"`, `"spinach"`)
  - `limit` (integer, optional): Maximum ranked matches to return (1-50, default: `10`)
  - `threshold` (number, optional): Minimum cosine similarity matching score (0.0 to 1.0)
- **Example Request**:
  ```json
  {
    "name": "search_grocery_products",
    "arguments": {
      "query": "paneer",
      "limit": 1
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "query": "paneer",
    "canonical_name": "paneer",
    "threshold": 0.4,
    "total_matches": 1,
    "results": [
      {
        "product_id": "p1",
        "product_name": "Amul Paneer 200g",
        "brand": "Amul",
        "category": "Dairy",
        "store_name": "Demo QuickMart",
        "store_id": "s1",
        "price": 90.25,
        "currency": "INR",
        "package_quantity": 200.0,
        "package_unit": "g",
        "unit_price": 0.451,
        "base_unit": "g",
        "similarity_score": 0.95,
        "match_status": "matched",
        "data_source_type": "demo",
        "price_freshness": "CACHED"
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
      "similarity_score": 0.95,
      "data_source_type": "demo",
      "price_freshness": "CACHED"
    },
    "comparison_mode": "unit_price",
    "data_source": "demo",
    "price_freshness": "CACHED"
  }
  ```

### 2. `compare_recipe_cart`
- **Purpose**: Calculate and compare the total basket cost of a list of recipe ingredients across different grocery stores (including delivery fees, packaging splits, and missing items).
- **Parameters**:
  - `ingredients` (array of objects, required): The ingredients to evaluate. Each ingredient has:
    - `name` (string, required): Ingredient query (e.g. `"paneer"`)
    - `quantity` (number, required): Required amount (e.g. `500.0`)
    - `unit` (string, required): Unit of measurement (e.g. `"g"`)
- **Example Request**:
  ```json
  {
    "name": "compare_recipe_cart",
    "arguments": {
      "ingredients": [
        {"name": "paneer", "quantity": 500.0, "unit": "g"}
      ]
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "stores": [
      {
        "store_id": "s1",
        "store_name": "Demo QuickMart",
        "subtotal": 270.75,
        "delivery_fee": 30.0,
        "total": 300.75,
        "complete": true,
        "selected_products": [
          {
            "product_id": "p1",
            "product_name": "Amul Paneer 200g",
            "quantity_to_buy": 3,
            "unit_price": 0.451,
            "line_cost": 270.75,
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
  ```

### 3. `get_store_prices`
- **Purpose**: Retrieve store-specific prices and availability catalogs from backend stores.
- **Parameters**:
  - `ingredient` (string, optional): Search catalog by ingredient name
  - `store_id` (string, optional): Filter by store identifier
  - `category` (string, optional): Filter by product category (e.g. `"Dairy"`)
  - `limit` (integer, optional): Maximum items to return (1-50, default: `10`)
- **Example Request**:
  ```json
  {
    "name": "get_store_prices",
    "arguments": {
      "ingredient": "paneer"
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "ingredient_text": "paneer",
    "canonical_name": "paneer",
    "results": [
      {
        "product_id": "p1",
        "product_name": "Amul Paneer 200g",
        "price": 90.25,
        "store_name": "Demo QuickMart",
        "similarity_score": 0.95
      }
    ]
  }
  ```

---

## 9. Pantry Tools
The Model Context Protocol (MCP) server acts strictly as an interface layer over DishIQ backend services. All pantry storage calculations, ingredient normalizations, and comparisons remain in the backend.

### Authentication & User Isolation
- Pantry data is user-specific. The MCP server does not allow arbitrary user ID passing in tool parameters to prevent privilege escalation.
- Because full database-backed authentication (Phase 11) is pending, the local development environment maps requests to a default seeded development user context. This limitation preserves user isolation design patterns without creating insecure ad-hoc security layers.

The following pantry-related tools are available:

### 1. `get_pantry`
- **Purpose**: Retrieve the pantry inventory available to the current DishIQ user.
- **Parameters**: None.
- **Example Request**:
  ```json
  {
    "name": "get_pantry",
    "arguments": {}
  }
  ```
- **Example Response**:
  ```json
  [
    {
      "id": "pantry-item-123",
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
  ```

### 2. `check_missing_ingredients`
- **Purpose**: Check which ingredients for a DishIQ recipe are already available, partially available, or missing from the pantry.
- **Parameters**:
  - `recipe_id` (string, required): Unique ID of the recipe
- **Example Request**:
  ```json
  {
    "name": "check_missing_ingredients",
    "arguments": {
      "recipe_id": "recipe-id-123"
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "recipe_id": "recipe-id-123",
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
  ```

### 3. `update_pantry`
- **Purpose**: Add, update, or remove pantry inventory using DishIQ's pantry services.
- **Parameters**:
  - `operation` (string, required): Operation type (`"add"`, `"update"`, or `"remove"`)
  - `ingredient_name` (string, optional): Ingredient name (required for `"add"`)
  - `item_id` (string, optional): The unique ID of the pantry item (required for `"update"` and `"remove"`)
  - `quantity` (number, optional): Ingredient quantity (positive number, required for `"add"` or `"update"`)
  - `unit` (string, optional): Measurement unit (required for `"add"`)
  - `expiration_date` (string, optional): Optional expiration date in `YYYY-MM-DD` format
- **Example Request**:
  ```json
  {
    "name": "update_pantry",
    "arguments": {
      "operation": "add",
      "ingredient_name": "paneer",
      "quantity": 500.0,
      "unit": "g",
      "expiration_date": "2026-09-01"
    }
  }
  ```
- **Example Response**:
  ```json
  {
    "id": "pantry-item-123",
    "ingredient_id": "ing-1",
    "ingredient_name": "paneer",
    "canonical_name": "paneer",
    "quantity": 500.0,
    "unit": "g",
    "expiration_date": "2026-09-01",
    "created_at": "2026-08-09T12:00:00Z",
    "updated_at": "2026-08-09T12:00:00Z"
  }
  ```
