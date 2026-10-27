import React from 'react';
import { Clock, Users, Star, ArrowRight, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Recipe } from '../../types';

export interface RecipeCardProps {
  recipe: Recipe;
}

export const RecipeCard: React.FC<RecipeCardProps> = ({ recipe }) => {
  return (
    <div className="bg-white rounded-2xl border border-orange-100/60 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col overflow-hidden group">
      <div className="p-5 flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between gap-2 mb-3">
            {recipe.cuisine && recipe.cuisine.toLowerCase() !== 'unknown' && (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">
                {recipe.cuisine}
              </span>
            )}
            <span className={`inline-flex items-center gap-1 text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full ${(!recipe.cuisine || recipe.cuisine.toLowerCase() === 'unknown') ? 'ml-auto' : ''}`}>
              <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
              {recipe.average_rating.toFixed(1)}
            </span>
          </div>

          <h3 className="text-lg font-bold text-gray-900 group-hover:text-emerald-600 transition-colors mb-2 line-clamp-1">
            {recipe.name}
          </h3>

          <p className="text-xs text-gray-600 line-clamp-2 mb-4">
            {recipe.description}
          </p>

          {/* Recommendation Explanations */}
          {recipe.explanations && recipe.explanations.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-1.5">
              {recipe.explanations.slice(0, 2).map((explanation, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 text-[11px] font-medium bg-orange-50 text-orange-700 border border-orange-200/60 px-2 py-0.5 rounded-full"
                >
                  <Sparkles className="w-3 h-3 text-orange-500 shrink-0" />
                  <span>{explanation}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between text-xs text-gray-500 border-t border-gray-100 pt-3 mb-4">
            <div className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-orange-500" />
              <span>{recipe.preparation_minutes + recipe.cooking_minutes} mins</span>
            </div>
            <div className="flex items-center gap-1">
              <Users className="w-3.5 h-3.5 text-gray-400" />
              <span>{recipe.servings} servings</span>
            </div>
            <span className="font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
              {recipe.dietary_type}
            </span>
          </div>

          <Link
            to={`/recipes/${recipe.id}`}
            className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-4 rounded-xl text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-600 hover:text-white transition-all group-hover:shadow-sm"
          >
            <span>View Recipe</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};
