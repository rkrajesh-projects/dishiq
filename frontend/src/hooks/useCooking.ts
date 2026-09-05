import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  startCookingSession,
  getCookingSession,
  nextCookingStep,
  previousCookingStep,
  completeCookingSession,
  getActiveCookingSession
} from '../api/cooking';
import { CookingSession, CookingSessionCreate } from '../types';

export const useCookingSession = (sessionId: string) => {
  return useQuery<CookingSession, Error>({
    queryKey: ['cooking-session', sessionId],
    queryFn: () => getCookingSession(sessionId),
    enabled: Boolean(sessionId),
    retry: 1,
    // Don't treat the session as stale for 30s to avoid redundant refetches
    // while the user is actively navigating steps.
    staleTime: 30_000,
    // Restoring focus to the tab (e.g. after a browser back/forward) should
    // always pull the latest persisted current_step from the backend.
    refetchOnWindowFocus: true,
  });
};

export const useActiveCookingSession = () => {
  return useQuery<CookingSession | null, Error>({
    queryKey: ['active-cooking-session'],
    queryFn: () => getActiveCookingSession(),
    retry: 1,
    // Refresh the spotlight whenever the tab regains focus so that completed
    // sessions disappear from the home page promptly.
    refetchOnWindowFocus: true,
  });
};

export const useStartCooking = () => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, CookingSessionCreate>({
    mutationFn: (payload) => startCookingSession(payload.recipe_id, payload.notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-cooking-session'] });
    },
  });
};

export const useNextStep = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, void>({
    mutationFn: () => nextCookingStep(sessionId),
    onSuccess: (data) => {
      // Immediately update the local cache so the UI doesn't wait for a refetch.
      queryClient.setQueryData(['cooking-session', sessionId], data);
      // Invalidate to ensure the server state is eventually consistent.
      queryClient.invalidateQueries({ queryKey: ['cooking-session', sessionId] });
    },
  });
};

export const usePreviousStep = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<CookingSession, Error, void>({
    mutationFn: () => previousCookingStep(sessionId),
    onSuccess: (data) => {
      // Immediately update the local cache so the UI doesn't wait for a refetch.
      queryClient.setQueryData(['cooking-session', sessionId], data);
      // Invalidate to ensure the server state is eventually consistent.
      queryClient.invalidateQueries({ queryKey: ['cooking-session', sessionId] });
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
