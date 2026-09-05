import React, { useState } from 'react';
import {
  Package,
  Plus,
  IndianRupee,
  Pencil,
  Trash2,
  AlertCircle,
  Loader2,
  X,
} from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { SectionTitle } from '../components/common/SectionTitle';
import { Button } from '../components/common/Button';
import { usePantryItems, useAddPantryItem, useUpdatePantryItem, useDeletePantryItem } from '../hooks/usePantry';
import { PantryItem } from '../types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatExpiry(expirationDate: string | null): string {
  if (!expirationDate) return 'No expiry set';
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const exp = new Date(expirationDate);
  exp.setHours(0, 0, 0, 0);
  const diffMs = exp.getTime() - today.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return `Expired ${Math.abs(diffDays)}d ago`;
  if (diffDays === 0) return 'Expires today';
  if (diffDays === 1) return 'In 1 day';
  return `In ${diffDays} days`;
}

function expiryBadgeClass(expirationDate: string | null): string {
  if (!expirationDate) return 'bg-gray-50 text-gray-500';
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const exp = new Date(expirationDate);
  exp.setHours(0, 0, 0, 0);
  const diffDays = Math.round((exp.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'bg-red-50 text-red-700';
  if (diffDays <= 3) return 'bg-orange-50 text-orange-700';
  return 'bg-amber-50 text-amber-700';
}

const COMMON_UNITS = ['grams', 'kg', 'pieces', 'litres', 'ml', 'cups', 'tbsp', 'tsp', 'packets'];

// ---------------------------------------------------------------------------
// Add / Edit Modal
// ---------------------------------------------------------------------------

interface AddEditModalProps {
  mode: 'add' | 'edit';
  initial?: PantryItem | null;
  onClose: () => void;
  onSubmit: (data: {
    ingredient_name?: string;
    quantity: number;
    unit: string;
    expiration_date?: string | null;
  }) => void;
  isLoading: boolean;
  error: string | null;
}

const AddEditModal: React.FC<AddEditModalProps> = ({
  mode,
  initial,
  onClose,
  onSubmit,
  isLoading,
  error,
}) => {
  const [name, setName] = useState(initial?.ingredient_name ?? '');
  const [qty, setQty] = useState(String(initial?.quantity ?? ''));
  const [unit, setUnit] = useState(initial?.unit ?? 'pieces');
  const [expiry, setExpiry] = useState(initial?.expiration_date ?? '');
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const parsedQty = parseFloat(qty);
    if (mode === 'add' && !name.trim()) {
      setValidationError('Ingredient name is required.');
      return;
    }
    if (isNaN(parsedQty) || parsedQty <= 0) {
      setValidationError('Quantity must be a positive number.');
      return;
    }
    if (!unit.trim()) {
      setValidationError('Unit is required.');
      return;
    }

    onSubmit({
      ...(mode === 'add' ? { ingredient_name: name.trim() } : {}),
      quantity: parsedQty,
      unit: unit.trim(),
      expiration_date: expiry || null,
    });
  };

  const displayError = validationError || error;

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={mode === 'add' ? 'Add pantry item' : 'Edit pantry item'}
    >
      <div className="bg-white rounded-3xl shadow-2xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-gray-900 text-lg">
            {mode === 'add' ? 'Add Pantry Item' : `Edit — ${initial?.ingredient_name}`}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {mode === 'add' && (
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="pantry-name">
                Ingredient Name
              </label>
              <input
                id="pantry-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. paneer, tomato, onion"
                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                autoFocus
              />
            </div>
          )}

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="pantry-qty">
                Quantity
              </label>
              <input
                id="pantry-qty"
                type="number"
                min="0.01"
                step="0.01"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>

            <div className="flex-1">
              <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="pantry-unit">
                Unit
              </label>
              <select
                id="pantry-unit"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
              >
                {COMMON_UNITS.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="pantry-expiry">
              Expiry Date <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              id="pantry-expiry"
              type="date"
              value={expiry ?? ''}
              onChange={(e) => setExpiry(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
            />
          </div>

          {displayError && (
            <div className="flex items-start gap-2 text-xs text-red-700 bg-red-50 rounded-xl px-3 py-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{displayError}</span>
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isLoading}
              disabled={isLoading}
              className="flex-1"
            >
              {mode === 'add' ? 'Add Item' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Delete Confirm
// ---------------------------------------------------------------------------

interface DeleteConfirmProps {
  item: PantryItem;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  error: string | null;
}

const DeleteConfirm: React.FC<DeleteConfirmProps> = ({ item, onClose, onConfirm, isLoading, error }) => (
  <div
    className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    role="dialog"
    aria-modal="true"
    aria-label={`Delete ${item.ingredient_name}`}
  >
    <div className="bg-white rounded-3xl shadow-2xl p-6 w-full max-w-sm">
      <h2 className="font-bold text-gray-900 text-lg mb-2">Remove from Pantry?</h2>
      <p className="text-sm text-gray-600 mb-5">
        Remove <strong>{item.ingredient_name}</strong> ({item.quantity} {item.unit}) from your pantry inventory.
      </p>
      {error && (
        <div className="flex items-start gap-2 text-xs text-red-700 bg-red-50 rounded-xl px-3 py-2 mb-4">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      <div className="flex gap-3">
        <Button variant="secondary" size="sm" onClick={onClose} className="flex-1">
          Cancel
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={onConfirm}
          isLoading={isLoading}
          disabled={isLoading}
          className="flex-1 !bg-red-600 hover:!bg-red-700 !shadow-red-600/20"
        >
          Remove
        </Button>
      </div>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// PantryPage
// ---------------------------------------------------------------------------

export const PantryPage: React.FC = () => {
  const { data: pantryItems = [], isLoading, isError, error } = usePantryItems();
  const addMutation = useAddPantryItem();
  const updateMutation = useUpdatePantryItem();
  const deleteMutation = useDeletePantryItem();

  const [showAdd, setShowAdd] = useState(false);
  const [editItem, setEditItem] = useState<PantryItem | null>(null);
  const [deleteItem, setDeleteItem] = useState<PantryItem | null>(null);

  const handleAdd = (data: {
    ingredient_name?: string;
    quantity: number;
    unit: string;
    expiration_date?: string | null;
  }) => {
    addMutation.mutate(
      {
        ingredient_name: data.ingredient_name!,
        quantity: data.quantity,
        unit: data.unit,
        expiration_date: data.expiration_date,
      },
      {
        onSuccess: () => setShowAdd(false),
      },
    );
  };

  const handleEdit = (data: {
    ingredient_name?: string;
    quantity: number;
    unit: string;
    expiration_date?: string | null;
  }) => {
    if (!editItem) return;
    updateMutation.mutate(
      {
        id: editItem.id,
        body: {
          quantity: data.quantity,
          unit: data.unit,
          expiration_date: data.expiration_date,
        },
      },
      {
        onSuccess: () => setEditItem(null),
      },
    );
  };

  const handleDelete = () => {
    if (!deleteItem) return;
    deleteMutation.mutate(deleteItem.id, {
      onSuccess: () => setDeleteItem(null),
    });
  };

  const getMutationError = (mutation: { error: Error | null }): string | null =>
    mutation.error
      ? (mutation.error as unknown as { message: string }).message || 'An error occurred.'
      : null;

  return (
    <PageContainer>
      <SectionTitle
        title="Pantry Inventory & Stock Tracker"
        subtitle="Manage active pantry stock to enable zero-waste meal recommendations"
        action={
          <Button
            variant="primary"
            size="sm"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => setShowAdd(true)}
          >
            Add Item
          </Button>
        }
      />

      {/* ── Inventory Summary Banner ── */}
      <div className="bg-emerald-900 text-white rounded-3xl p-6 mb-6 shadow-md flex items-center justify-between">
        <div>
          <span className="text-xs uppercase tracking-wider text-emerald-200 font-bold block mb-1">
            Active Stock Summary
          </span>
          <h3 className="text-xl font-extrabold">
            {isLoading ? '—' : `${pantryItems.length} Ingredient${pantryItems.length !== 1 ? 's' : ''} in Stock`}
          </h3>
        </div>
        <div className="text-right">
          <span className="text-xs text-emerald-200 block mb-1 flex items-center justify-end gap-1">
            <IndianRupee className="w-3.5 h-3.5" /> Total Quantity Units
          </span>
          <span className="text-2xl font-black text-amber-300">
            {isLoading ? '—' : pantryItems.length}
          </span>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="bg-white rounded-3xl border border-gray-100 p-6 shadow-sm min-h-[200px]">

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
            <span className="text-sm">Loading pantry…</span>
          </div>
        )}

        {/* Error */}
        {isError && !isLoading && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-red-600">
            <AlertCircle className="w-8 h-8" />
            <p className="text-sm font-medium">Failed to load pantry</p>
            <p className="text-xs text-gray-500 text-center max-w-xs">
              {(error as unknown as { message: string })?.message || 'Could not reach the backend.'}
            </p>
          </div>
        )}

        {/* Empty */}
        {!isLoading && !isError && pantryItems.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-400">
            <Package className="w-10 h-10 text-emerald-200" />
            <p className="text-sm font-medium text-gray-600">Your pantry is empty</p>
            <p className="text-xs text-gray-400">Add your first ingredient using the button above.</p>
          </div>
        )}

        {/* Items grid */}
        {!isLoading && !isError && pantryItems.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {pantryItems.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-2xl border border-orange-100 bg-orange-50/30 flex items-start justify-between gap-2 group"
              >
                <div className="flex items-start gap-3 min-w-0">
                  <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl shrink-0">
                    <Package className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="font-bold text-gray-900 text-sm capitalize truncate">
                      {item.ingredient_name}
                    </h4>
                    <p className="text-xs text-gray-500">
                      {item.quantity} {item.unit}
                    </p>
                    <span
                      className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full font-medium ${expiryBadgeClass(item.expiration_date)}`}
                    >
                      {formatExpiry(item.expiration_date)}
                    </span>
                  </div>
                </div>

                {/* Action buttons — visible on hover or always on mobile */}
                <div className="flex flex-col gap-1.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity focus-within:opacity-100">
                  <button
                    data-testid={`edit-btn-${item.id}`}
                    onClick={() => {
                      updateMutation.reset();
                      setEditItem(item);
                    }}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                    aria-label={`Edit ${item.ingredient_name}`}
                    title="Edit"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    data-testid={`delete-btn-${item.id}`}
                    onClick={() => {
                      deleteMutation.reset();
                      setDeleteItem(item);
                    }}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    aria-label={`Delete ${item.ingredient_name}`}
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Modals ── */}
      {showAdd && (
        <AddEditModal
          mode="add"
          onClose={() => { setShowAdd(false); addMutation.reset(); }}
          onSubmit={handleAdd}
          isLoading={addMutation.isPending}
          error={getMutationError(addMutation)}
        />
      )}

      {editItem && (
        <AddEditModal
          mode="edit"
          initial={editItem}
          onClose={() => { setEditItem(null); updateMutation.reset(); }}
          onSubmit={handleEdit}
          isLoading={updateMutation.isPending}
          error={getMutationError(updateMutation)}
        />
      )}

      {deleteItem && (
        <DeleteConfirm
          item={deleteItem}
          onClose={() => { setDeleteItem(null); deleteMutation.reset(); }}
          onConfirm={handleDelete}
          isLoading={deleteMutation.isPending}
          error={getMutationError(deleteMutation)}
        />
      )}
    </PageContainer>
  );
};
