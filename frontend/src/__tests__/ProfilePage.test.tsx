import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfilePage } from '../pages/ProfilePage';
import * as profileApi from '../api/profile';
import { UserProfile } from '../types';

vi.mock('../api/profile', () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

const mockProfile: UserProfile = {
  id: 'user-123',
  email: 'rajesh@example.com',
  full_name: 'Rajesh Kumar',
  preference: {
    dietary_type: 'Vegetarian',
    weekly_budget: 2500,
    household_size: 4,
    disliked_ingredients: [],
  },
};

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

function renderProfilePage() {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProfilePage — Live API & Preferences Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading state ────────────────────────────────────────────────────────
  it('shows loading spinner while fetching profile', () => {
    vi.spyOn(profileApi, 'getProfile').mockReturnValue(new Promise(() => {}));
    renderProfilePage();
    expect(screen.getByText(/loading profile/i)).toBeInTheDocument();
  });

  // ── Render loaded state ──────────────────────────────────────────────────
  it('displays loaded user profile information and target budgets', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(mockProfile);
    renderProfilePage();

    expect(await screen.findByText('Rajesh Kumar')).toBeInTheDocument();
    expect(screen.getByText(/rajesh@example.com/i)).toBeInTheDocument();
    expect(screen.getByText('Vegetarian')).toBeInTheDocument();
    expect(screen.getByText('₹2,500 / week')).toBeInTheDocument();
    expect(screen.getByText('4 Servings')).toBeInTheDocument();

    // Check budget breakdowns (calculated targets)
    const elementsWith2500 = screen.getAllByText('₹2,500');
    expect(elementsWith2500.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('₹10,000')).toBeInTheDocument();
  });

  // ── Error state ──────────────────────────────────────────────────────────
  it('shows error message if profile retrieval fails', async () => {
    vi.spyOn(profileApi, 'getProfile').mockRejectedValue({ message: 'Profile API down' });
    renderProfilePage();

    expect(await screen.findByText(/failed to load profile settings/i)).toBeInTheDocument();
    expect(screen.getByText('Profile API down')).toBeInTheDocument();
  });

  // ── Toggle edit mode ─────────────────────────────────────────────────────
  it('opens input controls when Edit Preferences is clicked', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(mockProfile);
    renderProfilePage();

    await screen.findByText('Rajesh Kumar');
    
    const editBtn = screen.getByRole('button', { name: /edit preferences/i });
    act(() => {
      fireEvent.click(editBtn);
    });

    // Wait for inputs to be rendered using findByLabelText
    expect(await screen.findByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/dietary preference/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/weekly grocery target/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/household members/i)).toBeInTheDocument();

    // Buttons should toggle to Cancel & Save Settings
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save settings/i })).toBeInTheDocument();
  });

  // ── Successful update ────────────────────────────────────────────────────
  it('calls updateProfile API on valid save and displays success message', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(mockProfile);
    const updateSpy = vi.spyOn(profileApi, 'updateProfile').mockResolvedValue({
      ...mockProfile,
      full_name: 'Rajesh K',
      preference: {
        ...mockProfile.preference,
        dietary_type: 'Vegan',
        weekly_budget: 3000,
        household_size: 2,
      },
    });

    renderProfilePage();
    await screen.findByText('Rajesh Kumar');

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /edit preferences/i }));
    });

    // Wait for input to render
    const nameInput = await screen.findByLabelText(/full name/i);

    // Make edits
    fireEvent.change(nameInput, { target: { value: 'Rajesh K' } });
    fireEvent.change(screen.getByLabelText(/dietary preference/i), { target: { value: 'Vegan' } });
    fireEvent.change(screen.getByLabelText(/weekly grocery target/i), { target: { value: '3000' } });
    fireEvent.change(screen.getByLabelText(/household members/i), { target: { value: '2' } });

    // Mock getProfile to return updated data on the invalidation refetch
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue({
      ...mockProfile,
      full_name: 'Rajesh K',
      preference: {
        ...mockProfile.preference,
        dietary_type: 'Vegan',
        weekly_budget: 3000,
        household_size: 2,
      },
    });

    // Save
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /save settings/i }));
    });

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        full_name: 'Rajesh K',
        dietary_type: 'Vegan',
        weekly_budget: 3000,
        household_size: 2,
      });
    });

    // Success alert should be present and values updated in read-only mode
    expect(await screen.findByText(/preferences saved successfully/i)).toBeInTheDocument();
    expect(screen.getByText('Rajesh K')).toBeInTheDocument();
    expect(screen.getByText('Vegan')).toBeInTheDocument();
    expect(screen.getByText('₹3,000 / week')).toBeInTheDocument();
    expect(screen.getByText('2 Servings')).toBeInTheDocument();
    expect(screen.getByText('₹12,000')).toBeInTheDocument(); // 3000 * 4
  });

  // ── Validation checks ────────────────────────────────────────────────────
  it('displays local validation error when full name is cleared', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(mockProfile);
    renderProfilePage();
    await screen.findByText('Rajesh Kumar');

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /edit preferences/i }));
    });

    const nameInput = await screen.findByLabelText(/full name/i);
    fireEvent.change(nameInput, { target: { value: ' ' } });

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /save settings/i }));
    });

    expect(await screen.findByText(/full name cannot be empty/i)).toBeInTheDocument();
    expect(profileApi.updateProfile).not.toHaveBeenCalled();
  });

  it('displays validation error when budget is negative or zero', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(mockProfile);
    renderProfilePage();
    await screen.findByText('Rajesh Kumar');

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /edit preferences/i }));
    });

    const budgetInput = await screen.findByLabelText(/weekly grocery target/i);
    fireEvent.change(budgetInput, { target: { value: '-10' } });

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /save settings/i }));
    });

    expect(await screen.findByText(/weekly grocery budget must be a positive number/i)).toBeInTheDocument();
    expect(profileApi.updateProfile).not.toHaveBeenCalled();
  });

  // ── Cancel edits revert state ────────────────────────────────────────────
  it('reverts inputs to existing profile values when Cancel is clicked', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(mockProfile);
    renderProfilePage();
    await screen.findByText('Rajesh Kumar');

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /edit preferences/i }));
    });

    const nameInput = await screen.findByLabelText(/full name/i);
    fireEvent.change(nameInput, { target: { value: 'Anoop' } });

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    });

    expect(screen.queryByLabelText(/full name/i)).not.toBeInTheDocument();
    expect(screen.getByText('Rajesh Kumar')).toBeInTheDocument();
  });
});
