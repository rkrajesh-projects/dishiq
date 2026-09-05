import React from 'react';
import { ShoppingBag, Tag, Sparkles, AlertTriangle, CheckCircle2, Trophy } from 'lucide-react';
import { ProductMatchResult } from '../../types';
import { formatINR, safeNumber } from '../../utils/currency';

export interface GroceryMatchCardProps {
  match: ProductMatchResult;
  isBestValue?: boolean;
  isSelected?: boolean;
  onSelect?: () => void;
  className?: string;
}

export const GroceryMatchCard: React.FC<GroceryMatchCardProps> = ({
  match,
  isBestValue = false,
  isSelected = false,
  onSelect,
  className = '',
}) => {
  const safePrice = match.price !== null && match.price !== undefined ? safeNumber(match.price) : null;
  const safeUnitPrice = match.unit_price !== null && match.unit_price !== undefined ? safeNumber(match.unit_price) : null;
  const matchPercentage = Math.round(safeNumber(match.similarity_score, 0) * 100);
  const isHighConfidence = match.match_status === 'matched';

  const cardStyle = isSelected
    ? 'border-emerald-500 ring-2 ring-emerald-500/20 bg-emerald-50/20 shadow-md cursor-pointer'
    : isHighConfidence
    ? 'border-gray-200 bg-white hover:border-emerald-300 cursor-pointer'
    : 'border-amber-200 bg-amber-50/20 hover:border-emerald-300 cursor-pointer';

  return (
    <div
      onClick={onSelect}
      className={`rounded-2xl border transition-all p-5 shadow-sm hover:shadow-md ${cardStyle} ${className}`}
      data-testid={`grocery-match-card-${match.product_id}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left Side: Product, Store & Metadata */}
        <div className="space-y-2 flex-1 min-w-0">
          <div className="flex items-center flex-wrap gap-2">
            {/* Best Value Badge */}
            {isBestValue && (
              <span
                className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-extrabold bg-amber-500 text-white shadow-xs"
                data-testid="best-value-badge"
              >
                <Trophy className="w-3.5 h-3.5 text-amber-100 fill-amber-100" />
                Best Value
              </span>
            )}

            {/* Store Badge */}
            {match.store_name && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-700">
                <ShoppingBag className="w-3.5 h-3.5" />
                {match.store_name}
              </span>
            )}

            {/* Brand / Category */}
            {match.brand && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-gray-100 text-gray-600">
                <Tag className="w-3 h-3" />
                {match.brand}
              </span>
            )}
            {match.category && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-gray-50 text-gray-500 border border-gray-100">
                {match.category}
              </span>
            )}
          </div>

          {/* Product Title */}
          <h4 className="text-base font-bold text-gray-900 leading-snug truncate">
            {match.product_name}
          </h4>

          {/* Match Score & Status Badges */}
          <div className="flex items-center flex-wrap gap-2 text-xs">
            <span
              className={`inline-flex items-center gap-1 font-semibold px-2.5 py-0.5 rounded-full ${
                isHighConfidence
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
              aria-label={`Parser confidence: ${matchPercentage}%`}
            >
              {isHighConfidence ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              )}
              {matchPercentage}% match
            </span>

            {match.rank > 0 && (
              <span className="text-gray-400 font-medium">
                #{match.rank} Match
              </span>
            )}
          </div>
        </div>

        {/* Right Side: Package Quantity & Pricing */}
        <div className="flex flex-row sm:flex-col items-baseline sm:items-end justify-between sm:justify-center border-t sm:border-t-0 pt-3 sm:pt-0 border-gray-100 shrink-0">
          <div className="text-right">
            {safePrice !== null ? (
              <span className="text-xl font-extrabold text-gray-900 tracking-tight">
                {formatINR(safePrice)}
              </span>
            ) : (
              <span className="text-sm font-medium text-gray-400">Price unavailable</span>
            )}

            {/* Package Quantity */}
            {match.package_quantity && match.package_unit && (
              <p className="text-xs text-gray-500 font-medium">
                {match.package_quantity} {match.package_unit}
              </p>
            )}
          </div>

          {/* Normalized Unit Price & Lowest Price Label */}
          <div className="flex flex-col items-end gap-1 mt-1">
            {safeUnitPrice !== null && match.base_unit && (
              <div className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                <Sparkles className="w-3 h-3 text-emerald-600" />
                <span>{formatINR(safeUnitPrice)}/{match.base_unit}</span>
              </div>
            )}

            {isBestValue && (
              <span className="text-[11px] font-semibold text-emerald-700">
                Lowest comparable price
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
