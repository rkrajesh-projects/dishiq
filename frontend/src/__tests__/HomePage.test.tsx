import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { HomePage } from '../pages/HomePage';
import * as cookingHooks from '../hooks/useCooking';
import * as recipesApi from '../api/recipes';
import * as profileHooks from '../hooks/useProfile';
import * as pantryHooks from '../hooks/usePantry';
import * as recsHooks from '../hooks/useRecommendations';

vi.mock('../hooks/useProfile', () => ({
  useProfile: vi.fn(),
}));

vi.mock('../hooks/usePantry', () => ({
  usePantryItems: vi.fn(),
}));

vi.mock('../hooks/useRecommendations', () => ({
  useRecommendations: vi.fn(),
}));

// Mock routing
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<any>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock active session hook
vi.mock('../hooks/useCooking', () => ({
  useActiveCookingSession: vi.fn(),
}));

// Mock recipe details fetch
vi.mock('../api/recipes', () => ({
  getRecipe: vi.fn(),
}));

const renderHomePage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('HomePage Resume Cooking Spotlight (Phase 9.8)', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (profileHooks.useProfile as any).mockReturnValue({
      data: {
        id: 'user-123',
        email: 'rajesh@example.com',
        full_name: 'Rajesh Kumar',
        preference: { dietary_type: 'Vegetarian', weekly_budget: 2500, household_size: 4 },
      },
      isLoading: false,
    });

    (pantryHooks.usePantryItems as any).mockReturnValue({
      data: [],
      isLoading: false,
    });

    (recsHooks.useRecommendations as any).mockReturnValue({
      data: { recommendations: [], total: 0 },
      isLoading: false,
      isError: false,
    });
  });

  it('1 & 6. Resume Cooking is not displayed when no active session exists or is completed', () => {
    (cookingHooks.useActiveCookingSession as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderHomePage();

    expect(screen.queryByText(/Continue Cooking/i)).not.toBeInTheDocument();
    expect(screen.queryByText('Resume Cooking')).not.toBeInTheDocument();
  });

  it('2, 3, 4. Resume Cooking card displays recipe title and step info when active session exists', async () => {
    (cookingHooks.useActiveCookingSession as any).mockReturnValue({
      data: {
        id: 'session-456',
        recipe_id: 'recipe-789',
        current_step: 2,
        status: 'active',
      },
      isLoading: false,
      error: null,
    });

    (recipesApi.getRecipe as any).mockResolvedValue({
      id: 'recipe-789',
      name: 'Paneer Butter Masala',
      instructions: ['Step 1', 'Step 2', 'Step 3', 'Step 4'],
    });

    renderHomePage();

    // Verify the resume card is loaded by waiting for the unique "Continue Cooking" heading
    expect(await screen.findByText(/Continue Cooking/i)).toBeInTheDocument();

    // Paneer Butter Masala appears in both popular dishes chips and the resume card
    const titleElements = screen.getAllByText('Paneer Butter Masala');
    expect(titleElements.length).toBeGreaterThan(1);

    // Verify current step info (2 is 0-indexed, meaning step 3)
    expect(screen.getByText('You are currently on Step 3 of 4')).toBeInTheDocument();
  });

  it('5. Clicking Resume Cooking navigates to the cooking session page', async () => {
    (cookingHooks.useActiveCookingSession as any).mockReturnValue({
      data: {
        id: 'session-456',
        recipe_id: 'recipe-789',
        current_step: 2,
        status: 'active',
      },
      isLoading: false,
      error: null,
    });

    (recipesApi.getRecipe as any).mockResolvedValue({
      id: 'recipe-789',
      name: 'Paneer Butter Masala',
      instructions: ['Step 1', 'Step 2', 'Step 3', 'Step 4'],
    });

    renderHomePage();

    const resumeBtn = await screen.findByRole('button', { name: /Resume cooking/i });
    fireEvent.click(resumeBtn);

    expect(mockNavigate).toHaveBeenCalledWith('/cooking/session-456');
  });

  it('7. Loading state is handled properly', async () => {
    (cookingHooks.useActiveCookingSession as any).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });

    renderHomePage();

    expect(screen.getByText('Loading active cooking session...')).toBeInTheDocument();
    expect(screen.queryByText(/Continue Cooking/i)).not.toBeInTheDocument();
  });

  it('8. Error state is handled gracefully', async () => {
    (cookingHooks.useActiveCookingSession as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed to fetch'),
    });

    renderHomePage();

    expect(screen.getByText('Failed to load active cooking session.')).toBeInTheDocument();
    expect(screen.queryByText(/Continue Cooking/i)).not.toBeInTheDocument();
  });

  // ── Phase 11.4 — Surface Personalized AI Recommendations on the UI ───
  describe('Phase 11.4 — Surface Personalized AI Recommendations on the UI', () => {
    it('shows loading state while recommendations are fetching', () => {
      (cookingHooks.useActiveCookingSession as any).mockReturnValue({ data: null });
      (recsHooks.useRecommendations as any).mockReturnValue({
        data: null,
        isLoading: true,
        isError: false,
      });

      renderHomePage();
      expect(screen.getByText(/Analyzing kitchen profile and pantry stock/i)).toBeInTheDocument();
    });

    it('renders dynamic spotlight card and recommendations grid when loaded', async () => {
      const mockRecommendedRecipes = [
        {
          id: 'recipe-1',
          name: 'Paneer Tikka',
          description: 'Spiced grilled cottage cheese',
          cuisine: 'Indian',
          dietary_type: 'Vegetarian',
          preparation_minutes: 15,
          cooking_minutes: 15,
          servings: 4,
          source_name: 'Custom',
          average_rating: 4.8,
          created_at: '2026-08-01T00:00:00Z',
          explanations: ['Matches your Vegetarian preference', '2 ingredient(s) already in your pantry'],
        },
        {
          id: 'recipe-2',
          name: 'Almond Milk Kheer',
          description: 'Vegan dessert',
          cuisine: 'Indian',
          dietary_type: 'Vegan',
          preparation_minutes: 10,
          cooking_minutes: 20,
          servings: 2,
          source_name: 'Custom',
          average_rating: 4.5,
          created_at: '2026-08-01T00:00:00Z',
          explanations: ['Matches your Vegan preference'],
        }
      ];

      (cookingHooks.useActiveCookingSession as any).mockReturnValue({ data: null });
      (recsHooks.useRecommendations as any).mockReturnValue({
        data: { recommendations: mockRecommendedRecipes, total: 2 },
        isLoading: false,
        isError: false,
      });

      renderHomePage();

      // Spotlight card assertions
      expect(screen.getByText('Suggested Tonight: Paneer Tikka')).toBeInTheDocument();
      expect(screen.getByText(/Matches your Vegetarian preference • 2 ingredient\(s\) already in your pantry/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Start Cooking →/i })).toBeInTheDocument();

      // Recommendations list/grid assertions
      expect(screen.getByText('Personalized Recommendations')).toBeInTheDocument();
      expect(screen.getByText('Paneer Tikka')).toBeInTheDocument();
      expect(screen.getByText('Almond Milk Kheer')).toBeInTheDocument();
    });

    it('shows graceful empty state if no recommendations are returned', () => {
      (cookingHooks.useActiveCookingSession as any).mockReturnValue({ data: null });
      (recsHooks.useRecommendations as any).mockReturnValue({
        data: { recommendations: [], total: 0 },
        isLoading: false,
        isError: false,
      });

      renderHomePage();
      expect(screen.getByText(/No personalized recommendations found/i)).toBeInTheDocument();
    });

    it('displays error banner without crashing the home page when recommendations fail', () => {
      (cookingHooks.useActiveCookingSession as any).mockReturnValue({ data: null });
      (recsHooks.useRecommendations as any).mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: new Error('Failed to compute recommendations'),
      });

      renderHomePage();
      expect(screen.getByText('Failed to compute recommendations')).toBeInTheDocument();
      // Ensure rest of page is intact
      expect(screen.getByText('What would you like to cook?')).toBeInTheDocument();
    });
  });
});
