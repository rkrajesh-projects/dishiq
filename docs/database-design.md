# DishIQ Database Schema & Entity Design

## 1. Overview
The DishIQ database is designed around a relational model implemented via PostgreSQL and SQLAlchemy ORM. The entities are partitioned into MVP Core Entities and Future Intelligence Entities.

---

## 2. MVP Core Entities

### User
- `id`: UUID (Primary Key)
- `email`: String (Unique, Indexed)
- `hashed_password`: String
- `full_name`: String
- `created_at`: Timestamp
- `updated_at`: Timestamp

### UserPreference
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id` (Unique)
- `dietary_restrictions`: JSONB (e.g. `["Vegetarian", "Gluten-Free"]`)
- `disliked_ingredients`: JSONB (e.g. `["mushroom", "olives"]`)
- `weekly_grocery_budget`: Decimal(10, 2)
- `household_size`: Integer
- `updated_at`: Timestamp

### Recipe
- `id`: UUID (Primary Key)
- `title`: String (Indexed)
- `description`: Text
- `prep_time_minutes`: Integer
- `cook_time_minutes`: Integer
- `servings`: Integer
- `instructions`: JSONB (Array of step strings)
- `cuisine_type`: String
- `created_at`: Timestamp

### Ingredient
- `id`: UUID (Primary Key)
- `canonical_name`: String (Unique, Indexed, e.g. "paneer", "tomato")
- `category`: String (e.g., "Dairy", "Produce", "Spices")

### RecipeIngredient
- `id`: UUID (Primary Key)
- `recipe_id`: ForeignKey -> `Recipe.id`
- `ingredient_id`: ForeignKey -> `Ingredient.id`
- `quantity`: Decimal(8, 2)
- `unit`: String (e.g., "grams", "cups", "pieces")
- `preparation_notes`: String (e.g., "chopped", "diced")

### GroceryStore
- `id`: UUID (Primary Key)
- `name`: String (e.g., "Demo Grocery Store A")
- `chain_code`: String
- `is_demo_data`: Boolean (Default: True)

### GroceryProduct
- `id`: UUID (Primary Key)
- `store_id`: ForeignKey -> `GroceryStore.id`
- `product_name`: String (Indexed)
- `canonical_ingredient_id`: ForeignKey -> `Ingredient.id` (Nullable)
- `package_size`: Decimal(8, 2)
- `unit`: String

### ProductPrice
- `id`: UUID (Primary Key)
- `product_id`: ForeignKey -> `GroceryProduct.id`
- `price`: Decimal(10, 2)
- `currency`: String (e.g., "USD")
- `effective_date`: Date
- `is_demo`: Boolean (Default: True)

### PantryItem
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id`
- `ingredient_id`: ForeignKey -> `Ingredient.id`
- `quantity`: Decimal(8, 2)
- `unit`: String
- `expiry_date`: Date (Nullable)
- `updated_at`: Timestamp

### ShoppingList
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id`
- `target_recipe_id`: ForeignKey -> `Recipe.id` (Nullable)
- `total_estimated_cost`: Decimal(10, 2)
- `status`: Enum ("DRAFT", "COMPLETED", "ARCHIVED")
- `created_at`: Timestamp

### ShoppingListItem
- `id`: UUID (Primary Key)
- `shopping_list_id`: ForeignKey -> `ShoppingList.id`
- `product_id`: ForeignKey -> `GroceryProduct.id`
- `quantity`: Integer
- `price_at_addition`: Decimal(10, 2)
- `purchased`: Boolean

### RecipeFeedback
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id`
- `recipe_id`: ForeignKey -> `Recipe.id`
- `rating`: Integer (1-5)
- `difficulty_rating`: Enum ("EASY", "MEDIUM", "HARD")
- `notes`: Text
- `cooked_at`: Timestamp

---

## 3. Future Intelligence Entities

### CookingSession
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id`
- `recipe_id`: ForeignKey -> `Recipe.id`
- `current_step_index`: Integer
- `started_at`: Timestamp
- `completed_at`: Timestamp (Nullable)

### KitchenMemory
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id`
- `memory_type`: Enum ("INGREDIENT_VELOCITY", "FAVORITE_DISH", "BUDGET_COMPLIANCE", "FAMILY_DISLIKE")
- `memory_data`: JSONB
- `confidence_score`: Float
- `last_reinforced_at`: Timestamp

### FamilyPreference
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id`
- `member_name`: String
- `relationship`: String
- `dietary_restrictions`: JSONB
- `dislikes`: JSONB

### MealHistory
- `id`: UUID (Primary Key)
- `user_id`: ForeignKey -> `User.id`
- `recipe_id`: ForeignKey -> `Recipe.id`
- `servings_cooked`: Integer
- `total_cost`: Decimal(10, 2)
- `cooked_date`: Date

---

## 4. Entity Relationship Summary

- **User** (1) <---> (1) **UserPreference**
- **User** (1) <---> (N) **PantryItem**
- **User** (1) <---> (N) **ShoppingList**
- **Recipe** (1) <---> (N) **RecipeIngredient** <---> (1) **Ingredient**
- **GroceryStore** (1) <---> (N) **GroceryProduct** <---> (N) **ProductPrice**
- **Ingredient** (1) <---> (N) **GroceryProduct**
- **User** (1) <---> (N) **KitchenMemory**
