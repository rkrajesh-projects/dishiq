import React, { act } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PantryPage } from '../pages/PantryPage';
import * as pantryApi from '../api/pantry';
import { PantryItem } from '../types';

vi.mock('../api/pantry', () => ({
  getPantryItems: vi.fn(),
  addPantryItem: vi.fn(),
  updatePantryItem: vi.fn(),
  deletePantryItem: vi.fn(),
}));

const mockItems: PantryItem[] = [
  {
    id: 'item-1',
    ingredient_id: 'ing-1',
    ingredient_name: 'tomato',
    canonical_name: 'tomato',
    quantity: 1.0,
    unit: 'kg',
    expiration_date: '2099-01-01',
    created_at: '2026-08-01T00:00:00Z',
    updated_at: '2026-08-01T00:00:00Z',
  },
  {
    id: 'item-2',
    ingredient_id: 'ing-2',
    ingredient_name: 'paneer',
    canonical_name: 'paneer',
    quantity: 200.0,
    unit: 'grams',
    expiration_date: null,
    created_at: '2026-08-01T00:00:00Z',
    updated_at: '2026-08-01T00:00:00Z',
  },
];

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

function renderPantryPage() {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PantryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PantryPage — Live API Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading state ────────────────────────────────────────────────────────
  it('shows loading spinner while fetching pantry items', () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockReturnValue(new Promise(() => {}));
    renderPantryPage();
    expect(screen.getByText(/loading pantry/i)).toBeInTheDocument();
  });

  // ── Empty state ──────────────────────────────────────────────────────────
  it('shows empty state when pantry is empty', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue([]);
    renderPantryPage();
    expect(await screen.findByText(/your pantry is empty/i)).toBeInTheDocument();
  });

  // ── List items ───────────────────────────────────────────────────────────
  it('displays loaded pantry items', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue(mockItems);
    renderPantryPage();
    expect(await screen.findByText('tomato')).toBeInTheDocument();
    expect(screen.getByText('paneer')).toBeInTheDocument();
    expect(screen.getByText('1 kg')).toBeInTheDocument();
    expect(screen.getByText('200 grams')).toBeInTheDocument();
  });

  // ── Error state ──────────────────────────────────────────────────────────
  it('shows error state when API fails', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockRejectedValue({ message: 'Network error' });
    renderPantryPage();
    expect(await screen.findByText(/failed to load pantry/i, {}, { timeout: 3000 })).toBeInTheDocument();
  });

  // ── Summary banner count ─────────────────────────────────────────────────
  it('shows correct ingredient count in banner', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue(mockItems);
    renderPantryPage();
    expect(await screen.findByText('2 Ingredients in Stock')).toBeInTheDocument();
  });

  // ── Add item — open modal ─────────────────────────────────────────────────
  it('opens Add Item modal when button clicked', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue([]);
    renderPantryPage();
    await screen.findByText(/your pantry is empty/i);
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /add item/i }));
    });
    expect(await screen.findByRole('dialog', { name: /add pantry item/i })).toBeInTheDocument();
  });

  // ── Add item — submit ─────────────────────────────────────────────────────
  it('calls addPantryItem API on valid submit', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue([]);
    const newItem: PantryItem = {
      id: 'item-3',
      ingredient_id: 'ing-3',
      ingredient_name: 'onion',
      canonical_name: 'onion',
      quantity: 500,
      unit: 'grams',
      expiration_date: null,
      created_at: '2026-08-21T00:00:00Z',
      updated_at: '2026-08-21T00:00:00Z',
    };
    vi.spyOn(pantryApi, 'addPantryItem').mockResolvedValue(newItem);

    renderPantryPage();
    await screen.findByText(/your pantry is empty/i);

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /add item/i }));
    });
    await screen.findByRole('dialog', { name: /add pantry item/i });

    fireEvent.change(screen.getByLabelText(/ingredient name/i), { target: { value: 'onion' } });
    fireEvent.change(screen.getByLabelText(/quantity/i), { target: { value: '500' } });

    const buttons = screen.getAllByRole('button', { name: /add item/i });
    act(() => {
      fireEvent.click(buttons[buttons.length - 1]);
    });

    await waitFor(() => {
      expect(pantryApi.addPantryItem).toHaveBeenCalledWith(
        expect.objectContaining({ ingredient_name: 'onion', quantity: 500 }),
      );
    });
  });

  // ── Add item — name validation ────────────────────────────────────────────
  it('shows validation error when name is empty', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue([]);
    renderPantryPage();
    await screen.findByText(/your pantry is empty/i);

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /add item/i }));
    });
    await screen.findByRole('dialog', { name: /add pantry item/i });

    const buttons = screen.getAllByRole('button', { name: /add item/i });
    act(() => {
      fireEvent.click(buttons[buttons.length - 1]);
    });

    expect(await screen.findByText(/ingredient name is required/i)).toBeInTheDocument();
    expect(pantryApi.addPantryItem).not.toHaveBeenCalled();
  });

  // ── Add item — quantity validation ────────────────────────────────────────
  it('shows validation error for invalid quantity', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue([]);
    renderPantryPage();
    await screen.findByText(/your pantry is empty/i);

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /add item/i }));
    });
    await screen.findByRole('dialog', { name: /add pantry item/i });

    fireEvent.change(screen.getByLabelText(/ingredient name/i), { target: { value: 'rice' } });
    fireEvent.change(screen.getByLabelText(/quantity/i), { target: { value: '-5' } });

    const buttons = screen.getAllByRole('button', { name: /add item/i });
    act(() => {
      fireEvent.click(buttons[buttons.length - 1]);
    });

    expect(await screen.findByText(/quantity must be a positive number/i)).toBeInTheDocument();
  });

  // ── Delete item — open confirm ────────────────────────────────────────────
  it('opens delete confirm when delete button clicked', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue(mockItems);
    renderPantryPage();
    await screen.findByText('tomato');

    act(() => {
      fireEvent.click(screen.getByTestId('delete-btn-item-1'));
    });

    expect(await screen.findByText(/Remove from Pantry\?/i)).toBeInTheDocument();
  });

  // ── Delete item — confirm ─────────────────────────────────────────────────
  it('calls deletePantryItem on confirm', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue(mockItems);
    const deleteSpy = vi.spyOn(pantryApi, 'deletePantryItem').mockResolvedValue(undefined);
    renderPantryPage();

    await screen.findByText('tomato');

    // Open the confirm dialog
    act(() => {
      fireEvent.click(screen.getByTestId('delete-btn-item-1'));
    });
    await screen.findByText(/Remove from Pantry\?/i);

    // Confirm the deletion
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /^remove$/i }));
    });

    // deletePantryItem should have been called
    await waitFor(
      () => {
        expect(deleteSpy).toHaveBeenCalled();
      },
      { timeout: 2000 },
    );
  });

  // ── Edit item — open modal ────────────────────────────────────────────────
  it('opens edit modal with pre-filled values', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue(mockItems);
    renderPantryPage();
    await screen.findByText('tomato');

    act(() => {
      fireEvent.click(screen.getByTestId('edit-btn-item-1'));
    });

    expect(await screen.findByText(/edit — tomato/i)).toBeInTheDocument();

    const qtyInput = screen.getByLabelText(/quantity/i) as HTMLInputElement;
    expect(qtyInput.value).toBe('1');
  });

  // ── Edit item — submit ────────────────────────────────────────────────────
  it('calls updatePantryItem with new values on submit', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue(mockItems);
    vi.spyOn(pantryApi, 'updatePantryItem').mockResolvedValue({ ...mockItems[0], quantity: 2 });
    renderPantryPage();

    await screen.findByText('tomato');

    act(() => {
      fireEvent.click(screen.getByTestId('edit-btn-item-1'));
    });
    await screen.findByText(/edit — tomato/i);

    fireEvent.change(screen.getByLabelText(/quantity/i), { target: { value: '2' } });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /save changes/i }));
    });

    await waitFor(() => {
      expect(pantryApi.updatePantryItem).toHaveBeenCalledWith(
        'item-1',
        expect.objectContaining({ quantity: 2 }),
      );
    });
  });

  // ── No expiry ─────────────────────────────────────────────────────────────
  it('shows "No expiry set" for items without expiration_date', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue(mockItems);
    renderPantryPage();
    await screen.findByText('paneer');
    expect(screen.getByText('No expiry set')).toBeInTheDocument();
  });

  // ── Close modal ───────────────────────────────────────────────────────────
  it('closes Add modal when Cancel is clicked', async () => {
    vi.spyOn(pantryApi, 'getPantryItems').mockResolvedValue([]);
    renderPantryPage();
    await screen.findByText(/your pantry is empty/i);

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /add item/i }));
    });
    await screen.findByRole('dialog', { name: /add pantry item/i });

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
