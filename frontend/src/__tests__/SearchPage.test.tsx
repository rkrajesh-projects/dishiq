import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { RecipeSearchPage } from '../pages/RecipeSearchPage';
import * as recipesApi from '../api/recipes';

vi.mock('../api/recipes', () => ({
  searchRecipes: vi.fn(),
}));

const renderSearchPage = (initialEntries = ['/recipes']) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <RecipeSearchPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('RecipeSearchPage Component', () => {
  it('renders search title and filter chips', () => {
    (recipesApi.searchRecipes as any).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    renderSearchPage();
    expect(screen.getByText('Recipe Search & Smart Ranking')).toBeInTheDocument();
    expect(screen.getByText('Vegetarian')).toBeInTheDocument();
    expect(screen.getByText('Vegan')).toBeInTheDocument();
  });

  it('renders recipe cards with recommendation tags when search data returns', async () => {
    (recipesApi.searchRecipes as any).mockResolvedValueOnce({
      items: [
        {
          id: 'rec_1',
          name: 'Paneer Bhurji',
          description: 'Scrambled paneer',
          cuisine: 'Indian',
          dietary_type: 'Vegetarian',
          preparation_minutes: 10,
          cooking_minutes: 15,
          servings: 4,
          source_name: 'DishIQ Demo Data',
          average_rating: 4.8,
          created_at: new Date().toISOString(),
          score: 0.95,
          explanations: ['Matches vegetarian preference', 'High rating (4.8 ★)'],
        },
      ],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    renderSearchPage();
    expect(await screen.findByText('Paneer Bhurji')).toBeInTheDocument();
    expect(screen.getByText('Matches vegetarian preference')).toBeInTheDocument();
  });
});
