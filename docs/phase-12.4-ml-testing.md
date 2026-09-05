# DishIQ Phase 12.4 ML Testing & Model Validation Report

## 1. Objective
Validate the existing DishIQ machine-learning components to ensure correctness, reproducibility, robustness to edge cases (e.g., missing artifacts), and proper integration with backend services.

## 2. ML Components Tested
1. **Recipe Recommendation Pipeline (TF-IDF)**
   - Text vectorization using `ml/utils/feature_engineering.py`.
   - Cosine similarity ranking merged with config-weighted personalization boosts (dietary, time, rating, pantry).
2. **Product Matching (Sentence Transformer)**
   - Semantic text similarity between normalized pantry ingredients and catalog items.
3. **Artifact Handling & Cache**
   - Resiliency of the embedding cache in `app.grocery_sources.demo_provider`.

## 3. Tests Performed
- Ran the existing `ml/tests/test_ml_pipeline.py` which verifies text normalization and the training script's metadata generation logic.
- Created `backend/tests/test_phase12_ml.py` introducing 5 new targeted ML integration tests:
  - `test_recipe_recommendation_dietary_and_pantry`: Validates dietary filters, pantry overlap boosts, and explanation generation.
  - `test_recipe_recommendation_time_penalty`: Validates the filtering logic for `max_time` preference parameters.
  - `test_recommender_handles_empty_query`: Verifies that empty/nonsense queries fall back cleanly without crashing the recommendation engine.
  - `test_product_matcher_semantic_filtering`: Validates that pure items (e.g., 'Fresh Paneer') rank distinctly above mixed/derived items (e.g., 'Paneer Tikka Masala Mix').
  - `test_demo_provider_cache_resilience`: Asserts the `DemoGroceryProvider` functions reliably when integrating pre-cached embeddings with uncached database products.

## 4. Defects Found/Fixes
No new ML defects were found in the current implementation. 
- *Note:* The critical `DemoGroceryProvider` cache defect (where database changes were ignored when cache files existed) was already discovered and rectified during Phase 12.2. The regression tests confirming this fix were implemented during this phase.

## 5. Evaluation
- **Dataset Size:** 0
- **Top-1 / Top-3 Accuracy:** NOT AVAILABLE — no qualifying labelled 50-pair evaluation dataset exists.
- The `ml/evaluation/evaluate_model.py` script provides rudimentary visual reporting of TF-IDF queries but does not constitute a formal quantitative evaluation set. This is documented as a testing/documentation gap for future iterations.

## 6. Test Results
- **ML Tests:** 7 Passed, 0 Failed, 0 Errors, 0 Skipped (2 existing + 5 new tests)
- **Backend Regression:** 292 Passed, 0 Failed
- **Training:** PASS (`ml/training/train_recipe_recommender.py` executed successfully, models regenerated cleanly)
- **Evaluation:** NOT AVAILABLE

## 7. Files Created/Modified
- **Created:** `backend/tests/test_phase12_ml.py` (Contains the new targeted ML tests)
- **Created:** `docs/phase-12.4-ml-testing.md` (This report)

## 8. Remaining Issues
- **Informational:** A formal labelled dataset (>=50 ingredient-product pairs) for product matching accuracy evaluation is currently absent.

## 9. Manual Verification
- **Recipe Recommendation:** Run `GET /api/recommendations` in Swagger UI, verify results align with semantic relevance.
- **Product Matching:** Run `GET /api/grocery/search?q=paneer` and verify that "Paneer" is ranked higher than "Paneer Masala".
- **Personalization:** Edit `dietary_type` in your user profile to 'Vegan' and verify that 'Paneer' recipes are appropriately filtered out.
- **Pantry Influence:** Add an item to your pantry (`POST /api/pantry`), then fetch recommendations and check the `explanations` array for pantry-matching badges.

## 10. Final Status
READY FOR PHASE 12.5
