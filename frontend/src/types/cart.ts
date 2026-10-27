/**
 * DishIQ Phase 7 — Cart Optimization Types
 * Mirrors backend Pydantic schemas in backend/app/schemas/cart.py
 */

export interface CartIngredientRequest {
  ingredient_name: string;
  required_quantity: number;
  required_unit: string;
}

export interface CartCompareRequest {
  budget_cap?: number;
  ingredients: CartIngredientRequest[];
}

export interface CartProductSelection {
  ingredient_name: string;
  product_id: string;
  product_name: string;
  store_id: string | null;
  store_name: string | null;
  brand: string | null;
  package_quantity: number | null;
  package_unit: string | null;
  packages_required: number;
  package_price: number | null;
  unit_price?: number | null;
  unit_price_label?: string | null;
  line_cost: number;
  currency: string;
  match_score: number;
  in_stock: boolean;
  data_source_type: string;
  price_freshness: string;
}

export interface CartMissingIngredient {
  ingredient_name: string;
  reason: string;
}

export interface CartStoreBreakdown {
  store_id: string | null;
  store_name: string;
  selected_products: CartProductSelection[];
  missing_ingredients: CartMissingIngredient[];
  subtotal: number;
  delivery_fee: number;
  total: number;
  complete: boolean;
}

export interface CartCompareResponse {
  stores: CartStoreBreakdown[];
  missing_ingredients: CartMissingIngredient[];
  data_source: string;
  price_freshness: string;
}

export interface CartStrategyResult {
  strategy: string;
  stores: CartStoreBreakdown[];
  stores_used: number;
  total_cost: number;
  currency: string;
  missing_ingredients: CartMissingIngredient[];
  explanation: string;
}

export interface CartOptimizeResponse {
  recommended_strategy: string;
  recommended_cart: CartStrategyResult;
  alternatives: CartStrategyResult[];
  store_baskets: CartStoreBreakdown[];
  total_cost: number;
  currency: string;
  estimated_savings: number;
  stores_used: number;
  missing_ingredients: CartMissingIngredient[];
  explanation: string;
  data_source: string;
  price_freshness: string;
}
