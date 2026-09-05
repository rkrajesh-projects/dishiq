import React from 'react';
import { List } from 'lucide-react';

export interface StepIngredientsCardProps {
  /** The list of ingredients relevant to the current step */
  matchedIngredients: any[];
}

export const StepIngredientsCard: React.FC<StepIngredientsCardProps> = ({
  matchedIngredients,
}) => {
  const hasMatches = matchedIngredients.length > 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm space-y-4">
      <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 border-b border-gray-50 pb-3">
        <List className="w-4 h-4 text-emerald-600" />
        <span>Ingredients for This Step</span>
      </h3>

      {hasMatches ? (
        <ul className="space-y-3" aria-label="Step ingredients list">
          {matchedIngredients.map((ri, index) => (
            <li
              key={ri.id || index}
              className="text-xs text-gray-700 bg-emerald-50/30 border border-emerald-100/50 p-3 rounded-xl flex flex-col gap-1"
            >
              <span className="font-bold capitalize text-gray-900">
                {ri.ingredient?.canonical_name || 'Ingredient'}
              </span>
              <span className="text-[10px] text-gray-500 font-medium">
                Quantity: {ri.quantity} {ri.unit} {ri.preparation_note ? `(${ri.preparation_note})` : ''}
              </span>
              {ri.raw_text && (
                <span className="text-[10px] italic text-gray-400">
                  {ri.raw_text}
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className="text-center py-4 space-y-1">
          <p className="text-xs text-gray-600 font-medium">
            No specific ingredients identified for this step.
          </p>
          <p className="text-[10px] text-gray-400">
            Please consult the complete recipe ingredients reference.
          </p>
        </div>
      )}
    </div>
  );
};
