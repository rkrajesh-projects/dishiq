import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Calendar,
  ShoppingBag,
  Plus,
  Trash2,
  CheckSquare,
  Square,
  RefreshCw,
  Search,
  AlertTriangle,
  ChevronRight,
  Package,
  Layers,
  ChefHat,
  Info,
  Check,
} from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { SectionTitle } from '../components/common/SectionTitle';
import { Button } from '../components/common/Button';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import {
  getMealPlans,
  createMealPlan,
  addMealToPlan,
  updatePlannedMeal,
  removePlannedMeal,
  generateShoppingList,
  getShoppingList,
  getShoppingLists,
  createShoppingList,
  addManualShoppingItem,
  updateShoppingListItem,
  deleteShoppingListItem,
  getShoppingListGroceryComparison,
} from '../api/mealPlanApi';
import { searchRecipes } from '../api/recipes';
import { useStartCooking } from '../hooks/useCooking';
import {
  MealPlan,
  ShoppingList,
  ShoppingListItem,
  ShoppingListGroceryComparison,
} from '../types/meal_plan';
import { RecommendedRecipe } from '../types';

export const MealPlanPage: React.FC = () => {
  const navigate = useNavigate();
  const startCookingMutation = useStartCooking();

  // Navigation Tabs: 'plan' | 'shopping_list' | 'grocery_comparison'
  const [activeTab, setActiveTab] = useState<'plan' | 'shopping_list' | 'grocery_comparison'>('plan');

  // Meal Plan State
  const [plans, setPlans] = useState<MealPlan[]>([]);
  const [activePlan, setActivePlan] = useState<MealPlan | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New Plan Modal / Form State
  const [showNewPlanModal, setShowNewPlanModal] = useState<boolean>(false);
  const [newPlanName, setNewPlanName] = useState<string>('');

  // Add Recipe Modal State
  const [showAddRecipeModal, setShowAddRecipeModal] = useState<boolean>(false);
  const [recipeSearchQuery, setRecipeSearchQuery] = useState<string>('');
  const [recipeSearchResults, setRecipeSearchResults] = useState<RecommendedRecipe[]>([]);
  const [searchingRecipes, setSearchingRecipes] = useState<boolean>(false);
  const [selectedRecipe, setSelectedRecipe] = useState<RecommendedRecipe | null>(null);
  const [newMealServings, setNewMealServings] = useState<number>(2);
  const [newMealType, setNewMealType] = useState<string>('dinner');
  const [newMealDate, setNewMealDate] = useState<string>('');

  // Shopping List State
  const [shoppingList, setShoppingList] = useState<ShoppingList | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(false);
  const [deductPantry, setDeductPantry] = useState<boolean>(true);
  const [manualItemName, setManualItemName] = useState<string>('');
  const [manualItemQty, setManualItemQty] = useState<number>(1);
  const [manualItemUnit, setManualItemUnit] = useState<string>('piece');
  const [addingManualItem, setAddingManualItem] = useState<boolean>(false);

  // Grocery Comparison State
  const [groceryComparison, setGroceryComparison] = useState<ShoppingListGroceryComparison | null>(null);
  const [loadingGrocery, setLoadingGrocery] = useState<boolean>(false);

  // ---------------------------------------------------------------------------
  // Data Fetching
  // ---------------------------------------------------------------------------

  const loadPlans = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getMealPlans();
      setPlans(data);
      if (data.length > 0) {
        if (!activePlan) {
          setActivePlan(data[0]);
        }
      } else {
        // If no meal plans exist yet, check if any standalone shopping lists exist
        try {
          const lists = await getShoppingLists();
          if (lists.length > 0) {
            setShoppingList(lists[0]);
          }
        } catch {
          // ignore
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load meal plans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlans();
  }, []);

  // When active plan changes, attempt to load its shopping list if one exists
  useEffect(() => {
    if (activePlan) {
      loadShoppingListForPlan(activePlan.id);
    }
  }, [activePlan?.id]);

  const loadShoppingListForPlan = async (planId: string) => {
    try {
      setLoadingList(true);
      // Try generating / fetching
      const list = await generateShoppingList(planId, { deduct_pantry: deductPantry });
      setShoppingList(list);
    } catch {
      // If generate fails, check if any shopping list exists for this plan or user
      try {
        const lists = await getShoppingLists();
        const found = lists.find((l) => l.meal_plan_id === planId) || (lists.length > 0 ? lists[0] : null);
        setShoppingList(found);
      } catch {
        setShoppingList(null);
      }
    } finally {
      setLoadingList(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Meal Plan Handlers
  // ---------------------------------------------------------------------------

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlanName.trim()) return;

    try {
      const created = await createMealPlan({ name: newPlanName.trim() });
      setPlans((prev) => [created, ...prev]);
      setActivePlan(created);
      setNewPlanName('');
      setShowNewPlanModal(false);
    } catch (err: any) {
      alert(err?.message || 'Failed to create plan');
    }
  };

  const handleSearchRecipes = async (q: string) => {
    setRecipeSearchQuery(q);
    if (!q.trim()) {
      setRecipeSearchResults([]);
      return;
    }
    setSearchingRecipes(true);
    try {
      const res = await searchRecipes({ q, page_size: 10 });
      setRecipeSearchResults(res.items || []);
    } catch {
      setRecipeSearchResults([]);
    } finally {
      setSearchingRecipes(false);
    }
  };

  const handleAddMeal = async () => {
    if (!activePlan || !selectedRecipe) return;

    try {
      const newMeal = await addMealToPlan(activePlan.id, {
        recipe_id: selectedRecipe.id,
        meal_type: newMealType,
        servings: newMealServings,
        meal_date: newMealDate ? newMealDate : undefined,
      });

      // Update active plan state
      setActivePlan((prev) =>
        prev ? { ...prev, meals: [...prev.meals, newMeal] } : null
      );

      // Reset modal state
      setSelectedRecipe(null);
      setRecipeSearchQuery('');
      setRecipeSearchResults([]);
      setShowAddRecipeModal(false);

      // Auto-refresh shopping list
      if (activePlan) {
        loadShoppingListForPlan(activePlan.id);
      }
    } catch (err: any) {
      alert(err?.message || 'Failed to add meal');
    }
  };

  const handleUpdateServings = async (mealId: string, currentServings: number, delta: number) => {
    if (!activePlan) return;
    const nextServings = currentServings + delta;
    if (nextServings <= 0) return;

    try {
      const updated = await updatePlannedMeal(activePlan.id, mealId, {
        servings: nextServings,
      });

      setActivePlan((prev) =>
        prev
          ? {
              ...prev,
              meals: prev.meals.map((m) => (m.id === mealId ? updated : m)),
            }
          : null
      );

      // Auto-refresh shopping list
      loadShoppingListForPlan(activePlan.id);
    } catch (err: any) {
      alert(err?.message || 'Failed to update servings');
    }
  };

  const handleRemoveMeal = async (mealId: string) => {
    if (!activePlan) return;
    if (!confirm('Remove this planned meal from your schedule?')) return;

    try {
      await removePlannedMeal(activePlan.id, mealId);
      setActivePlan((prev) =>
        prev
          ? {
              ...prev,
              meals: prev.meals.filter((m) => m.id !== mealId),
            }
          : null
      );

      // Refresh list
      loadShoppingListForPlan(activePlan.id);
    } catch (err: any) {
      alert(err?.message || 'Failed to remove meal');
    }
  };

  // ---------------------------------------------------------------------------
  // Shopping List Handlers
  // ---------------------------------------------------------------------------

  const handleRefreshShoppingList = async () => {
    if (!activePlan) return;
    setLoadingList(true);
    try {
      const list = await generateShoppingList(activePlan.id, { deduct_pantry: deductPantry });
      setShoppingList(list);
    } catch (err: any) {
      alert(err?.message || 'Failed to refresh shopping list');
    } finally {
      setLoadingList(false);
    }
  };

  const handleToggleObtained = async (item: ShoppingListItem) => {
    if (!shoppingList) return;
    try {
      const updated = await updateShoppingListItem(shoppingList.id, item.id, {
        is_obtained: !item.is_obtained,
      });
      setShoppingList((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((it) => (it.id === item.id ? updated : it)),
              obtained_items: updated.is_obtained
                ? prev.obtained_items + 1
                : prev.obtained_items - 1,
            }
          : null
      );
    } catch (err: any) {
      alert(err?.message || 'Failed to update item status');
    }
  };

  const handleAddManualItem = async (e: React.FormEvent) => {
    e.preventDefault();
    const itemName = manualItemName.trim();
    if (!itemName) return;

    setAddingManualItem(true);
    try {
      let currentList = shoppingList;

      // If shopping list is not yet initialized in state:
      if (!currentList) {
        if (activePlan) {
          currentList = await generateShoppingList(activePlan.id, { deduct_pantry: deductPantry });
        } else {
          // Check if any meal plans exist
          const existingPlans = await getMealPlans();
          if (existingPlans.length > 0) {
            setActivePlan(existingPlans[0]);
            setPlans(existingPlans);
            currentList = await generateShoppingList(existingPlans[0].id, { deduct_pantry: deductPantry });
          } else {
            // Check if any shopping list exists
            const existingLists = await getShoppingLists();
            if (existingLists.length > 0) {
              currentList = existingLists[0];
            } else {
              // Create a default meal plan and generate its shopping list
              const today = new Date();
              const startDate = today.toISOString().split('T')[0];
              const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
              const defaultPlan = await createMealPlan({
                name: 'Weekly Meal Plan',
                start_date: startDate,
                end_date: nextWeek,
              });
              setActivePlan(defaultPlan);
              setPlans([defaultPlan]);
              currentList = await generateShoppingList(defaultPlan.id, { deduct_pantry: deductPantry });
            }
          }
        }
        setShoppingList(currentList);
      }

      if (!currentList) {
        alert('Could not initialize shopping list. Please try again.');
        return;
      }

      const created = await addManualShoppingItem(currentList.id, {
        ingredient_name: itemName,
        quantity: manualItemQty,
        unit: manualItemUnit,
      });

      setShoppingList((prev) =>
        prev
          ? {
              ...prev,
              items: [...prev.items, created],
              total_items: prev.total_items + 1,
            }
          : {
              ...currentList!,
              items: [created],
              total_items: 1,
              obtained_items: 0,
            }
      );
      setManualItemName('');
      setManualItemQty(1);
    } catch (err: any) {
      alert(err?.message || 'Failed to add manual item');
    } finally {
      setAddingManualItem(false);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!shoppingList) return;
    try {
      await deleteShoppingListItem(shoppingList.id, itemId);
      setShoppingList((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.filter((it) => it.id !== itemId),
              total_items: prev.total_items - 1,
            }
          : null
      );
    } catch (err: any) {
      alert(err?.message || 'Failed to delete item');
    }
  };

  // ---------------------------------------------------------------------------
  // Grocery Comparison Handlers
  // ---------------------------------------------------------------------------

  const handleLoadGroceryComparison = async () => {
    if (!shoppingList) return;
    setLoadingGrocery(true);
    try {
      const comp = await getShoppingListGroceryComparison(shoppingList.id);
      setGroceryComparison(comp);
      setActiveTab('grocery_comparison');
    } catch (err: any) {
      alert(err?.message || 'Failed to fetch grocery price comparison');
    } finally {
      setLoadingGrocery(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <PageContainer>
        <LoadingState message="Loading meal plans & shopping lists..." />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <div className="py-12">
          <ErrorState title="Meal Planning Error" message={error} onRetry={loadPlans} />
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="py-8 space-y-6">
        
        {/* Header & Plan Selector */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-orange-100/60 pb-6">
          <div>
            <SectionTitle
              title="Meal Planning & Shopping Lists"
              subtitle="Design your menu, adjust servings, consolidate ingredients, and verify live grocery availability."
            />
          </div>

          <div className="flex items-center gap-3">
            {plans.length > 0 && (
              <select
                value={activePlan?.id || ''}
                onChange={(e) => {
                  const sel = plans.find((p) => p.id === e.target.value);
                  if (sel) setActivePlan(sel);
                }}
                className="px-3 py-2 text-sm border border-emerald-200 rounded-xl bg-white shadow-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-600"
              >
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            )}

            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowNewPlanModal(true)}
              className="flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>New Plan</span>
            </Button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-gray-200 pb-2">
          <button
            onClick={() => setActiveTab('plan')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center gap-2 ${
              activeTab === 'plan'
                ? 'bg-emerald-700 text-white shadow-md shadow-emerald-700/20'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <Calendar className="w-4 h-4" />
            <span>Planned Meals</span>
            {activePlan && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-emerald-800 text-emerald-100">
                {activePlan.meals.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('shopping_list')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center gap-2 ${
              activeTab === 'shopping_list'
                ? 'bg-emerald-700 text-white shadow-md shadow-emerald-700/20'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <ShoppingBag className="w-4 h-4" />
            <span>Shopping List</span>
            {shoppingList && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-emerald-800 text-emerald-100">
                {shoppingList.obtained_items}/{shoppingList.total_items}
              </span>
            )}
          </button>

          <button
            onClick={() => {
              if (!groceryComparison) {
                handleLoadGroceryComparison();
              } else {
                setActiveTab('grocery_comparison');
              }
            }}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center gap-2 ${
              activeTab === 'grocery_comparison'
                ? 'bg-emerald-700 text-white shadow-md shadow-emerald-700/20'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Grocery Availability & Cost</span>
          </button>
        </div>

        {/* =================================================================== */}
        {/* TAB 1: PLANNED MEALS */}
        {/* =================================================================== */}
        {activeTab === 'plan' && (
          <div className="space-y-6">
            {!activePlan ? (
              <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 p-8">
                <ChefHat className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-gray-900">No Meal Plan Selected</h3>
                <p className="text-sm text-gray-500 max-w-md mx-auto mt-1 mb-6">
                  Create a meal plan to start adding your favorite recipes, adjust serving counts, and generate a smart grocery list.
                </p>
                <Button variant="primary" onClick={() => setShowNewPlanModal(true)}>
                  Create Your First Plan
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-emerald-50/60 border border-emerald-100 rounded-2xl p-4">
                  <div>
                    <h2 className="font-bold text-emerald-950 text-lg">{activePlan.name}</h2>
                    <p className="text-xs text-emerald-800">
                      {activePlan.meals.length} recipe{activePlan.meals.length === 1 ? '' : 's'} scheduled
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAddRecipeModal(true)}
                      className="flex items-center gap-1.5"
                    >
                      <Plus className="w-4 h-4 text-emerald-700" />
                      <span>Add Recipe</span>
                    </Button>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => {
                        handleRefreshShoppingList();
                        setActiveTab('shopping_list');
                      }}
                      className="flex items-center gap-1.5"
                    >
                      <ShoppingBag className="w-4 h-4" />
                      <span>View Consolidated List</span>
                    </Button>
                  </div>
                </div>

                {activePlan.meals.length === 0 ? (
                  <div className="text-center py-12 bg-white rounded-2xl border border-dashed border-gray-200 p-8">
                    <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-gray-700">No recipes scheduled in this plan yet.</p>
                    <p className="text-xs text-gray-400 mt-1 mb-4">Add dishes from the DishIQ catalogue to begin.</p>
                    <Button variant="primary" size="sm" onClick={() => setShowAddRecipeModal(true)}>
                      Browse Recipes
                    </Button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {activePlan.meals.map((meal) => (
                      <div
                        key={meal.id}
                        className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-orange-100 text-orange-800">
                              {meal.meal_type}
                            </span>
                            <button
                              onClick={() => handleRemoveMeal(meal.id)}
                              className="text-gray-400 hover:text-red-600 transition-colors"
                              title="Remove meal"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>

                          <h3 className="font-bold text-base text-gray-900 mt-2 line-clamp-1">
                            {meal.recipe_name}
                          </h3>
                          {meal.recipe_cuisine && (
                            <p className="text-xs text-gray-500">{meal.recipe_cuisine} Cuisine</p>
                          )}
                          {meal.meal_date && (
                            <p className="text-xs text-emerald-700 font-medium mt-1">
                              📅 {meal.meal_date}
                            </p>
                          )}
                        </div>

                        {/* Serving Count Controls */}
                        <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
                          <span className="text-xs font-semibold text-gray-600">Servings</span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleUpdateServings(meal.id, meal.servings, -1)}
                              disabled={meal.servings <= 1}
                              className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-40 text-gray-700 font-bold flex items-center justify-center transition-colors"
                            >
                              -
                            </button>
                            <span className="w-8 text-center text-sm font-bold text-gray-900">
                              {meal.servings}
                            </span>
                            <button
                              onClick={() => handleUpdateServings(meal.id, meal.servings, 1)}
                              className="w-7 h-7 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold flex items-center justify-center transition-colors"
                            >
                              +
                            </button>
                          </div>
                        </div>

                        {/* Quick Action: View Recipe and Cook Dish */}
                        <div className="mt-3 pt-2 border-t border-gray-50 flex items-center justify-between text-xs">
                          <Link
                            to={`/recipes/${meal.recipe_id}`}
                            className="font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
                          >
                            View Recipe
                          </Link>
                          <button
                            type="button"
                            onClick={() => {
                              startCookingMutation.mutate(
                                { recipe_id: meal.recipe_id, servings: meal.servings },
                                {
                                  onSuccess: (session) => {
                                    navigate(`/cooking/${session.id}`);
                                  },
                                }
                              );
                            }}
                            className="font-bold text-orange-600 hover:text-orange-700 flex items-center gap-1 transition-colors"
                          >
                            <ChefHat className="w-3.5 h-3.5" />
                            <span>Cook ({meal.servings})</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* =================================================================== */}
        {/* TAB 2: CONSOLIDATED SHOPPING LIST */}
        {/* =================================================================== */}
        {activeTab === 'shopping_list' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-cream-50 border border-orange-100 rounded-2xl p-4">
              <div>
                <h2 className="font-bold text-gray-900 text-base">
                  {shoppingList ? shoppingList.name : 'Consolidated Shopping List'}
                </h2>
                <p className="text-xs text-gray-500">
                  Quantities scaled from scheduled servings and consolidated across compatible ingredients.
                </p>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-gray-700">
                  <input
                    type="checkbox"
                    checked={deductPantry}
                    onChange={(e) => {
                      setDeductPantry(e.target.checked);
                      if (activePlan) {
                        generateShoppingList(activePlan.id, { deduct_pantry: e.target.checked }).then(
                          (list) => setShoppingList(list)
                        );
                      }
                    }}
                    className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                  />
                  <span>Deduct Available Pantry</span>
                </label>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRefreshShoppingList}
                  disabled={loadingList}
                  className="flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingList ? 'animate-spin' : ''}`} />
                  <span>Refresh List</span>
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleLoadGroceryComparison}
                  disabled={!shoppingList || shoppingList.items.length === 0 || loadingGrocery}
                  className="flex items-center gap-1.5"
                >
                  <ShoppingBag className="w-3.5 h-3.5" />
                  <span>Compare Prices</span>
                </Button>
              </div>
            </div>

            {/* Manual Item Add Bar */}
            <form
              onSubmit={handleAddManualItem}
              className="flex flex-wrap items-center gap-2 bg-white p-3 rounded-2xl border border-gray-100 shadow-sm"
            >
              <input
                type="text"
                placeholder="Add extra item (e.g. Olive oil, Dish soap)..."
                value={manualItemName}
                onChange={(e) => setManualItemName(e.target.value)}
                className="flex-grow min-w-[200px] px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
              />
              <input
                type="number"
                min="0.1"
                step="any"
                value={manualItemQty}
                onChange={(e) => setManualItemQty(parseFloat(e.target.value) || 1)}
                className="w-20 px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
              />
              <input
                type="text"
                placeholder="Unit (piece, bottle, g)"
                value={manualItemUnit}
                onChange={(e) => setManualItemUnit(e.target.value)}
                className="w-28 px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
              />
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={addingManualItem || !manualItemName.trim()}
              >
                {addingManualItem ? 'Adding...' : 'Add Item'}
              </Button>
            </form>

            {/* Shopping List Items Table / Cards */}
            {!shoppingList || shoppingList.items.length === 0 ? (
              <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 p-8">
                <ShoppingBag className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-700">No items on this shopping list.</p>
                <p className="text-xs text-gray-400 mt-1">Schedule meals in the plan or add items manually.</p>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100">
                {shoppingList.items.map((item) => (
                  <div
                    key={item.id}
                    className={`p-4 flex items-center justify-between gap-4 transition-colors ${
                      item.is_obtained ? 'bg-gray-50/70 text-gray-400' : 'hover:bg-cream-50/40'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleToggleObtained(item)}
                        data-testid={`toggle-obtained-${item.id}`}
                        aria-label={`Toggle ${item.ingredient_name}`}
                        className="text-emerald-700 hover:scale-105 transition-transform"
                      >
                        {item.is_obtained ? (
                          <CheckSquare className="w-5 h-5 text-emerald-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>

                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`font-semibold text-sm ${
                              item.is_obtained ? 'line-through text-gray-400' : 'text-gray-900'
                            }`}
                          >
                            {item.ingredient_name}
                          </span>
                          {item.is_manual && (
                            <span className="px-1.5 py-0.2 text-[9px] font-bold rounded uppercase bg-blue-100 text-blue-800">
                              Manual
                            </span>
                          )}
                        </div>

                        {/* Source recipe badges */}
                        {item.source_recipes && item.source_recipes.length > 0 && (
                          <p className="text-[11px] text-gray-400 mt-0.5">
                            From:{' '}
                            {item.source_recipes
                              .map((s) => `${s.recipe_name} (${s.quantity} ${s.unit})`)
                              .join(', ')}
                          </p>
                        )}

                        {/* Pantry note badge */}
                        {item.notes && (
                          <p className="text-[11px] text-emerald-700 font-medium mt-0.5 flex items-center gap-1">
                            <Info className="w-3 h-3" />
                            <span>{item.notes}</span>
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className="text-sm font-bold text-gray-900">
                          {item.effective_quantity} {item.unit}
                        </span>
                        {item.pantry_quantity > 0 && (
                          <p className="text-[10px] text-emerald-700">
                            Pantry: {item.pantry_quantity} {item.unit}
                          </p>
                        )}
                      </div>

                      <button
                        onClick={() => handleDeleteItem(item.id)}
                        className="text-gray-300 hover:text-red-500 transition-colors"
                        title="Delete item"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* =================================================================== */}
        {/* TAB 3: GROCERY PRICE & AVAILABILITY */}
        {/* =================================================================== */}
        {activeTab === 'grocery_comparison' && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-100 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Grocery Price & Product Matching</h2>
                  <p className="text-xs text-gray-500">
                    Matches your shopping list against live Swiggy Instamart and catalogue options.
                  </p>
                </div>

                {groceryComparison?.total_estimated_cost && (
                  <div className="text-right">
                    <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">
                      Estimated Cost
                    </span>
                    <p className="text-2xl font-bold text-emerald-700">
                      ₹{groceryComparison.total_estimated_cost.toFixed(2)}
                    </p>
                  </div>
                )}
              </div>

              {loadingGrocery ? (
                <LoadingState message="Matching grocery items with available stores..." />
              ) : !groceryComparison ? (
                <div className="py-12 text-center">
                  <p className="text-sm text-gray-500">No comparison loaded yet.</p>
                  <Button variant="primary" size="sm" onClick={handleLoadGroceryComparison} className="mt-4">
                    Fetch Grocery Prices
                  </Button>
                </div>
              ) : (
                <div className="mt-6 space-y-4">
                  {/* Notes / Disclosure Alert */}
                  {groceryComparison.notes && (
                    <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                      <span>{groceryComparison.notes}</span>
                    </div>
                  )}

                  {/* Item Matches */}
                  <div className="divide-y divide-gray-100 border border-gray-100 rounded-xl overflow-hidden">
                    {groceryComparison.items.map((match) => (
                      <div key={match.item_id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-gray-900">
                              {match.ingredient_name}
                            </span>
                            <span className="text-xs text-gray-400">
                              ({match.quantity_needed} {match.unit} needed)
                            </span>
                          </div>

                          {match.best_product ? (
                            <div className="mt-1 flex items-center gap-2 text-xs">
                              <span className="text-gray-800 font-medium">
                                Matched: {match.best_product.product_name}
                              </span>
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                                {match.best_product.store_name}
                              </span>
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-gray-100 text-gray-600">
                                {match.best_product.price_freshness || 'CACHED'}
                              </span>
                            </div>
                          ) : (
                            <p className="text-xs text-amber-600 font-medium mt-1">
                              {match.missing_reason || 'No compatible in-stock product found'}
                            </p>
                          )}
                        </div>

                        {match.best_product && (
                          <div className="text-right">
                            <span className="text-sm font-bold text-gray-900">
                              ₹{parseFloat(match.best_product.price).toFixed(2)}
                            </span>
                            {match.best_product.standardized_unit_price && (
                              <p className="text-[10px] text-gray-400">
                                ₹{match.best_product.standardized_unit_price.toFixed(2)} / {match.best_product.standardized_unit}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* =================================================================== */}
      {/* MODAL: NEW MEAL PLAN */}
      {/* =================================================================== */}
      {showNewPlanModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 w-full max-w-md shadow-2xl space-y-4">
            <h3 className="font-bold text-lg text-gray-900">Create New Meal Plan</h3>
            <form onSubmit={handleCreatePlan} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Plan Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Next Week Dinners, Diwali Feast"
                  value={newPlanName}
                  onChange={(e) => setNewPlanName(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button variant="outline" size="sm" type="button" onClick={() => setShowNewPlanModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit">
                  Create Plan
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: ADD RECIPE TO PLAN */}
      {/* =================================================================== */}
      {showAddRecipeModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 w-full max-w-lg shadow-2xl space-y-4">
            <h3 className="font-bold text-lg text-gray-900">Add Recipe to Meal Plan</h3>

            {/* Recipe Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search recipe by name (e.g. Paneer Butter Masala)..."
                value={recipeSearchQuery}
                onChange={(e) => handleSearchRecipes(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
              />
            </div>

            {/* Recipe Search Results */}
            {searchingRecipes && (
              <p className="text-xs text-gray-400 text-center py-2">Searching recipes...</p>
            )}

            {recipeSearchResults.length > 0 && !selectedRecipe && (
              <div className="max-h-48 overflow-y-auto divide-y divide-gray-100 border border-gray-100 rounded-xl">
                {recipeSearchResults.map((rec) => (
                  <button
                    key={rec.id}
                    onClick={() => {
                      setSelectedRecipe(rec);
                      setNewMealServings(rec.servings || 2);
                    }}
                    className="w-full text-left p-2.5 hover:bg-emerald-50 text-xs flex items-center justify-between"
                  >
                    <span className="font-semibold text-gray-900">{rec.name}</span>
                    <span className="text-gray-400">{rec.cuisine}</span>
                  </button>
                ))}
              </div>
            )}

            {selectedRecipe && (
              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100 text-xs space-y-1">
                <p className="font-bold text-emerald-900">Selected: {selectedRecipe.name}</p>
                <p className="text-emerald-700">Original Baseline: {selectedRecipe.servings || 4} servings</p>
              </div>
            )}

            {/* Serving Count & Date Settings */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Planned Servings
                </label>
                <input
                  type="number"
                  min="1"
                  value={newMealServings}
                  onChange={(e) => setNewMealServings(parseInt(e.target.value) || 2)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Meal Type
                </label>
                <select
                  value={newMealType}
                  onChange={(e) => setNewMealType(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
                >
                  <option value="breakfast">Breakfast</option>
                  <option value="lunch">Lunch</option>
                  <option value="dinner">Dinner</option>
                  <option value="snack">Snack</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Planned Date (Optional)
              </label>
              <input
                type="date"
                value={newMealDate}
                onChange={(e) => setNewMealDate(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSelectedRecipe(null);
                  setShowAddRecipeModal(false);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!selectedRecipe}
                onClick={handleAddMeal}
              >
                Add to Plan
              </Button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default MealPlanPage;
