import apiClient from './client';
import { PantryItem, PantryItemCreate, PantryItemUpdate } from '../types';

/** GET /api/pantry — fetch all pantry items for the demo user */
export const getPantryItems = async (): Promise<PantryItem[]> => {
  const response = await apiClient.get<PantryItem[]>('/pantry');
  return response.data;
};

/** POST /api/pantry — add (or increment) a pantry item */
export const addPantryItem = async (body: PantryItemCreate): Promise<PantryItem> => {
  const response = await apiClient.post<PantryItem>('/pantry', body);
  return response.data;
};

/** PATCH /api/pantry/:id — update quantity / unit / expiration_date */
export const updatePantryItem = async (
  id: string,
  body: PantryItemUpdate,
): Promise<PantryItem> => {
  const response = await apiClient.patch<PantryItem>(`/pantry/${id}`, body);
  return response.data;
};

/** DELETE /api/pantry/:id — remove item (204, no body) */
export const deletePantryItem = async (id: string): Promise<void> => {
  await apiClient.delete(`/pantry/${id}`);
};
