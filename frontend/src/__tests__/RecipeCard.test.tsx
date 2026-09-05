import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { RecipeCard } from '../components/recipe/RecipeCard';
import { Recipe } from '../types';

const mockRecipe: Recipe = {
  id: 'recipe_123',
  name: 'Paneer Bhurji',
  description: 'Scrambled paneer curry',
  cuisine: 'Indian',
  dietary_type: 'Vegetarian',
  preparation_minutes: 10,
  cooking_minutes: 15,
  servings: 4,
  source_name: 'DishIQ Demo Data',
  average_rating: 4.8,
  created_at: new Date().toISOString(),
};

describe('RecipeCard Component', () => {
  it('renders recipe title, cuisine, rating, and view button', () => {
    render(
      <BrowserRouter>
        <RecipeCard recipe={mockRecipe} />
      </BrowserRouter>
    );

    expect(screen.getByText('Paneer Bhurji')).toBeInTheDocument();
    expect(screen.getByText('Indian')).toBeInTheDocument();
    expect(screen.getByText('Vegetarian')).toBeInTheDocument();
    expect(screen.getByText('4.8')).toBeInTheDocument();
    expect(screen.getByText('25 mins')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /View Recipe/i })).toHaveAttribute('href', '/recipes/recipe_123');
  });
});
