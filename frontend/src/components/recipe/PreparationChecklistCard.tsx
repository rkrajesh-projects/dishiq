import React, { useState } from 'react';
import { CheckCircle2, Circle, CheckSquare, Square, Filter, ChefHat, Sparkles } from 'lucide-react';
import { Button } from '../common/Button';
import { PreparationChecklist, PreparationItem } from '../../types/cooking';

interface PreparationChecklistCardProps {
  checklist: PreparationChecklist | undefined;
  isLoading: boolean;
  onToggleIngredient: (ingredientKey: string) => void;
  onMarkAllPrepared: () => void;
  onContinueToCooking?: () => void;
  isUpdating?: boolean;
}

export const PreparationChecklistCard: React.FC<PreparationChecklistCardProps> = ({
  checklist,
  isLoading,
  onToggleIngredient,
  onMarkAllPrepared,
  onContinueToCooking,
  isUpdating = false,
}) => {
  const [filterRemainingOnly, setFilterRemainingOnly] = useState<boolean>(false);

  if (isLoading || !checklist) {
    return (
      <div className="bg-white rounded-3xl border border-gray-100 p-6 shadow-sm animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-10 bg-gray-100 rounded-xl"></div>
          <div className="h-10 bg-gray-100 rounded-xl"></div>
          <div className="h-10 bg-gray-100 rounded-xl"></div>
        </div>
      </div>
    );
  }

  const items = checklist.items || [];
  const displayedItems = filterRemainingOnly
    ? items.filter((item) => !item.is_prepared)
    : items;

  const total = checklist.total_ingredients;
  const prepared = checklist.prepared_count;
  const percent = total > 0 ? Math.round((prepared / total) * 100) : 0;
  const remainingCount = total - prepared;

  return (
    <div className="bg-white rounded-3xl border border-emerald-100/80 p-6 sm:p-8 shadow-sm space-y-6">
      {/* Header and Progress */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-extrabold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full">
              Phase 10 • Kitchen Prep
            </span>
            <span className="text-xs text-gray-400">
              Serves {checklist.servings} (scale: {checklist.scale_factor}×)
            </span>
          </div>
          <h2 className="text-lg sm:text-xl font-extrabold text-gray-900 flex items-center gap-2">
            <span>Ingredient Preparation Checklist</span>
            {checklist.all_prepared && (
              <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-emerald-600" />
                All Ready
              </span>
            )}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Mise en place: Wash, chop, measure, and prepare ingredients before starting heat.
          </p>
        </div>

        {/* Progress Pill */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <span className="text-xs font-bold text-gray-700 block">
              {prepared} of {total} Prepared
            </span>
            <span className="text-[11px] text-emerald-700 font-semibold">
              {percent}% Ready
            </span>
          </div>
          <div className="w-12 h-12 rounded-full border-2 border-emerald-500 flex items-center justify-center font-extrabold text-xs text-emerald-800 bg-emerald-50">
            {percent}%
          </div>
        </div>
      </div>

      {/* Filter and Bulk Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setFilterRemainingOnly(false)}
            className={`px-3 py-1.5 rounded-xl font-semibold transition-colors ${
              !filterRemainingOnly
                ? 'bg-emerald-700 text-white shadow-xs'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            All ({total})
          </button>
          <button
            type="button"
            onClick={() => setFilterRemainingOnly(true)}
            className={`px-3 py-1.5 rounded-xl font-semibold transition-colors flex items-center gap-1.5 ${
              filterRemainingOnly
                ? 'bg-emerald-700 text-white shadow-xs'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Filter className="w-3 h-3" />
            <span>Remaining ({remainingCount})</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {prepared < total && (
            <Button
              variant="outline"
              size="sm"
              icon={<CheckSquare className="w-3.5 h-3.5 text-emerald-600" />}
              onClick={onMarkAllPrepared}
              disabled={isUpdating}
            >
              Mark All Prepared
            </Button>
          )}
          {onContinueToCooking && (
            <Button
              variant="primary"
              size="sm"
              icon={<ChefHat className="w-3.5 h-3.5" />}
              onClick={onContinueToCooking}
            >
              Start Cooking Steps →
            </Button>
          )}
        </div>
      </div>

      {/* Checklist items */}
      <ul className="divide-y divide-gray-100 border border-gray-100 rounded-2xl overflow-hidden" aria-label="Ingredient preparation checklist">
        {displayedItems.length === 0 ? (
          <li className="p-6 text-center text-xs text-gray-400 bg-gray-50/50">
            {filterRemainingOnly
              ? '🎉 All ingredients have been marked as prepared!'
              : 'No ingredients listed for preparation.'}
          </li>
        ) : (
          displayedItems.map((item: PreparationItem) => {
            const itemKey = item.name || item.id;
            return (
              <li
                key={item.id}
                onClick={() => onToggleIngredient(itemKey)}
                className={`p-3.5 sm:p-4 flex items-center justify-between gap-3 cursor-pointer select-none transition-colors ${
                  item.is_prepared
                    ? 'bg-emerald-50/40 text-emerald-950 hover:bg-emerald-50/70'
                    : 'bg-white hover:bg-gray-50'
                }`}
                role="checkbox"
                aria-checked={item.is_prepared}
                aria-label={`Ingredient ${item.name}, ${item.is_prepared ? 'prepared' : 'unprepared'}`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    type="button"
                    aria-hidden="true"
                    className="shrink-0 text-emerald-600 focus:outline-none"
                  >
                    {item.is_prepared ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 fill-emerald-100" />
                    ) : (
                      <Circle className="w-5 h-5 text-gray-300 hover:text-emerald-500 transition-colors" />
                    )}
                  </button>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-bold capitalize ${item.is_prepared ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                        {item.name}
                      </span>
                      {item.category && (
                        <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                          {item.category}
                        </span>
                      )}
                      {item.to_taste && (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">
                          To taste
                        </span>
                      )}
                    </div>
                    {item.preparation_note && (
                      <p className="text-xs text-orange-600/90 font-medium mt-0.5">
                        Prep: {item.preparation_note}
                      </p>
                    )}
                    <p className="text-[11px] text-gray-400 italic mt-0.5 truncate">
                      {item.raw_text}
                    </p>
                  </div>
                </div>

                {/* Scaled Quantity Display */}
                <div className="text-right shrink-0">
                  {item.scaled_quantity !== null && item.scaled_quantity !== undefined ? (
                    <span className="text-sm font-extrabold font-mono text-gray-800">
                      {item.scaled_quantity} {item.unit || ''}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400 font-medium">As needed</span>
                  )}
                  {checklist.scale_factor !== 1 && item.quantity && !item.to_taste && (
                    <span className="block text-[10px] text-gray-400 font-mono">
                      (orig: {item.quantity} {item.unit})
                    </span>
                  )}
                </div>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
};
