import React, { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ShoppingCart, RefreshCw, AlertTriangle, Info, Trophy, Split, Clock, CheckCircle } from 'lucide-react';
import { getRecipeIngredients } from '../../api/ingredients';
import { useCartOptimize } from '../../hooks/useCartOptimization';
import { formatINR } from '../../utils/currency';
import { CartIngredientRequest } from '../../types/cart';

export const CartOptimizationPanel: React.FC = () => {
  const [searchParams] = useSearchParams();
  const recipeId = searchParams.get('recipeId') || '';

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
  } = useCartOptimize();

  // Trigger optimization automatically when ingredients are fetched
  useEffect(() => {
    if (ingredientsData?.results && ingredientsData.results.length > 0) {
      const ingredientsList: CartIngredientRequest[] = ingredientsData.results.map((ing) => ({
        ingredient_name: ing.canonical_name,
        required_quantity: ing.quantity || 1.0,
        required_unit: ing.unit || 'piece',
      }));
      optimize({ ingredients: ingredientsList });
    }
  }, [ingredientsData, optimize]);

  const handleOptimize = () => {
    if (ingredientsData?.results && ingredientsData.results.length > 0) {
      const ingredientsList: CartIngredientRequest[] = ingredientsData.results.map((ing) => ({
        ingredient_name: ing.canonical_name,
        required_quantity: ing.quantity || 1.0,
        required_unit: ing.unit || 'piece',
      }));
      optimize({ ingredients: ingredientsList });
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
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-xs text-amber-800 flex items-start gap-2.5 shadow-xs">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Demonstration Notice:</span> All store prices and delivery fees are generated from fallback demonstration retail datasets in Indian Rupees (INR). Freshness metadata is strictly marked as cached.
        </div>
      </div>

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

              {optimizeResult.estimated_savings > 0 && (
                <p className="text-xs text-emerald-800 font-semibold mt-1.5 flex items-center gap-1" data-testid="estimated-savings">
                  <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>You save {formatINR(optimizeResult.estimated_savings)} compared with the cheapest single-store option!</span>
                </p>
              )}

              <p className="text-xs text-gray-600 leading-relaxed mt-3 border-t border-emerald-100/60 pt-3 italic">
                "{optimizeResult.explanation}"
              </p>
            </div>

            {/* Store Breakdowns list */}
            <div className="space-y-4">
              <h5 className="text-xs font-bold text-gray-400 tracking-wider uppercase">Stores Breakdown</h5>
              
              <div className="grid grid-cols-1 gap-6">
                {optimizeResult.recommended_cart.stores.map((storeBreakdown, idx) => (
                  <div key={idx} className="border border-gray-100 rounded-2xl overflow-hidden shadow-2xs bg-white">
                    {/* Store Title Bar */}
                    <div className="bg-gray-50 border-b border-gray-100 px-5 py-4 flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h6 className="font-extrabold text-sm text-gray-900" data-testid="store-name">
                          {storeBreakdown.store_name}
                        </h6>
                        <p className="text-[10px] text-gray-500 font-medium">
                          {storeBreakdown.complete ? '✓ Fulfills all required items' : '⚠️ Partial fulfillment'}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-black text-gray-900">
                          {formatINR(storeBreakdown.total)}
                        </span>
                        <p className="text-[9px] text-gray-400">
                          Incl. {formatINR(storeBreakdown.delivery_fee)} delivery
                        </p>
                      </div>
                    </div>

                    {/* Products list */}
                    <div className="p-5 divide-y divide-gray-50">
                      {storeBreakdown.selected_products.map((selProduct, pIdx) => (
                        <div key={pIdx} className="py-3 first:pt-0 last:pb-0 flex items-start justify-between gap-4 text-xs">
                          <div>
                            <p className="font-bold text-gray-900" data-testid="product-name">
                              {selProduct.product_name}
                            </p>
                            <p className="text-[10px] text-gray-500 mt-0.5">
                              Fulfills: <span className="font-medium text-gray-700">{selProduct.ingredient_name}</span> • Brand: {selProduct.brand || 'Generic'}
                            </p>
                            <p className="text-[10px] text-emerald-700 font-semibold mt-1">
                              {selProduct.packages_required} × {formatINR(selProduct.package_price)} ({selProduct.package_quantity} {selProduct.package_unit})
                            </p>
                          </div>
                          <span className="font-extrabold text-gray-900 shrink-0">
                            {formatINR(selProduct.line_cost)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

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
      </div>
    </div>
  );
};
