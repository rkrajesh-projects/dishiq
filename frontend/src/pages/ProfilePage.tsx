import React, { useState, useEffect } from 'react';
import { User, Shield, IndianRupee, Users, Wallet, CreditCard, Pencil, Check, X, Loader2, AlertCircle } from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { SectionTitle } from '../components/common/SectionTitle';
import { Button } from '../components/common/Button';
import { formatINR } from '../utils/currency';
import { useProfile, useUpdateProfile } from '../hooks/useProfile';

export const ProfilePage: React.FC = () => {
  const { data: profile, isLoading, isError, error } = useProfile();
  const updateMutation = useUpdateProfile();

  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState('');
  const [dietaryType, setDietaryType] = useState('None');
  const [weeklyBudget, setWeeklyBudget] = useState(2500);
  const [householdSize, setHouseholdSize] = useState(4);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load backend data into state when loaded
  useEffect(() => {
    if (profile) {
      setFullName(profile.full_name);
      setDietaryType(profile.preference.dietary_type);
      setWeeklyBudget(profile.preference.weekly_budget);
      setHouseholdSize(profile.preference.household_size);
    }
  }, [profile]);

  const handleEditToggle = () => {
    if (isEditing) {
      // Revert to current profile values if cancelling
      if (profile) {
        setFullName(profile.full_name);
        setDietaryType(profile.preference.dietary_type);
        setWeeklyBudget(profile.preference.weekly_budget);
        setHouseholdSize(profile.preference.household_size);
      }
      setIsEditing(false);
      setValidationError(null);
      setSaveSuccess(false);
    } else {
      setIsEditing(true);
      setSaveSuccess(false);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    setSaveSuccess(false);

    if (!fullName.trim()) {
      setValidationError('Full Name cannot be empty.');
      return;
    }

    if (weeklyBudget <= 0) {
      setValidationError('Weekly grocery budget must be a positive number.');
      return;
    }

    if (householdSize < 1) {
      setValidationError('Household size must be at least 1.');
      return;
    }

    updateMutation.mutate(
      {
        full_name: fullName.trim(),
        dietary_type: dietaryType,
        weekly_budget: weeklyBudget,
        household_size: householdSize,
      },
      {
        onSuccess: () => {
          setIsEditing(false);
          setSaveSuccess(true);
          // auto-clear success indicator after 3 seconds
          setTimeout(() => setSaveSuccess(false), 3000);
        },
        onError: (err: any) => {
          setValidationError(err.message || 'Failed to save changes.');
        },
      }
    );
  };

  const monthlyBudget = weeklyBudget * 4;
  const shoppingBudget = weeklyBudget;

  const displayError = validationError || (updateMutation.error ? (updateMutation.error as any).message : null);

  return (
    <PageContainer max-w-4xl>
      <SectionTitle
        title="User & Family Kitchen Preferences"
        subtitle="Configure dietary limits, household size, and weekly grocery targets for AI Kitchen Memory"
        action={
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleEditToggle}
                  icon={<X className="w-4 h-4" />}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSave}
                  isLoading={updateMutation.isPending}
                  icon={<Check className="w-4 h-4" />}
                >
                  Save Settings
                </Button>
              </>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleEditToggle}
                icon={<Pencil className="w-4 h-4" />}
              >
                Edit Preferences
              </Button>
            )}
          </div>
        }
      />

      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-400">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
          <span className="text-sm">Loading profile and preferences…</span>
        </div>
      )}

      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-red-600 bg-white rounded-3xl border border-gray-100 p-6 shadow-sm">
          <AlertCircle className="w-8 h-8" />
          <p className="text-sm font-medium">Failed to load profile settings</p>
          <p className="text-xs text-gray-500 text-center max-w-xs">
            {error?.message || 'Could not connect to the profile service.'}
          </p>
        </div>
      )}

      {!isLoading && !isError && profile && (
        <form onSubmit={handleSave} className="space-y-6" noValidate>
          {displayError && (
            <div className="flex items-start gap-2 text-xs text-red-700 bg-red-50 rounded-xl px-4 py-3 shadow-sm border border-red-100">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{displayError}</span>
            </div>
          )}

          {saveSuccess && (
            <div className="flex items-start gap-2 text-xs text-emerald-700 bg-emerald-50 rounded-xl px-4 py-3 shadow-sm border border-emerald-100 font-semibold animate-pulse">
              <Check className="w-4 h-4 shrink-0" />
              <span>Preferences saved successfully! Kitchen Memory updated.</span>
            </div>
          )}

          {/* User Profile Card */}
          <div className="bg-white rounded-3xl border border-gray-100 p-6 shadow-sm flex items-center gap-4">
            <div className="p-4 bg-emerald-50 text-emerald-600 rounded-2xl shrink-0">
              <User className="w-8 h-8" />
            </div>
            <div className="flex-1 min-w-0">
              {isEditing ? (
                <div className="max-w-xs">
                  <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1" htmlFor="full-name">
                    Full Name
                  </label>
                  <input
                    id="full-name"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full border border-gray-200 rounded-xl px-3 py-1.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                    placeholder="E.g. Rajesh Kumar"
                  />
                </div>
              ) : (
                <>
                  <h3 className="text-lg font-bold text-gray-900 truncate">{fullName}</h3>
                  <p className="text-xs text-gray-500 truncate">{profile.email} • DishIQ Premium Kitchen</p>
                </>
              )}
            </div>
          </div>

          {/* Preferences Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Dietary Card */}
            <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
              <Shield className="w-5 h-5 text-emerald-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <label className="text-xs text-gray-500 block mb-1" htmlFor="dietary-preference">Dietary Preference</label>
                {isEditing ? (
                  <select
                    id="dietary-preference"
                    value={dietaryType}
                    onChange={(e) => setDietaryType(e.target.value)}
                    className="w-full border border-gray-200 rounded-xl px-2 py-1 text-sm font-bold text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                  >
                    <option value="None">None</option>
                    <option value="Vegetarian">Vegetarian</option>
                    <option value="Vegan">Vegan</option>
                    <option value="Non-Vegetarian">Non-Vegetarian</option>
                  </select>
                ) : (
                  <span className="font-bold text-sm text-gray-900 capitalize">{dietaryType}</span>
                )}
              </div>
            </div>

            {/* Target Budget Card */}
            <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
              <IndianRupee className="w-5 h-5 text-orange-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <label className="text-xs text-gray-500 block mb-1" htmlFor="weekly-budget">Weekly Grocery Target</label>
                {isEditing ? (
                  <div className="flex items-center gap-1">
                    <input
                      id="weekly-budget"
                      type="number"
                      min="1"
                      step="50"
                      value={weeklyBudget}
                      onChange={(e) => setWeeklyBudget(Math.max(0, parseFloat(e.target.value) || 0))}
                      className="w-full border border-gray-200 rounded-xl px-2 py-1 text-sm font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                    />
                    <span className="text-xs text-gray-500 shrink-0">/ wk</span>
                  </div>
                ) : (
                  <span className="font-bold text-sm text-gray-900">{formatINR(weeklyBudget)} / week</span>
                )}
              </div>
            </div>

            {/* Household Size Card */}
            <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
              <Users className="w-5 h-5 text-amber-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <label className="text-xs text-gray-500 block mb-1" htmlFor="household-size">Household Members</label>
                {isEditing ? (
                  <div className="flex items-center gap-1">
                    <input
                      id="household-size"
                      type="number"
                      min="1"
                      step="1"
                      value={householdSize}
                      onChange={(e) => setHouseholdSize(Math.max(1, parseInt(e.target.value, 10) || 1))}
                      className="w-full border border-gray-200 rounded-xl px-2 py-1 text-sm font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                    />
                    <span className="text-xs text-gray-500 shrink-0">Serv.</span>
                  </div>
                ) : (
                  <span className="font-bold text-sm text-gray-900">{householdSize} Servings</span>
                )}
              </div>
            </div>
          </div>

          {/* Budget Breakdown Card */}
          <div className="bg-white rounded-3xl border border-gray-100 p-6 shadow-sm">
            <h4 className="font-bold text-gray-900 text-sm mb-4">Household Grocery Budget Targets (INR)</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-2xl bg-orange-50/60 border border-orange-100">
                <div className="flex items-center gap-2 text-xs text-orange-700 font-semibold mb-1">
                  <Wallet className="w-4 h-4" />
                  Weekly Budget
                </div>
                <div className="text-xl font-extrabold text-gray-900">{formatINR(weeklyBudget)}</div>
              </div>

              <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-100">
                <div className="flex items-center gap-2 text-xs text-emerald-700 font-semibold mb-1">
                  <CreditCard className="w-4 h-4" />
                  Monthly Budget
                </div>
                <div className="text-xl font-extrabold text-gray-900">{formatINR(monthlyBudget)}</div>
              </div>

              <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-100">
                <div className="flex items-center gap-2 text-xs text-amber-700 font-semibold mb-1">
                  <IndianRupee className="w-4 h-4" />
                  Shopping Target
                </div>
                <div className="text-xl font-extrabold text-gray-900">{formatINR(shoppingBudget)}</div>
              </div>
            </div>
          </div>
        </form>
      )}
    </PageContainer>
  );
};
