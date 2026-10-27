# DishIQ — Phase 5: Ingredient Intelligence and Normalization Report

**Project:** DishIQ — Intelligent Meal Planning, Grocery Comparison, and Cooking Assistant  
**Date:** October 18, 2026  
**Status:** Complete & Fully Verified  

---

## 1. Executive Summary

Phase 5 audited and enhanced DishIQ's **Ingredient Intelligence Layer**, which bridges recipe text, inventory tracking, grocery matching, shopping list aggregation, and cooking execution.

The core journey of DishIQ:
$$\text{Recipe} \longrightarrow \text{Ingredient Intelligence} \longrightarrow \text{Grocery Matching} \longrightarrow \text{Shopping List} \longrightarrow \text{Cooking Assistant}$$

Prior to this phase:
1. **Substring Overmatching Defect:** Partial substring alias matching (`alias in key`) caused common ingredients to wrongly collapse into unrelated categories: `"eggplant"` normalized to `"egg"`, `"boiled egg"` matched `"oil"` (from `boil`), and `"buttermilk"` or `"peanut butter"` collapsed into dairy `"butter"`.
2. **Mixed Fraction Quantity Truncation:** Mixed fraction text strings such as `"1 1/2 cups flour"` were incorrectly parsed as `quantity=0.5, unit=None, canonical_name='1 cups flour'` because regex parsing lacked mixed text fraction support (`\d+\s*[- ]\s*\d+/\d+`).
3. **Dual-Nature Noun Guard Failure:** Tokens like `"cloves"` or `"head"` acted as both units (e.g., *4 cloves of garlic*) and ingredient nouns (e.g., *4 whole cloves*). When used as an ingredient noun, the parser consumed the token as a unit, leaving an empty remainder string and producing an orphaned ingredient with `canonical_name=""`.
4. **No Dimension-Safe Unit Conversion System:** No centralized, dimensionally verified conversion system existed, risking illegal conversions (e.g. converting mass directly to volume without density).

All issues have been resolved with strict backward compatibility, zero regression, and complete architectural preservation:
- **Centralized Unit Engine:** Created `backend/app/ingredient_intelligence/units.py` enforcing physical dimensions (`MASS`, `VOLUME`, `COUNT`, `DESCRIPTIVE`), dimensional safety, and standardized conversion multipliers.
- **Word-Boundary Matching:** Replaced raw substring checks with `\b` word-boundary patterns and prioritized alias matching.
- **Distinct Concepts:** Added explicit mappings and categories preserving `eggplant` (vegetable), `buttermilk` (dairy), `peanut butter` (nut), `coconut milk` (dairy-free alternative), `mustard oil` (oil), `coriander seeds` (spice vs herb), `cumin powder`, and `ginger powder`.
- **Dual-Nature Guard:** Dual-nature tokens without trailing nouns are preserved as the ingredient noun rather than consumed as a unit.
- **Safe Dry-Run Audit Script:** Developed `backend/app/scripts/audit_and_repair_ingredients.py` with default dry-run mode for safe database inspections.
- **Automated Verification:** 398 backend pytest tests pass (0 failures), 267 frontend vitest tests pass across 30 suites (0 failures), and the frontend Vite production build succeeded cleanly.

---

## 2. Database Baseline Audit

An audit was performed across both active SQLite database files (`backend/dishiq.db` and root `dishiq.db`).

| Metric | Measured Count | Status / Notes |
|---|---|---|
| **Total Recipes** | 1,040 | Verified consistent across database replicas |
| **Total Ingredients** | 1,404 | 1,403 valid named entities + 1 empty canonical record |
| **Recipe-Ingredient Links** | 9,032 | All foreign keys intact |
| **Grocery Products** | 208 | All unit pricing and package data intact |
| **Orphaned References** | 0 | No dangling foreign keys |
| **Invalid Quantities ($\le 0$)** | 0 | All quantified ingredients have valid positive values |
| **Empty Canonical Names** | 1 | ID `3f85b93c-cb5f-4f3f-9503-7b2b14c96332` (referenced by 12 recipes where raw_text was `"clove"` / `"cloves"`) |
| **Unmapped / Unknown Units** | 100 | Descriptive or unquantified entries (e.g. "to taste", "as needed") |

> [!NOTE]
> Per the mandatory safety rules, the persistent development database was **not modified or wiped**. The 1 empty canonical record was diagnosed, tested in the parser, and can be updated safely via `audit_and_repair_ingredients.py` upon explicit user request.

---

## 3. Parser & Normalization Enhancements

### 3.1 Substring Overmatching Elimination
- **Defect:** `normalize_ingredient` previously used `if key.startswith(alias) or alias in key:`. Because `"oil"` is inside `"boiled egg"`, or `"egg"` starts `"eggplant"`, ingredients were frequently assigned erroneous canonical identities.
- **Fix:** Switched to regex word boundaries: `re.search(r"\b" + re.escape(alias) + r"\b", key)`.
- **Result:**
  - `"1 medium eggplant"` $\rightarrow$ canonical: `"eggplant"` (category: `vegetable`), not `"egg"`.
  - `"2 cups buttermilk"` $\rightarrow$ canonical: `"buttermilk"` (category: `dairy`), not `"butter"`.
  - `"2 tbsp peanut butter"` $\rightarrow$ canonical: `"peanut butter"` (category: `nut`), not `"butter"`.
  - `"2 tbsp mustard oil"` $\rightarrow$ canonical: `"mustard oil"` (category: `oil`), not `"mustard seeds"` or `"oil"`.

### 3.2 Mixed Text Fractions & Unicode Support
- **Defect:** `resolve_fractions` only handled unicode fractions (e.g. `½`) or simple slash fractions (`1/2`). It could not parse text mixed fractions like `"1 1/2"` or `"1-1/2"`.
- **Fix:** Introduced `_MIXED_TEXT_FRAC_RE = re.compile(r"(?P<whole>\d+)\s*[- ]\s*(?P<num>\d+)\s*/\s*(?P<den>\d+)")` evaluated before single fraction matching.
- **Result:**
  - `"1 1/2 cups flour"` $\rightarrow$ quantity: `1.5`, unit: `"cup"`, canonical: `"flour"`.
  - `"1-1/2 cups maida"` $\rightarrow$ quantity: `1.5`, unit: `"cup"`, canonical: `"all-purpose flour"`.

### 3.3 Dual-Nature Nouns (Cloves / Garlic)
- **Defect:** `"clove"` was registered solely as a unit in `UNIT_NORMALIZATION`. When parsing `"4 cloves"`, `extract_unit` consumed `"clove"` as the unit, leaving the remainder empty `""`, creating an ingredient with no canonical name.
- **Fix:** Added a dual-nature noun guard in `extract_unit`:
  ```python
  if not remainder and canonical in {"clove", "head", "bunch"}:
      return None, text
  ```
- **Result:**
  - `"4 cloves of garlic"` $\rightarrow$ quantity: `4.0`, unit: `"clove"`, canonical: `"garlic"`.
  - `"4 cloves"` $\rightarrow$ quantity: `4.0`, unit: `None`, canonical: `"clove"`, category: `"spice"`.
  - `"1/4 tsp ground cloves"` $\rightarrow$ quantity: `0.25`, unit: `"tsp"`, preparation_note: `"ground"`, canonical: `"clove"`, category: `"spice"`.

### 3.4 Leading "of" Removal
- Added `re.sub(r"^(?:of\s+)", "", remainder, flags=re.IGNORECASE)` in `extract_unit`.
- `"1 cup of milk"` extracts unit `"cup"` and remainder `"milk"` instead of `"of milk"`.

---

## 4. Centralized Unit Conversion System

Created `backend/app/ingredient_intelligence/units.py` providing an extensible, physically grounded unit normalization and conversion framework.

### 4.1 Physical Dimensions
```python
class UnitDimension(str, Enum):
    MASS = "mass"              # Base unit: g
    VOLUME = "volume"          # Base unit: ml
    COUNT = "count"            # Base unit: piece
    DESCRIPTIVE = "descriptive"# Contextual (pinch, to taste, bunch)
```

### 4.2 Dimensionally-Safe Conversions
Conversions between units within the same dimension are converted through their base unit with exact multiplier factors:
- **Mass:** `g`, `kg`, `mg`, `oz`, `lb`
- **Volume:** `ml`, `l`, `tsp`, `tbsp`, `cup`, `fl oz`, `pt`, `qt`
- **Count:** `piece`, `clove`, `head`, `slice`

Cross-dimensional conversions (e.g. converting grams directly to milliliters without ingredient density) are strictly rejected with an explicit error:
```python
val, err = convert_quantity(500.0, "g", "ml")
# Returns: (None, "Incompatible conversion: cannot convert mass ('g') to volume ('ml') without density")
```

### 4.3 Integration Across Backend
- Integrated into `backend/app/api/pantry.py` for calculating recipe availability against pantry stock.
- Exported in `backend/app/ingredient_intelligence/__init__.py`.
- Synchronized with `backend/app/product_matching/unit_pricing.py` to ensure grocery price comparisons utilize the same unit definitions.

---

## 5. Safe Audit & Data Repair Script

Created `backend/app/scripts/audit_and_repair_ingredients.py` to inspect the database, check for data integrity anomalies, and safely repair them.

- **Default Safety:** Defaults to `--dry-run` mode. Will not modify any database records unless executed with `--apply`.
- **Dry-Run Output on Live Database:**
  ```text
  Audit summary:
    Total recipes: 1,040
    Total ingredients: 1,404
    Total recipe_ingredient links: 9,032
    Total grocery products: 208
    Orphaned recipe_ingredient rows: 0
    Empty canonical_name ingredients: 1
    Invalid quantities (<= 0): 0
    Unknown units: 100
  [DRY-RUN] Found 1 ingredient with empty canonical name:
    Ingredient 3f85b93c-cb5f-4f3f-9503-7b2b14c96332: raw_text='clove', proposed canonical='clove', category='spice'
  [DRY-RUN] Complete. No changes were committed to the database.
  ```

---

## 6. Test Suite & Verification Results

### 6.1 Unit & Regression Tests
- **Unit Conversion Tests (`backend/tests/test_units.py`):** 13 passed, 0 failed.
- **Ingredient Parser & API Tests (`backend/tests/test_ingredient_parser.py`, `backend/tests/test_ingredient_api.py`):** 117 passed, 0 failed.

### 6.2 Full Test Suites
- **Full Backend Pytest Suite:**
  ```text
  398 passed, 16 warnings in 51.08s
  Exit code: 0
  ```
- **Full Frontend Vitest Suite:**
  ```text
  Test Files: 30 passed (30)
  Tests: 267 passed (267)
  Duration: 7.34s
  Exit code: 0
  ```
- **Frontend Production Build (`npm run build`):**
  ```text
  ✓ 1644 modules transformed.
  dist/index.html                   0.83 kB │ gzip:   0.48 kB
  dist/assets/index-D7ZIx8pO.css   40.50 kB │ gzip:   7.46 kB
  dist/assets/index-C9jIj7B4.js   433.26 kB │ gzip: 124.66 kB
  ✓ built in 4.08s
  Exit code: 0
  ```

---

## 7. Phase 6 Readiness

Phase 5 has verified that:
1. Ingredients are accurately parsed with correct quantities, units, canonical names, and categories.
2. Incompatible unit conversions are strictly guarded against across pantry stock checks and grocery matching.
3. Live grocery comparison and Swiggy Instamart OAuth workflows remain functional with zero regressions.
4. Database integrity is preserved without destructive operations.

DishIQ is ready to proceed to **Phase 6: Grocery Matching & Price Comparison Engine**.
