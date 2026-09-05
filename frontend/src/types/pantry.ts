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
  created_at: string;
  updated_at: string;
}

/** Matches backend PantryItemCreate schema */
export interface PantryItemCreate {
  ingredient_name: string;
  quantity: number;
  unit: string;
  expiration_date?: string | null;
}

/** Matches backend PantryItemUpdate schema (all fields optional) */
export interface PantryItemUpdate {
  quantity?: number;
  unit?: string;
  expiration_date?: string | null;
}
