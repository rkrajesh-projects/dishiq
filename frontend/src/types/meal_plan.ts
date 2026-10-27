/**
 * DishIQ Phase 9 — Meal Planning & Shopping List Types
 */

export interface MealPlanItem {
  id: string;
  meal_plan_id: string;
  recipe_id: string;
  recipe_name: string;
  recipe_cuisine?: string | null;
  meal_date?: string | null;
  meal_type: string;
  servings: number;
  original_servings: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MealPlan {
  id: string;
  user_id?: string | null;
  name: string;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
  meals: MealPlanItem[];
  created_at: string;
  updated_at: string;
}

export interface MealPlanCreate {
  name: string;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
  meals?: MealPlanItemCreate[];
}

export interface MealPlanUpdate {
  name?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
}

export interface MealPlanItemCreate {
  recipe_id: string;
  meal_date?: string | null;
  meal_type?: string;
  servings?: number;
  notes?: string | null;
}

export interface MealPlanItemUpdate {
  meal_date?: string | null;
  meal_type?: string | null;
  servings?: number | null;
  notes?: string | null;
}

export interface SourceRecipeRef {
  recipe_id: string;
  recipe_name: string;
  quantity: number;
  unit: string;
}

export interface ShoppingListItem {
  id: string;
  shopping_list_id: string;
  ingredient_id?: string | null;
  ingredient_name: string;
  required_quantity: number;
  unit: string;
  pantry_quantity: number;
  quantity_to_buy: number;
  user_quantity_override?: number | null;
  effective_quantity: number;
  is_obtained: boolean;
  is_manual: boolean;
  source_recipes: SourceRecipeRef[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShoppingList {
  id: string;
  user_id?: string | null;
  meal_plan_id?: string | null;
  name: string;
  status: string;
  items: ShoppingListItem[];
  total_items: number;
  obtained_items: number;
  created_at: string;
  updated_at: string;
}

export interface ShoppingListItemCreate {
  ingredient_name: string;
  quantity: number;
  unit: string;
  notes?: string | null;
}

export interface ShoppingListItemUpdate {
  is_obtained?: boolean | null;
  user_quantity_override?: number | null;
  notes?: string | null;
}

export interface ShoppingListGenerateRequest {
  name?: string | null;
  deduct_pantry?: boolean;
}

export interface ShoppingListGroceryItemMatch {
  item_id: string;
  ingredient_name: string;
  quantity_needed: number;
  unit: string;
  matched_products: any[];
  best_product?: any;
  missing_reason?: string | null;
}

export interface ShoppingListGroceryComparison {
  shopping_list_id: string;
  items: ShoppingListGroceryItemMatch[];
  store_baskets: any[];
  unmatched_ingredients: string[];
  total_estimated_cost?: number | null;
  is_complete: boolean;
  notes?: string | null;
}
