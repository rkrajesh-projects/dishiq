import React from 'react';
import { ShoppingBag, RefreshCw } from 'lucide-react';
import { useGroceryMatch } from '../../hooks/useGrocery';
import { useGroceryFilters } from '../../hooks/useGroceryFilters';
import { GroceryMatchCard } from './GroceryMatchCard';
import { GroceryFilterBar } from './GroceryFilterBar';
import { MatchGroceryParams } from '../../types';

export interface GroceryMatchListProps extends MatchGroceryParams {
  className?: string;
  title?: string;
}

export const GroceryMatchList: React.FC<GroceryMatchListProps> = ({
  ingredient,
  limit = 10,
  threshold,
  live_mode = false,
  className = '',
  title,
}) => {
  const { data, isPending, isError, error, refetch } = useGroceryMatch({
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

  // 1. Loading State (Skeleton Cards)
  if (isPending) {
    return (
      <div className={`space-y-3 ${className}`} data-testid="grocery-match-loading">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-emerald-100 rounded-full animate-pulse" />
          <div className="h-4 w-40 bg-gray-200 rounded animate-pulse" />
        </div>
        {[1, 2].map((idx) => (
          <div
            key={idx}
            className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm space-y-3 animate-pulse"
          >
            <div className="flex justify-between items-start">
              <div className="space-y-2 flex-1">
                <div className="h-4 w-28 bg-gray-200 rounded" />
                <div className="h-5 w-48 bg-gray-300 rounded" />
              </div>
              <div className="h-6 w-16 bg-gray-200 rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // 2. Error State with Retry Button
  if (isError) {
    const errorMessage =
      (error as { message?: string })?.message || 'Failed to search grocery products';

    return (
      <div
        className={`bg-rose-50/50 border border-rose-200 rounded-2xl p-6 text-center space-y-3 ${className}`}
        data-testid="grocery-match-error"
      >
        <p className="text-sm font-medium text-rose-800">{errorMessage}</p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-xl transition-colors shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Search
        </button>
      </div>
    );
  }

  // 3. API Empty State (No Matches Returned by Backend)
  if (!data || data.total_matches === 0 || !data.results || data.results.length === 0) {
    return (
      <div
        className={`bg-gray-50 border border-dashed border-gray-200 rounded-2xl p-6 text-center space-y-2 ${className}`}
        data-testid="grocery-match-empty"
      >
        <ShoppingBag className="w-8 h-8 text-gray-400 mx-auto mb-1" />
        <h4 className="text-sm font-bold text-gray-700">No matching grocery products found</h4>
        <p className="text-xs text-gray-500 max-w-sm mx-auto">
          No store products matched &quot;{cleanedQuery}&quot; above the similarity threshold.
        </p>
      </div>
    );
  }

  // 4. Successful Matches & Filter Controls

  return (
    <div className={`space-y-4 ${className}`} data-testid="grocery-match-list">
      {/* Header Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <ShoppingBag className="w-4 h-4 text-emerald-600" />
          {title || `Matched Grocery Products (${data.total_matches})`}
        </h3>
        <div className="flex items-center gap-2">
          {data.data_source === 'live' || data.price_freshness === 'PROVIDER_LIVE' ? (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live Store Data
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
              Demo Data
            </span>
          )}
          <span className="text-xs text-gray-500 font-medium">
            Query: &quot;{data.canonical_name || data.ingredient_text}&quot;
          </span>
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
          totalCount={totalCount}
          filteredCount={filteredCount}
        />
      )}

      {/* Filter Empty State */}
      {filteredCount === 0 ? (
        <div
          className="bg-gray-50 border border-dashed border-gray-200 rounded-2xl p-6 text-center space-y-3"
          data-testid="grocery-filter-empty"
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
        /* Cards List */
        <div className="space-y-3">
          {filteredAndSortedResults.map((product) => (
            <GroceryMatchCard
              key={product.product_id}
              match={product}
              isBestValue={Boolean(bestOptionId && product.product_id === bestOptionId)}
              isSelected={product.product_id === selectedProductId}
              onSelect={() => setSelectedProductId(product.product_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
