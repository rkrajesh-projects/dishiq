import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  Users,
  Star,
  ArrowLeft,
  ShoppingBag,
  ChefHat,
  IndianRupee,
  ExternalLink,
  ShieldCheck,
  MapPin,
  Flame,
  CheckSquare,
} from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { NormalizedIngredientList } from '../components/recipe/NormalizedIngredientList';
import { Button } from '../components/common/Button';
import { formatINR } from '../utils/currency';
import { getRecipe } from '../api/recipes';
import { useStartCooking, useActiveCookingSession } from '../hooks/useCooking';
import { usePantryItems } from '../hooks/usePantry';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';

export const RecipeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const startCookingMutation = useStartCooking();
  const { data: activeSession } = useActiveCookingSession(id);
  const { data: pantryItems } = usePantryItems();

  const pantryIngredients = React.useMemo(() => {
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

  const baseServings = recipe?.servings || 4;
  const [servings, setServings] = useState<number>(baseServings);

  useEffect(() => {
    if (recipe?.servings) {
      setServings(recipe.servings);
    }
  }, [recipe?.servings]);

  const scaleFactor = baseServings > 0 ? servings / baseServings : 1;
  const baseEstimatedCost = 105;
  const totalEstimatedCost = Math.round(baseEstimatedCost * scaleFactor);
  const costPerServing = baseServings > 0 ? baseEstimatedCost / baseServings : 0;

  const handleStartCooking = () => {
    if (!id) return;
    if (activeSession && activeSession.status !== 'completed') {
      navigate(`/cooking/${activeSession.id}`);
      return;
    }
    startCookingMutation.mutate(
      { recipe_id: id, servings: servings },
      {
        onSuccess: (session) => {
          navigate(`/cooking/${session.id}`);
        },
      }
    );
  };

  const handleOpenPreparation = () => {
    if (!id) return;
    if (activeSession && activeSession.status !== 'completed') {
      navigate(`/cooking/${activeSession.id}?mode=prep`);
      return;
    }
    startCookingMutation.mutate(
      { recipe_id: id, servings: servings },
      {
        onSuccess: (session) => {
          navigate(`/cooking/${session.id}?mode=prep`);
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
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="bg-emerald-50 text-emerald-700 text-xs font-semibold px-2.5 py-1 rounded-full">
                {recipe.cuisine} Cuisine
              </span>
              {recipe.dietary_type && (
                <span className="bg-blue-50 text-blue-700 text-xs font-semibold px-2.5 py-1 rounded-full">
                  {recipe.dietary_type}
                </span>
              )}
              {recipe.region && (
                <span className="bg-purple-50 text-purple-700 text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-purple-600" />
                  {recipe.region}
                </span>
              )}
              <span className="bg-amber-50 text-amber-700 text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1">
                <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                {recipe.average_rating || '4.5'}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900">
              {recipe.name}
            </h1>
            {recipe.original_name && recipe.original_name !== recipe.name && (
              <p className="text-xs text-gray-400 italic mt-0.5">
                Also known as: {recipe.original_name}
              </p>
            )}
            <p className="text-sm text-gray-600 mt-2 max-w-2xl">
              {recipe.description}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <Link to={`/grocery?recipeId=${recipe.id}&servings=${servings}&baseServings=${baseServings}`}>
              <Button variant="accent" icon={<ShoppingBag className="w-4 h-4" />}>
                Compare Prices
              </Button>
            </Link>
            <Button
              variant="outline"
              icon={<CheckSquare className="w-4 h-4 text-emerald-600" />}
              onClick={handleOpenPreparation}
              isLoading={startCookingMutation.isPending}
            >
              Prep Checklist
            </Button>
            {activeSession && activeSession.status !== 'completed' ? (
              <Button
                variant="primary"
                icon={<ChefHat className="w-4 h-4" />}
                onClick={handleStartCooking}
              >
                Resume Cooking (Step {activeSession.current_step + 1})
              </Button>
            ) : (
              <Button
                variant="primary"
                icon={<ChefHat className="w-4 h-4" />}
                onClick={handleStartCooking}
                isLoading={startCookingMutation.isPending}
              >
                Start Cooking
              </Button>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 sm:gap-6 border-t border-b border-gray-100 py-4 text-xs font-medium text-gray-600">
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-orange-500" />
            <span>Prep: {recipe.preparation_minutes || 10} mins • Cook: {recipe.cooking_minutes || 15} mins</span>
          </div>

          {/* Servings Stepper */}
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 px-3 py-1 rounded-full" data-testid="servings-stepper">
            <Users className="w-4 h-4 text-gray-500" />
            <span className="font-semibold text-gray-800">Servings:</span>
            <button
              type="button"
              onClick={() => setServings((s) => Math.max(1, s - 1))}
              disabled={servings <= 1}
              className="w-5 h-5 rounded-full bg-white border border-gray-300 flex items-center justify-center font-bold text-gray-700 hover:bg-gray-100 disabled:opacity-40 transition-colors"
              aria-label="Decrease servings"
              data-testid="decrease-servings"
            >
              -
            </button>
            <span className="font-bold text-gray-900 min-w-5 text-center" data-testid="serving-count">{servings}</span>
            <button
              type="button"
              onClick={() => setServings((s) => Math.min(24, s + 1))}
              disabled={servings >= 24}
              className="w-5 h-5 rounded-full bg-white border border-gray-300 flex items-center justify-center font-bold text-gray-700 hover:bg-gray-100 disabled:opacity-40 transition-colors"
              aria-label="Increase servings"
              data-testid="increase-servings"
            >
              +
            </button>
            {servings !== baseServings && (
              <button
                type="button"
                onClick={() => setServings(baseServings)}
                className="text-[11px] text-emerald-700 hover:underline font-semibold ml-1"
                data-testid="reset-servings"
              >
                Reset ({baseServings})
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 text-emerald-700 font-semibold bg-emerald-50 px-3 py-1 rounded-full">
            <IndianRupee className="w-3.5 h-3.5" />
            <span>Est. Cost: {formatINR(totalEstimatedCost)} ({formatINR(costPerServing)}/serving)</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Ingredients panel ──────────────────────────────────────── */}
        <div className="lg:col-span-1 space-y-6">
          <NormalizedIngredientList
            recipeId={recipe.id}
            scaleFactor={scaleFactor}
            pantryIngredients={pantryIngredients}
          />

          {/* Provenance and Attribution Card */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm text-xs text-gray-600 space-y-3" data-testid="recipe-provenance">
            <h4 className="font-bold text-gray-900 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Recipe Attribution & Provenance
            </h4>
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <span className="text-gray-400">Source:</span>
                <span className="font-medium text-gray-800">{recipe.source_name || 'DishIQ Kitchen'}</span>
              </div>
              {recipe.author && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Author:</span>
                  <span className="font-medium text-gray-800">{recipe.author}</span>
                </div>
              )}
              {recipe.state && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Origin State:</span>
                  <span className="font-medium text-gray-800">{recipe.state}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-400">Status:</span>
                <span className={`font-semibold ${recipe.verification_status === 'VERIFIED' ? 'text-emerald-700' : 'text-gray-600'}`}>
                  {recipe.verification_status || 'Curated'}
                </span>
              </div>
              {recipe.source_license && (
                <div className="flex justify-between">
                  <span className="text-gray-400">License:</span>
                  <span className="text-gray-600 font-mono text-[11px]">{recipe.source_license}</span>
                </div>
              )}
            </div>
            {recipe.source_url && (
              <div className="pt-2 border-t border-gray-50">
                <a
                  href={recipe.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-700 hover:text-emerald-800 font-medium inline-flex items-center gap-1"
                >
                  <span>View Original Recipe</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}
          </div>
        </div>

        {/* ── Instructions panel ────────────────────────────────────── */}
        <div className="lg:col-span-2 bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Step-by-Step Instructions</h2>

          {recipe.structured_instructions && recipe.structured_instructions.length > 0 ? (
            <ol className="space-y-5" data-testid="structured-instructions">
              {recipe.structured_instructions.map((step) => (
                <li key={step.step_number} className="flex items-start gap-3 text-sm text-gray-700">
                  <span className="w-6 h-6 rounded-full bg-emerald-50 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                    {step.step_number}
                  </span>
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {step.action_type && (
                        <span className="bg-gray-100 text-gray-600 text-[10px] uppercase font-bold px-2 py-0.5 rounded">
                          {step.action_type}
                        </span>
                      )}
                      {step.timing_minutes && (
                        <span className="text-xs text-orange-600 font-medium flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {step.timing_minutes} mins
                        </span>
                      )}
                      {step.temperature && (
                        <span className="text-xs text-rose-600 font-medium flex items-center gap-1">
                          <Flame className="w-3 h-3" />
                          {step.temperature}
                        </span>
                      )}
                    </div>
                    <p className="leading-relaxed">{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <ol className="space-y-4" data-testid="legacy-instructions">
              {recipe.instructions.map((step, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm text-gray-700">
                  <span className="w-6 h-6 rounded-full bg-emerald-50 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span className="leading-relaxed">{step}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </PageContainer>
  );
};
