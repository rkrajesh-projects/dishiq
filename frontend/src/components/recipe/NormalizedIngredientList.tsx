/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * NormalizedIngredientList — container component that fetches and renders
 * a recipe's normalised ingredients via the Ingredient Intelligence API.
 *
 * States handled:
 *   ▸ Loading  → reuses <LoadingState>
 *   ▸ Error    → reuses <ErrorState> with retry
 *   ▸ Empty    → reuses <EmptyState>
 *   ▸ Loaded   → renders a list of <IngredientRow> components
 *
 * Phase 6.4.6 Integration:
 *   Integrates <GroceryQuickMatch> modal for finding missing grocery items.
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { IngredientRow } from './IngredientRow';
import { GroceryQuickMatch } from '../grocery/GroceryQuickMatch';
import { getRecipeIngredients } from '../../api/ingredients';
import type { ParsedIngredient } from '../../types/ingredient';

export interface NormalizedIngredientListProps {
  recipeId: string;
  /** Optional set of pantry ingredient canonical names for "In Pantry" highlighting */
  pantryIngredients?: Set<string>;
}

export const NormalizedIngredientList: React.FC<NormalizedIngredientListProps> = ({
  recipeId,
  pantryIngredients,
}) => {
  const [quickMatchIngredient, setQuickMatchIngredient] = useState<string | null>(null);
  const [selectedIngredients, setSelectedIngredients] = useState<Set<string>>(new Set());

  // Sync with pantryIngredients if it changes
  React.useEffect(() => {
    if (pantryIngredients) {
      setSelectedIngredients(new Set(pantryIngredients));
    }
  }, [pantryIngredients]);

  const handleToggleIngredient = (canonicalName: string) => {
    setSelectedIngredients((prev) => {
      const next = new Set(prev);
      if (next.has(canonicalName)) {
        next.delete(canonicalName);
      } else {
        next.add(canonicalName);
      }
      return next;
    });
  };

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['recipe-ingredients', recipeId],
    queryFn: () => getRecipeIngredients(recipeId),
    staleTime: 5 * 60 * 1000,   // 5 minutes — ingredients don't change often
  });

  // ── Loading ────────────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingState message="Analysing ingredients…" />;
  }

  // ── Error ──────────────────────────────────────────────────────────────
  if (isError) {
    const message =
      (error as { message?: string })?.message ??
      'Unable to load ingredient data. Please try again.';
    return (
      <ErrorState
        title="Could not load ingredients"
        message={message}
        onRetry={() => refetch()}
      />
    );
  }

  const ingredients: ParsedIngredient[] = data?.results ?? [];

  // ── Empty ──────────────────────────────────────────────────────────────
  if (ingredients.length === 0) {
    return (
      <EmptyState
        title="No ingredients found"
        description="This recipe does not have any stored ingredient data yet."
      />
    );
  }

  // ── Ingredient list ────────────────────────────────────────────────────
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center justify-between">
        <span>Ingredients</span>
        <span className="text-xs font-normal text-gray-500">
          {ingredients.length} {ingredients.length === 1 ? 'item' : 'items'}
        </span>
      </h3>

      <ul className="divide-y divide-gray-50" aria-label="Ingredient list">
        {ingredients.map((ingredient, idx) => (
          <IngredientRow
            key={`${ingredient.raw_text}-${idx}`}
            ingredient={ingredient}
            inPantry={pantryIngredients?.has(ingredient.canonical_name) ?? false}
            isSelected={selectedIngredients.has(ingredient.canonical_name)}
            onToggle={() => handleToggleIngredient(ingredient.canonical_name)}
            onQuickMatch={(ingredientName) => setQuickMatchIngredient(ingredientName)}
          />
        ))}
      </ul>

      {/* Category legend */}
      <div className="mt-4 pt-3 border-t border-gray-50 flex flex-wrap gap-2 text-[10px] text-gray-400">
        <span className="inline-flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />Category
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-gray-400" />Prep Note
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-400" />To Taste
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-400" />Optional
        </span>
      </div>

      {/* Quick Match Modal */}
      <GroceryQuickMatch
        ingredient={quickMatchIngredient || ''}
        isOpen={Boolean(quickMatchIngredient)}
        onClose={() => setQuickMatchIngredient(null)}
      />
    </div>
  );
};
