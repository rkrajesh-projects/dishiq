# DishIQ Requirements Specification

## 1. System Requirements & Overview

DishIQ is an intelligent meal planning, grocery price comparison, interactive cooking assistant, and AI Kitchen Memory platform.

### Core Capabilities
1. **Recipe Search & Smart Ranking**: Search recipes by dish name, ingredients, or craving, ranked by user dietary preferences, cooking time, and available pantry items.
2. **Ingredient Extraction & Normalization**: Standardize raw recipe ingredient strings into structured canonical entities (name, quantity, unit, preparation style).
3. **Grocery Product Matching & Store Comparison**: Match normalized ingredients against real demonstration store inventories and compare costs across multiple grocery chains.
4. **Economical Cart Optimizer**: Generate optimal shopping lists considering multi-store vs. single-store trade-offs, budget constraints, and missing items.
5. **Interactive Step-by-Step Cooking**: Interactive voice- or UI-guided cooking mode tracking active step timer and ingredient usage.
6. **AI Kitchen Memory**: Persistent learning engine tracking user preferences, family preferences, pantry inventory, purchase history, dietary restrictions, and cooking frequency to deliver proactive, automated meal suggestions.

---

## 2. MVP User Journey

The 12-step MVP workflow consists of the following sequential pipeline:

```
[1. User Searches Dish] -> [2. Ranked Recipes Returned] -> [3. User Selects Recipe]
                                                                  |
[6. Grocery Products Searched] <- [5. Pantry Inventory Checked] <- [4. Ingredients Extracted]
          |
[7. Store Prices Compared] -> [8. Best Cart Generated] -> [9. Interactive Cooking Mode]
                                                                  |
[12. AI Kitchen Memory Updated] <- [11. Preferences Learnt] <- [10. User Feedback Submitted]
```

1. **User Searches for a Dish**: User enters a query (e.g., "Paneer Bhurji" or "high protein dinner under 30 mins").
2. **System Returns Ranked Recipes**: Search results are scored and ordered using vector similarity and preference-matching models.
3. **User Selects a Recipe**: Detailed view displays prep time, nutritional breakdown, and required ingredients.
4. **Ingredients Extracted & Normalized**: Raw strings (e.g., "2 cups diced firm paneer") parsed into `{ingredient: "paneer", quantity: 2, unit: "cups", prep: "diced"}`.
5. **Pantry Inventory Checked**: System checks current `PantryItem` stock, highlighting items already owned and identifying missing items.
6. **Grocery Products Searched**: Missing ingredients matched against demonstration store product catalogs.
7. **Store Prices Compared**: Price comparison across demonstration stores (e.g., Store A, Store B, Store C).
8. **Best Shopping Cart Generated**: Optimal cart computed minimizing total cost while respecting store split limits.
9. **User Cooks Using Interactive Cooking Mode**: Guided step-by-step assistant with timer management.
10. **User Submits Recipe Feedback**: Post-meal rating, difficulty feedback, and taste notes recorded.
11. **User Preferences Updated**: Explicit and implicit rating signals refine preference weights.
12. **AI Kitchen Memory Stores Learning**: Memory engine updates pantry balances, ingredient utilization history, and generates future proactive recommendations.

---

## 3. AI Kitchen Memory Vision

### Concept
AI Kitchen Memory transforms DishIQ from a passive search tool into a proactive kitchen intelligence assistant.

### Tracked Memory Dimensions
- **Pantry Inventory**: Real-time stock counts, expiration estimates, and ingredient usage velocity.
- **Grocery Purchase History**: Historical shopping lists, store preferences, and price trends.
- **Budget**: Weekly/monthly grocery expenditure targets and price sensitivity metrics.
- **Dietary Preferences**: Strict requirements (Vegetarian, Vegan, Gluten-Free, Halal) and macro targets.
- **Family Preferences**: Household member likes, dislikes, allergen alerts, and portion multipliers.
- **Cooking Schedule**: Days cooked per week, quick weeknight vs. weekend cooking habits.
- **Favorite Recipes & Usage Frequency**: High-frequency comfort meals and repeat intervals.

### Example Proactive Recommendation
> "You already have tomatoes, onions and eggs in your pantry. Paneer is available in today's demonstration grocery data. Based on your family's vegetarian preference and your weekly grocery budget, I recommend **Paneer Bhurji** tonight. Buying only paneer and coriander completes the meal."

> **Notice**: Demonstration grocery data is mock data used for system evaluation and development. It does not represent live store web-scraping.

---

## 4. Non-Functional & Engineering Requirements

- **Modular Architecture**: Complete decoupling of Frontend (React/TS), Backend (FastAPI), ML Engine (Scikit-learn/Sentence Transformers), and MCP Server (Python MCP SDK).
- **Validation**: Strict schema validation using Pydantic models for all API contracts and data models.
- **Demonstration Data Privacy**: No restricted live web-scraping. Clean abstraction adapters for future official provider integrations.
- **Logging & Diagnostics**: Structured JSON logging capturing startup, request trace IDs, error stacks, and system events.
