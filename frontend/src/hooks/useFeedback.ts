import { useMutation, useQueryClient } from '@tanstack/react-query';
import { submitRecipeFeedback } from '../api/recipes';
import { RecipeFeedbackInput, RecipeFeedback } from '../types';

export const useSubmitRecipeFeedback = (recipeId: string) => {
  const queryClient = useQueryClient();
  return useMutation<RecipeFeedback, Error, RecipeFeedbackInput>({
    mutationFn: (payload) => submitRecipeFeedback(recipeId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe', recipeId] });
    },
  });
};
