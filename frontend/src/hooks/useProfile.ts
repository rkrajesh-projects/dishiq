import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProfile, updateProfile } from '../api/profile';
import { UserProfile, ProfileUpdatePayload } from '../types';

export const PROFILE_QUERY_KEY = ['user-profile'] as const;

/** Fetch user profile and preferences. */
export const useProfile = () => {
  return useQuery<UserProfile, Error>({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: getProfile,
    refetchOnWindowFocus: true,
  });
};

/** Update user profile / preferences; invalidates profile cache on success. */
export const useUpdateProfile = () => {
  const queryClient = useQueryClient();
  return useMutation<UserProfile, Error, ProfileUpdatePayload>({
    mutationFn: (body) => updateProfile(body),
    onSuccess: (data) => {
      queryClient.setQueryData(PROFILE_QUERY_KEY, data);
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY });
    },
  });
};
