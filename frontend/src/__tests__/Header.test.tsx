import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect } from 'vitest';
import { Header } from '../components/layout/Header';

import { AuthProvider } from '../context/AuthContext';

const renderHeader = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Header />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('Header Component', () => {
  it('renders DishIQ logo branding', () => {
    renderHeader();
    expect(screen.getByText(/Dish/i)).toBeInTheDocument();
    expect(screen.getByText(/IQ/i)).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderHeader();
    expect(screen.getAllByText('Home')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Recipes')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Grocery')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Cooking')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Pantry')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Profile')[0]).toBeInTheDocument();
  });

  it('renders backend status badge', () => {
    renderHeader();
    const statusBadge = screen.getByTestId('backend-status');
    expect(statusBadge).toBeInTheDocument();
  });
});
