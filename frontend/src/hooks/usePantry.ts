import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getPantryItems,
  addPantryItem,
  updatePantryItem,
  deletePantryItem,
} from '../api/pantry';
import { PantryItem, PantryItemCreate, PantryItemUpdate } from '../types';

export const PANTRY_QUERY_KEY = ['pantry-items'] as const;

/** Fetch all pantry items. Refetches when tab regains focus. */
export const usePantryItems = () => {
  return useQuery<PantryItem[], Error>({
    queryKey: PANTRY_QUERY_KEY,
    queryFn: getPantryItems,
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

/** Update quantity / unit / expiration_date of an existing item. */
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
