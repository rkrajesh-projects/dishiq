import { describe, it, expect } from 'vitest';
import { formatINR, formatPrice, safeNumber, calculateTotalCost } from '../utils/currency';

describe('Currency & Safe Calculation Utilities (INR)', () => {
  it('safeNumber parses valid numbers and handles invalid values gracefully', () => {
    expect(safeNumber(95)).toBe(95);
    expect(safeNumber('165')).toBe(165);
    expect(safeNumber(0)).toBe(0);
    expect(safeNumber(undefined)).toBe(0);
    expect(safeNumber(null)).toBe(0);
    expect(safeNumber(NaN)).toBe(0);
    expect(safeNumber(Infinity)).toBe(0);
    expect(safeNumber(undefined, 10)).toBe(10);
  });

  it('formatINR never produces ₹NaN and handles invalid inputs', () => {
    expect(formatINR(95)).toBe('₹95');
    expect(formatINR(165)).toBe('₹165');
    expect(formatINR(undefined)).toBe('₹0');
    expect(formatINR(null)).toBe('₹0');
    expect(formatINR(NaN)).toBe('₹0');
  });

  it('formatPrice handles invalid input and missing currency safely', () => {
    expect(formatPrice(95, 'INR')).toBe(formatINR(95));
    expect(formatPrice(undefined, 'INR')).toBe('₹0');
    expect(formatPrice(null, '')).toBe('₹0');
  });

  it('calculateTotalCost calculates sum correctly and handles empty lists / missing values', () => {
    const products = [
      { name: 'Paneer', price: 95 },
      { name: 'Oil', price: 165 },
      { name: 'Eggs', price: 48 },
    ];
    expect(calculateTotalCost(products, (p) => p.price)).toBe(308);

    // Empty array returns 0
    expect(calculateTotalCost([], (p: any) => p.price)).toBe(0);
    expect(calculateTotalCost(null, (p: any) => p.price)).toBe(0);
    expect(calculateTotalCost(undefined, (p: any) => p.price)).toBe(0);

    // Array with missing/undefined prices returns sum of valid prices
    const messyProducts = [
      { name: 'Paneer', price: 95 },
      { name: 'Unknown', price: undefined },
      { name: 'Corrupt', price: NaN },
      { name: 'NullItem', price: null },
      { name: 'Milk', price: 32 },
    ];
    expect(calculateTotalCost(messyProducts, (p) => p.price)).toBe(127);
  });
});
