import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect } from 'vitest';
import { AppRoutes } from '../routes/AppRoutes';

const renderWithRouter = (initialEntries = ['/']) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('Routing Integration', () => {
  it('renders HomePage on "/" route', () => {
    renderWithRouter(['/']);
    expect(screen.getByText('What would you like to cook?')).toBeInTheDocument();
  });

  it('renders RecipeSearchPage on "/recipes" route', () => {
    renderWithRouter(['/recipes']);
    expect(screen.getByText('Recipe Search & Smart Ranking')).toBeInTheDocument();
  });

  it('renders NotFoundPage on unknown route', () => {
    renderWithRouter(['/unknown-path-xyz']);
    expect(screen.getByText('Recipe or Page Not Found')).toBeInTheDocument();
  });
});
