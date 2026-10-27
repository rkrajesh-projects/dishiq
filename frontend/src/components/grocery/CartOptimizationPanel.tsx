import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ShoppingCart, RefreshCw, AlertTriangle, Info, Trophy, Split, Clock, CheckCircle, ChefHat, ExternalLink } from 'lucide-react';
import { getRecipeIngredients } from '../../api/ingredients';
import { useCartOptimize } from '../../hooks/useCartOptimization';
import { useStartCooking, useActiveCookingSession } from '../../hooks/useCooking';
import { usePantryItems } from '../../hooks/usePantry';
import { formatINR } from '../../utils/currency';
import { CartIngredientRequest } from '../../types/cart';
import { PriceComparisonCard } from './PriceComparisonCard';
import { CartOptimizeResponse } from '../../types';

export interface CartOptimizationPanelProps {
  onOptimizationResult?: (result: CartOptimizeResponse) => void;
  defaultLiveMode?: boolean;
}

export const CartOptimizationPanel: React.FC<CartOptimizationPanelProps> = ({
  onOptimizationResult,
  defaultLiveMode = false,
}) => {
  const [searchParams] = useSearchParams();
  const recipeId = searchParams.get('recipeId') || '';
  const servingsParam = searchParams.get('servings');
  const baseServingsParam = searchParams.get('baseServings');
  const servings = servingsParam ? parseFloat(servingsParam) : null;
  const baseServings = baseServingsParam ? parseFloat(baseServingsParam) : null;
  const scaleFactor = (servings && baseServings && baseServings > 0) ? (servings / baseServings) : 1;

  const [budgetCap, setBudgetCap] = useState<string>('');
  const [isLiveMode, setIsLiveMode] = useState<boolean>(defaultLiveMode);
  const [deductPantry, setDeductPantry] = useState<boolean>(true);

  const navigate = useNavigate();
  const startCookingMutation = useStartCooking();
  const { data: activeSession } = useActiveCookingSession(recipeId || undefined);
  const { data: pantryItems } = usePantryItems();

  const pantrySet = React.useMemo(() => {
    const set = new Set<string>();
    if (pantryItems && Array.isArray(pantryItems)) {
      for (const item of pantryItems) {
        if (item.canonical_name) set.add(item.canonical_name.toLowerCase().trim());
        if (item.ingredient_name) set.add(item.ingredient_name.toLowerCase().trim());
        if (item.custom_name) set.add(item.custom_name.toLowerCase().trim());
      }
    }
    return set;
  }, [pantryItems]);

  const isIngredientInPantry = React.useCallback(
    (canonicalName: string, displayName?: string) => {
      if (pantrySet.size === 0) return false;
      const can = (canonicalName || '').toLowerCase().trim();
      const disp = (displayName || '').toLowerCase().trim();
      if (pantrySet.has(can) || pantrySet.has(disp)) return true;
      for (const p of pantrySet) {
        if (can && (can === p || can.includes(p) || p.includes(can))) return true;
        if (disp && (disp === p || disp.includes(p) || p.includes(disp))) return true;
      }
      return false;
    },
    [pantrySet]
  );

  // Get recipe ingredients if recipeId is available
  const {
    data: ingredientsData,
    isLoading: isIngredientsLoading,
    isError: isIngredientsError,
    error: ingredientsError,
  } = useQuery({
    queryKey: ['recipe-ingredients', recipeId],
    queryFn: () => getRecipeIngredients(recipeId),
    enabled: !!recipeId,
  });

  const {
    mutate: optimize,
    data: optimizeResult,
    isPending: isOptimizePending,
    isError: isOptimizeError,
    error: optimizeError,
  } = useCartOptimize(isLiveMode);

  const { coveredByPantry, itemsToOptimize } = React.useMemo(() => {
    const results = ingredientsData?.results || [];
    if (!deductPantry || pantrySet.size === 0) {
      return { coveredByPantry: [], itemsToOptimize: results };
    }
    const covered: typeof results = [];
    const toOpt: typeof results = [];
    for (const ing of results) {
      if (isIngredientInPantry(ing.canonical_name, ing.display_name)) {
        covered.push(ing);
      } else {
        toOpt.push(ing);
      }
    }
    return { coveredByPantry: covered, itemsToOptimize: toOpt };
  }, [ingredientsData?.results, deductPantry, pantrySet, isIngredientInPantry]);

  const handleStartCooking = () => {
    if (!recipeId) return;
    if (activeSession && activeSession.status !== 'completed') {
      navigate(`/cooking/${activeSession.id}`);
      return;
    }
    startCookingMutation.mutate(
      { recipe_id: recipeId, servings: servings || undefined },
      {
        onSuccess: (session) => {
          navigate(`/cooking/${session.id}`);
        },
        onError: () => {
          navigate(`/cooking/${recipeId}`);
        },
      }
    );
  };

  // Trigger optimization automatically when ingredients are fetched
  useEffect(() => {
    if (itemsToOptimize.length > 0) {
      const ingredientsList: CartIngredientRequest[] = itemsToOptimize.map((ing) => {
        const rawQty = ing.quantity || 1.0;
        const scaledQty = Math.round(rawQty * scaleFactor * 100) / 100;
        return {
          ingredient_name: ing.canonical_name,
          required_quantity: scaledQty,
          required_unit: ing.unit || 'piece',
        };
      });
      optimize({ ingredients: ingredientsList, budget_cap: budgetCap ? parseFloat(budgetCap) : undefined });
    }
  }, [itemsToOptimize, optimize, scaleFactor]);

  // Pass result up to parent if callback is provided
  useEffect(() => {
    if (optimizeResult && onOptimizationResult) {
      onOptimizationResult(optimizeResult);
    }
  }, [optimizeResult, onOptimizationResult]);

  const handleOptimize = () => {
    if (itemsToOptimize.length > 0) {
      const ingredientsList: CartIngredientRequest[] = itemsToOptimize.map((ing) => {
        const rawQty = ing.quantity || 1.0;
        const scaledQty = Math.round(rawQty * scaleFactor * 100) / 100;
        return {
          ingredient_name: ing.canonical_name,
          required_quantity: scaledQty,
          required_unit: ing.unit || 'piece',
        };
      });
      optimize({ ingredients: ingredientsList, budget_cap: budgetCap ? parseFloat(budgetCap) : undefined });
    }
  };

  if (!recipeId) {
    return (
      <div className="bg-amber-50 border border-amber-100 rounded-3xl p-6 text-center text-amber-800 shadow-xs">
        <ShoppingCart className="w-8 h-8 text-amber-600 mx-auto mb-3" />
        <h4 className="font-bold text-base mb-1">No Recipe Selected for Optimization</h4>
        <p className="text-xs text-amber-700 max-w-md mx-auto">
          Please select a recipe from the recipe list and click "Compare Prices" to generate and optimize your shopping cart.
        </p>
      </div>
    );
  }

  if (isIngredientsLoading) {
    return (
      <div className="bg-white rounded-3xl border border-gray-100 p-8 text-center space-y-4 shadow-sm" data-testid="cart-optimize-loading">
        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-gray-500 font-medium">Fetching recipe ingredients...</p>
      </div>
    );
  }

  if (isIngredientsError) {
    return (
      <div className="bg-rose-50 border border-rose-100 rounded-3xl p-6 text-center text-rose-800 shadow-xs" data-testid="cart-optimize-error">
        <AlertTriangle className="w-8 h-8 text-rose-600 mx-auto mb-3" />
        <h4 className="font-bold text-base mb-1">Failed to Load Ingredients</h4>
        <p className="text-xs text-rose-700 mb-4">
          {ingredientsError?.message || 'Could not fetch ingredients for this recipe.'}
        </p>
        <button
          onClick={() => handleOptimize()}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-xl transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const ingredientsCount = ingredientsData?.results?.length || 0;

  if (ingredientsCount === 0) {
    return (
      <div className="bg-white rounded-3xl border border-gray-100 p-8 text-center shadow-sm">
        <AlertTriangle className="w-8 h-8 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-500">This recipe has no ingredients to optimize.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="cart-optimization-panel">
      {/* Disclaimer */}
      {optimizeResult?.data_source === 'live' ? (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-xs text-emerald-800 flex items-start gap-2.5 shadow-xs">
          <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Live Data Notice:</span> Prices and delivery fees were fetched in real-time from supported QuickCommerce APIs.
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-2xl p-4 text-xs text-gray-700 flex items-start gap-2.5 shadow-xs">
          <Info className="w-4 h-4 text-gray-500 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Live Data Notice:</span> (Demo Mode Active) You are currently viewing static/demo grocery data. Configure QuickCommerce API credentials in the backend to enable live real-time pricing.
          </div>
        </div>
      )}

      {/* Main Optimization Area */}
      <div className="bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm space-y-6 relative overflow-hidden">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 pb-5">
          <div>
            <h3 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-emerald-600" />
              Recommended Shopping Plan
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Optimizing {ingredientsCount} ingredients for maximum value, convenience, and delivery parameters
            </p>
          </div>
          <button
            onClick={handleOptimize}
            disabled={isOptimizePending}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-50 hover:bg-gray-100 disabled:opacity-50 border border-gray-200 text-xs font-semibold text-gray-700 rounded-xl transition-all self-start sm:self-center"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isOptimizePending ? 'animate-spin' : ''}`} />
            <span>Optimize Cart</span>
          </button>
        </div>

        {/* Covered by Pantry Section */}
        {coveredByPantry.length > 0 && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-xs text-emerald-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs" data-testid="covered-by-pantry-banner">
            <div className="flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Covered by Your Pantry ({coveredByPantry.length}):</span>{' '}
                <span className="font-medium text-emerald-800">
                  {coveredByPantry.map((ing) => ing.display_name || ing.canonical_name).join(', ')}
                </span>
                <p className="text-[11px] text-emerald-700/80 mt-0.5">
                  These ingredients are already in your pantry and deducted from your shopping cart.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setDeductPantry(!deductPantry)}
              className="px-3 py-1 bg-white hover:bg-emerald-100/70 border border-emerald-300 text-emerald-800 font-semibold text-[11px] rounded-lg shadow-2xs transition-all shrink-0 cursor-pointer"
              data-testid="toggle-deduct-pantry"
            >
              {deductPantry ? 'Include in cart' : 'Deduct from cart'}
            </button>
          </div>
        )}

        {/* All covered by pantry state */}
        {itemsToOptimize.length === 0 && coveredByPantry.length > 0 && (
          <div className="py-8 text-center space-y-3 bg-emerald-50/60 border border-emerald-100 rounded-2xl p-6" data-testid="all-covered-by-pantry">
            <CheckCircle className="w-10 h-10 text-emerald-600 mx-auto" />
            <h4 className="text-base font-bold text-emerald-900">All Ingredients Ready in Pantry!</h4>
            <p className="text-xs text-emerald-700 max-w-md mx-auto">
              All {ingredientsCount} ingredients for this recipe are already in your pantry. No store shopping needed!
            </p>
          </div>
        )}

        {/* Loading overlay for optimization */}
        {isOptimizePending && (
          <div className="py-12 text-center space-y-4" data-testid="cart-optimize-pending">
            <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-gray-500 font-medium animate-pulse">Running basket value optimizations...</p>
          </div>
        )}

        {isOptimizeError && !isOptimizePending && (
          <div className="bg-rose-50 border border-rose-100 rounded-2xl p-6 text-center text-rose-800 shadow-xs">
            <AlertTriangle className="w-8 h-8 text-rose-600 mx-auto mb-3" />
            <h4 className="font-bold text-sm mb-1">Optimization Failed</h4>
            <p className="text-xs text-rose-700 mb-4">{optimizeError?.message || 'Failed to calculate optimal cart strategy.'}</p>
            <button
              onClick={handleOptimize}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-xl transition-colors"
            >
              Retry Optimization
            </button>
          </div>
        )}

        {/* Results display */}
        {optimizeResult && !isOptimizePending && (
          <div className="space-y-6 animate-fadeIn" data-testid="optimization-results">
            
            {/* Budget Warning Banner */}
            {budgetCap && parseFloat(budgetCap) > 0 && optimizeResult.total_cost > parseFloat(budgetCap) && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex gap-3 items-start shadow-sm animate-pulse">
                <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
                <div>
                  <h5 className="text-xs font-bold text-rose-900">Budget Exceeded</h5>
                  <p className="text-[10px] text-rose-700 mt-0.5 font-medium leading-relaxed">
                    Your optimized cart (₹{optimizeResult.total_cost.toFixed(2)}) is over your budget limit of ₹{budgetCap}.
                    Consider swapping the most expensive ingredients or buying smaller quantities.
                  </p>
                </div>
              </div>
            )}

            {/* Recommendation Strategy Header Card */}
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50/50 border border-emerald-100/80 rounded-2xl p-5 sm:p-6 shadow-2xs">
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <span className="bg-emerald-600 text-white text-[10px] font-bold tracking-wide uppercase px-2.5 py-1 rounded-full flex items-center gap-1 shadow-xs">
                  {optimizeResult.recommended_strategy === 'cheapest_split_cart' ? (
                    <>
                      <Split className="w-3 h-3" />
                      Cheapest Split Cart
                    </>
                  ) : optimizeResult.recommended_strategy === 'cheapest_single_store' ? (
                    <>
                      <Trophy className="w-3 h-3" />
                      Cheapest Single Store
                    </>
                  ) : (
                    <>
                      <Clock className="w-3 h-3" />
                      Fastest Available Cart
                    </>
                  )}
                </span>
                <span className="bg-white text-emerald-800 text-[10px] font-semibold px-2 py-0.5 rounded-md border border-emerald-100 shadow-2xs">
                  Freshness: {optimizeResult.price_freshness}
                </span>
              </div>

              <h4 className="text-xl font-black text-gray-900 flex items-baseline gap-1" data-testid="recommended-total">
                Total cost: <span className="text-emerald-700">{formatINR(optimizeResult.total_cost)}</span>
              </h4>

              {budgetCap && parseFloat(budgetCap) > 0 && optimizeResult.total_cost > parseFloat(budgetCap) && (
                <div className="mt-3 mb-1 p-3 bg-rose-50 border border-rose-200 rounded-xl flex gap-3 items-start shadow-sm animate-pulse">
                  <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
                  <div>
                    <h5 className="text-xs font-bold text-rose-900">Budget Exceeded</h5>
                    <p className="text-[10px] text-rose-700 mt-0.5 font-medium leading-relaxed">
                      Your optimized cart (₹{optimizeResult.total_cost.toFixed(2)}) is over your budget limit of ₹{budgetCap}.
                      Consider swapping the most expensive ingredients or buying smaller quantities.
                    </p>
                  </div>
                </div>
              )}

              {optimizeResult.estimated_savings > 0 && (
                <p className="text-xs text-emerald-800 font-semibold mt-1.5 flex items-center gap-1" data-testid="estimated-savings">
                  <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>You save {formatINR(optimizeResult.estimated_savings)} compared with the cheapest single-store option!</span>
                </p>
              )}

              <div className="mt-3 border-t border-emerald-100/60 pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <p className="text-xs text-gray-600 leading-relaxed italic flex-1">
                  "{optimizeResult.explanation}"
                </p>
                <a
                  href="https://www.swiggy.com/instamart"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-600 active:scale-95 text-white text-xs font-bold rounded-xl shadow-xs transition-all shrink-0 cursor-pointer"
                  data-testid="open-swiggy-web-basket"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open Basket on Swiggy Web</span>
                </a>
              </div>
            </div>

            {/* Store Breakdowns list */}
            {optimizeResult.store_baskets && optimizeResult.store_baskets.length > 0 && (
              <div className="space-y-4">
                <h5 className="text-xs font-bold text-gray-400 tracking-wider uppercase">Store Cart Summaries</h5>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {optimizeResult.store_baskets.map((storeBreakdown, idx) => {
                    const isBest = optimizeResult.recommended_cart.stores.some(s => s.store_name === storeBreakdown.store_name);
                    
                    return (
                      <PriceComparisonCard
                        key={idx}
                        store={{ 
                          id: storeBreakdown.store_id || String(idx), 
                          name: storeBreakdown.store_name,
                          is_demo_store: optimizeResult.data_source === 'demo',
                          store_type: 'Grocery Store',
                          city: 'Local',
                          created_at: new Date().toISOString()
                        }}
                        itemCost={storeBreakdown.subtotal}
                        deliveryFee={storeBreakdown.delivery_fee}
                        isLowestPrice={isBest}
                        isSelected={isBest}
                        items={storeBreakdown.selected_products}
                        isExpandedByDefault={isBest}
                      />
                    );
                  })}
                </div>
              </div>
            )}

            {/* Unfulfilled / Missing Ingredients */}
            {optimizeResult.missing_ingredients.length > 0 && (
              <div className="bg-rose-50/50 border border-rose-100 rounded-2xl p-5 space-y-3 shadow-2xs" data-testid="missing-ingredients">
                <h5 className="text-xs font-bold text-rose-800 uppercase flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-rose-600" />
                  Unfulfilled Recipe Ingredients ({optimizeResult.missing_ingredients.length})
                </h5>
                <div className="divide-y divide-rose-100/50">
                  {optimizeResult.missing_ingredients.map((missing, idx) => (
                    <div key={idx} className="py-2 first:pt-0 last:pb-0 flex items-start justify-between gap-3 text-xs">
                      <span className="font-bold text-rose-900">{missing.ingredient_name}</span>
                      <span className="text-[10px] text-rose-700 italic">{missing.reason}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Alternative Strategies */}
            {optimizeResult.alternatives.length > 0 && (
              <div className="border-t border-gray-100 pt-6 space-y-4">
                <h5 className="text-xs font-bold text-gray-400 tracking-wider uppercase">Alternative Cart Options</h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {optimizeResult.alternatives.map((alt, idx) => (
                    <div key={idx} className="border border-gray-100 hover:border-gray-200 rounded-xl p-4 space-y-2 bg-gray-50/30 transition-all">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-gray-800 capitalize">
                          {alt.strategy.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs font-black text-emerald-700">
                          {formatINR(alt.total_cost)}
                        </span>
                      </div>
                      <p className="text-[10px] text-gray-500 leading-relaxed italic">
                        "{alt.explanation}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Start Cooking Section */}
        {recipeId && (
          <div
            className="pt-6 border-t border-gray-100 flex flex-col sm:flex-row items-center justify-between gap-4 bg-emerald-50/60 -mx-6 sm:-mx-8 -mb-6 sm:-mb-8 p-6 rounded-b-3xl"
            data-testid="optimizer-start-cooking-section"
          >
            <div>
              <h4 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <ChefHat className="w-4.5 h-4.5 text-emerald-600" />
                Ready to cook this recipe?
              </h4>
              <p className="text-xs text-gray-600 mt-0.5">
                Ingredients reviewed. Jump straight to step-by-step guided cooking with timers and tips.
              </p>
            </div>
            <button
              type="button"
              onClick={handleStartCooking}
              disabled={startCookingMutation.isPending}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs transition-all flex items-center gap-2 shrink-0 cursor-pointer disabled:opacity-50"
              data-testid="optimizer-start-cooking-btn"
            >
              <ChefHat className="w-4 h-4 text-white" />
              <span>{activeSession && activeSession.status !== 'completed' ? 'Resume Cooking' : 'Start Cooking'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
