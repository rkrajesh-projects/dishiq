/**
 * DishIQ Phase 12.3 — Frontend Regression Tests
 *
 * Targeted regression tests protecting recently fixed or high-risk behaviors.
 * Each test documents the specific defect or behavior it guards against.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { HomePage } from '../pages/HomePage';
import * as cookingHooks from '../hooks/useCooking';
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
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<any>('react-router-dom');
  return { ...actual, useNavigate: () => vi.fn() };
});
vi.mock('../hooks/useCooking', () => ({
  useActiveCookingSession: vi.fn(),
}));
vi.mock('../api/recipes', () => ({
  getRecipe: vi.fn(),
}));

const renderHomePage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

const mockRecommendations = [
  {
    id: 'rec-1',
    name: 'Palak Paneer',
    description: 'Spinach cottage cheese curry',
    cuisine: 'Indian',
    dietary_type: 'Vegetarian',
    preparation_minutes: 15,
    cooking_minutes: 20,
    servings: 4,
    source_name: 'Custom',
    average_rating: 4.7,
    created_at: '2026-08-01T00:00:00Z',
    explanations: [
      'Matches your Vegetarian preference',
      '3 ingredient(s) already in your pantry',
    ],
  },
];

describe('Phase 12.3 — AI Kitchen Memory Spotlight CTA Visibility Regression', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (profileHooks.useProfile as any).mockReturnValue({
      data: { id: 'u1', preference: { dietary_type: 'Vegetarian' } },
      isLoading: false,
    });
    (pantryHooks.usePantryItems as any).mockReturnValue({ data: [], isLoading: false });
    (cookingHooks.useActiveCookingSession as any).mockReturnValue({ data: null });
  });

  it('Start Cooking CTA is rendered and visible immediately without hover interaction', () => {
    (recsHooks.useRecommendations as any).mockReturnValue({
      data: { recommendations: mockRecommendations, total: 1 },
      isLoading: false,
      isError: false,
    });

    renderHomePage();

    const ctaButton = screen.getByRole('button', { name: /Start Cooking →/i });

    // The button must exist in the document
    expect(ctaButton).toBeInTheDocument();

    // It must NOT have any hover-dependent visibility classes that would hide it by default
    expect(ctaButton).not.toHaveClass('opacity-0');
    expect(ctaButton).not.toHaveClass('invisible');
    expect(ctaButton).not.toHaveClass('hidden');
    expect(ctaButton).not.toHaveClass('sr-only');

    // The parent container must also not be hidden
    const parent = ctaButton.parentElement;
    expect(parent).not.toHaveClass('opacity-0');
    expect(parent).not.toHaveClass('invisible');
    expect(parent).not.toHaveClass('hidden');
  });

  it('Spotlight renders the recommended recipe name in the heading', () => {
    (recsHooks.useRecommendations as any).mockReturnValue({
      data: { recommendations: mockRecommendations, total: 1 },
      isLoading: false,
      isError: false,
    });

    renderHomePage();
    expect(screen.getByText('Suggested Tonight: Palak Paneer')).toBeInTheDocument();
  });

  it('Spotlight renders recommendation explanation text from the API', () => {
    (recsHooks.useRecommendations as any).mockReturnValue({
      data: { recommendations: mockRecommendations, total: 1 },
      isLoading: false,
      isError: false,
    });

    renderHomePage();
    // Explanations are joined with ' • '
    expect(
      screen.getByText(/Matches your Vegetarian preference • 3 ingredient\(s\) already in your pantry/i),
    ).toBeInTheDocument();
  });

  it('Spotlight shows empty-state message when no personalized recommendations are found', () => {
    (recsHooks.useRecommendations as any).mockReturnValue({
      data: { recommendations: [], total: 0 },
      isLoading: false,
      isError: false,
    });

    renderHomePage();
    expect(screen.getByText(/No personalized recommendations found/i)).toBeInTheDocument();
    // "Start Cooking →" must NOT appear when there are no recommendations
    expect(screen.queryByRole('button', { name: /Start Cooking →/i })).not.toBeInTheDocument();
  });

  it('Recommendation loading skeleton shows pantry analysis message', () => {
    (recsHooks.useRecommendations as any).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
    });

    renderHomePage();
    expect(screen.getByText(/Analyzing kitchen profile and pantry stock/i)).toBeInTheDocument();
  });
});
