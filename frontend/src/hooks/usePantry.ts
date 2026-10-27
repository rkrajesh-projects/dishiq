import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getPantryItems,
  addPantryItem,
  updatePantryItem,
  deletePantryItem,
  previewConsumption,
  confirmConsumption,
  PantryQueryParams,
} from '../api/pantry';
import {
  PantryItem,
  PantryItemCreate,
  PantryItemUpdate,
  ConsumptionPreviewRequest,
  ConsumptionPreviewResponse,
  ConsumptionConfirmRequest,
  ConsumptionConfirmResponse,
} from '../types';

export const PANTRY_QUERY_KEY = ['pantry-items'] as const;

/** Fetch all pantry items with optional search and filter parameters. */
export const usePantryItems = (params?: PantryQueryParams) => {
  return useQuery<PantryItem[], Error>({
    queryKey: [...PANTRY_QUERY_KEY, params],
    queryFn: () => getPantryItems(params),
    refetchOnWindowFocus: true,
  });
};

/** Add or increment a pantry item; invalidates the list on success. */
export const useAddPantryItem = () => {
  const queryClient = useQueryClient();
  return useMutation<PantryItem, Error, PantryItemCreate>({
    mutationFn: (body) => addPantryItem(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PANTRY_QUERY_KEY });
    },
  });
};

/** Update quantity / unit / expiration_date / location / notes of an existing item. */
export const useUpdatePantryItem = () => {
  const queryClient = useQueryClient();
  return useMutation<PantryItem, Error, { id: string; body: PantryItemUpdate }>({
    mutationFn: ({ id, body }) => updatePantryItem(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PANTRY_QUERY_KEY });
    },
  });
};

/** Delete a pantry item by id. */
export const useDeletePantryItem = () => {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => deletePantryItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PANTRY_QUERY_KEY });
    },
  });
};

/** Non-destructive consumption preview. */
export const usePreviewConsumption = () => {
  return useMutation<ConsumptionPreviewResponse, Error, ConsumptionPreviewRequest>({
    mutationFn: (req) => previewConsumption(req),
  });
};

/** Explicit confirmed pantry consumption. */
export const useConfirmConsumption = () => {
  const queryClient = useQueryClient();
  return useMutation<ConsumptionConfirmResponse, Error, ConsumptionConfirmRequest>({
    mutationFn: (req) => confirmConsumption(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PANTRY_QUERY_KEY });
    },
  });
};
