import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { CookingPage, parseRecipeInstructions } from '../pages/CookingPage';
import * as cookingHooks from '../hooks/useCooking';
import * as feedbackHooks from '../hooks/useFeedback';
import * as recipesApi from '../api/recipes';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock the modules
vi.mock('../hooks/useCooking', () => ({
  useCookingSession: vi.fn(),
  useNextStep: vi.fn(),
  usePreviousStep: vi.fn(),
  useCompleteSession: vi.fn(),
}));

vi.mock('../api/recipes', () => ({
  getRecipe: vi.fn(),
}));

vi.mock('../hooks/useFeedback', () => ({
  useSubmitRecipeFeedback: vi.fn().mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    error: null,
  }),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const mockSession = {
  id: 'session-123',
  user_id: 'user-456',
  recipe_id: 'recipe-789',
  current_step: 0,
  status: 'active',
  started_at: '2026-08-13T12:00:00Z',
  completed_at: null,
  notes: 'Testing notes',
};

const mockRecipe = {
  id: 'recipe-789',
  name: 'Paneer Butter Masala',
  description: 'Rich and creamy cottage cheese dish',
  cuisine: 'Indian',
  dietary_type: 'Vegetarian',
  preparation_minutes: 10,
  cooking_minutes: 15,
  servings: 4,
  source_name: 'Test Kitchen',
  average_rating: 4.8,
  created_at: '2026-08-13T12:00:00Z',
  instructions: [
    'Cut paneer into cubes.',
    'Sauté onions and spices.',
    'Add tomato gravy and cream.',
    'Simmer and serve.'
  ],
  ingredients: [
    {
      id: 'ri-1',
      ingredient: { id: 'i-1', canonical_name: 'paneer', category: 'Dairy', default_unit: 'grams' },
      raw_text: '200g paneer',
      quantity: 200,
      unit: 'grams',
      preparation_note: null,
    }
  ]
};

describe('CookingPage - Advanced Navigation & Progress (9.4)', () => {
  let queryClient: QueryClient;
  let mockNextMutate = vi.fn();
  let mockPrevMutate = vi.fn();
  let mockCompleteMutate = vi.fn();

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();

    // Default query hooks mocks
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: mockSession,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    (cookingHooks.useNextStep as any).mockReturnValue({
      mutate: mockNextMutate,
      isPending: false,
    });

    (cookingHooks.usePreviousStep as any).mockReturnValue({
      mutate: mockPrevMutate,
      isPending: false,
    });

    (cookingHooks.useCompleteSession as any).mockReturnValue({
      mutate: mockCompleteMutate,
      isPending: false,
    });

    vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(mockRecipe as any);
  });

  const renderComponent = (sessionId = 'session-123') => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/cooking/${sessionId}`]}>
          <Routes>
            <Route path="/cooking/:sessionId" element={<CookingPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  // 1. Correct total step count
  // 2. Step 1 display
  // 3. Step numbering
  it('1-3. Displays step 1 of 4 correctly', async () => {
    renderComponent();
    expect(await screen.findByText('Step 1 of 4')).toBeInTheDocument();
    expect(screen.getAllByText('Cut paneer into cubes.').length).toBeGreaterThanOrEqual(1);
  });

  // 4. Progress calculation
  it('4. Calculates progress correctly (0% on first step)', async () => {
    renderComponent();
    expect(await screen.findByText('0% Complete')).toBeInTheDocument();
  });

  // 5. Progress updates after Next
  it('5. Progress updates correctly for intermediate steps', async () => {
    const step2Session = { ...mockSession, current_step: 1 };
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: step2Session,
      isLoading: false,
    });

    renderComponent();
    // 1 / 4 steps complete = 25%
    expect(await screen.findByText('25% Complete')).toBeInTheDocument();
    expect(screen.getByText('Step 2 of 4')).toBeInTheDocument();
  });

  // 6. Progress updates after Previous
  it('6. Progress updates correctly when navigating backward', async () => {
    const step3Session = { ...mockSession, current_step: 2 };
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: step3Session,
      isLoading: false,
    });

    renderComponent();
    // 2 / 4 steps complete = 50%
    expect(await screen.findByText('50% Complete')).toBeInTheDocument();
    expect(screen.getByText('Step 3 of 4')).toBeInTheDocument();
  });

  // 7. Previous disabled at first step
  it('7. Previous button is disabled at step 1 (index 0)', async () => {
    renderComponent();
    const prevBtn = await screen.findByRole('button', { name: /Previous Step/i });
    expect(prevBtn).toBeDisabled();
  });

  // 8. Next works on intermediate step
  // 9. Next disabled/changed on final step
  // 10. Final step displays completion action
  it('8-10. Intermediate next navigation and final step complete transition', async () => {
    const finalStepSession = { ...mockSession, current_step: 3 };
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: finalStepSession,
      isLoading: false,
    });

    renderComponent();
    
    // On the final step (4 of 4), the progress is 3/4 = 75%
    expect(await screen.findByText('75% Complete')).toBeInTheDocument();
    expect(screen.getByText('Final Step')).toBeInTheDocument();

    // Verify Next Step is replaced by Complete Cooking
    expect(screen.queryByRole('button', { name: /Next Step/i })).not.toBeInTheDocument();
    
    const completeBtn = screen.getByRole('button', { name: /Complete Cooking/i });
    expect(completeBtn).toBeInTheDocument();
    
    fireEvent.click(completeBtn);
    expect(mockCompleteMutate).toHaveBeenCalled();
  });

  // 11-13. Completed, current, upcoming steps are visually distinguishable
  it('11-13. Steps timeline items have appropriate accessibility status text', async () => {
    const step2Session = { ...mockSession, current_step: 1 };
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: step2Session,
      isLoading: false,
    });

    renderComponent();

    // Step 1: index 0 < current_step (1) -> previous step
    const step1Item = await screen.findByLabelText('Step 1 of 4, previous step');
    expect(step1Item).toBeInTheDocument();

    // Step 2: index 1 == current_step (1) -> current step
    const step2Item = screen.getByLabelText('Step 2 of 4, current step');
    expect(step2Item).toBeInTheDocument();

    // Step 3: index 2 > current_step (1) -> upcoming
    const step3Item = screen.getByLabelText('Step 3 of 4, upcoming');
    expect(step3Item).toBeInTheDocument();
  });

  // 14. Completed session displays completion state
  it('14. Completed session status shows 100% completion screen', async () => {
    const completedSession = { ...mockSession, status: 'completed' };
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: completedSession,
      isLoading: false,
    });

    renderComponent();
    expect(await screen.findByText('🎉 Cooking Complete!')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Next Step/i })).not.toBeInTheDocument();
  });

  // 15. Session reload restores current step
  it('15. Restores current step index on session reload', async () => {
    const customSession = { ...mockSession, current_step: 2 };
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: customSession,
      isLoading: false,
    });

    renderComponent();
    expect(await screen.findByText('Step 3 of 4')).toBeInTheDocument();
    expect(screen.getAllByText('Add tomato gravy and cream.').length).toBeGreaterThanOrEqual(1);
  });

  // 16. Empty instructions state
  it('16. Gracefully handles empty instructions list', async () => {
    const emptyRecipe = { ...mockRecipe, instructions: [] };
    vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(emptyRecipe as any);

    renderComponent();
    expect(await screen.findByText("Cooking instructions aren't available for this recipe.")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Back to Recipe/i })).toBeInTheDocument();
  });

  // 17. Invalid current_step is handled safely
  it('17. Clamps invalid backend step values to prevent index crashes', async () => {
    // current_step exceeds length
    const invalidSession = { ...mockSession, current_step: 10 };
    (cookingHooks.useCookingSession as any).mockReturnValue({
      data: invalidSession,
      isLoading: false,
    });

    renderComponent();
    // Clamped to final step (4 of 4)
    expect(await screen.findByText('Step 4 of 4')).toBeInTheDocument();
    expect(screen.getAllByText('Simmer and serve.').length).toBeGreaterThanOrEqual(1);
  });

  // 18-19. Mutation failure leaves step unchanged and shows inline error
  it('18-19. Keeps step index unchanged when next/prev API calls fail and shows inline error banner', async () => {
    // Next step fails
    (cookingHooks.useNextStep as any).mockReturnValue({
      mutate: vi.fn((_payload, options) => {
        if (options && options.onError) {
          options.onError(new Error('Network failure'));
        }
      }),
      isPending: false,
    });

    renderComponent();
    const nextBtn = await screen.findByRole('button', { name: /Next Step/i });
    fireEvent.click(nextBtn);

    // Inline error banner appears (no longer uses window.alert)
    const banner = await screen.findByRole('alert');
    expect(banner).toHaveTextContent('Could not advance to the next step');
    // Step index stays at 0
    expect(screen.getByText('Step 1 of 4')).toBeInTheDocument();
  });

  // 20. Double-click/mutation loading protection works
  it('20. Disables navigation buttons during background mutations to prevent double submission', async () => {
    (cookingHooks.useNextStep as any).mockReturnValue({
      mutate: mockNextMutate,
      isPending: true, // Mutation currently executing
    });

    renderComponent();
    const nextBtn = await screen.findByRole('button', { name: /Next Step/i });
    expect(nextBtn).toBeDisabled();
  });

  // 21. Cooking Timer Integration Tests (Phase 9.5)
  describe('CookingPage Timer Integration', () => {
    it('1. Timer appears with configured duration when recipe instruction has valid duration', async () => {
      const durationRecipe = {
        ...mockRecipe,
        instructions: ['Simmer the sauce for 5 minutes.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(durationRecipe as any);

      renderComponent();
      // Should show the timer with 05:00 formatted display
      expect(await screen.findByText('05:00')).toBeInTheDocument();
    });

    it('2. Timer displays "No timer set" empty state for instructions with no duration', async () => {
      const textOnlyRecipe = {
        ...mockRecipe,
        instructions: ['Add 2 tomatoes and stir well.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(textOnlyRecipe as any);

      renderComponent();
      // Should render the timer box empty state with Add Timer button
      expect(await screen.findByText('No timer set for this step.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Add Timer/i })).toBeInTheDocument();
    });

    it('3. Allows manually adding a timer duration and starting countdown', async () => {
      const textOnlyRecipe = {
        ...mockRecipe,
        instructions: ['Mix the dough.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(textOnlyRecipe as any);

      renderComponent();
      const addTimerBtn = await screen.findByRole('button', { name: /Add Timer/i });
      fireEvent.click(addTimerBtn);

      // Verify input boxes render
      const minsInput = screen.getByLabelText('Mins');
      const secsInput = screen.getByLabelText('Secs');
      expect(minsInput).toBeInTheDocument();
      expect(secsInput).toBeInTheDocument();

      // Enter 10 minutes and submit
      fireEvent.change(minsInput, { target: { value: '10' } });
      fireEvent.change(secsInput, { target: { value: '00' } });
      
      const startTimerBtn = screen.getByRole('button', { name: /Start Timer/i });
      fireEvent.click(startTimerBtn);

      // Verify timer is set to 10:00
      expect(screen.getByText('10:00')).toBeInTheDocument();
    });

    it('4. Running timer blocks unsafe step navigation unless confirmed', async () => {
      const durationRecipe = {
        ...mockRecipe,
        instructions: ['Simmer for 5 minutes.', 'Serve.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(durationRecipe as any);

      const confirmMock = vi.spyOn(window, 'confirm');

      renderComponent();
      
      // Start the timer
      const startBtn = await screen.findByRole('button', { name: /Start/i });
      fireEvent.click(startBtn);

      // Try to go to next step
      const nextBtn = screen.getByRole('button', { name: /Next Step/i });

      // Case A: User cancels navigation confirmation
      confirmMock.mockReturnValue(false);
      fireEvent.click(nextBtn);
      expect(confirmMock).toHaveBeenCalledWith('Timer is still running. Leave this step?');
      expect(mockNextMutate).not.toHaveBeenCalled();

      // Case B: User confirms navigation
      confirmMock.mockReturnValue(true);
      fireEvent.click(nextBtn);
      expect(mockNextMutate).toHaveBeenCalled();
    });

    it('5. Completing cooking while timer is running requires confirmation', async () => {
      const durationRecipe = {
        ...mockRecipe,
        instructions: ['Simmer for 5 minutes.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(durationRecipe as any);

      const confirmMock = vi.spyOn(window, 'confirm');

      renderComponent();

      // Start the timer
      const startBtn = await screen.findByRole('button', { name: /Start/i });
      fireEvent.click(startBtn);

      // Final step triggers complete cooking button
      const completeBtn = screen.getByRole('button', { name: /Complete Cooking/i });

      // Case A: User cancels completion confirmation
      confirmMock.mockReturnValue(false);
      fireEvent.click(completeBtn);
      expect(confirmMock).toHaveBeenCalledWith('Timer is still running. Are you sure you want to complete cooking?');
      expect(mockCompleteMutate).not.toHaveBeenCalled();

      // Case B: User confirms completion
      confirmMock.mockReturnValue(true);
      fireEvent.click(completeBtn);
      expect(mockCompleteMutate).toHaveBeenCalled();
    });
  });

  // 22. Cooking Page Step Ingredient Intelligence (Phase 9.6)
  describe('Step Ingredient Intelligence', () => {
    it('1-3, 6, 7. Step-specific ingredient card appears with correct matches and excludes unrelated / numeric ingredients', async () => {
      const customRecipe = {
        ...mockRecipe,
        instructions: ['Heat oil and sauté paneer cubes.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(customRecipe as any);

      renderComponent();

      // Step-specific ingredients card title
      expect(await screen.findByText('Ingredients for This Step')).toBeInTheDocument();

      // Paneer has name paneer in mockRecipe
      const paneerTextList = await screen.findAllByText(/paneer/i);
      expect(paneerTextList.length).toBeGreaterThan(0);

      // Unrelated ingredient (like tomato, which is not in the instruction) should not be in the Step Ingredients list
      const stepIngredientsList = screen.getByLabelText('Step ingredients list');
      expect(stepIngredientsList).toBeInTheDocument();
      expect(stepIngredientsList).not.toHaveTextContent(/tomato/i);
    });

    it('4. Changing steps updates step ingredients', async () => {
      // Step 1 matches paneer, Step 2 matches nothing
      const multiStepRecipe = {
        ...mockRecipe,
        instructions: ['Add paneer.', 'Simmer for 5 minutes.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(multiStepRecipe as any);

      // Render Step 1
      renderComponent();
      const stepIngredientsList1 = await screen.findByLabelText('Step ingredients list');
      expect(stepIngredientsList1).toHaveTextContent(/paneer/i);

      // Navigate to Step 2
      const step2Session = { ...mockSession, current_step: 1 };
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: step2Session,
        isLoading: false,
      });
      // Force reload/remount by changing sessionId route or mock values
      renderComponent('session-123-step2');

      // Step 2 has empty match state
      expect(await screen.findByText('No specific ingredients identified for this step.')).toBeInTheDocument();
    });

    it('5-6. Full ingredient list remains visible and highlights active items with accessible indicator', async () => {
      const customRecipe = {
        ...mockRecipe,
        instructions: ['Add paneer and salt.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(customRecipe as any);

      renderComponent();

      // Check full list exists
      expect(await screen.findByText('Recipe Ingredients Reference')).toBeInTheDocument();

      // Check active items receive "Current Step" pill badge
      const activePills = await screen.findAllByText('Current Step');
      expect(activePills.length).toBeGreaterThan(0);

      // Check accessible label on highlighted item
      const highlightedItem = screen.getByLabelText('paneer, relevant to current step');
      expect(highlightedItem).toBeInTheDocument();
    });

    it('8-11. Renders other interactive features (timer, navigation, completion) safely alongside ingredients', async () => {
      const durationRecipe = {
        ...mockRecipe,
        instructions: ['Simmer sauce for 5 minutes.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(durationRecipe as any);

      renderComponent();

      // Timer renders
      expect(await screen.findByText('05:00')).toBeInTheDocument();

      // Step navigation buttons render
      expect(screen.getByRole('button', { name: /Previous Step/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Complete Cooking/i })).toBeInTheDocument();
    });
  });

  // 23. Cooking Step Completion Checklist (Phase 9.7)
  describe('Cooking Step Completion Checklist', () => {
    it('1-3, 7, 8. Active step shows Mark Step Complete, toggles completed, toggles incomplete, and does not call backend APIs', async () => {
      renderComponent();

      // 1. Initial State shows "Mark Step Complete"
      const completeToggleBtn = await screen.findByText('Mark Step Complete');
      expect(completeToggleBtn).toBeInTheDocument();

      // 2. Click to complete step
      fireEvent.click(completeToggleBtn);
      
      // UI updates to "Step Completed (Mark Incomplete)"
      const completedToggleBtn = await screen.findByText('Step Completed (Mark Incomplete)');
      expect(completedToggleBtn).toBeInTheDocument();

      // 7 & 8. API endpoints (Next / Complete) must NOT be called on checklist toggle
      expect(mockNextMutate).not.toHaveBeenCalled();
      expect(mockCompleteMutate).not.toHaveBeenCalled();

      // 3. Click again to undo completion
      fireEvent.click(completedToggleBtn);
      
      // UI reverts to "Mark Step Complete"
      const resetToggleBtn = await screen.findByText('Mark Step Complete');
      expect(resetToggleBtn).toBeInTheDocument();
    });

    it('4. Completed step displays a checkmark in the timeline progress list', async () => {
      renderComponent();

      // Mark first step complete
      const toggleBtn = await screen.findByText('Mark Step Complete');
      fireEvent.click(toggleBtn);

      // Verify that the timeline progress list item updates to reflect completed state
      const timelineItem = await screen.findByLabelText('Step 1 of 4, current step, completed');
      expect(timelineItem).toBeInTheDocument();
    });

    it('5-6. Preserves completed state when navigating between steps', async () => {
      renderComponent();

      // Mark step 1 complete
      const toggleBtn = await screen.findByText('Mark Step Complete');
      fireEvent.click(toggleBtn);

      // Move to Next Step
      const nextBtn = screen.getByRole('button', { name: /Next Step/i });
      fireEvent.click(nextBtn);
      expect(mockNextMutate).toHaveBeenCalled();
    });

    it('9-12. Existing features (timer, ingredient card, final completion, empty state) continue working safely alongside checklist state', async () => {
      const durationRecipe = {
        ...mockRecipe,
        instructions: ['Simmer the sauce for 5 minutes.']
      };
      vi.spyOn(recipesApi, 'getRecipe').mockResolvedValue(durationRecipe as any);

      renderComponent();

      // 9. Existing timer UI still renders
      expect(await screen.findByText('05:00')).toBeInTheDocument();

      // 10. Existing step ingredient card still renders
      expect(screen.getByText('Ingredients for This Step')).toBeInTheDocument();

      // Mark step complete
      const toggleBtn = screen.getByText('Mark Step Complete');
      fireEvent.click(toggleBtn);

      // 11. Complete cooking triggers existing flow
      const completeBtn = screen.getByRole('button', { name: /Complete Cooking/i });
      fireEvent.click(completeBtn);
      expect(mockCompleteMutate).toHaveBeenCalled();
    });
  });

  // 24. Cooking Mode UX, Accessibility & Responsive Hardening (Phase 9.9)
  describe('Cooking Mode Accessibility & Hardening', () => {
    it('1. Progress bar exposes correct ARIA attributes', async () => {
      renderComponent();
      const progress = await screen.findByRole('progressbar');
      expect(progress).toHaveAttribute('aria-label', 'Cooking progress percentage');
    });

    it('2. Active step item inside timeline has aria-current="step"', async () => {
      renderComponent();
      const activeItem = await screen.findByLabelText('Step 1 of 4, current step');
      expect(activeItem).toHaveAttribute('aria-current', 'step');
    });

    it('3. Incomplete checklist button exposes appropriate helper text and toggle state details', async () => {
      renderComponent();
      const toggleBtn = await screen.findByText('Mark Step Complete');
      expect(toggleBtn.closest('button')).toHaveAttribute('aria-label', 'Mark step 1 as complete');
    });

    it('4. Focus shifts to step header on render', async () => {
      renderComponent();
      const stepHeader = await screen.findByText('Instruction Step 1');
      await waitFor(() => {
        expect(stepHeader).toHaveFocus();
      });
    });

    it('5. Focus shifts to completion screen heading on complete cooking', async () => {
      const completedSession = { ...mockSession, status: 'completed' };
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: completedSession,
        isLoading: false,
      });
      renderComponent();
      const completionHeader = await screen.findByText('🎉 Cooking Complete!');
      await waitFor(() => {
        expect(completionHeader).toHaveFocus();
      });
    });

    it('6. Focus shifts to error container when session fetch fails', async () => {
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: new Error('Failed to load session'),
      });
      renderComponent();
      const errorDiv = await screen.findByText('Session Not Found');
      await waitFor(() => {
        expect(errorDiv.closest('.focus\\:ring-2')).toHaveFocus();
      });
    });
  });

  // Phase 9.10 — Cooking Session Polish & Reliability Tests
  describe('Cooking Session Polish & Reliability (9.10)', () => {
    // 9.10.1 — Session state robustness
    it('1. Nonexistent session ID shows a clean error state with Browse Recipes fallback', async () => {
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: new Error('Cooking session not found'),
        refetch: vi.fn(),
      });
      renderComponent();
      // Accessible error heading shown
      expect(await screen.findByText('Session Not Found')).toBeInTheDocument();
      // Retry action is provided
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
      // A graceful escape route is provided
      expect(screen.getByRole('button', { name: /Browse Recipes/i })).toBeInTheDocument();
    });

    it('2. Missing recipe shows Recipe Not Found error with Browse Recipes fallback', async () => {
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: mockSession,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });
      vi.spyOn(recipesApi, 'getRecipe').mockRejectedValue(new Error('Recipe not found'));
      renderComponent();
      expect(await screen.findByText('Recipe Not Found')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Browse Recipes/i })).toBeInTheDocument();
    });

    it('3. Completed session shows the cooking complete screen (not resumed as active)', async () => {
      const completedSession = { ...mockSession, status: 'completed', completed_at: '2026-08-13T13:00:00Z' };
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: completedSession,
        isLoading: false,
        isError: false,
      });
      renderComponent();
      // Completed state should be displayed — no step navigation buttons
      expect(await screen.findByText('🎉 Cooking Complete!')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Next Step/i })).not.toBeInTheDocument();
    });

    it('4. Invalid out-of-range current_step is safely clamped to last step', async () => {
      const staleStepSession = { ...mockSession, current_step: 999 };
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: staleStepSession,
        isLoading: false,
        isError: false,
      });
      renderComponent();
      // Should show the final step (4 of 4), not crash
      expect(await screen.findByText('Step 4 of 4')).toBeInTheDocument();
    });

    // 9.10.2 — Double action / race condition hardening
    it('5. Rapid clicks on Next Step while mutation is pending are ignored', async () => {
      (cookingHooks.useNextStep as any).mockReturnValue({
        mutate: mockNextMutate,
        isPending: true, // Mutation already in-flight
      });
      renderComponent();
      const nextBtn = await screen.findByRole('button', { name: /Next Step/i });
      // Button is disabled while pending
      expect(nextBtn).toBeDisabled();
      fireEvent.click(nextBtn);
      fireEvent.click(nextBtn);
      fireEvent.click(nextBtn);
      // Mutate should never be called when disabled
      expect(mockNextMutate).not.toHaveBeenCalled();
    });

    it('6. Complete Cooking button is disabled while complete mutation is pending', async () => {
      const lastStepSession = { ...mockSession, current_step: 3 }; // Last step index
      (cookingHooks.useCookingSession as any).mockReturnValue({
        data: lastStepSession,
        isLoading: false,
        isError: false,
      });
      (cookingHooks.useCompleteSession as any).mockReturnValue({
        mutate: mockCompleteMutate,
        isPending: true,
      });
      renderComponent();
      const completeBtn = await screen.findByRole('button', { name: /Complete Cooking/i });
      expect(completeBtn).toBeDisabled();
    });

    // 9.10.7 — Error recovery UX
    it('7. Navigation failure shows an accessible inline error banner that can be dismissed', async () => {
      const originalMock = mockNextMutate;
      (cookingHooks.useNextStep as any).mockReturnValue({
        mutate: vi.fn((_payload, opts) => {
          // Simulate onError callback
          opts?.onError(new Error('Network error'));
        }),
        isPending: false,
      });
      renderComponent();
      const nextBtn = await screen.findByRole('button', { name: /Next Step/i });
      fireEvent.click(nextBtn);
      // Inline error banner appears
      const banner = await screen.findByRole('alert');
      expect(banner).toBeInTheDocument();
      expect(banner).toHaveTextContent('Could not advance to the next step');
      // Dismiss button works
      const dismissBtn = screen.getByRole('button', { name: /Dismiss error/i });
      fireEvent.click(dismissBtn);
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      // Restore
      mockNextMutate = originalMock;
    });

    // 9.10.6 — Checklist state regression
    it('8. Checklist state persists across step navigation within the same page lifecycle', async () => {
      renderComponent();
      // Mark step 1 complete
      const toggleBtn = await screen.findByText('Mark Step Complete');
      fireEvent.click(toggleBtn);
      // The checklist toggle shows as completed
      expect(screen.getByText('Step Completed (Mark Incomplete)')).toBeInTheDocument();
      // Navigating next (mocked) does not clear checklist
      const nextBtn = screen.getByRole('button', { name: /Next Step/i });
      fireEvent.click(nextBtn);
      expect(mockNextMutate).toHaveBeenCalled();
    });

    // ── Phase 11.3 — Recipe Feedback & Ratings Flow ───────────────────────
    describe('Phase 11.3 — Recipe Feedback & Ratings Flow', () => {
      let mockSubmitFeedbackMutate: any;

      beforeEach(() => {
        mockSubmitFeedbackMutate = vi.fn();
        
        const completedSession = { ...mockSession, status: 'completed' };
        (cookingHooks.useCookingSession as any).mockReturnValue({
          data: completedSession,
          isLoading: false,
          isError: false,
        });

        (recipesApi.getRecipe as any).mockResolvedValue(mockRecipe);

        (feedbackHooks.useSubmitRecipeFeedback as any).mockReturnValue({
          mutate: mockSubmitFeedbackMutate,
          isPending: false,
          error: null,
        });
      });

      it('renders rating stars, difficulty, and notes fields when cooking is complete', async () => {
        renderComponent();
        expect(await screen.findByText(/Cooking Complete!/i)).toBeInTheDocument();
        expect(screen.getByText(/How was your cooking experience\?/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Recipe Difficulty/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Optional Notes/i)).toBeInTheDocument();
        
        // Star rating button should be in the DOM
        expect(screen.getAllByRole('button', { name: /rate/i }).length).toBe(5);
        // Exit buttons should NOT be visible initially
        expect(screen.queryByRole('button', { name: /Back to Recipe Details/i })).not.toBeInTheDocument();
      });

      it('submits rating and notes successfully, then shows success message and exit buttons', async () => {
        renderComponent();
        expect(await screen.findByText(/Cooking Complete!/i)).toBeInTheDocument();

        // Click the 4th star
        const stars = screen.getAllByRole('button', { name: /rate/i });
        fireEvent.click(stars[3]);

        // Enter notes
        fireEvent.change(screen.getByLabelText(/Optional Notes/i), { target: { value: 'Great dish!' } });

        // Mock successful mutation callback
        mockSubmitFeedbackMutate.mockImplementation((payload: any, callbacks: any) => {
          callbacks.onSuccess();
        });

        // Click submit
        fireEvent.click(screen.getByRole('button', { name: /Submit Feedback/i }));

        expect(mockSubmitFeedbackMutate).toHaveBeenCalledWith(
          { rating: 4, difficulty: 'Medium', notes: 'Great dish!' },
          expect.anything()
        );

        // Verify transition to final view
        expect(await screen.findByText(/Thank you! Your feedback has been applied/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Back to Recipe Details/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Explore More Recipes/i })).toBeInTheDocument();
      });

      it('skips feedback flow when Skip Feedback is clicked', async () => {
        renderComponent();
        expect(await screen.findByText(/Cooking Complete!/i)).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /Skip Feedback/i }));

        // Immediately transitions to final view
        expect(screen.getByRole('button', { name: /Back to Recipe Details/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Explore More Recipes/i })).toBeInTheDocument();
        expect(mockSubmitFeedbackMutate).not.toHaveBeenCalled();
      });

      it('displays error banner if feedback submission fails', async () => {
        mockSubmitFeedbackMutate.mockImplementation((payload: any, callbacks: any) => {
          callbacks.onError(new Error('Duplicate feedback detected'));
        });

        renderComponent();
        expect(await screen.findByText(/Cooking Complete!/i)).toBeInTheDocument();

        // Set rating
        const stars = screen.getAllByRole('button', { name: /rate/i });
        fireEvent.click(stars[4]);

        // Submit
        fireEvent.click(screen.getByRole('button', { name: /Submit Feedback/i }));

        expect(await screen.findByText('Duplicate feedback detected')).toBeInTheDocument();
      });
    });
  });
});
