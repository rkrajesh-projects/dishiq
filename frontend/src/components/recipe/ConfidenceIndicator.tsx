/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * ConfidenceIndicator — displays parser confidence as a coloured percentage.
 *
 * IMPORTANT: This component should only be rendered in development mode.
 * The parent (IngredientRow) is responsible for gating render behind
 * `import.meta.env.DEV`. This component does NOT enforce that guard
 * itself so it remains straightforwardly testable in unit tests.
 */
import React from 'react';
import { IngredientBadge } from './IngredientBadge';

export interface ConfidenceIndicatorProps {
  /** Parser confidence score in [0, 1] */
  score: number;
}

export const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({ score }) => {
  const pct = Math.round(score * 100);
  return (
    <IngredientBadge
      label={`${pct}%`}
      variant="confidence"
      ariaLabel={`Parser confidence: ${pct}%`}
    />
  );
};
