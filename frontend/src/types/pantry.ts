/** Matches backend PantryItemRead schema */
export interface PantryItem {
  id: string;
  ingredient_id: string;
  ingredient_name: string;
  canonical_name: string;
  quantity: number;
  unit: string;
  /** ISO date string e.g. "2026-09-01", or null */
  expiration_date: string | null;
  custom_name?: string | null;
  location?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

/** Matches backend PantryItemCreate schema */
export interface PantryItemCreate {
  ingredient_name: string;
  quantity: number;
  unit: string;
  expiration_date?: string | null;
  custom_name?: string | null;
  location?: string | null;
  notes?: string | null;
}

/** Matches backend PantryItemUpdate schema (all fields optional) */
export interface PantryItemUpdate {
  quantity?: number;
  unit?: string;
  expiration_date?: string | null;
  custom_name?: string | null;
  location?: string | null;
  notes?: string | null;
}

export interface ConsumptionPreviewItem {
  ingredient_id?: string | null;
  ingredient_name: string;
  required_quantity: number;
  required_unit: string;
  pantry_item_id?: string | null;
  pantry_quantity: number;
  pantry_unit?: string | null;
  converted_deduct_quantity: number;
  remaining_stock: number;
  is_compatible: boolean;
  can_deduct: boolean;
  status: 'fully_covered' | 'partially_covered' | 'incompatible_unit' | 'missing' | 'uncertain_match';
  reason?: string | null;
}

export interface ConsumptionPreviewRequest {
  recipe_id?: string;
  cooking_session_id?: string;
  servings?: number;
  items?: Array<{
    ingredient_id?: string;
    ingredient_name: string;
    required_quantity: number;
    required_unit: string;
  }>;
}

export interface ConsumptionPreviewResponse {
  preview_token: string;
  recipe_id?: string | null;
  cooking_session_id?: string | null;
  items: ConsumptionPreviewItem[];
  total_deductible_items: number;
  has_incompatible_or_uncertain: boolean;
}

export interface ConsumptionConfirmRequest {
  preview_token: string;
  recipe_id?: string;
  cooking_session_id?: string;
  items: Array<{
    pantry_item_id: string;
    deduct_quantity: number;
  }>;
}

export interface ConsumptionConfirmResponse {
  success: boolean;
  deducted_count: number;
  message: string;
  deductions: Array<{
    pantry_item_id: string;
    ingredient_name: string;
    previous_quantity: number;
    deducted_quantity: number;
    new_quantity: number;
    unit: string;
  }>;
}
