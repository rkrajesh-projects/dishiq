/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * Tests for IngredientRow and IngredientBadge components.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { IngredientRow } from '../components/recipe/IngredientRow';
import type { ParsedIngredient } from '../types/ingredient';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a full ParsedIngredient with sensible defaults */
function makeIngredient(overrides: Partial<ParsedIngredient> = {}): ParsedIngredient {
  return {
    raw_text: '500 g paneer',
    display_name: 'Paneer',
    canonical_name: 'paneer',
    category: 'dairy',
    quantity: 500,
    unit: 'g',
    preparation_note: null,
    optional: false,
    to_taste: false,
    confidence_score: 0.95,
    matched_alias: 'paneer',
    normalization_source: 'dictionary',
    parser_version: '1.0',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// IngredientRow — core rendering
// ---------------------------------------------------------------------------

describe('IngredientRow — quantity and unit', () => {
  it('renders the canonical ingredient name', () => {
    render(<IngredientRow ingredient={makeIngredient()} />);
    expect(screen.getByText('Paneer')).toBeInTheDocument();
  });

  it('renders quantity and unit together', () => {
    render(<IngredientRow ingredient={makeIngredient({ quantity: 500, unit: 'g' })} />);
    expect(screen.getByText('500 g')).toBeInTheDocument();
  });

  it('renders whole-number quantity without decimal', () => {
    render(<IngredientRow ingredient={makeIngredient({ quantity: 2, unit: null })} />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('omits quantity text when quantity is null', () => {
    render(<IngredientRow ingredient={makeIngredient({ quantity: null, unit: null })} />);
    // "Paneer" name present, but no standalone number
    expect(screen.queryByText('null')).not.toBeInTheDocument();
  });

  it('renders unit alone when quantity is null but unit is present', () => {
    render(<IngredientRow ingredient={makeIngredient({ quantity: null, unit: 'tbsp' })} />);
    expect(screen.getByText('tbsp')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IngredientRow — category badge
// ---------------------------------------------------------------------------

describe('IngredientRow — category badge', () => {
  it('shows category badge for known ingredient', () => {
    render(<IngredientRow ingredient={makeIngredient({ category: 'dairy' })} />);
    expect(screen.getByLabelText('Category: dairy')).toBeInTheDocument();
  });

  it('shows vegetable category badge', () => {
    render(<IngredientRow ingredient={makeIngredient({ category: 'vegetable' })} />);
    expect(screen.getByLabelText('Category: vegetable')).toBeInTheDocument();
  });

  it('does not render category badge when category is null', () => {
    render(<IngredientRow ingredient={makeIngredient({ category: null })} />);
    expect(screen.queryByLabelText(/Category:/)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IngredientRow — preparation note badge
// ---------------------------------------------------------------------------

describe('IngredientRow — preparation note', () => {
  it('shows preparation note badge', () => {
    render(
      <IngredientRow ingredient={makeIngredient({ preparation_note: 'finely chopped' })} />
    );
    expect(screen.getByLabelText('Preparation: finely chopped')).toBeInTheDocument();
  });

  it('does not show prep note badge when null', () => {
    render(<IngredientRow ingredient={makeIngredient({ preparation_note: null })} />);
    expect(screen.queryByLabelText(/Preparation:/)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IngredientRow — optional badge
// ---------------------------------------------------------------------------

describe('IngredientRow — optional badge', () => {
  it('shows Optional badge when ingredient is optional', () => {
    render(<IngredientRow ingredient={makeIngredient({ optional: true })} />);
    expect(screen.getByLabelText('This ingredient is optional')).toBeInTheDocument();
  });

  it('does not show Optional badge when not optional', () => {
    render(<IngredientRow ingredient={makeIngredient({ optional: false })} />);
    expect(screen.queryByLabelText('This ingredient is optional')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IngredientRow — to taste badge
// ---------------------------------------------------------------------------

describe('IngredientRow — to taste badge', () => {
  it('shows To Taste badge for to_taste ingredients', () => {
    render(
      <IngredientRow
        ingredient={makeIngredient({ to_taste: true, quantity: null, unit: null })}
      />
    );
    expect(
      screen.getByLabelText('No fixed quantity — add to taste')
    ).toBeInTheDocument();
  });

  it('does not show To Taste badge for normal ingredients', () => {
    render(<IngredientRow ingredient={makeIngredient({ to_taste: false })} />);
    expect(screen.queryByLabelText('No fixed quantity — add to taste')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IngredientRow — unknown ingredient
// ---------------------------------------------------------------------------

describe('IngredientRow — unknown ingredient', () => {
  it('renders unknown ingredient name without crashing', () => {
    const unknownIngredient = makeIngredient({
      raw_text: 'dragon bark xyz',
      display_name: 'Dragon Bark Xyz',
      canonical_name: 'dragon bark xyz',
      category: null,
      matched_alias: null,
      normalization_source: 'unknown',
      confidence_score: 0.45,
    });
    render(<IngredientRow ingredient={unknownIngredient} />);
    expect(screen.getByText('Dragon Bark Xyz')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IngredientRow — in pantry
// ---------------------------------------------------------------------------

describe('IngredientRow — in-pantry state', () => {
  it('shows In Pantry badge when inPantry is true', () => {
    render(<IngredientRow ingredient={makeIngredient()} inPantry={true} />);
    expect(screen.getByText('In Pantry')).toBeInTheDocument();
  });

  it('does not show In Pantry badge when inPantry is false', () => {
    render(<IngredientRow ingredient={makeIngredient()} inPantry={false} />);
    expect(screen.queryByText('In Pantry')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IngredientRow — confidence indicator (dev vs production)
// ---------------------------------------------------------------------------

describe('IngredientRow — confidence indicator visibility', () => {
  it('does not render confidence badge in production mode (import.meta.env.DEV = false)', () => {
    // Simulate production: import.meta.env.DEV is false by default in vitest jsdom
    const ingredient = makeIngredient({ confidence_score: 0.95 });
    render(<IngredientRow ingredient={ingredient} />);
    // In non-dev mode the confidence badge should not appear
    // (vitest sets import.meta.env.DEV = false by default)
    expect(screen.queryByLabelText(/Parser confidence:/)).not.toBeInTheDocument();
  });
});

describe('IngredientRow — onQuickMatch callback', () => {
  it('renders Match button and triggers callback with correct ingredient name when clicked', () => {
    const onQuickMatchMock = vi.fn();
    const ingredient = makeIngredient({ canonical_name: 'paneer', display_name: 'Paneer' });
    render(<IngredientRow ingredient={ingredient} onQuickMatch={onQuickMatchMock} />);

    const matchBtn = screen.getByRole('button', { name: /find grocery match for paneer/i });
    expect(matchBtn).toBeInTheDocument();

    fireEvent.click(matchBtn);
    expect(onQuickMatchMock).toHaveBeenCalledTimes(1);
    expect(onQuickMatchMock).toHaveBeenCalledWith('paneer');
  });
});

describe('IngredientRow — isSelected and onToggle', () => {
  it('renders checked icon when isSelected is true', () => {
    const ingredient = makeIngredient({ canonical_name: 'paneer', display_name: 'Paneer' });
    render(<IngredientRow ingredient={ingredient} isSelected={true} />);
    expect(screen.getByLabelText('In pantry')).toBeInTheDocument();
  });

  it('triggers onToggle callback when left container is clicked', () => {
    const onToggleMock = vi.fn();
    const ingredient = makeIngredient({ canonical_name: 'paneer', display_name: 'Paneer' });
    render(<IngredientRow ingredient={ingredient} onToggle={onToggleMock} />);

    const selectContainer = screen.getByTestId('ingredient-select-paneer');
    fireEvent.click(selectContainer);
    expect(onToggleMock).toHaveBeenCalledTimes(1);
  });
});
