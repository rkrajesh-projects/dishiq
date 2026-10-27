import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient from '../api/client';
import {
  getProducts,
  getStores,
  matchGroceryProducts,
  compareGroceryPrices,
} from '../api/grocery';

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url === '/grocery/match' || url === '/grocery/compare') {
        return Promise.resolve({
          data: {
            ingredient_text: 'paneer',
            canonical_name: 'paneer',
            threshold: 0.4,
            total_matches: 1,
            results: [
              {
                product_id: 'p1',
                product_name: 'Amul Fresh Paneer 200g',
                brand: 'Amul',
                category: 'Dairy',
                store_id: 's1',
                store_name: 'Demo QuickMart',
                price: 95.0,
                currency: 'INR',
                package_quantity: 200.0,
                package_unit: 'grams',
                unit_price: 0.475,
                base_unit: 'g',
                similarity_score: 0.92,
                matched_text: 'paneer',
                match_status: 'matched',
                rank: 1,
                price_rank: 1,
              },
            ],
            best_option: {
              product_id: 'p1',
              product_name: 'Amul Fresh Paneer 200g',
              store_id: 's1',
              store_name: 'Demo QuickMart',
              brand: 'Amul',
              category: 'Dairy',
              price: 95.0,
              currency: 'INR',
              package_quantity: 200.0,
              package_unit: 'grams',
              unit_price: 0.475,
              base_unit: 'g',
              similarity_score: 0.92,
            },
            comparison_mode: 'unit_price',
          },
        });
      }
      return Promise.resolve({ data: { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 } });
    }),
  },
}));

describe('Grocery API Integration Safeguards', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('caps getProducts page_size at 50 when requesting page_size=100', async () => {
    await getProducts({ page_size: 100 });
    expect(apiClient.get).toHaveBeenCalledWith('/products', {
      params: { page_size: 50 },
    });
  });

  it('preserves getProducts page_size when requesting valid page_size=20', async () => {
    await getProducts({ page_size: 20 });
    expect(apiClient.get).toHaveBeenCalledWith('/products', {
      params: { page_size: 20 },
    });
  });

  it('caps getStores page_size at 50 when requesting page_size=100', async () => {
    await getStores({ page_size: 100 });
    expect(apiClient.get).toHaveBeenCalledWith('/stores', {
      params: { page_size: 50 },
    });
  });

  it('matchGroceryProducts calls /grocery/match with encoded ingredient and returns typed response', async () => {
    const data = await matchGroceryProducts({ ingredient: '  paneer  ', limit: 5 });
    expect(apiClient.get).toHaveBeenCalledWith('/grocery/match', {
      params: { ingredient: 'paneer', limit: 5 },
    });
    expect(data.canonical_name).toBe('paneer');
    expect(data.results.length).toBe(1);
    expect(data.results[0].currency).toBe('INR');
  });

  it('compareGroceryPrices calls /grocery/compare with encoded ingredient and returns typed response', async () => {
    const data = await compareGroceryPrices({ ingredient: 'paneer' });
    expect(apiClient.get).toHaveBeenCalledWith('/grocery/compare', {
      params: { ingredient: 'paneer', live_mode: false },
    });
    expect(data.best_option).not.toBeNull();
    expect(data.best_option?.store_name).toBe('Demo QuickMart');
    expect(data.best_option?.currency).toBe('INR');
  });

  it('returns empty result structure without calling API when ingredient is empty or whitespace', async () => {
    const dataMatch = await matchGroceryProducts({ ingredient: '   ' });
    expect(apiClient.get).not.toHaveBeenCalled();
    expect(dataMatch.total_matches).toBe(0);
    expect(dataMatch.results).toEqual([]);
    expect(dataMatch.best_option).toBeNull();

    const dataCompare = await compareGroceryPrices({ ingredient: '' });
    expect(apiClient.get).not.toHaveBeenCalled();
    expect(dataCompare.total_matches).toBe(0);
    expect(dataCompare.results).toEqual([]);
    expect(dataCompare.best_option).toBeNull();
  });
});
