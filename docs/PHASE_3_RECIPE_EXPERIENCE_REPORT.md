# DishIQ — Phase 3: Recipe Catalogue & Recipe Experience Report

## 1. Executive Summary

Phase 3 focused on auditing and enhancing the DishIQ recipe catalogue and user experience across the full discovery and cooking preparation journey:
**Discover → Understand → Plan → Shop → Cook**

All enhancements strictly preserved existing application architectures, ML models, Swiggy Instamart OAuth PKCE integrations, and the DishIQ visual identity (`#FAF8F3` background, `#245C45` primary green, `#D97757` accent coral, `#26332E` dark green text).

### Test Suite Status Summary
- **Backend Tests:** **375 passed** (+6 new dedicated catalogue tests, 0 failed, 0 skipped)
- **ML Tests:** **39 passed** (0 failed, 0 skipped)
- **Frontend Tests:** **267 passed** (+7 new recipe detail tests across 30 test suites, 0 failed)
- **Frontend Production Build:** **Built successfully** with Vite 5.4.21 & TypeScript (`tsc && vite build` exited with code 0)

---

## 2. Recipe Catalogue Audit & Findings

A comprehensive audit of `backend/dishiq.db` was performed:
- **Total Recipes:** 1,040 recipes
  - **Food.com Dataset:** 1,011 recipes
  - **DishIQ Demo:** 15 recipes
  - **Archana's Kitchen:** 10 recipes
  - **INDoRI:** 3 recipes
  - **CommunityCookbook:** 1 recipe
- **Ingredients & Mappings:** 1,404 distinct canonical ingredients; 9,032 recipe-ingredient associations.
- **Data Quality:**
  - 0 missing recipe titles
  - 0 missing instructions
  - 0 negative preparation or cooking times
  - 0 duplicate recipe names
- **Identified Defect & Correction:**
  - Archana's Kitchen dataset had fragmented cuisine labels ending with `" Recipes"` (e.g., `South Indian Recipes` [2] vs `South Indian` [3], `North Indian Recipes` [1] vs `North Indian` [2], `Bengali Recipes` [1], `Goan Recipes` [1], `Maharashtrian Recipes` [1]).
  - **Resolution:** Cleaned and normalized cuisine records in SQLite and implemented alias matching in `RecipeRepository.get_list`, `search_recipes`, and `/recipes/filters`. Search queries and filter chips now gracefully match both exact and aliased variants without duplicate filter chips.

---

## 3. Schema & Provenance Enhancements

### 3.1 Backend Schemas
- Extended `RecipeDetailRead` in `backend/app/schemas/recipe.py` to expose full provenance and attribution metadata:
  - `author`: Original chef or contributor
  - `source_license`: Open data or attribution license (e.g., `CC-BY-SA 4.0`)
  - `region`: Geographical culinary region (e.g., `North India`, `South India`)
  - `state`: State of origin (e.g., `Punjab`, `Telangana`, `West Bengal`)
  - `original_name`: Regional or traditional title (e.g., `Paneer Makhani`, `Kacchi Biryani`)
  - `is_indian_recipe`: Boolean indicator
  - `verification_status`: Status (`VERIFIED`, `COMMUNITY`, `UNVERIFIED`)
- Introduced `RecipeStepRead` schema supporting structured instructions (`step_number`, `action_type`, `timing_minutes`, `temperature`, `equipment`, `ingredients`) alongside backward-compatible `legacy_instructions`.

### 3.2 Frontend Types & Schemas
- Updated `frontend/src/types/index.ts` to include `RecipeStepRead` and provenance attributes on `RecipeDetail`.

---

## 4. Serving Adjustment & Proportional Quantity Scaling

### 4.1 Interactive Servings Stepper
- Implemented in `frontend/src/pages/RecipeDetailPage.tsx`:
  - Interactive stepper (`-` and `+`) with boundary checks (min: 1, max: 24).
  - Dynamic scale factor calculation: $\text{scaleFactor} = \frac{\text{servings}}{\text{baseServings}}$.
  - One-click "Reset" button when current serving count differs from base recipe servings.
  - Dynamically recalculated estimated cost based on serving scale.

### 4.2 Proportional Ingredient Scaling
- Enhanced `frontend/src/components/recipe/IngredientRow.tsx` and `frontend/src/components/recipe/NormalizedIngredientList.tsx`:
  - Added `scaleFactor` prop.
  - Multiplies numeric quantities by `scaleFactor` while preserving non-numeric quantities ("to taste", `to_taste: true`) untouched.
  - Visual indicator in ingredient header displaying current scale factor (e.g. `Scaled (1.5x) •`).

---

## 5. Recipe-to-Grocery Seamless Connection

### 5.1 Parameter Propagation
- In `frontend/src/pages/RecipeDetailPage.tsx`:
  - Updated "Compare Prices" navigation to include URL search parameters: `/grocery?recipeId=${recipe.id}&servings=${servings}&baseServings=${baseServings}`.

### 5.2 Cart Optimization Scaling
- In `frontend/src/components/grocery/CartOptimizationPanel.tsx`:
  - Parses `servings` and `baseServings` from URL search parameters.
  - Scales `required_quantity` for every recipe ingredient sent to the cart optimization engine.
  - Displays a visual badge indicating that optimization is tailored to the user's custom serving size.

---

## 6. Provenance & Attribution UI

- Added a dedicated "Recipe Attribution & Provenance" card in `RecipeDetailPage`:
  - Displays source name, author, state/region, verification badge, and source license.
  - Provides a secure external link (`rel="noopener noreferrer" target="_blank"`) to the original recipe source.
  - Added support for structured instructions displaying action tags (`PREP`, `SAUTE`, `SIMMER`), step timings, and cooking temperatures when available.

---

## 7. Verification & Test Stability

### 7.1 Backend Unit & Integration Tests
- Created `backend/tests/test_recipe_catalogue.py`:
  - `test_recipe_detail_provenance_fields`: Passed
  - `test_recipe_detail_structured_instructions`: Passed
  - `test_recipe_filters_normalization`: Passed
  - `test_recipe_search_by_cuisine_alias`: Passed
  - `test_recipe_list_by_cuisine_alias`: Passed
  - `test_recipe_not_found`: Passed

### 7.2 Frontend Vitest Tests
- Created `frontend/src/__tests__/RecipeDetailPage.test.tsx`:
  - Renders loading and error states properly: Passed
  - Renders title, cuisine, rating, prep/cook times, and default servings: Passed
  - Interactive stepper adjusts servings and updates URL params: Passed
  - Reset button restores default servings: Passed
  - Respects minimum limit of 1 serving: Passed
  - Renders provenance and attribution card: Passed
  - Renders structured instructions with action badges: Passed

### 7.3 Full Suite Verification Run
```text
Backend:  pytest backend/tests (375 passed in 2m 25s)
ML:       pytest ml/tests (39 passed in 4m 35s)
Frontend: vitest run (267 passed across 30 test files)
Build:    npm run build (0 errors, dist bundle generated in 3.00s)
```

---

## 8. Preserved Integrations & Zero Side Effects

- **Swiggy Instamart OAuth PKCE Flow:** Untouched and fully preserved.
- **Live vs Demo Grocery Mode:** Preserved with accurate data source tagging.
- **Cart Optimization & Multi-Store Splitting:** Fully preserved and now scaling-aware.
- **Design System:** Background `#FAF8F3`, primary `#245C45`, accent `#D97757` strictly preserved.
- **Zero Invented Data:** All recipe attributes reflect genuine catalogue data.
