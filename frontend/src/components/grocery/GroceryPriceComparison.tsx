import React from 'react';
import { Store, ShoppingBag, RefreshCw, Trophy, Sparkles, Tag, AlertTriangle, TrendingDown } from 'lucide-react';
import { useGroceryCompare } from '../../hooks/useGrocery';
import { useGroceryFilters } from '../../hooks/useGroceryFilters';
import { GroceryFilterBar } from './GroceryFilterBar';
import { CompareGroceryParams } from '../../types';
import { formatINR, safeNumber } from '../../utils/currency';

export interface GroceryPriceComparisonProps extends CompareGroceryParams {
  className?: string;
  title?: string;
}

export const GroceryPriceComparison: React.FC<GroceryPriceComparisonProps> = ({
  ingredient,
  limit = 10,
  threshold,
  live_mode = false,
  className = '',
  title,
}) => {
  const { data, isPending, isError, error, refetch } = useGroceryCompare({
    ingredient,
    limit,
    threshold,
    live_mode,
  });

  const {
    selectedStore,
    setSelectedStore,
    sortOption,
    setSortOption,
    availableStores,
    hasComparableUnitPrices,
    filteredAndSortedResults,
    totalCount,
    filteredCount,
    resetFilters,
  } = useGroceryFilters({ results: data?.results });

  const [selectedProductId, setSelectedProductId] = React.useState<string | null>(null);
  const bestOptionId = data?.best_option?.product_id || null;

  React.useEffect(() => {
    if (bestOptionId) {
      setSelectedProductId(bestOptionId);
    } else if (data?.results && data.results.length > 0) {
      setSelectedProductId(data.results[0].product_id);
    } else {
      setSelectedProductId(null);
    }
  }, [bestOptionId, data?.results]);

  const cleanedQuery = ingredient ? ingredient.trim() : '';

  if (!cleanedQuery) {
    return null;
  }

  // 1. Loading State (Skeleton Grid)
  if (isPending) {
    return (
      <div className={`space-y-4 ${className}`} data-testid="grocery-compare-loading">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-emerald-100 rounded-full animate-pulse" />
          <div className="h-4 w-48 bg-gray-200 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((idx) => (
            <div
              key={idx}
              className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm space-y-4 animate-pulse"
            >
              <div className="h-4 w-28 bg-gray-200 rounded" />
              <div className="h-5 w-40 bg-gray-300 rounded" />
              <div className="h-8 w-24 bg-gray-200 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 2. Error State with Retry Action
  if (isError) {
    const errorMessage =
      (error as { message?: string })?.message || 'Failed to compare grocery store prices';

    return (
      <div
        className={`bg-rose-50/50 border border-rose-200 rounded-2xl p-6 text-center space-y-3 ${className}`}
        data-testid="grocery-compare-error"
      >
        <p className="text-sm font-medium text-rose-800">{errorMessage}</p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-xl transition-colors shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Comparison
        </button>
      </div>
    );
  }

  // 3. API Empty State (No Matches)
  if (!data || data.total_matches === 0 || !data.results || data.results.length === 0) {
    return (
      <div
        className={`bg-gray-50 border border-dashed border-gray-200 rounded-2xl p-6 text-center space-y-2 ${className}`}
        data-testid="grocery-compare-empty"
      >
        <ShoppingBag className="w-8 h-8 text-gray-400 mx-auto mb-1" />
        <h4 className="text-sm font-bold text-gray-700">No grocery price comparisons found</h4>
        <p className="text-xs text-gray-500 max-w-sm mx-auto">
          No store price listings available for &quot;{cleanedQuery}&quot;.
        </p>
      </div>
    );
  }

  // 4. Comparison Data Processing
  const isUnitPriceMode = data.comparison_mode === 'unit_price';

  return (
    <div className={`space-y-4 ${className}`} data-testid="grocery-compare-container">
      {/* Header & Comparison Mode Indicator */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <Store className="w-4 h-4 text-emerald-600" />
          {title || `Multi-Store Price Comparison (${data.total_matches} Offers)`}
        </h3>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 font-medium hidden sm:inline">
            Query: &quot;{data.canonical_name || data.ingredient_text}&quot;
          </span>
          {data.comparison_mode && (
            <span
              className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
                isUnitPriceMode
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-blue-50 text-blue-700 border border-blue-200'
              }`}
              data-testid="comparison-mode-badge"
            >
              <Sparkles className="w-3 h-3" />
              {isUnitPriceMode ? 'Normalized Unit Price' : 'Package Price'}
            </span>
          )}
          {data.data_source === 'live' || data.price_freshness === 'PROVIDER_LIVE' || data.price_freshness === 'LIVE' ? (
             <span className="inline-flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-xs" title="Prices fetched in real-time from store provider">
               <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> LIVE PRICE
             </span>
          ) : data.data_source === 'demo' || data.price_freshness === 'DEMO' ? (
             <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
               <span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> Demo Dataset
             </span>
          ) : (
             <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-gray-50 text-gray-600 border border-gray-200">
               <span className="w-1.5 h-1.5 rounded-full bg-gray-400" /> Cached
             </span>
          )}
          <button onClick={() => refetch()} className="text-xs text-blue-600 font-medium hover:text-blue-800 flex items-center gap-1 px-2 py-1 rounded bg-blue-50 hover:bg-blue-100 transition-colors">
             <RefreshCw className="w-3 h-3" /> Refresh Prices
          </button>
        </div>
      </div>

      {/* Filter & Sort Bar */}
      {availableStores.length > 0 && (
        <GroceryFilterBar
          selectedStore={selectedStore}
          onSelectStore={setSelectedStore}
          sortOption={sortOption}
          onSelectSort={setSortOption}
          availableStores={availableStores}
          hasComparableUnitPrices={hasComparableUnitPrices}
          totalCount={totalCount}
          filteredCount={filteredCount}
        />
      )}

      {/* Filter Empty State */}
      {filteredCount === 0 ? (
        <div
          className="bg-gray-50 border border-dashed border-gray-200 rounded-2xl p-6 text-center space-y-3"
          data-testid="grocery-compare-filter-empty"
        >
          <ShoppingBag className="w-8 h-8 text-gray-400 mx-auto mb-1" />
          <h4 className="text-sm font-bold text-gray-700">
            No products found for &quot;{selectedStore}&quot;
          </h4>
          <p className="text-xs text-gray-500 max-w-sm mx-auto">
            Try switching to another store or clear your store filter.
          </p>
          <button
            onClick={resetFilters}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl transition-colors shadow-sm"
          >
            Show All Stores
          </button>
        </div>
      ) : (
        /* Comparison Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAndSortedResults.map((product) => {
            const isBestValue = Boolean(bestOptionId && product.product_id === bestOptionId);
            const safePrice = product.price !== null && product.price !== undefined ? safeNumber(product.price) : null;
            
            // Standardized unit price preferred over raw base unit price
            const displayUnitPrice = product.standardized_unit_price !== null && product.standardized_unit_price !== undefined
              ? safeNumber(product.standardized_unit_price)
              : (product.unit_price !== null && product.unit_price !== undefined ? safeNumber(product.unit_price) : null);
            const displayUnit = product.standardized_unit || product.base_unit;

            const isSelected = selectedProductId === product.product_id;
            const cardStyle = isSelected
              ? 'border-emerald-500 ring-2 ring-emerald-500/20 bg-emerald-50/20 shadow-md cursor-pointer'
              : 'border-gray-200 bg-white shadow-sm hover:shadow-md hover:border-emerald-300 cursor-pointer';

            return (
              <div
                key={product.product_id}
                onClick={() => setSelectedProductId(product.product_id)}
                className={`rounded-2xl border transition-all p-5 flex flex-col justify-between ${cardStyle}`}
                data-testid={`grocery-compare-item-${product.product_id}`}
              >
                {/* Store & Rank Header */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    {/* Store Name Badge */}
                    <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg truncate ${
                      product.price_freshness === 'PROVIDER_LIVE' || data.data_source === 'live'
                        ? 'text-emerald-800 bg-emerald-50 border border-emerald-100'
                        : 'text-gray-800 bg-gray-100'
                    }`}>
                      <Store className="w-3.5 h-3.5 text-gray-600 shrink-0" />
                      {product.store_name || 'Store Listing'}
                      {(product.price_freshness === 'PROVIDER_LIVE' || data.data_source === 'live') && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" title="Live Store Product" />
                      )}
                    </span>

                    {/* Price Rank Badge */}
                    {product.price_rank && (
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded-md ${
                          product.price_rank === 1
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                        data-testid={`price-rank-${product.product_id}`}
                      >
                        #{product.price_rank} Price
                      </span>
                    )}
                  </div>

                  {/* Best Value Badge & Savings Pill */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                    {isBestValue && (
                      <span
                        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-amber-500 text-white shadow-xs"
                        data-testid="best-value-badge"
                      >
                        <Trophy className="w-3 h-3 text-amber-100 fill-amber-100" />
                        Best Value
                      </span>
                    )}
                    {product.savings_amount !== undefined && product.savings_amount !== null && product.savings_amount > 0 && (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200"
                        title={product.reference_product_name ? `Savings vs ${product.reference_product_name}` : 'Savings vs higher-priced offer'}
                        data-testid="savings-badge"
                      >
                        <TrendingDown className="w-3 h-3 text-emerald-600" />
                        Save {formatINR(product.savings_amount)} ({product.savings_percent}%)
                      </span>
                    )}
                  </div>

                  {/* Product Metadata */}
                  <div>
                    <h4 className="text-sm font-bold text-gray-900 leading-snug line-clamp-2">
                      {product.product_name}
                    </h4>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                      {product.brand && (
                        <span className="inline-flex items-center gap-1 font-medium">
                          <Tag className="w-3 h-3 text-gray-400" />
                          {product.brand}
                        </span>
                      )}
                      {product.package_quantity && product.package_unit && (
                        <span className="font-medium">
                          • {product.package_quantity} {product.package_unit}
                        </span>
                      )}
                    </div>
                    {/* Incomparable / Uncertainty Note */}
                    {product.is_comparable === false && product.comparison_notes && (
                      <div className="mt-1.5">
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md">
                          <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />
                          {product.comparison_notes}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Price Breakdown */}
                <div className="border-t border-gray-100 pt-3 mt-4 flex items-end justify-between">
                  {isUnitPriceMode && displayUnitPrice !== null && displayUnit ? (
                    /* Unit Price Highlight Mode */
                    <div>
                      <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide block">
                        Unit Price
                      </span>
                      <span className="text-lg font-extrabold text-emerald-700 tracking-tight">
                        {formatINR(displayUnitPrice)}/{displayUnit}
                      </span>
                      {safePrice !== null && (
                        <span className="text-xs text-gray-500 block">
                          Package: {formatINR(safePrice)}
                        </span>
                      )}
                    </div>
                  ) : (
                    /* Package Price Highlight Mode (Default) */
                    <div>
                      <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide block">
                        Package Price
                      </span>
                      {safePrice !== null ? (
                        <span className="text-xl font-extrabold text-gray-900 tracking-tight">
                          {formatINR(safePrice)}
                        </span>
                      ) : (
                        <span className="text-sm font-medium text-gray-400">Price unavailable</span>
                      )}
                      {displayUnitPrice !== null && displayUnit && (
                        <span className="text-xs font-semibold text-emerald-700 block mt-0.5">
                          {formatINR(displayUnitPrice)}/{displayUnit}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Similarity Match Badge */}
                  {product.similarity_score > 0 && (
                    <span className="text-[11px] font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded border border-gray-100">
                      {Math.round(product.similarity_score * 100)}% match
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
