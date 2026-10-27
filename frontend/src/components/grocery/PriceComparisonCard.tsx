import React, { useState } from 'react';
import { Store, Truck, ShoppingCart, AlertCircle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { GroceryStore, CartProductSelection } from '../../types';
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
  items?: CartProductSelection[];
  isExpandedByDefault?: boolean;
}

export const PriceComparisonCard: React.FC<PriceComparisonCardProps> = ({
  store,
  itemCost,
  deliveryFee,
  totalCost,
  isLowestPrice = false,
  isSelected = false,
  onClick,
  items,
  isExpandedByDefault = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(isExpandedByDefault);
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
            <h4 className="font-bold text-gray-900 text-sm" data-testid="store-name">{store?.name || 'Grocery Store'}</h4>
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
            {items ? `${items.length} items` : 'Items'}
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

      {items && items.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <button
            type="button"
            className="flex items-center justify-between w-full text-xs font-semibold text-gray-600 hover:text-gray-900 py-1 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse item list" : "Expand item list"}
          >
            <span>{isExpanded ? 'Hide items' : 'View items'}</span>
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          
          {isExpanded && (
            <div className="mt-3 space-y-3 pt-2">
              {items.map((item, idx) => (
                <div key={idx} className="flex justify-between items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <p className="text-xs font-bold text-gray-900 truncate" title={item.product_name} data-testid="product-name">
                        {item.product_name}
                      </p>
                      <a
                        href={`https://www.swiggy.com/instamart/search?custom_back=true&query=${encodeURIComponent(item.product_name)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-orange-500 hover:text-orange-600 transition-colors p-0.5 shrink-0"
                        title="Search product on Swiggy Instamart Web"
                        data-testid={`swiggy-product-link-${idx}`}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <p className="text-[10px] text-gray-500 mt-0.5">
                      {item.packages_required} × {item.package_quantity} {item.package_unit}
                      {item.package_price ? ` @ ${formatINR(item.package_price)}` : ''}
                    </p>
                    {!item.in_stock && (
                      <span className="inline-block mt-0.5 text-[9px] font-bold uppercase tracking-wider text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded">
                        Unavailable
                      </span>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-xs font-semibold text-gray-900">
                      {formatINR(item.line_cost)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Open / Order in Swiggy Web */}
      <a
        href="https://www.swiggy.com/instamart"
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="mt-3.5 flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-orange-500 hover:bg-orange-600 text-white text-xs font-bold rounded-xl transition-all shadow-xs cursor-pointer"
        data-testid={`swiggy-web-order-${store?.id}`}
      >
        <ExternalLink className="w-3.5 h-3.5" />
        <span>Order on Swiggy Instamart Web</span>
      </a>

      {store?.is_demo_store && (
        <div className="mt-3 flex items-center gap-1.5 text-[11px] text-amber-700 bg-amber-50 px-2.5 py-1 rounded-lg">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
          <span>Demonstration grocery pricing data (INR)</span>
        </div>
      )}
    </div>
  );
};
