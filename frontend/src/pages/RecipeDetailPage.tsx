import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Clock, Users, Star, ArrowLeft, ShoppingBag, ChefHat, IndianRupee } from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { NormalizedIngredientList } from '../components/recipe/NormalizedIngredientList';
import { Button } from '../components/common/Button';
import { formatINR } from '../utils/currency';
import { getRecipe } from '../api/recipes';
import { useStartCooking } from '../hooks/useCooking';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';

export const RecipeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const startCookingMutation = useStartCooking();

  const {
    data: recipe,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['recipe', id],
    queryFn: () => getRecipe(id!),
    enabled: Boolean(id),
  });

  const handleStartCooking = () => {
    if (!id) return;
    startCookingMutation.mutate(
      { recipe_id: id },
      {
        onSuccess: (session) => {
          navigate(`/cooking/${session.id}`);
        },
      }
    );
  };

  if (isLoading) {
    return <LoadingState message="Loading recipe details..." />;
  }

  if (isError || !recipe) {
    const errMsg = (error as { message?: string })?.message ?? 'Recipe details could not be loaded.';
    return (
      <ErrorState
        title="Could not load recipe"
        message={errMsg}
        onRetry={() => refetch()}
      />
    );
  }

  const estimatedCost = 105; // Kept demo cost as per layout
  const servings = recipe.servings || 4;
  const costPerServing = estimatedCost / servings;

  return (
    <PageContainer>
      <div className="mb-6">
        <Link to="/recipes" className="inline-flex items-center gap-1 text-xs font-semibold text-gray-500 hover:text-emerald-600 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to recipes</span>
        </Link>
      </div>

      <div className="bg-white rounded-3xl border border-orange-100/60 p-6 sm:p-8 shadow-sm mb-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-emerald-50 text-emerald-700 text-xs font-semibold px-2.5 py-1 rounded-full">
                {recipe.cuisine} Cuisine
              </span>
              <span className="bg-amber-50 text-amber-700 text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1">
                <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                {recipe.average_rating || '4.5'}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900">
              {recipe.name}
            </h1>
            <p className="text-sm text-gray-600 mt-2">
              {recipe.description}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link to={`/grocery?recipeId=${recipe.id}`}>
              <Button variant="accent" icon={<ShoppingBag className="w-4 h-4" />}>
                Compare Prices
              </Button>
            </Link>
            <Button
              variant="primary"
              icon={<ChefHat className="w-4 h-4" />}
              onClick={handleStartCooking}
              isLoading={startCookingMutation.isPending}
            >
              Start Cooking
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-6 border-t border-b border-gray-100 py-4 text-xs font-medium text-gray-600">
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-orange-500" />
            <span>Prep: {recipe.preparation_minutes || 10} mins • Cook: {recipe.cooking_minutes || 15} mins</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Users className="w-4 h-4 text-gray-400" />
            <span>Serves {servings}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700 font-semibold bg-emerald-50 px-3 py-1 rounded-full">
            <IndianRupee className="w-3.5 h-3.5" />
            <span>Est. Cost: {formatINR(estimatedCost)} ({formatINR(estimatedCost / servings)}/serving)</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Ingredients panel ──────────────────────────────────────── */}
        <div className="lg:col-span-1">
          <NormalizedIngredientList recipeId={recipe.id} />
        </div>

        {/* ── Instructions panel ────────────────────────────────────── */}
        <div className="lg:col-span-2 bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Step-by-Step Instructions</h2>
          <ol className="space-y-4">
            {recipe.instructions.map((step, idx) => (
              <li key={idx} className="flex items-start gap-3 text-sm text-gray-700">
                <span className="w-6 h-6 rounded-full bg-emerald-50 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                  {idx + 1}
                </span>
                <span className="leading-relaxed">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </PageContainer>
  );
};
