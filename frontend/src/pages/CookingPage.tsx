import React, { useState, useMemo } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ChefHat,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  RotateCcw,
  List,
  Check,
  Star,
  AlertCircle,
  Pause,
  Play,
  CheckSquare,
  Package,
  X,
  Clock,
  Sparkles,
} from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { Button } from '../components/common/Button';
import { getRecipe } from '../api/recipes';
import { CookingTimerCard } from '../components/recipe/CookingTimerCard';
import { CookingCompanionCard } from '../components/recipe/CookingCompanionCard';
import { StepIngredientsCard } from '../components/recipe/StepIngredientsCard';
import { PreparationChecklistCard } from '../components/recipe/PreparationChecklistCard';
import { matchStepIngredients } from '../utils/stepIngredientMatcher';
import {
  useCookingSession,
  useNextStep,
  usePreviousStep,
  useCompleteSession,
  usePauseSession,
  useResumeSession,
  usePreparationChecklist,
  useUpdatePreparedIngredients,
} from '../hooks/useCooking';
import { useSubmitRecipeFeedback } from '../hooks/useFeedback';
import { usePreviewConsumption, useConfirmConsumption } from '../hooks/usePantry';
import { ConsumptionPreviewResponse } from '../types';

export interface CookingStep {
  index: number;
  stepNumber: number;
  instruction: string;
}

/**
 * Reusable utility to parse recipe instruction strings into structured steps.
 */
export function parseRecipeInstructions(instructions: string[]): CookingStep[] {
  if (!instructions) return [];
  return instructions.map((inst, idx) => ({
    index: idx,
    stepNumber: idx + 1,
    instruction: inst,
  }));
}

/**
 * Deterministically parses a step instruction for duration keywords.
 * Converts recognized patterns (minutes, mins, min, hours, hr) to seconds.
 * Returns 0 if no duration found or if multiple durations exist.
 */
export function parseDuration(instruction: string): number {
  if (!instruction) return 0;
  const cleanStr = instruction.toLowerCase().trim();

  // Check if multiple durations exist to avoid ambiguity (e.g. "Boil for 5 minutes, then simmer for 10 minutes")
  const timeWordCount = (cleanStr.match(/(?:minute|min|hour|hr)s?/g) || []).length;
  const hrMinRegex = /(\d+)\s*(?:hour|hr)s?\s*(\d+)\s*(?:minute|min)s?/;
  if (timeWordCount > 2 || (timeWordCount === 2 && !hrMinRegex.test(cleanStr))) {
    return 0; // Exclude multiple durations
  }

  // Pattern: X hour(s) Y minute(s)/min(s)
  const hrMinMatch = cleanStr.match(hrMinRegex);
  if (hrMinMatch) {
    const hours = parseInt(hrMinMatch[1], 10);
    const minutes = parseInt(hrMinMatch[2], 10);
    return hours * 3600 + minutes * 60;
  }

  // Pattern: X hour(s)/hr(s)
  const hrRegex = /(\d+)\s*(?:hour|hr)s?/;
  const hrMatch = cleanStr.match(hrRegex);
  if (hrMatch) {
    const hours = parseInt(hrMatch[1], 10);
    return hours * 3600;
  }

  // Pattern: X minute(s)/min(s)/mins
  const minRegex = /(\d+)\s*(?:minute|min)s?/;
  const minMatch = cleanStr.match(minRegex);
  if (minMatch) {
    const minutes = parseInt(minMatch[1], 10);
    return minutes * 60;
  }

  return 0;
}

/**
 * CookingErrorBoundary — local error boundary for the Cooking page only.
 * Renders the actual exception message and stack in the DOM so it can be
 * read by Playwright / DevTools even when the top-level boundary swallows it.
 * This is a temporary diagnostic aid; once the crash is fixed this component
 * will never activate in normal usage.
 */
class CookingErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Surface to DevTools console with full detail
    console.error('[CookingPage crash]', error, info.componentStack ?? '(no stack available)');
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'monospace', background: '#fff0f0', border: '2px solid red', borderRadius: 8, margin: 16 }}>
          <h3 data-testid="cooking-crash-heading" style={{ color: 'red', marginTop: 0 }}>
            CookingPage Render Error (diagnostic)
          </h3>
          <p data-testid="cooking-crash-message" style={{ fontWeight: 'bold' }}>
            {this.state.error.message}
          </p>
          <pre data-testid="cooking-crash-stack" style={{ fontSize: 11, whiteSpace: 'pre-wrap', color: '#333' }}>
            {this.state.error.stack?.split('\n').slice(0, 10).join('\n')}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export const CookingPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  // Search params for mode (prep vs cooking)
  const [searchParams] = useSearchParams();
  const initialMode = searchParams.get('mode') === 'prep' ? 'prep' : 'cooking';
  const [activeView, setActiveView] = useState<'cooking' | 'prep'>(initialMode);

  // Phase 12: Sidebar Tab Switcher (AI Cooking Companion vs Ingredients Reference)
  const [sidebarTab, setSidebarTab] = useState<'ingredients' | 'companion'>('ingredients');

  // Timer running status to warn before step change or completion
  const [isTimerRunning, setIsTimerRunning] = useState(false);

  // Frontend-local cooking step checklist state (Phase 9.7)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  // Inline navigation error (replaces browser alert() calls)
  const [navError, setNavError] = useState<string | null>(null);

  // Recipe Feedback states (Phase 11.3)
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackDifficulty, setFeedbackDifficulty] = useState<string>('Medium');
  const [feedbackNotes, setFeedbackNotes] = useState<string>('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  // Focus management refs (Phase 9.9)
  const stepHeadingRef = React.useRef<HTMLHeadingElement | HTMLSpanElement>(null);
  const completionHeadingRef = React.useRef<HTMLHeadingElement>(null);
  const errorRef = React.useRef<HTMLDivElement>(null);
  const navErrorRef = React.useRef<HTMLDivElement>(null);

  const toggleStepCompletion = (stepIndex: number) => {
    setCompletedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepIndex)) {
        next.delete(stepIndex);
      } else {
        next.add(stepIndex);
      }
      return next;
    });
  };

  // 1. Fetch Cooking Session
  const {
    data: session,
    isLoading: sessionLoading,
    isError: sessionError,
    error: sessionErrDetail,
    refetch: refetchSession,
  } = useCookingSession(sessionId || '');

  // 2. Fetch Recipe (only if session is successfully loaded)
  const recipeId = session?.recipe_id;
  const {
    data: recipe,
    isLoading: recipeLoading,
    isError: recipeError,
    error: recipeErrDetail,
    refetch: refetchRecipe,
  } = useQuery({
    queryKey: ['recipe', recipeId],
    queryFn: () => getRecipe(recipeId!),
    enabled: Boolean(recipeId),
  });

  const baseServings = recipe?.servings || 4;
  const effectiveServings = session?.servings || baseServings;
  const scaleFactor = baseServings > 0 ? effectiveServings / baseServings : 1;

  // 3. Navigation Mutations
  const nextMutation = useNextStep(sessionId || '');
  const prevMutation = usePreviousStep(sessionId || '');
  const completeMutation = useCompleteSession(sessionId || '');

  // 4. Phase 10: Pause & Resume and Preparation Checklist hooks
  const pauseMutation = usePauseSession(sessionId || '');
  const resumeMutation = useResumeSession(sessionId || '');
  const { data: checklist, isLoading: checklistLoading } = usePreparationChecklist(sessionId || '');
  const updatePreparedMutation = useUpdatePreparedIngredients(sessionId || '');

  const handleTogglePrepared = (ingredientKey: string) => {
    if (!session) return;
    const current = new Set(session.prepared_ingredients || []);
    if (current.has(ingredientKey)) {
      current.delete(ingredientKey);
    } else {
      current.add(ingredientKey);
    }
    updatePreparedMutation.mutate(Array.from(current));
  };

  const handleMarkAllPrepared = () => {
    if (!checklist) return;
    const allKeys = checklist.items.map((it) => it.name || it.id);
    updatePreparedMutation.mutate(allKeys);
  };

  const handlePause = () => {
    pauseMutation.mutate(undefined, {
      onError: () => setNavError('Could not pause cooking session.'),
    });
  };

  const handleResume = () => {
    resumeMutation.mutate(undefined, {
      onError: () => setNavError('Could not resume cooking session.'),
    });
  };

  // 5. Feedback mutation — must be declared here unconditionally (Rules of Hooks).
  const feedbackMutation = useSubmitRecipeFeedback(recipeId || '');

  // 6. Phase 11: Explicit Pantry Consumption hooks
  const previewConsumptionMutation = usePreviewConsumption();
  const confirmConsumptionMutation = useConfirmConsumption();
  const [consumptionPreview, setConsumptionPreview] = useState<ConsumptionPreviewResponse | null>(null);
  const [showConsumptionModal, setShowConsumptionModal] = useState(false);
  const [consumptionConfirmed, setConsumptionConfirmed] = useState(false);
  const [consumptionError, setConsumptionError] = useState<string | null>(null);

  const isNavigating = nextMutation.isPending || prevMutation.isPending || completeMutation.isPending || pauseMutation.isPending || resumeMutation.isPending;

  // Focus step heading on step change (Phase 9.9)
  React.useEffect(() => {
    setNavError(null); // Clear nav error when step changes
    if (stepHeadingRef.current) {
      stepHeadingRef.current.focus();
    }
  }, [session?.current_step, recipe, sessionLoading, recipeLoading]);

  // Focus navigation error when it appears (Phase 9.10)
  React.useEffect(() => {
    if (navError && navErrorRef.current) {
      navErrorRef.current.focus();
    }
  }, [navError]);

  // Focus completion heading on cooking completion (Phase 9.9)
  React.useEffect(() => {
    const isComp = session?.status === 'completed';
    if (isComp && completionHeadingRef.current) {
      completionHeadingRef.current.focus();
    }
  }, [session?.status, recipe, sessionLoading, recipeLoading]);

  // Focus error message container if error occurs (Phase 9.9)
  React.useEffect(() => {
    if ((sessionError || recipeError) && errorRef.current) {
      errorRef.current.focus();
    }
  }, [sessionError, recipeError]);

  // Intelligently identify step-specific ingredients (declared before early returns)
  const stepIngredients = useMemo(() => {
    if (!recipe || !recipe.instructions || !session) return [];
    const parsed = parseRecipeInstructions(recipe.instructions);
    let stepIdx = session.current_step ?? 0;
    if (stepIdx < 0) {
      stepIdx = 0;
    } else if (parsed.length > 0 && stepIdx >= parsed.length) {
      stepIdx = parsed.length - 1;
    }
    const currentStep = parsed[stepIdx];
    if (!currentStep) return [];
    return matchStepIngredients(currentStep.instruction, recipe.ingredients || []);
  }, [recipe, session]);

  if (!sessionId) {
    return (
      <PageContainer>
        <ErrorState
          title="No active cooking session"
          message="Please select a recipe and start cooking to begin."
          onRetry={() => navigate('/recipes')}
        />
      </PageContainer>
    );
  }

  if (sessionLoading || (recipeId && recipeLoading)) {
    return <LoadingState message="Loading cooking assistant..." />;
  }

  if (sessionError) {
    const msg = (sessionErrDetail as { message?: string })?.message ?? 'Cooking session could not be found.';
    return (
      <PageContainer>
        <div ref={errorRef} tabIndex={-1} className="focus:outline-none focus:ring-2 focus:ring-red-500 rounded-2xl">
          <ErrorState
            title="Session Not Found"
            message={msg}
            onRetry={() => refetchSession()}
          />
          <div className="text-center mt-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/recipes')}>
              ← Browse Recipes
            </Button>
          </div>
        </div>
      </PageContainer>
    );
  }

  if (recipeError || !recipe) {
    const msg = (recipeErrDetail as { message?: string })?.message ?? 'Associated recipe details could not be loaded.';
    return (
      <PageContainer>
        <div ref={errorRef} tabIndex={-1} className="focus:outline-none focus:ring-2 focus:ring-red-500 rounded-2xl">
          <ErrorState
            title="Recipe Not Found"
            message="The recipe for this cooking session could not be loaded. It may have been removed."
            onRetry={() => refetchRecipe()}
          />
          <div className="text-center mt-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/recipes')}>
              ← Browse Recipes
            </Button>
          </div>
        </div>
      </PageContainer>
    );
  }

  const parsedSteps = parseRecipeInstructions(recipe.instructions || []);
  const totalSteps = parsedSteps.length;
  const isCompleted = session?.status === 'completed';

  // ── EMPTY INSTRUCTIONS STATE ───────────────────────────────────────────
  if (totalSteps === 0) {
    return (
      <PageContainer>
        <div className="max-w-md mx-auto bg-white rounded-3xl border border-gray-100 p-8 text-center shadow-sm">
          <p className="text-sm text-gray-600 mb-6">
            Cooking instructions aren't available for this recipe.
          </p>
          <Button variant="outline" onClick={() => navigate(`/recipes/${recipe.id}`)}>
            Back to Recipe
          </Button>
        </div>
      </PageContainer>
    );
  }

  // ── SAFETY CLAMPING FOR INVALID BACKEND STEP VALUES ─────────────────────
  let currentStepIndex = session?.current_step ?? 0;
  if (currentStepIndex < 0) {
    currentStepIndex = 0;
  } else if (currentStepIndex >= totalSteps) {
    currentStepIndex = totalSteps - 1;
  }

  const currentStep = parsedSteps[currentStepIndex];

  
  // Progress formula represents completion:
  // - Being on Step 1 = 0 steps completed = 0%
  // - Being on final step = (total-1)/total %
  // - Completed screen = 100%
  const percentComplete = isCompleted
    ? 100
    : Math.round((currentStepIndex / totalSteps) * 100);

  const handleSubmitFeedback = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackError(null);

    if (feedbackRating < 1 || feedbackRating > 5) {
      setFeedbackError('Please select a rating between 1 and 5 stars.');
      return;
    }

    feedbackMutation.mutate(
      {
        rating: feedbackRating,
        difficulty: feedbackDifficulty,
        notes: feedbackNotes.trim() || undefined,
      },
      {
        onSuccess: () => {
          setFeedbackSubmitted(true);
        },
        onError: (err: any) => {
          const msg = err.response?.data?.error?.message || err.message || 'Failed to submit feedback.';
          setFeedbackError(msg);
        },
      }
    );
  };

  const handleSkipFeedback = () => {
    setFeedbackSubmitted(true);
  };

  // Render Completed UI State
  if (isCompleted) {
    return (
      <PageContainer>
        <div className="max-w-xl mx-auto bg-white rounded-3xl border border-emerald-100/60 p-8 text-center shadow-md my-8">
          <div className="w-20 h-20 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-12 h-12" />
          </div>
          <h1
            ref={completionHeadingRef}
            tabIndex={-1}
            className="text-3xl font-extrabold text-gray-900 mb-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 rounded-lg"
          >
            🎉 Cooking Complete!
          </h1>
          <p className="text-gray-600 mb-6 leading-relaxed">
            Congratulations! You have completed cooking <strong>{recipe.name}</strong>. We hope you enjoy your meal!
          </p>

          {!feedbackSubmitted ? (
            <form onSubmit={handleSubmitFeedback} className="border-t border-gray-100 pt-6 mt-6 max-w-md mx-auto" noValidate>
              <h2 className="text-sm font-bold text-gray-800 mb-3">How was your cooking experience?</h2>
              
              {/* Star rating selector */}
              <div className="flex items-center justify-center gap-1.5 mb-4">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setFeedbackRating(star)}
                    className="p-1 text-gray-300 hover:text-amber-400 focus:outline-none transition-colors"
                    aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
                  >
                    <Star
                      className={`w-8 h-8 ${
                        star <= feedbackRating
                          ? 'text-amber-400 fill-amber-400'
                          : 'text-gray-300'
                      }`}
                    />
                  </button>
                ))}
              </div>

              {/* Difficulty selector */}
              <div className="mb-4 text-left">
                <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="feedback-difficulty">
                  Recipe Difficulty
                </label>
                <select
                  id="feedback-difficulty"
                  value={feedbackDifficulty}
                  onChange={(e) => setFeedbackDifficulty(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white font-medium"
                >
                  <option value="Easy">Easy</option>
                  <option value="Medium">Medium</option>
                  <option value="Hard">Hard</option>
                </select>
              </div>

              {/* Optional notes */}
              <div className="mb-6 text-left">
                <label className="block text-xs font-semibold text-gray-600 mb-1" htmlFor="feedback-notes">
                  Optional Notes & Remarks
                </label>
                <textarea
                  id="feedback-notes"
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="Tell us what you liked or how you customized it..."
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 h-20 resize-none"
                />
              </div>

              {feedbackError && (
                <div className="mb-4 text-xs text-red-700 bg-red-50 rounded-xl px-3 py-2 text-left border border-red-100 flex items-start gap-2">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>{feedbackError}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-center gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleSkipFeedback}
                >
                  Skip Feedback
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={feedbackMutation.isPending}
                  disabled={feedbackRating === 0}
                >
                  Submit Feedback
                </Button>
              </div>
            </form>
          ) : (
            <div className="border-t border-gray-100 pt-6 mt-6">
              <p className="text-xs text-emerald-700 bg-emerald-50 rounded-xl px-4 py-3 border border-emerald-100 font-semibold mb-6 animate-pulse">
                ✓ Thank you! Your feedback has been applied to your Kitchen Memory.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Button
                  variant="outline"
                  icon={<RotateCcw className="w-4 h-4" />}
                  onClick={() => navigate(`/recipes/${recipe.id}`)}
                >
                  Back to Recipe Details
                </Button>
                <Button
                  variant="primary"
                  icon={<ChefHat className="w-4 h-4" />}
                  onClick={() => navigate('/recipes')}
                >
                  Explore More Recipes
                </Button>
              </div>
            </div>
          )}

          {/* Phase 11: Explicit Pantry Inventory Deduction Review */}
          <div className="border-t border-gray-100 pt-6 mt-6 text-left bg-emerald-50/40 rounded-2xl p-5 border border-emerald-100/60">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Package className="w-5 h-5 text-emerald-700" />
                <h3 className="text-sm font-bold text-gray-900">Pantry Inventory Tracking</h3>
              </div>
              {consumptionConfirmed ? (
                <span className="text-[10px] font-extrabold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                  <Check className="w-3 h-3" /> Stock Updated
                </span>
              ) : (
                <span className="text-[10px] font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                  Optional
                </span>
              )}
            </div>
            <p className="text-xs text-gray-600 mb-4 leading-relaxed">
              {consumptionConfirmed
                ? "Ingredients used for this cooking session have been deducted from your pantry stock."
                : "Would you like to deduct the ingredients used in this recipe from your pantry inventory?"}
            </p>

            {!consumptionConfirmed && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                icon={<Package className="w-3.5 h-3.5 text-emerald-600" />}
                onClick={() => {
                  setConsumptionError(null);
                  previewConsumptionMutation.mutate(
                    {
                      recipe_id: recipe.id,
                      cooking_session_id: session?.id,
                      servings: effectiveServings,
                    },
                    {
                      onSuccess: (data) => {
                        setConsumptionPreview(data);
                        setShowConsumptionModal(true);
                      },
                      onError: () => {
                        setConsumptionError('Could not load consumption preview.');
                      },
                    }
                  );
                }}
                isLoading={previewConsumptionMutation.isPending}
              >
                Review & Deduct Pantry Stock
              </Button>
            )}

            {consumptionError && (
              <p className="text-[11px] text-red-600 font-semibold mt-2">{consumptionError}</p>
            )}
          </div>
        </div>

        {/* Phase 11: Consumption Confirmation Modal */}
        {showConsumptionModal && consumptionPreview && (
          <div
            className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Review Pantry Deductions"
          >
            <div className="bg-white rounded-3xl shadow-2xl p-6 w-full max-w-lg max-h-[85vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Package className="w-5 h-5 text-emerald-700" />
                  <h2 className="font-bold text-gray-900 text-lg">Pantry Deductions Review</h2>
                </div>
                <button
                  onClick={() => setShowConsumptionModal(false)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                  aria-label="Close modal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <p className="text-xs text-gray-600 mb-4">
                Review ingredients required for <strong>{effectiveServings} servings</strong> against your current pantry stock. Unmatched or incompatible items will not be deducted.
              </p>

              <div className="space-y-2 mb-5">
                {consumptionPreview.items.map((it, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border text-xs flex items-center justify-between gap-3 ${
                      it.can_deduct
                        ? 'border-emerald-100 bg-emerald-50/30'
                        : 'border-gray-100 bg-gray-50/50 text-gray-500'
                    }`}
                  >
                    <div>
                      <span className="font-bold text-gray-900 capitalize block">{it.ingredient_name}</span>
                      <span className="text-[11px] text-gray-500">
                        Recipe requires: {it.required_quantity} {it.required_unit}
                      </span>
                      {it.pantry_item_id && (
                        <span className="text-[11px] text-emerald-700 block">
                          Pantry has: {it.pantry_quantity} {it.pantry_unit} → Deduct: {it.converted_deduct_quantity} {it.pantry_unit}
                        </span>
                      )}
                      {it.reason && (
                        <span className="text-[10px] text-amber-700 block mt-0.5 italic">
                          {it.reason}
                        </span>
                      )}
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                        it.status === 'fully_covered'
                          ? 'bg-emerald-100 text-emerald-800'
                          : it.status === 'partially_covered'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {it.status === 'fully_covered'
                        ? 'Fully Covered'
                        : it.status === 'partially_covered'
                        ? 'Partial Stock'
                        : it.status === 'incompatible_unit'
                        ? 'Incompatible Unit'
                        : 'Not in Stock'}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex gap-3 pt-2 border-t border-gray-100">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowConsumptionModal(false)}
                  className="flex-1"
                >
                  Skip / Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={consumptionPreview.total_deductible_items === 0 || confirmConsumptionMutation.isPending}
                  isLoading={confirmConsumptionMutation.isPending}
                  onClick={() => {
                    const deductibleItems = consumptionPreview.items
                      .filter((it) => it.can_deduct && it.pantry_item_id)
                      .map((it) => ({
                        pantry_item_id: it.pantry_item_id!,
                        deduct_quantity: it.converted_deduct_quantity,
                      }));

                    confirmConsumptionMutation.mutate(
                      {
                        preview_token: consumptionPreview.preview_token,
                        recipe_id: recipe.id,
                        cooking_session_id: session?.id,
                        items: deductibleItems,
                      },
                      {
                        onSuccess: () => {
                          setConsumptionConfirmed(true);
                          setShowConsumptionModal(false);
                        },
                        onError: (err: any) => {
                          setConsumptionError(err?.response?.data?.detail || 'Failed to update pantry stock.');
                        },
                      }
                    );
                  }}
                  className="flex-1"
                >
                  Confirm & Deduct Stock ({consumptionPreview.total_deductible_items})
                </Button>
              </div>
            </div>
          </div>
        )}
      </PageContainer>
    );
  }

  const confirmNavigation = (actionName: string): boolean => {
    if (isTimerRunning) {
      return window.confirm(
        `Timer is still running. Leave this step?`
      );
    }
    return true;
  };

  const handleNext = () => {
    if (isNavigating) return;
    if (!confirmNavigation('leave this step')) return;
    setNavError(null);
    nextMutation.mutate(undefined, {
      onError: () => {
        setNavError('Could not advance to the next step. Please try again.');
      }
    });
  };

  const handlePrevious = () => {
    if (isNavigating) return;
    if (!confirmNavigation('leave this step')) return;
    setNavError(null);
    prevMutation.mutate(undefined, {
      onError: () => {
        setNavError('Could not return to the previous step. Please try again.');
      }
    });
  };

  const handleComplete = () => {
    if (isNavigating) return;
    if (isTimerRunning) {
      const confirmComplete = window.confirm(
        'Timer is still running. Are you sure you want to complete cooking?'
      );
      if (!confirmComplete) return;
    }
    setNavError(null);
    completeMutation.mutate(undefined, {
      onError: () => {
        setNavError('Could not complete the cooking session. Please try again.');
      }
    });
  };

  const isLastStep = currentStepIndex === totalSteps - 1;

  return (
    <PageContainer>
      {/* Back button */}
      <div className="mb-6">
        <Link
          to={`/recipes/${recipe.id}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-gray-500 hover:text-emerald-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Exit to Recipe details</span>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Main Cooking Control panel */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header Card */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex items-center gap-2 text-xs font-medium text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full w-fit">
                    <ChefHat className="w-3.5 h-3.5" />
                    <span>DishIQ Cooking Assistant</span>
                  </div>
                  {session?.status === 'paused' && (
                    <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                      <Pause className="w-3 h-3" /> Paused
                    </span>
                  )}
                </div>
                <h1 className="text-xl sm:text-2xl font-black text-gray-900 leading-tight">
                  {recipe.name}
                </h1>
                <p className="text-xs text-gray-500 mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
                  <span>{recipe.cuisine} Cuisine</span>
                  <span>•</span>
                  <span>Serves {effectiveServings}{effectiveServings !== baseServings ? ` (scaled from ${baseServings})` : ''}</span>
                  <span>•</span>
                  <span>Time: {(recipe.preparation_minutes || 0) + (recipe.cooking_minutes || 0)} mins</span>
                </p>
              </div>

              {/* Pause / Resume Controls */}
              <div className="flex items-center gap-2 shrink-0">
                {session?.status === 'paused' ? (
                  <Button
                    variant="primary"
                    size="sm"
                    icon={<Play className="w-4 h-4" />}
                    onClick={handleResume}
                    isLoading={resumeMutation.isPending}
                    aria-label="Resume cooking"
                  >
                    Resume Cooking
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    icon={<Pause className="w-4 h-4" />}
                    onClick={handlePause}
                    isLoading={pauseMutation.isPending}
                    aria-label="Pause cooking"
                  >
                    Pause
                  </Button>
                )}
              </div>
            </div>

            {/* View Switcher: Cooking Steps vs Preparation Checklist */}
            <div className="flex items-center gap-3 border-t border-gray-100 pt-4 mt-4">
              <button
                type="button"
                onClick={() => setActiveView('cooking')}
                className={`text-xs font-bold transition-all px-3.5 py-1.5 rounded-xl flex items-center gap-1.5 ${
                  activeView === 'cooking'
                    ? 'bg-emerald-700 text-white shadow-xs'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <ChefHat className="w-3.5 h-3.5" />
                <span>Cooking Steps</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveView('prep')}
                className={`text-xs font-bold transition-all px-3.5 py-1.5 rounded-xl flex items-center gap-1.5 ${
                  activeView === 'prep'
                    ? 'bg-emerald-700 text-white shadow-xs'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <CheckSquare className="w-3.5 h-3.5" />
                <span>Preparation Checklist</span>
                {checklist && (
                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                    activeView === 'prep' ? 'bg-white/20 text-white' : 'bg-emerald-100 text-emerald-800'
                  }`}>
                    {checklist.prepared_count}/{checklist.total_ingredients}
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Inline navigation error banner (Phase 9.10) */}
          {navError && (
            <div
              ref={navErrorRef}
              tabIndex={-1}
              role="alert"
              className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-xs font-medium text-red-700 flex items-center justify-between gap-3 focus:outline-none focus:ring-2 focus:ring-red-400"
            >
              <span>{navError}</span>
              <button
                onClick={() => setNavError(null)}
                aria-label="Dismiss error"
                className="shrink-0 text-red-500 hover:text-red-700 transition-colors text-lg leading-none"
              >
                ×
              </button>
            </div>
          )}

          {/* Conditional View: Preparation Checklist vs Step-by-Step Cooking */}
          {activeView === 'prep' ? (
            <PreparationChecklistCard
              checklist={checklist}
              isLoading={checklistLoading}
              onToggleIngredient={handleTogglePrepared}
              onMarkAllPrepared={handleMarkAllPrepared}
              onContinueToCooking={() => setActiveView('cooking')}
              isUpdating={updatePreparedMutation.isPending}
            />
          ) : (
            <>
              {/* Step Progress bar */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-gray-700">
              <span>Step {currentStepIndex + 1} of {totalSteps}</span>
              <span className="text-emerald-700">{percentComplete}% Complete</span>
            </div>
            <div className="text-[10px] text-gray-500 font-medium">
              {completedSteps.size} of {totalSteps} steps completed
            </div>
            <div className="w-full bg-gray-100 h-3 rounded-full overflow-hidden">
              <div
                className="bg-emerald-600 h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${percentComplete}%` }}
                aria-valuenow={percentComplete}
                aria-valuemin={0}
                aria-valuemax={100}
                role="progressbar"
                aria-label="Cooking progress percentage"
              />
            </div>
          </div>

          {/* Current Step Instruction Card */}
          <div className="bg-white rounded-3xl border border-gray-100 p-8 sm:p-10 shadow-sm relative overflow-hidden min-h-[220px] flex flex-col justify-between">
            <div>
              <span
                ref={stepHeadingRef}
                tabIndex={-1}
                className="text-xs uppercase font-extrabold tracking-wider text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full w-fit mb-4 block focus:outline-none focus:ring-2 focus:ring-emerald-500 rounded-lg"
              >
                {isLastStep ? 'Final Step' : `Instruction Step ${currentStep.stepNumber}`}
              </span>
              <p className="text-xl sm:text-2xl font-semibold text-gray-800 leading-relaxed">
                {currentStep.instruction}
              </p>
            </div>

            {/* Checklist Completion Toggle Button */}
            <div className="mt-6 flex items-center justify-start">
              <Button
                variant={completedSteps.has(currentStepIndex) ? 'outline' : 'primary'}
                size="sm"
                icon={completedSteps.has(currentStepIndex) ? <Check className="w-4 h-4 text-emerald-600" /> : undefined}
                onClick={() => toggleStepCompletion(currentStepIndex)}
                aria-label={completedSteps.has(currentStepIndex) ? `Mark step ${currentStep.stepNumber} as incomplete` : `Mark step ${currentStep.stepNumber} as complete`}
              >
                {completedSteps.has(currentStepIndex) ? 'Step Completed (Mark Incomplete)' : 'Mark Step Complete'}
              </Button>
            </div>

            {/* Bottom Panel Actions */}
            <div className="flex flex-wrap items-center justify-between gap-4 mt-8 pt-6 border-t border-gray-50">
              <Button
                variant="outline"
                icon={<ChevronLeft className="w-5 h-5" />}
                onClick={handlePrevious}
                disabled={currentStepIndex === 0 || isNavigating}
              >
                Previous Step
              </Button>

              {isLastStep ? (
                <Button
                  variant="primary"
                  icon={<CheckCircle className="w-5 h-5" />}
                  onClick={handleComplete}
                  isLoading={completeMutation.isPending}
                  disabled={isNavigating}
                >
                  Complete Cooking
                </Button>
              ) : (
                <Button
                  variant="primary"
                  icon={<ChevronRight className="w-5 h-5" />}
                  iconPosition="right"
                  onClick={handleNext}
                  isLoading={nextMutation.isPending}
                  disabled={isNavigating}
                >
                  Next Step
                </Button>
              )}
            </div>
          </div>

          {/* Step Ingredients Card */}
          <StepIngredientsCard matchedIngredients={stepIngredients} />

          {/* Cooking Timer Card */}
          <CookingTimerCard
            key={currentStepIndex}
            stepDuration={parseDuration(currentStep.instruction)}
            stepLabel={`Step ${currentStep.stepNumber}`}
            onTimerRunningChange={setIsTimerRunning}
          />

          {/* Interactive Steps List Timeline */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <List className="w-4 h-4 text-emerald-600" />
              <span>Recipe Steps Progress</span>
            </h3>
            <ol className="space-y-3" aria-label="Recipe steps progress list">
              {parsedSteps.map((step) => {
                const isStepCompleted = completedSteps.has(step.index);
                const isCurrent = step.index === currentStepIndex;

                let statusIcon = '○';
                let statusText = 'upcoming';
                let statusClass = 'text-gray-400 bg-gray-50 border-gray-100';

                if (isStepCompleted) {
                  statusIcon = '✓';
                  statusText = isCurrent ? 'current step, completed' : 'completed';
                  statusClass = isCurrent
                    ? 'text-emerald-800 bg-emerald-50 border-2 border-emerald-600 font-bold'
                    : 'text-emerald-700 bg-emerald-50/50 border-emerald-200';
                } else if (isCurrent) {
                  statusIcon = '●';
                  statusText = 'current step';
                  statusClass = 'text-gray-900 bg-white border-2 border-emerald-600 font-bold';
                } else if (step.index < currentStepIndex) {
                  statusText = 'previous step';
                  statusClass = 'text-gray-500 bg-gray-50 border-gray-100';
                }

                const ariaLabel = `Step ${step.stepNumber} of ${totalSteps}, ${statusText}`;

                return (
                  <li
                    key={step.index}
                    className={`text-xs p-3 rounded-lg border flex items-start gap-2.5 transition-all duration-200 ${statusClass}`}
                    aria-label={ariaLabel}
                    aria-current={isCurrent ? 'step' : undefined}
                  >
                    <span className="shrink-0 font-bold text-xs" aria-hidden="true">
                      {statusIcon}
                    </span>
                    <div className="flex-1">
                      <span className="font-bold text-[10px] block uppercase tracking-wider mb-0.5">
                        Step {step.stepNumber}
                      </span>
                      <p className="line-clamp-2 leading-relaxed">
                        {step.instruction}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
            </>
          )}
        </div>

        {/* Sidebar panel with Tab Switching: AI Cooking Companion vs Ingredients Reference */}
        <div className="lg:col-span-1 space-y-4">
          <div className="flex items-center gap-1.5 p-1 bg-gray-100/80 rounded-xl border border-gray-200/60">
            <button
              type="button"
              onClick={() => setSidebarTab('companion')}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                sidebarTab === 'companion'
                  ? 'bg-white text-emerald-900 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              aria-label="Show AI Cooking Companion"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>AI Companion</span>
            </button>
            <button
              type="button"
              onClick={() => setSidebarTab('ingredients')}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                sidebarTab === 'ingredients'
                  ? 'bg-white text-emerald-900 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              aria-label="Show Recipe Ingredients Reference"
            >
              <List className="w-3.5 h-3.5 text-gray-500" />
              <span>Ingredients</span>
            </button>
          </div>

          {sidebarTab === 'companion' ? (
            <CookingCompanionCard
              sessionId={session?.id || sessionId || ''}
              recipeName={recipe.name}
              currentStepIndex={currentStepIndex}
              totalSteps={totalSteps}
              currentInstruction={currentStep?.instruction}
            />
          ) : (
            <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
              <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                <List className="w-4 h-4 text-emerald-600" />
                <span>Recipe Ingredients Reference</span>
              </h3>
              <ul className="space-y-3" aria-label="Recipe ingredients reference list">
                {recipe.ingredients && recipe.ingredients.map((ri, index) => {
                  const isHighlighted = stepIngredients.some(si => si.id === ri.id);
                  const itemAria = isHighlighted 
                    ? `${ri.ingredient?.canonical_name || 'Ingredient'}, relevant to current step`
                    : ri.ingredient?.canonical_name || 'Ingredient';

                  const scaledQty = (ri.quantity !== null && ri.quantity !== undefined && scaleFactor !== 1)
                    ? Math.round(ri.quantity * scaleFactor * 100) / 100
                    : ri.quantity;

                  return (
                    <li
                      key={ri.id || index}
                      className={`text-xs p-2.5 rounded-lg border flex flex-col gap-0.5 transition-all duration-200 ${
                        isHighlighted 
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-950 font-medium ring-2 ring-emerald-100/50'
                          : 'text-gray-700 bg-gray-50 border-gray-100'
                      }`}
                      aria-label={itemAria}
                    >
                      <span className="font-semibold capitalize flex items-center justify-between">
                        <span>{ri.ingredient?.canonical_name || 'Ingredient'}</span>
                        {isHighlighted && (
                          <span className="text-[9px] uppercase tracking-wider font-extrabold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                            Current Step
                          </span>
                        )}
                      </span>
                      <span className={`text-[10px] ${isHighlighted ? 'text-emerald-700' : 'text-gray-500'}`}>
                        Quantity: {scaledQty} {ri.unit} {ri.preparation_note ? `(${ri.preparation_note})` : ''}
                      </span>
                      <span className={`text-[10px] italic ${isHighlighted ? 'text-emerald-600/70' : 'text-gray-400'}`}>
                        {ri.raw_text}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
};

/**
 * CookingPage wrapped in its own local error boundary.
 * Used in AppRoutes instead of the bare CookingPage so that the specific
 * crash message and stack are surfaced in the DOM for diagnosis.
 */
export const CookingPageWithBoundary: React.FC = () => (
  <CookingErrorBoundary>
    <CookingPage />
  </CookingErrorBoundary>
);

