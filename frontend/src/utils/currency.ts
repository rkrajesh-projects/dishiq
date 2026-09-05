/**
 * DishIQ Currency Formatting & Safe Calculation Utilities
 *
 * All grocery prices are stored and calculated in Indian Rupees (INR).
 * Safe numerical parsing prevents NaN / undefined propagation.
 */

/** Intl.NumberFormat instance for Indian Rupees, en-IN locale */
const INR_FORMATTER = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

/**
 * Safely parse any numerical value into a valid finite number.
 * Returns defaultValue (0) if value is null, undefined, NaN, or non-finite.
 */
export function safeNumber(value: unknown, defaultValue = 0): number {
  if (value === null || value === undefined) {
    return defaultValue;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : defaultValue;
}

/**
 * Format a numeric price value into an INR currency string.
 * Always handles null, undefined, or NaN safely by returning ₹0.
 * Example: formatINR(95) → "₹95"
 *          formatINR(undefined) → "₹0"
 *          formatINR(NaN) → "₹0"
 */
export function formatINR(amount: unknown): string {
  const safe = safeNumber(amount, 0);
  return INR_FORMATTER.format(safe);
}

/**
 * Format a price using the currency code returned from the API.
 * Safely defaults to INR if currency is missing or invalid.
 * Example: formatPrice(95, 'INR') → "₹95"
 *          formatPrice(undefined) → "₹0"
 */
export function formatPrice(amount: unknown, currency = 'INR'): string {
  const safe = safeNumber(amount, 0);
  const validCurrency = currency && typeof currency === 'string' ? currency.trim() : 'INR';

  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: validCurrency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(safe);
  } catch {
    return `₹${safe.toFixed(2)}`;
  }
}

/**
 * Safely calculate total sum from an array of items with numerical price fields.
 * Safely handles missing/empty arrays, undefined prices, or invalid values.
 */
export function calculateTotalCost<T>(
  items: T[] | null | undefined,
  priceExtractor: (item: T) => unknown
): number {
  if (!Array.isArray(items) || items.length === 0) {
    return 0;
  }
  return items.reduce<number>((sum, item) => {
    const rawPrice = priceExtractor(item);
    return sum + safeNumber(rawPrice, 0);
  }, 0);
}
