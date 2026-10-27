import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  startCookingSession,
  getCookingSession,
  updateCookingSession,
  nextCookingStep,
  previousCookingStep,
  pauseCookingSession,
  resumeCookingSession,
  completeCookingSession,
  getActiveCookingSession,
  getPreparationChecklist,
  updatePreparedIngredients,
} from '../api/cooking';
import { CookingSession, CookingSessionCreate, CookingSessionUpdate, PreparationChecklist } from '../types/cooking';

export const useCookingSession = (sessionId: string) => {
  return useQuery<CookingSession, Error>({
    queryKey: ['cooking-session', sessionId],
    queryFn: () => getCookingSession(sessionId),
    enabled: Boolean(sessionId),
    retry: 1,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });
};

export const useActiveCookingSession = (recipeId?: string) => {
  return useQuery<CookingSession | null, Error>({
    queryKey: ['active-cooking-session', recipeId],
    queryFn: () => getActiveCookingSession(recipeId),
    retry: 1,
    refetchOnWindowFocus: true,
  });
};

export const useStartCooking = () => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, CookingSessionCreate>({
    mutationFn: (payload) => startCookingSession(payload.recipe_id, payload.notes, payload.servings),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['active-cooking-session'] });
      queryClient.setQueryData(['cooking-session', data.id], data);
    },
  });
};

export const useNextStep = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, void>({
    mutationFn: () => nextCookingStep(sessionId),
    onSuccess: (data) => {
      queryClient.setQueryData(['cooking-session', sessionId], data);
      queryClient.invalidateQueries({ queryKey: ['cooking-session', sessionId] });
    },
  });
};

export const usePreviousStep = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, void>({
    mutationFn: () => previousCookingStep(sessionId),
    onSuccess: (data) => {
      queryClient.setQueryData(['cooking-session', sessionId], data);
      queryClient.invalidateQueries({ queryKey: ['cooking-session', sessionId] });
    },
  });
};

export const usePauseSession = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, void>({
    mutationFn: () => pauseCookingSession(sessionId),
    onSuccess: (data) => {
      queryClient.setQueryData(['cooking-session', sessionId], data);
      queryClient.invalidateQueries({ queryKey: ['cooking-session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['active-cooking-session'] });
    },
  });
};

export const useResumeSession = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, void>({
    mutationFn: () => resumeCookingSession(sessionId),
    onSuccess: (data) => {
      queryClient.setQueryData(['cooking-session', sessionId], data);
      queryClient.invalidateQueries({ queryKey: ['cooking-session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['active-cooking-session'] });
    },
  });
};

export const useCompleteSession = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, void>({
    mutationFn: () => completeCookingSession(sessionId),
    onSuccess: (data) => {
      queryClient.setQueryData(['cooking-session', sessionId], data);
      queryClient.invalidateQueries({ queryKey: ['cooking-session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['active-cooking-session'] });
    },
  });
};

export const usePreparationChecklist = (sessionId: string) => {
  return useQuery<PreparationChecklist, Error>({
    queryKey: ['preparation-checklist', sessionId],
    queryFn: () => getPreparationChecklist(sessionId),
    enabled: Boolean(sessionId),
    staleTime: 10_000,
  });
};

export const useUpdatePreparedIngredients = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, string[]>({
    mutationFn: (ingredients) => updatePreparedIngredients(sessionId, ingredients),
    onSuccess: (data) => {
      queryClient.setQueryData(['cooking-session', sessionId], data);
      queryClient.invalidateQueries({ queryKey: ['preparation-checklist', sessionId] });
    },
  });
};
