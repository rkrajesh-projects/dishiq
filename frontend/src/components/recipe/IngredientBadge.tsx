/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * IngredientBadge — reusable colour-coded pill badge.
 *
 * Variants map to the design specification:
 *   category   → green
 *   optional   → amber
 *   toTaste    → blue
 *   preparation → gray
 *   confidence → purple  (dev-mode only; enforcement is the parent's job)
 */
import React from 'react';

export type BadgeVariant = 'category' | 'optional' | 'toTaste' | 'preparation' | 'confidence';

export interface IngredientBadgeProps {
  label: string;
  variant: BadgeVariant;
  /** Accessible description (e.g. "Category: vegetable"). Falls back to label. */
  ariaLabel?: string;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  category:    'bg-emerald-50  text-emerald-700 border border-emerald-100',
  optional:    'bg-amber-50    text-amber-700   border border-amber-100',
  toTaste:     'bg-blue-50     text-blue-700    border border-blue-100',
  preparation: 'bg-gray-100    text-gray-600    border border-gray-200',
  confidence:  'bg-purple-50   text-purple-700  border border-purple-100',
};

export const IngredientBadge: React.FC<IngredientBadgeProps> = ({
  label,
  variant,
  ariaLabel,
}) => (
  <span
    className={`inline-flex items-center text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full ${VARIANT_CLASSES[variant]}`}
    aria-label={ariaLabel ?? label}
  >
    {label}
  </span>
);
