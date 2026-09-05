# DishIQ API Design Specification

## 1. Overview
DishIQ backend provides a versioned RESTful API under the `/api/v1` base route. All requests and responses use JSON formatting with standard HTTP status codes and uniform error payloads.

---

## 2. Logical Endpoint Modules

### Module 1: System & Health
#### GET `/api/health`
- **Purpose**: Service health check & status probe (does not require DB connection).
- **Authentication**: None.
- **Response (200 OK)**:
```json
{
  "status": "ok",
  "application": "DishIQ",
  "version": "1.0.0"
}
```

---

### Module 2: Authentication & User Profile
#### POST `/api/v1/auth/register`
- **Purpose**: Create a new user account.
- **Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "Rajesh Kumar"
}
```
- **Response (201 Created)**: `User` object schema.

#### POST `/api/v1/auth/login`
- **Purpose**: Authenticate user and receive JWT access token.
- **Request**: `OAuth2` password form or JSON `{ "email": "...", "password": "..." }`.
- **Response (200 OK)**: `{ "access_token": "...", "token_type": "bearer" }`.

---

### Module 3: User Preferences & Family Profile
#### GET `/api/v1/preferences`
- **Purpose**: Fetch current user dietary, budget, and family preferences.
- **Authentication**: Bearer JWT.
- **Response (200 OK)**:
```json
{
  "dietary_restrictions": ["Vegetarian"],
  "weekly_budget": 150.00,
  "household_size": 3,
  "disliked_ingredients": ["mushroom"],
  "preferred_stores": ["Demo Store A", "Demo Store B"]
}
```

#### PUT `/api/v1/preferences`
- **Purpose**: Update user preference configuration.
- **Authentication**: Bearer JWT.

---

### Module 4: Recipe Search & Smart Ranking
#### GET `/api/v1/recipes/search`
- **Purpose**: Search recipes with AI preference ranking and pantry matching score.
- **Authentication**: Optional / Bearer JWT.
- **Query Params**: `q` (string), `cuisine` (string), `max_prep_time` (int), `diet` (string).
- **Response (200 OK)**:
```json
{
  "query": "Paneer",
  "total": 1,
  "recipes": [
    {
      "id": "recipe_123",
      "title": "Paneer Bhurji",
      "prep_time_minutes": 20,
      "servings": 4,
      "relevance_score": 0.95,
      "pantry_match_percentage": 75.0,
      "missing_ingredients_count": 2
    }
  ]
}
```

#### GET `/api/v1/recipes/{recipe_id}`
- **Purpose**: Get full details of a single recipe, normalized ingredient list, and instructions.
- **Authentication**: Optional.

---

### Module 5: Pantry Inventory Management
#### GET `/api/v1/pantry`
- **Purpose**: List user's active pantry inventory.
- **Authentication**: Bearer JWT.
- **Response (200 OK)**:
```json
{
  "items": [
    {"id": "p1", "ingredient_name": "Tomato", "quantity": 3.0, "unit": "pieces"},
    {"id": "p2", "ingredient_name": "Onion", "quantity": 2.0, "unit": "pieces"},
    {"id": "p3", "ingredient_name": "Egg", "quantity": 6.0, "unit": "pieces"}
  ]
}
```

#### POST `/api/v1/pantry`
- **Purpose**: Add or update an item in pantry inventory.
- **Authentication**: Bearer JWT.

---

### Module 6: Grocery Comparison & Cart Optimization
#### POST `/api/v1/grocery/compare`
- **Purpose**: Extract required ingredients for a recipe, match against demo stores, and generate optimal cart.
- **Authentication**: Bearer JWT.
- **Request**:
```json
{
  "recipe_id": "recipe_123",
  "servings_override": 4,
  "max_stores": 2
}
```
- **Response (200 OK)**:
```json
{
  "recipe_id": "recipe_123",
  "already_in_pantry": ["Tomato", "Onion"],
  "needed_ingredients": ["Paneer", "Coriander"],
  "recommended_cart": {
    "total_cost": 6.49,
    "store_breakdown": [
      {
        "store_name": "Demo Grocery Store A",
        "items": [
          {"product_name": "Fresh Paneer 200g", "price": 4.99, "quantity": 1},
          {"product_name": "Fresh Coriander Bunch", "price": 1.50, "quantity": 1}
        ]
      }
    ]
  }
}
```

---

### Module 7: Interactive Cooking Assistant
#### POST `/api/v1/cooking/start`
- **Purpose**: Initiate a step-by-step cooking session.
- **Authentication**: Bearer JWT.
- **Request**: `{ "recipe_id": "recipe_123" }`.
- **Response (201 Created)**: Session ID, current step, timers, ingredient check list.

#### POST `/api/v1/cooking/{session_id}/next`
- **Purpose**: Advance to the next cooking step.

---

### Module 8: AI Kitchen Memory & Proactive Recommendations
#### GET `/api/v1/recommendations/proactive`
- **Purpose**: Get proactive meal recommendations generated from AI Kitchen Memory.
- **Authentication**: Bearer JWT.
- **Response (200 OK)**:
```json
{
  "recommendations": [
    {
      "recipe_id": "recipe_123",
      "recipe_title": "Paneer Bhurji",
      "reasoning": "You already have tomatoes, onions and eggs. Paneer is available in today's demonstration grocery data. Based on your family's vegetarian preference and weekly budget, I recommend Paneer Bhurji. Buying only paneer and coriander completes the meal.",
      "existing_pantry_items": ["Tomatoes", "Onions", "Eggs"],
      "items_to_buy": ["Paneer", "Coriander"],
      "estimated_additional_cost": 6.49
    }
  ]
}
```
