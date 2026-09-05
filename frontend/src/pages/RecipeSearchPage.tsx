import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PageContainer } from '../components/common/PageContainer';
import { SectionTitle } from '../components/common/SectionTitle';
import { SearchBar } from '../components/common/SearchBar';
import { RecipeCard } from '../components/recipe/RecipeCard';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { searchRecipes } from '../api/recipes';

export const RecipeSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const initialDiet = searchParams.get('dietary_type') || '';
  const initialCuisine = searchParams.get('cuisine') || '';

  const [query, setQuery] = useState(initialQuery);
  const [dietaryType, setDietaryType] = useState(initialDiet);
  const [cuisine, setCuisine] = useState(initialCuisine);

  useEffect(() => {
    setQuery(searchParams.get('q') || '');
    setDietaryType(searchParams.get('dietary_type') || '');
    setCuisine(searchParams.get('cuisine') || '');
  }, [searchParams]);

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['recipe-search', query, dietaryType, cuisine],
    queryFn: () => searchRecipes({ q: query, dietary_type: dietaryType, cuisine: cuisine, page_size: 15 }),
  });

  const handleSearchSubmit = (newQuery: string) => {
    setQuery(newQuery);
    const params: Record<string, string> = {};
    if (newQuery) params.q = newQuery;
    if (dietaryType) params.dietary_type = dietaryType;
    if (cuisine) params.cuisine = cuisine;
    setSearchParams(params);
  };

  const handleDietFilter = (diet: string) => {
    const updated = dietaryType === diet ? '' : diet;
    setDietaryType(updated);
    const params: Record<string, string> = {};
    if (query) params.q = query;
    if (updated) params.dietary_type = updated;
    if (cuisine) params.cuisine = cuisine;
    setSearchParams(params);
  };

  return (
    <PageContainer>
      <SectionTitle
        title="Recipe Search & Smart Ranking"
        subtitle="Ranked by TF-IDF relevance, dietary preferences, and cooking time"
      />

      <div className="mb-6 max-w-2xl">
        <SearchBar onSearch={handleSearchSubmit} placeholder="Search recipes by dish name, ingredient..." />
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap items-center gap-2 mb-8">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Filter Diet:</span>
        {['Vegetarian', 'Vegan', 'Non-Vegetarian'].map((diet) => (
          <button
            key={diet}
            onClick={() => handleDietFilter(diet)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all border ${
              dietaryType === diet
                ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                : 'bg-white text-gray-700 border-gray-200 hover:border-emerald-300'
            }`}
          >
            {diet}
          </button>
        ))}
      </div>

      {/* States Handling */}
      {isPending ? (
        <LoadingState message="Ranking recipes with TF-IDF engine..." />
      ) : isError ? (
        <ErrorState
          title="Search Failed"
          message="Unable to fetch recipe recommendations. Verify backend service is online."
          onRetry={refetch}
        />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No recipes found"
          description={`No matching recipes found for "${query || 'your filters'}". Try broadening your search.`}
          actionText="Clear Filters"
          onAction={() => {
            setQuery('');
            setDietaryType('');
            setCuisine('');
            setSearchParams({});
          }}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.items.map((recipe) => (
            <RecipeCard key={recipe.id} recipe={recipe} />
          ))}
        </div>
      )}
    </PageContainer>
  );
};
