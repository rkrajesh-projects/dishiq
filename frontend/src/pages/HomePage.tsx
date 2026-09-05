import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Compass, ShoppingCart, ChefHat, CheckCircle2, AlertCircle } from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { SearchBar } from '../components/common/SearchBar';
import { Button } from '../components/common/Button';
import { useActiveCookingSession } from '../hooks/useCooking';
import { useQuery } from '@tanstack/react-query';
import { getRecipe } from '../api/recipes';
import { useProfile } from '../hooks/useProfile';
import { usePantryItems } from '../hooks/usePantry';
import { useRecommendations } from '../hooks/useRecommendations';
import { RecipeCard } from '../components/recipe/RecipeCard';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { data: activeSession, isLoading: sessionLoading, error: sessionError } = useActiveCookingSession();

  const recipeId = activeSession?.recipe_id;
  const { data: recipe, isLoading: recipeLoading, error: recipeError } = useQuery({
    queryKey: ['recipe', recipeId],
    queryFn: () => getRecipe(recipeId!),
    enabled: Boolean(recipeId),
  });

  const { data: profile } = useProfile();
  const { data: pantryItems } = usePantryItems();

  const pantryIngredients = React.useMemo(() => {
    return pantryItems?.map(item => item.canonical_name) || [];
  }, [pantryItems]);

  const recPayload = React.useMemo(() => ({
    dietary_type: profile?.preference?.dietary_type || 'None',
    pantry_ingredients: pantryIngredients,
    limit: 3
  }), [profile, pantryIngredients]);

  const {
    data: recData,
    isLoading: recLoading,
    isError: recError,
    error: recErrorDetail
  } = useRecommendations(recPayload);

  const popularDishes = [
    'Paneer Butter Masala',
    'Masala Dosa',
    'Veg Fried Rice',
    'Chicken Biryani',
    'Dal Tadka',
    'Palak Paneer',
  ];

  const handleSearch = (query: string) => {
    if (query.trim()) {
      navigate(`/recipes?q=${encodeURIComponent(query)}`);
    } else {
      navigate('/recipes');
    }
  };

  return (
    <PageContainer className="flex flex-col gap-12 py-10">
      
      {/* Hero Section */}
      <section className="text-center max-w-3xl mx-auto flex flex-col items-center gap-6 pt-4">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-orange-50 text-orange-700 text-xs font-semibold border border-orange-200 shadow-sm">
          <Sparkles className="w-4 h-4 text-orange-500" />
          <span>AI Kitchen Assistant & Smart Memory</span>
        </div>

        <h1 className="text-3xl sm:text-5xl font-extrabold text-gray-900 tracking-tight leading-tight">
          What would you like to cook?
        </h1>

        <p className="text-base text-gray-600 max-w-xl">
          Discover recipes, compare real grocery prices across stores, manage your pantry inventory, and enjoy guided cooking.
        </p>

        {/* Large Search Bar */}
        <div className="w-full max-w-2xl mt-2">
          <SearchBar onSearch={handleSearch} large />
        </div>

        {/* Popular Dishes Chips */}
        <div className="flex flex-wrap items-center justify-center gap-2 mt-2">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Popular:</span>
          {popularDishes.map((dish) => (
            <button
              key={dish}
              onClick={() => handleSearch(dish)}
              className="px-3 py-1.5 rounded-full text-xs font-medium bg-white text-gray-700 hover:bg-emerald-50 hover:text-emerald-700 border border-gray-200 hover:border-emerald-300 transition-all shadow-sm"
            >
              {dish}
            </button>
          ))}
        </div>
      </section>

      {/* Resume Cooking Section */}
      {(sessionLoading || (recipeId && recipeLoading)) && (
        <section className="bg-gray-50 border border-gray-100 rounded-3xl p-6 shadow-sm max-w-2xl mx-auto w-full -mt-4 text-center">
          <p className="text-xs text-gray-500 animate-pulse">Loading active cooking session...</p>
        </section>
      )}

      {(sessionError || (recipeId && recipeError)) && (
        <section className="bg-red-50 border border-red-100 rounded-3xl p-6 shadow-sm max-w-2xl mx-auto w-full -mt-4 text-center">
          <p className="text-xs text-red-600">Failed to load active cooking session.</p>
        </section>
      )}

      {!sessionLoading && !sessionError && activeSession && recipe && (
        <section className="bg-orange-50/50 border border-orange-100 rounded-3xl p-6 shadow-sm max-w-2xl mx-auto w-full -mt-4 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold text-orange-700">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500"></span>
                </span>
                <span>🍳 Continue Cooking</span>
              </div>
              <h2 className="text-lg font-bold text-gray-900 capitalize">
                {recipe.name}
              </h2>
              <p className="text-xs text-gray-600">
                You are currently on Step {activeSession.current_step + 1} of {recipe.instructions?.length || 1}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/recipes/${recipe.id}`)}
                aria-label={`View recipe details for ${recipe.name}`}
              >
                View Recipe
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate(`/cooking/${activeSession.id}`)}
                aria-label={`Resume cooking ${recipe.name} from step ${activeSession.current_step + 1}`}
              >
                Resume Cooking
              </Button>
            </div>
          </div>
        </section>
      )}

      {/* Three-Step Explanation */}
      <section className="mt-8">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-gray-900">How DishIQ Works</h2>
          <p className="text-sm text-gray-600 mt-1">From recipe craving to economical home cooking in three simple steps</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Step 1 */}
          <div className="bg-white rounded-2xl border border-orange-100/60 p-6 shadow-sm flex flex-col items-center text-center relative overflow-hidden group hover:shadow-md transition-all">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Compass className="w-6 h-6" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-emerald-600 mb-1">Step 1</span>
            <h3 className="text-lg font-bold text-gray-900 mb-2">1. Discover Recipes</h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              Find recipes semantic-ranked by your family preferences, dietary limits, and active pantry stock.
            </p>
          </div>

          {/* Step 2 */}
          <div className="bg-white rounded-2xl border border-orange-100/60 p-6 shadow-sm flex flex-col items-center text-center relative overflow-hidden group hover:shadow-md transition-all">
            <div className="w-12 h-12 rounded-2xl bg-orange-50 text-orange-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <ShoppingCart className="w-6 h-6" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-orange-600 mb-1">Step 2</span>
            <h3 className="text-lg font-bold text-gray-900 mb-2">2. Compare Grocery Prices</h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              Automatically match missing ingredients across demonstration grocery stores to build the lowest cost shopping cart.
            </p>
          </div>

          {/* Step 3 */}
          <div className="bg-white rounded-2xl border border-orange-100/60 p-6 shadow-sm flex flex-col items-center text-center relative overflow-hidden group hover:shadow-md transition-all">
            <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <ChefHat className="w-6 h-6" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-amber-600 mb-1">Step 3</span>
            <h3 className="text-lg font-bold text-gray-900 mb-2">3. Cook with Guidance</h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              Follow step-by-step interactive cooking mode with live timers while AI Kitchen Memory learns your preferences.
            </p>
          </div>

        </div>
      </section>

      {/* Proactive Recommendation Spotlight */}
      <section className="bg-gradient-to-r from-emerald-950 to-emerald-800 text-white rounded-3xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="max-w-xl space-y-2">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-700/60 text-emerald-200 text-xs font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>AI Kitchen Memory Spotlight</span>
            </div>
            
            {recLoading && (
              <p className="text-xs text-emerald-200 animate-pulse">Analyzing kitchen profile and pantry stock...</p>
            )}

            {recError && (
              <>
                <h3 className="text-xl font-bold text-white">
                  "You already have tomatoes, onions and eggs..."
                </h3>
                <p className="text-xs text-emerald-100/90 leading-relaxed">
                  Based on your family's vegetarian preference and weekly budget, DishIQ recommends Paneer Bhurji tonight. Buying only paneer and coriander completes the meal!
                </p>
              </>
            )}

            {!recLoading && !recError && recData && recData.recommendations.length === 0 && (
              <>
                <h3 className="text-xl font-bold text-white">
                  "What shall we cook today?"
                </h3>
                <p className="text-xs text-emerald-100/90 leading-relaxed">
                  Add items to your pantry or specify dietary limits in your profile to let DishIQ's personalization engine tailor suggestions for you!
                </p>
              </>
            )}

            {!recLoading && !recError && recData && recData.recommendations.length > 0 && (
              (() => {
                const spotlight = recData.recommendations[0];
                return (
                  <>
                    <h3 className="text-xl font-bold text-white capitalize">
                      Suggested Tonight: {spotlight.name}
                    </h3>
                    <p className="text-xs text-emerald-100/90 leading-relaxed">
                      {spotlight.explanations.join(' • ')}. This fits your {spotlight.dietary_type} preference perfectly.
                    </p>
                    <div className="pt-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => navigate(`/recipes/${spotlight.id}`)}
                        className="text-emerald-950 hover:bg-emerald-50 font-bold border-none"
                      >
                        Start Cooking →
                      </Button>
                    </div>
                  </>
                );
              })()
            )}
          </div>
        </div>
      </section>

      {/* AI Personalized Recommendations Grid */}
      <section className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Personalized Recommendations</h2>
          <p className="text-xs text-gray-500 mt-1">Suggested based on your dietary preference and pantry ingredients</p>
        </div>
        
        {recLoading && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((n) => (
              <div key={n} className="bg-white border border-gray-100 rounded-3xl p-6 h-60 animate-pulse flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                  <div className="h-6 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                </div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        )}

        {recError && (
          <div className="flex items-center gap-2 text-xs text-red-700 bg-red-50 rounded-xl px-4 py-3 border border-red-100">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{recErrorDetail?.message || 'Failed to load personalized recommendations.'}</span>
          </div>
        )}

        {!recLoading && !recError && recData && recData.recommendations.length === 0 && (
          <div className="bg-white border border-dashed border-gray-200 rounded-3xl p-8 text-center text-gray-500 text-xs">
            No personalized recommendations found. Try adding items to your pantry or updating your dietary preferences!
          </div>
        )}

        {!recLoading && !recError && recData && recData.recommendations.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {recData.recommendations.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </div>
        )}
      </section>
    </PageContainer>
  );
};
