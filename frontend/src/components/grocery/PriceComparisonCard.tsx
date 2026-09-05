import React from 'react';
import { Store, Truck, ShoppingCart, AlertCircle } from 'lucide-react';
import { GroceryStore } from '../../types';
import { formatINR, safeNumber } from '../../utils/currency';

export interface PriceComparisonCardProps {
  store: GroceryStore;
  /** Total item cost in INR (excl. delivery) */
  itemCost?: number;
  /** Delivery fee in INR */
  deliveryFee?: number;
  /** Legacy total cost prop for backward compatibility */
  totalCost?: number;
  isLowestPrice?: boolean;
  isSelected?: boolean;
  onClick?: () => void;
}

export const PriceComparisonCard: React.FC<PriceComparisonCardProps> = ({
  store,
  itemCost,
  deliveryFee,
  totalCost,
  isLowestPrice = false,
  isSelected = false,
  onClick,
}) => {
  const safeDelivery = safeNumber(deliveryFee, 0);

  let safeItem = 0;
  if (itemCost !== undefined && itemCost !== null && !isNaN(Number(itemCost))) {
    safeItem = safeNumber(itemCost, 0);
  } else if (totalCost !== undefined && totalCost !== null && !isNaN(Number(totalCost))) {
    const safeTot = safeNumber(totalCost, 0);
    safeItem = Math.max(0, safeTot - safeDelivery);
  }

  const safeTotal = safeItem + safeDelivery;

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl border p-5 transition-all shadow-sm cursor-pointer ${
        isSelected ? 'border-emerald-500 ring-2 ring-emerald-500/20 shadow-md' : 'border-gray-100 hover:border-emerald-300'
      }`}
      data-testid={`store-card-${store?.id}`}
    >
      {/* Store Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${isLowestPrice ? 'bg-emerald-50 text-emerald-600' : 'bg-orange-50 text-orange-600'}`}>
            <Store className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-gray-900 text-sm">{store?.name || 'Grocery Store'}</h4>
            <p className="text-xs text-gray-500">{store?.store_type || 'Supermarket'} • {store?.city || 'Local'}</p>
          </div>
        </div>
        {isLowestPrice && (
          <span className="bg-emerald-500 text-white text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full shadow-sm">
            Best Cart
          </span>
        )}
      </div>

      {/* Price Breakdown */}
      <div className="border-t border-gray-50 pt-3 mt-3 space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500 flex items-center gap-1.5">
            <ShoppingCart className="w-3.5 h-3.5" />
            Items
          </span>
          <span className="font-medium text-gray-700">{formatINR(safeItem)}</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500 flex items-center gap-1.5">
            <Truck className="w-3.5 h-3.5" />
            Delivery
          </span>
          <span className={`font-medium ${safeDelivery === 0 ? 'text-emerald-600' : 'text-gray-700'}`}>
            {safeDelivery === 0 ? 'Free' : formatINR(safeDelivery)}
          </span>
        </div>

        <div className="flex items-baseline justify-between pt-2 border-t border-gray-100">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Total</span>
          <span className="text-xl font-bold text-gray-900">{formatINR(safeTotal)}</span>
        </div>
      </div>

      {store?.is_demo_store && (
        <div className="mt-3 flex items-center gap-1.5 text-[11px] text-amber-700 bg-amber-50 px-2.5 py-1 rounded-lg">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
          <span>Demonstration grocery pricing data (INR)</span>
        </div>
      )}
    </div>
  );
};
