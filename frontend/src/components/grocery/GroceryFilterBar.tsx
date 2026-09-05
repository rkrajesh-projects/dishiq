import React from 'react';
import { Filter, ArrowUpDown } from 'lucide-react';
import { SortOption } from '../../hooks/useGroceryFilters';

export interface GroceryFilterBarProps {
  selectedStore: string;
  onSelectStore: (store: string) => void;
  sortOption: SortOption;
  onSelectSort: (sort: SortOption) => void;
  availableStores: string[];
  totalCount: number;
  filteredCount: number;
  className?: string;
}

export const GroceryFilterBar: React.FC<GroceryFilterBarProps> = ({
  selectedStore,
  onSelectStore,
  sortOption,
  onSelectSort,
  availableStores,
  totalCount,
  filteredCount,
  className = '',
}) => {
  return (
    <div
      className={`bg-gray-50 border border-gray-100 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${className}`}
      data-testid="grocery-filter-bar"
    >
      {/* Left: Filter Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {/* Store Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500 shrink-0" />
          <label htmlFor="grocery-store-filter" className="sr-only">
            Filter by store
          </label>
          <select
            id="grocery-store-filter"
            aria-label="Filter by store"
            value={selectedStore}
            onChange={(e) => onSelectStore(e.target.value)}
            className="bg-white border border-gray-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all cursor-pointer"
          >
            <option value="all">All Stores</option>
            {availableStores.map((store) => (
              <option key={store} value={store}>
                {store}
              </option>
            ))}
          </select>
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-2">
          <ArrowUpDown className="w-4 h-4 text-gray-500 shrink-0" />
          <label htmlFor="grocery-sort-select" className="sr-only">
            Sort products
          </label>
          <select
            id="grocery-sort-select"
            aria-label="Sort products"
            value={sortOption}
            onChange={(e) => onSelectSort(e.target.value as SortOption)}
            className="bg-white border border-gray-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all cursor-pointer"
          >
            <option value="default">Default Order</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="similarity_desc">Similarity: High to Low</option>
            <option value="similarity_asc">Similarity: Low to High</option>
          </select>
        </div>
      </div>

      {/* Right: Result Count Indicator */}
      <div className="text-xs font-medium text-gray-500 shrink-0" data-testid="grocery-result-count">
        Showing {filteredCount} of {totalCount} products
      </div>
    </div>
  );
};
