import apiClient from './client';
import {
  PantryItem,
  PantryItemCreate,
  PantryItemUpdate,
  ConsumptionPreviewRequest,
  ConsumptionPreviewResponse,
  ConsumptionConfirmRequest,
  ConsumptionConfirmResponse,
} from '../types';

export interface PantryQueryParams {
  search?: string;
  location?: string;
  expiring_within_days?: number;
}

/** GET /api/pantry — fetch all pantry items for the user with optional filters */
export const getPantryItems = async (params?: PantryQueryParams): Promise<PantryItem[]> => {
  const response = await apiClient.get<PantryItem[]>('/pantry', { params });
  return response.data;
};

/** POST /api/pantry — add (or increment) a pantry item */
export const addPantryItem = async (body: PantryItemCreate): Promise<PantryItem> => {
  const response = await apiClient.post<PantryItem>('/pantry', body);
  return response.data;
};

/** PATCH /api/pantry/:id — update quantity / unit / expiration_date / location / notes */
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

/** POST /api/pantry/preview-consumption — non-destructive preview of inventory deductions */
export const previewConsumption = async (
  body: ConsumptionPreviewRequest,
): Promise<ConsumptionPreviewResponse> => {
  const response = await apiClient.post<ConsumptionPreviewResponse>('/pantry/preview-consumption', body);
  return response.data;
};

/** POST /api/pantry/consume — confirm explicit pantry deduction */
export const confirmConsumption = async (
  body: ConsumptionConfirmRequest,
): Promise<ConsumptionConfirmResponse> => {
  const response = await apiClient.post<ConsumptionConfirmResponse>('/pantry/consume', body);
  return response.data;
};
