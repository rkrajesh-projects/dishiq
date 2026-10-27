import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Filter, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { SectionTitle } from '../components/common/SectionTitle';
import { SearchBar } from '../components/common/SearchBar';
import { RecipeCard } from '../components/recipe/RecipeCard';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { searchRecipes, getRecipeFilters } from '../api/recipes';

export const RecipeSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // State from URL
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [dietaryType, setDietaryType] = useState(searchParams.get('dietary_type') || 'All');
  const [cuisine, setCuisine] = useState(searchParams.get('cuisine') || 'All');
  const [maxTime, setMaxTime] = useState(searchParams.get('max_time') || 'All');
  const [minRating, setMinRating] = useState(searchParams.get('min_rating') || 'All');
  const [sortBy, setSortBy] = useState(searchParams.get('sort_by') || 'recommended');
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1);

  // Sync state when URL changes
  useEffect(() => {
    setQuery(searchParams.get('q') || '');
    setDietaryType(searchParams.get('dietary_type') || 'All');
    setCuisine(searchParams.get('cuisine') || 'All');
    setMaxTime(searchParams.get('max_time') || 'All');
    setMinRating(searchParams.get('min_rating') || 'All');
    setSortBy(searchParams.get('sort_by') || 'recommended');
    setPage(Number(searchParams.get('page')) || 1);
  }, [searchParams]);

  // Update URL function
  const updateURL = (params: Record<string, any>) => {
    const newParams = new URLSearchParams();
    if (params.q) newParams.set('q', params.q);
    if (params.dietary_type && params.dietary_type !== 'All') newParams.set('dietary_type', params.dietary_type);
    if (params.cuisine && params.cuisine !== 'All') newParams.set('cuisine', params.cuisine);
    if (params.max_time && params.max_time !== 'All') newParams.set('max_time', params.max_time);
    if (params.min_rating && params.min_rating !== 'All') newParams.set('min_rating', params.min_rating);
    if (params.sort_by && params.sort_by !== 'recommended') newParams.set('sort_by', params.sort_by);
    if (params.page > 1) newParams.set('page', params.page.toString());
    setSearchParams(newParams);
  };

  // Fetch Filters
  const { data: filtersData } = useQuery({
    queryKey: ['recipe-filters'],
    queryFn: getRecipeFilters,
    staleTime: Infinity,
  });

  const cuisines = ['All', ...(filtersData?.cuisines || [])];
  const dietaryTypes = ['All', ...(filtersData?.dietary_types || [])];
  
  const timeOptions = [
    { label: 'Any time', value: 'All' },
    { label: 'Under 15 min', value: '15' },
    { label: '15-30 min', value: '30' },
    { label: '30-60 min', value: '60' },
    { label: '60+ min', value: '1440' },
  ];

  const ratingOptions = [
    { label: 'Any rating', value: 'All' },
    { label: '4+ ?', value: '4' },
    { label: '3+ ?', value: '3' },
  ];

  const sortOptions = [
    { label: 'Recommended', value: 'recommended' },
    { label: 'Rating: High -> Low', value: 'rating_desc' },
    { label: 'Cooking Time: Low -> High', value: 'time_asc' },
    { label: 'Name: A -> Z', value: 'name_asc' },
  ];

  // Fetch Recipes
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['recipe-search', query, dietaryType, cuisine, maxTime, minRating, sortBy, page],
    queryFn: () => searchRecipes({
      q: query || undefined,
      dietary_type: dietaryType !== 'All' ? dietaryType : undefined,
      cuisine: cuisine !== 'All' ? cuisine : undefined,
      max_time: maxTime !== 'All' ? Number(maxTime) : undefined,
      min_rating: minRating !== 'All' ? Number(minRating) : undefined,
      sort_by: sortBy !== 'recommended' ? sortBy : undefined,
      page,
      page_size: 15
    }),
  });

  const handleSearchSubmit = (newQuery: string) => {
    setQuery(newQuery);
    setPage(1);
    updateURL({ q: newQuery, dietary_type: dietaryType, cuisine, max_time: maxTime, min_rating: minRating, sort_by: sortBy, page: 1 });
  };

  const handleFilterChange = (key: string, value: string) => {
    const newParams = { q: query, dietary_type: dietaryType, cuisine, max_time: maxTime, min_rating: minRating, sort_by: sortBy, page: 1 } as any;
    newParams[key] = value;
    
    if (key === 'dietary_type') setDietaryType(value);
    if (key === 'cuisine') setCuisine(value);
    if (key === 'max_time') setMaxTime(value);
    if (key === 'min_rating') setMinRating(value);
    if (key === 'sort_by') setSortBy(value);
    setPage(1);

    updateURL(newParams);
  };

  const removeFilter = (key: string) => {
    handleFilterChange(key, key === 'q' ? '' : 'All');
  };

  const clearFilters = () => {
    setQuery('');
    setDietaryType('All');
    setCuisine('All');
    setMaxTime('All');
    setMinRating('All');
    setSortBy('recommended');
    setPage(1);
    setSearchParams({});
  };

  // Active filters count
  const activeFilters = [];
  if (query) activeFilters.push({ key: 'q', label: "" });
  if (cuisine !== 'All') activeFilters.push({ key: 'cuisine', label: cuisine });
  if (dietaryType !== 'All') activeFilters.push({ key: 'dietary_type', label: dietaryType });
  if (maxTime !== 'All') activeFilters.push({ key: 'max_time', label: timeOptions.find(o => o.value === maxTime)?.label || 'Time' });
  if (minRating !== 'All') activeFilters.push({ key: 'min_rating', label: ratingOptions.find(o => o.value === minRating)?.label || 'Rating' });

  return (
    <PageContainer>
      <div className="flex flex-col lg:flex-row gap-8">
        
        {/* Sidebar Filters */}
        <aside className="w-full lg:w-64 shrink-0 space-y-6">
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Filter className="w-5 h-5 text-emerald-600" />
              Filters
            </h2>
            
            <div className="space-y-6">
              {/* Cuisine */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Cuisine</label>
                <select
                  value={cuisine}
                  onChange={(e) => handleFilterChange('cuisine', e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-xl focus:ring-emerald-500 focus:border-emerald-500 block p-2.5"
                >
                  {cuisines.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              {/* Diet */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Dietary Preference</label>
                <select
                  value={dietaryType}
                  onChange={(e) => handleFilterChange('dietary_type', e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-xl focus:ring-emerald-500 focus:border-emerald-500 block p-2.5"
                >
                  {dietaryTypes.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>

              {/* Cooking Time */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Cooking Time</label>
                <select
                  value={maxTime}
                  onChange={(e) => handleFilterChange('max_time', e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-xl focus:ring-emerald-500 focus:border-emerald-500 block p-2.5"
                >
                  {timeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>

              {/* Rating */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Rating</label>
                <select
                  value={minRating}
                  onChange={(e) => handleFilterChange('min_rating', e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-xl focus:ring-emerald-500 focus:border-emerald-500 block p-2.5"
                >
                  {ratingOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          <SectionTitle title="Recipe Finder" subtitle="Discover recipes based on your exact preferences" />
          
          <div className="mt-4 mb-6 flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="w-full sm:max-w-md">
              <SearchBar 
                initialValue={query}
                onSearch={handleSearchSubmit} 
                placeholder="Search recipes..." 
              />
            </div>
            
            <div className="w-full sm:w-auto shrink-0 flex items-center gap-2">
              <label className="text-sm text-gray-500 font-medium">Sort by:</label>
              <select
                value={sortBy}
                onChange={(e) => handleFilterChange('sort_by', e.target.value)}
                className="bg-white border border-gray-200 text-gray-700 text-sm rounded-xl focus:ring-emerald-500 focus:border-emerald-500 block p-2 pr-8 shadow-sm"
              >
                {sortOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          {/* Active Filters */}
          {activeFilters.length > 0 && (
            <div className="mb-6 flex flex-wrap items-center gap-2">
              <span className="text-xs text-gray-500 font-medium mr-1">Active:</span>
              {activeFilters.map(f => (
                <span key={f.key} className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full border border-emerald-100">
                  {f.label}
                  <button onClick={() => removeFilter(f.key)} className="hover:bg-emerald-200 p-0.5 rounded-full transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              <button 
                onClick={clearFilters}
                className="text-xs text-gray-500 hover:text-gray-900 font-medium ml-2 underline underline-offset-2"
              >
                Clear Filters
              </button>
            </div>
          )}

          {isPending ? (
            <LoadingState message="Searching recipes..." />
          ) : isError ? (
            <ErrorState 
              title="Search failed" 
              message="Failed to load recipes. Please try again." 
              onRetry={() => refetch()} 
            />
          ) : !data || data.items.length === 0 ? (
            <EmptyState
              title="No recipes found."
              description="Try changing your filters."
              actionText="Clear Filters"
              onAction={clearFilters}
            />
          ) : (
            <>
              <div className="mb-4 text-sm text-gray-500 font-medium">
                Found {data.total} {data.total === 1 ? 'recipe' : 'recipes'}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {data.items.map((recipe) => (
                  <RecipeCard key={recipe.id} recipe={recipe} />
                ))}
              </div>
              
              {/* Pagination */}
              {data.total_pages > 1 && (
                <div className="mt-10 flex items-center justify-center gap-4 border-t border-gray-100 pt-6">
                  <button
                    onClick={() => {
                      const newPage = Math.max(page - 1, 1);
                      setPage(newPage);
                      updateURL({ q: query, dietary_type: dietaryType, cuisine, max_time: maxTime, min_rating: minRating, sort_by: sortBy, page: newPage });
                    }}
                    disabled={page === 1}
                    className="flex items-center justify-center w-10 h-10 rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm bg-white"
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <span className="text-sm font-medium text-gray-700 bg-gray-50 px-4 py-2 rounded-xl border border-gray-100">
                    Page {data.page} of {data.total_pages}
                  </span>
                  <button
                    onClick={() => {
                      const newPage = Math.min(page + 1, data.total_pages);
                      setPage(newPage);
                      updateURL({ q: query, dietary_type: dietaryType, cuisine, max_time: maxTime, min_rating: minRating, sort_by: sortBy, page: newPage });
                    }}
                    disabled={page >= data.total_pages}
                    className="flex items-center justify-center w-10 h-10 rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm bg-white"
                    aria-label="Next page"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </PageContainer>
  );
};
