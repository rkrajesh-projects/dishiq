/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * IngredientRow — displays one normalised ingredient with badges.
 *
 * Layout (responsive):
 *
 *   ● [qty unit]  Canonical Name   [Category] [Prep Note] [Optional] [To Taste] [Quick Match]
 *                                  ↳ ParserMetadata (dev mode only)
 */
import React from 'react';
import { Circle, CheckCircle2, ShoppingBag } from 'lucide-react';
import { IngredientBadge } from './IngredientBadge';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import type { ParsedIngredient } from '../../types/ingredient';

export interface IngredientRowProps {
  ingredient: ParsedIngredient;
  /** Mark the ingredient as already stocked in the user's pantry */
  inPantry?: boolean;
  /** Optional callback to open Quick Match modal for this ingredient */
  onQuickMatch?: (ingredientName: string) => void;
  isSelected?: boolean;
  onToggle?: () => void;
  scaleFactor?: number;
}

/** Capitalise first letter of each word */
function titleCase(str: string): string {
  return str.replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format quantity for display — hides trailing .0 for whole numbers */
function formatQty(qty: number | null): string {
  if (qty === null) return '';
  return qty % 1 === 0 ? String(Math.round(qty)) : String(qty);
}

export const IngredientRow: React.FC<IngredientRowProps> = ({
  ingredient,
  inPantry = false,
  onQuickMatch,
  isSelected = false,
  onToggle,
  scaleFactor = 1,
}) => {
  const {
    canonical_name,
    display_name,
    quantity,
    unit,
    preparation_note,
    optional,
    to_taste,
    category,
    confidence_score,
    matched_alias,
    normalization_source,
    parser_version,
  } = ingredient;

  const effectiveQty = (quantity !== null && quantity !== undefined && scaleFactor && scaleFactor !== 1 && !to_taste)
    ? Math.round(quantity * scaleFactor * 100) / 100
    : quantity;

  const qtyText = [formatQty(effectiveQty), unit].filter(Boolean).join(' ');
  const isDev = import.meta.env.DEV && import.meta.env.MODE === 'development';
  const targetIngredient = canonical_name || display_name;

  return (
    <li
      className={`py-3 flex flex-col gap-1.5 border-b border-gray-50 last:border-0 transition-colors ${
        (isSelected || inPantry) ? 'bg-emerald-50/40 rounded-xl px-2.5 -mx-2.5' : ''
      }`}
      data-testid={`ingredient-row-${canonical_name}`}
      data-in-pantry={inPantry || isSelected}
    >
      {/* ── Main row ──────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-2 text-sm">
        {/* Left: icon + name */}
        <div
          onClick={onToggle}
          className={`flex items-start gap-2.5 min-w-0 ${onToggle ? 'cursor-pointer select-none' : ''}`}
          data-testid={`ingredient-select-${canonical_name}`}
        >
          {isSelected || inPantry ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" aria-label="In pantry" />
          ) : (
            <Circle className="w-4 h-4 text-gray-300 shrink-0 mt-0.5" aria-label="Not in pantry" />
          )}
          <div className="min-w-0">
            <span className={`font-semibold leading-snug ${(isSelected || inPantry) ? 'text-gray-900' : 'text-gray-800'}`}>
              {titleCase(canonical_name)}
            </span>
            {display_name.toLowerCase() !== canonical_name.toLowerCase() && (
              <span className="block text-[11px] text-gray-400 truncate" title={display_name}>
                {display_name}
              </span>
            )}
          </div>
        </div>

        {/* Right: quantity + pantry badge + quick match button */}
        <div className="flex items-center gap-2 shrink-0 mt-0.5">
          {qtyText && (
            <span className="text-xs text-gray-500 font-mono tabular-nums">{qtyText}</span>
          )}
          {inPantry ? (
            <span className="text-[10px] uppercase tracking-wider font-bold bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded">
              In Pantry
            </span>
          ) : (
            onQuickMatch && (
              <button
                onClick={() => onQuickMatch(targetIngredient)}
                className="p-1 px-2 text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors inline-flex items-center gap-1"
                aria-label={`Find grocery match for ${targetIngredient}`}
                data-testid={`quick-match-button-${targetIngredient.toLowerCase()}`}
              >
                <ShoppingBag className="w-3 h-3 text-emerald-600" />
                <span>Match</span>
              </button>
            )
          )}
        </div>
      </div>

      {/* ── Badges row ──────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-1 pl-7">
        {category && (
          <IngredientBadge
            label={category}
            variant="category"
            ariaLabel={`Category: ${category}`}
          />
        )}
        {preparation_note && (
          <IngredientBadge
            label={preparation_note}
            variant="preparation"
            ariaLabel={`Preparation: ${preparation_note}`}
          />
        )}
        {to_taste && (
          <IngredientBadge
            label="To Taste"
            variant="toTaste"
            ariaLabel="No fixed quantity — add to taste"
          />
        )}
        {optional && (
          <IngredientBadge
            label="Optional"
            variant="optional"
            ariaLabel="This ingredient is optional"
          />
        )}

        {/* Confidence indicator — development mode only */}
        {isDev && (
          <ConfidenceIndicator score={confidence_score} />
        )}
      </div>

      {/* ── Parser metadata — development mode only ────────────────────── */}
      {isDev && (
        <div className="pl-7 text-[10px] text-purple-500 font-mono space-x-3">
          <span>v{parser_version}</span>
          {matched_alias && <span>alias: {matched_alias}</span>}
          <span>src: {normalization_source}</span>
        </div>
      )}
    </li>
  );
};
