import React from 'react';
import { CheckCircle2, Circle } from 'lucide-react';

export interface IngredientItem {
  name: string;
  quantity: string;
  inPantry?: boolean;
}

export interface IngredientListProps {
  ingredients: IngredientItem[];
}

export const IngredientList: React.FC<IngredientListProps> = ({ ingredients }) => {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center justify-between">
        <span>Required Ingredients</span>
        <span className="text-xs font-normal text-gray-500">{ingredients.length} items</span>
      </h3>
      <ul className="divide-y divide-gray-50">
        {ingredients.map((item, idx) => (
          <li key={idx} className="py-2.5 flex items-center justify-between text-sm">
            <div className="flex items-center gap-2.5">
              {item.inPantry ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <Circle className="w-4 h-4 text-gray-300 shrink-0" />
              )}
              <span className={`font-medium ${item.inPantry ? 'text-gray-900' : 'text-gray-700'}`}>
                {item.name}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-mono">{item.quantity}</span>
              {item.inPantry && (
                <span className="text-[10px] uppercase tracking-wider font-bold bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded">
                  In Pantry
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
