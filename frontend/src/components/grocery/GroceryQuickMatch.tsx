import React from 'react';
import { X, ShoppingBag, RefreshCw, Sparkles } from 'lucide-react';
import { useGroceryMatch } from '../../hooks/useGrocery';
import { GroceryMatchCard } from './GroceryMatchCard';

export interface GroceryQuickMatchProps {
  ingredient: string;
  isOpen: boolean;
  onClose: () => void;
  limit?: number;
}

export const GroceryQuickMatch: React.FC<GroceryQuickMatchProps> = ({
  ingredient,
  isOpen,
  onClose,
  limit = 10,
}) => {
  const cleanedIngredient = (ingredient || '').trim();

  // Fetch only when modal is open and ingredient is present
  const { data, isPending, isError, error, refetch } = useGroceryMatch({
    ingredient: isOpen ? cleanedIngredient : '',
    limit,
  });

  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const bestOptionId = data?.best_option?.product_id || null;

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 overflow-y-auto animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="quick-match-dialog-title"
      data-testid="grocery-quick-match-modal"
    >
      <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden border border-gray-100 my-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100 bg-gray-50/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl">
              <ShoppingBag className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="quick-match-dialog-title"
                className="text-base font-bold text-gray-900 leading-snug"
              >
                Quick Match for &quot;{cleanedIngredient}&quot;
              </h2>
              <p className="text-xs text-gray-500 font-medium">
                Live grocery matching &amp; unit prices (INR ₹)
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
            aria-label="Close Quick Match"
            data-testid="quick-match-close-button"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          {/* 1. Loading State */}
          {isPending && (
            <div className="space-y-3 p-4" data-testid="quick-match-loading">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-4 h-4 bg-emerald-100 rounded-full animate-pulse" />
                <div className="h-4 w-44 bg-gray-200 rounded animate-pulse" />
              </div>
              {[1, 2].map((idx) => (
                <div
                  key={idx}
                  className="bg-white rounded-2xl border border-gray-100 p-4 shadow-xs space-y-2 animate-pulse"
                >
                  <div className="h-4 w-32 bg-gray-200 rounded" />
                  <div className="h-5 w-48 bg-gray-300 rounded" />
                </div>
              ))}
            </div>
          )}

          {/* 2. Error State */}
          {isError && (
            <div
              className="bg-rose-50/50 border border-rose-200 rounded-2xl p-6 text-center space-y-3"
              data-testid="quick-match-error"
            >
              <p className="text-sm font-medium text-rose-800">
                {(error as { message?: string })?.message || 'Unable to find grocery matches.'}
              </p>
              <button
                onClick={() => refetch()}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-xl transition-colors shadow-sm"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry
              </button>
            </div>
          )}

          {/* 3. Empty State */}
          {!isPending && !isError && (!data || data.total_matches === 0 || data.results.length === 0) && (
            <div
              className="bg-gray-50 border border-dashed border-gray-200 rounded-2xl p-8 text-center space-y-2"
              data-testid="quick-match-empty"
            >
              <ShoppingBag className="w-8 h-8 text-gray-400 mx-auto mb-1" />
              <h4 className="text-sm font-bold text-gray-700">No matching grocery products found.</h4>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                No store products matched &quot;{cleanedIngredient}&quot; in the store catalog.
              </p>
            </div>
          )}

          {/* 4. Results List */}
          {!isPending && !isError && data && data.total_matches > 0 && data.results.length > 0 && (
            <div className="space-y-3" data-testid="quick-match-results">
              <div className="flex items-center justify-between text-xs text-gray-500 font-medium px-1 pb-1">
                <span className="flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  Canonical: &quot;{data.canonical_name || data.ingredient_text}&quot;
                </span>
                <span>{data.total_matches} {data.total_matches === 1 ? 'Match' : 'Matches'} Found</span>
              </div>

              {data.results.map((product) => (
                <GroceryMatchCard
                  key={product.product_id}
                  match={product}
                  isBestValue={Boolean(bestOptionId && product.product_id === bestOptionId)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
