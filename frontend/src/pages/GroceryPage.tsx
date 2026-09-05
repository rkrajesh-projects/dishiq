import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PageContainer } from '../components/common/PageContainer';
import { SectionTitle } from '../components/common/SectionTitle';
import { PriceComparisonCard } from '../components/grocery/PriceComparisonCard';
import { GroceryMatchList } from '../components/grocery/GroceryMatchList';
import { GroceryPriceComparison } from '../components/grocery/GroceryPriceComparison';
import { CartOptimizationPanel } from '../components/grocery/CartOptimizationPanel';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { getStores, getProducts } from '../api/grocery';
import { GroceryStore, GroceryProduct } from '../types';
import { safeNumber } from '../utils/currency';
import { Search, Sparkles } from 'lucide-react';

interface StoreCartSummary {
  store: GroceryStore;
  itemCost: number;
  deliveryFee: number;
  totalCost: number;
}

export const GroceryPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const recipeId = searchParams.get('recipeId');
  const [searchIngredient, setSearchIngredient] = useState('paneer');

  const {
    data: storesData,
    isPending: storesPending,
    isError: storesError,
    refetch: refetchStores,
  } = useQuery({
    queryKey: ['stores'],
    queryFn: () => getStores(),
  });

  const {
    data: productsData,
    isPending: productsPending,
    isError: productsError,
    refetch: refetchProducts,
  } = useQuery({
    queryKey: ['products'],
    queryFn: () => getProducts({ page_size: 50 }),
  });

  const isLoading = storesPending || productsPending;
  const isError = storesError || productsError;

  // Fallback demo stores in case backend API is offline
  const fallbackStores: GroceryStore[] = [
    { id: '1', name: 'Demo QuickMart', store_type: 'Convenience Supermarket', city: 'Demo City', is_demo_store: true, created_at: new Date().toISOString() },
    { id: '2', name: 'Demo FreshBasket', store_type: 'Organic Fresh Market', city: 'Demo City', is_demo_store: true, created_at: new Date().toISOString() },
    { id: '3', name: 'Demo LocalGrocer', store_type: 'Neighborhood Grocery', city: 'Demo City', is_demo_store: true, created_at: new Date().toISOString() },
  ];

  const stores: GroceryStore[] = storesData?.items && storesData.items.length > 0
    ? storesData.items
    : fallbackStores;

  const products: GroceryProduct[] = productsData?.items || [];

  // Calculate realistic store cart summaries from product API data or fallback seeded values
  const storeSummaries: StoreCartSummary[] = stores.map((store) => {
    const storeProducts = products.filter((p) => p.store_id === store.id);

    let itemCost = 0;
    let deliveryFee = 0;

    if (storeProducts.length > 0) {
      itemCost = storeProducts.reduce((sum, p) => {
        const latestPrice = p.prices && p.prices.length > 0 ? safeNumber(p.prices[0].price, 0) : 0;
        return sum + latestPrice;
      }, 0);

      if (storeProducts[0].prices && storeProducts[0].prices.length > 0) {
        deliveryFee = safeNumber(storeProducts[0].prices[0].delivery_fee, 0);
      }
    } else {
      if (store.name.includes('QuickMart')) {
        itemCost = 412;
        deliveryFee = 0;
      } else if (store.name.includes('FreshBasket')) {
        itemCost = 473.8;
        deliveryFee = 30;
      } else {
        itemCost = 391.4;
        deliveryFee = 0;
      }
    }

    return {
      store,
      itemCost: roundCurrency(itemCost),
      deliveryFee: roundCurrency(deliveryFee),
      totalCost: roundCurrency(itemCost + deliveryFee),
    };
  });

  // Find lowest total cost store
  const lowestTotal = storeSummaries.length > 0
    ? Math.min(...storeSummaries.map((s) => s.totalCost))
    : 0;

  const cheapestStoreId = React.useMemo(() => {
    const cheapest = storeSummaries.find((s) => s.totalCost === lowestTotal && lowestTotal > 0);
    return cheapest?.store.id || null;
  }, [storeSummaries, lowestTotal]);

  // Track explicit user clicks. null means "user hasn't picked yet → use cheapest as default"
  const [userSelectedStoreId, setUserSelectedStoreId] = useState<string | null>(null);

  // Effective selection: user's choice takes priority; fall back to cheapest
  const selectedStoreId = userSelectedStoreId ?? cheapestStoreId;

  const sampleIngredients = ['paneer', 'tomatoes', 'spinach', 'toor dal', 'chicken breast', 'dragonfruitxyz'];

  return (
    <PageContainer>
      <SectionTitle
        title="Grocery Product Matching & Multi-Store Pricing"
        subtitle="Match ingredients against store products using AI semantic embeddings and compare prices in INR (₹)"
      />

      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-8 text-xs text-amber-800">
        <strong>Demonstration Notice:</strong> Store prices shown below are demonstration retail datasets in Indian Rupees (INR). DishIQ does not scrape restricted grocery websites.
      </div>
      {recipeId && (
        <div className="mb-10">
          <CartOptimizationPanel />
        </div>
      )}

      {/* Live Ingredient Grocery Matching Search Section */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm mb-10 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-600" />
              Live Ingredient Product Matcher
            </h3>
            <p className="text-xs text-gray-500">
              Type an ingredient to view real-time matched grocery cards and vector similarity scores
            </p>
          </div>
          {/* Quick Select Chips */}
          <div className="flex items-center flex-wrap gap-1.5">
            {sampleIngredients.map((item) => (
              <button
                key={item}
                onClick={() => setSearchIngredient(item)}
                className={`text-xs px-2.5 py-1 rounded-lg transition-colors font-medium ${
                  searchIngredient.toLowerCase() === item
                    ? 'bg-emerald-600 text-white font-semibold shadow-xs'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchIngredient}
            onChange={(e) => setSearchIngredient(e.target.value)}
            placeholder="Search ingredient (e.g. paneer, tomatoes, toor dal)..."
            className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
          />
        </div>

        {/* Matched Cards List */}
        <GroceryMatchList ingredient={searchIngredient} limit={6} />
      </div>

      {/* Multi-Store Price Comparison Breakdown */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm mb-10">
        <GroceryPriceComparison ingredient={searchIngredient} limit={6} />
      </div>

      {/* Multi-Store Cart Summaries Section */}
      <div className="mb-6">
        <h3 className="text-base font-bold text-gray-900 mb-4">Store Cart Summaries</h3>
        {isLoading ? (
          <LoadingState message="Loading grocery stores and product prices..." />
        ) : isError ? (
          <ErrorState
            title="Grocery Data Offline"
            message="Unable to fetch live store catalog. Displaying fallback demonstration pricing."
            onRetry={() => {
              refetchStores();
              refetchProducts();
            }}
          />
        ) : storeSummaries.length === 0 ? (
          <EmptyState
            title="No stores available"
            description="No grocery store records found."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {storeSummaries.map((summary) => (
              <PriceComparisonCard
                key={summary.store.id}
                store={summary.store}
                itemCost={summary.itemCost}
                deliveryFee={summary.deliveryFee}
                isLowestPrice={summary.totalCost === lowestTotal && lowestTotal > 0}
                isSelected={selectedStoreId === summary.store.id}
                onClick={() => setUserSelectedStoreId(summary.store.id)}
              />
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  );
};

function roundCurrency(num: number): number {
  const safe = safeNumber(num, 0);
  return Math.round(safe * 100) / 100;
}
