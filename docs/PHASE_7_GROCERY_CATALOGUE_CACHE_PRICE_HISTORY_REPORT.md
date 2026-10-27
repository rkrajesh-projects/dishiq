# DishIQ — Phase 7: Grocery Catalogue, Caching, and Price History Report

## 1. Executive Summary

Phase 7 has been successfully implemented, audited, and verified for the **DishIQ** project. 

The primary objectives of this phase were:
1. **Grocery Catalogue Identity & Separation**: Establish reliable product identity without merging distinct package sizes, brands, or variants (e.g., 200g vs 500g paneer remain distinct items).
2. **Safe Caching Lifecycle**: Introduce an in-memory TTL and stale-cache lifecycle in `GroceryProviderRegistry` that explicitly distinguishes `PROVIDER_LIVE`, `CACHED` (cached live data), and `DEMO` data, providing stale-cache fallback during transient provider network failures.
3. **Chronological Price History Ingestion**: Record genuine price history observations over time when prices change, deduplicate consecutive identical observations, prevent in-place mutation of history, and strictly prohibit demo prices or cache hits from polluting live price history.
4. **API & Background Sync**: Enable `BackgroundTasks` on grocery endpoints, localized pincode searching, and introduce `GET /api/grocery/products/{product_id}/price-history`.
5. **Zero Regression**: Preserve all Swiggy Instamart OAuth 2.1 PKCE flows, ML recommendation pipelines, recipe search, and database integrity.

All 406 backend tests and 268 frontend Vitest tests passed with zero regressions, and the production build succeeded.

---

## 2. Database Schema & Migration (004)

### 2.1 Schema Extensions
- **`grocery_products`**:
  - Added `source_product_id` (`String(255)`, nullable, indexed) to store platform-specific SKUs/IDs (e.g., Swiggy `spinId` or external quick-commerce product IDs).
  - Added composite index `ix_grocery_products_store_source_id` on `(store_id, source_product_id)`.
  - Added composite index `ix_grocery_products_store_name_pkg` on `(store_id, name, package_quantity, package_unit)`.
- **`product_prices`**:
  - Added `currency` (`String(10)`, non-nullable, server default `'INR'`).
  - Added `price_freshness` (`String(50)`, non-nullable, server default `'CACHED'`).
  - Added composite index `ix_product_prices_product_observed` on `(product_id, observed_at)`.
  - Added `order_by="ProductPrice.observed_at.asc()"` on `GroceryProduct.prices` relationship and introduced `latest_price` property.

### 2.2 Migration Verification
Migration `004_grocery_catalogue_and_price_history.py` was applied using Alembic batch alterations across both SQLite targets (`backend/dishiq.db` and `dishiq.db`).
- **Data Preservation**: 100% of the existing catalogue (208 products, 302 prices) was preserved with zero data loss or corruption.

---

## 3. Implementation Details

### 3.1 Product Identity & Package Size Separation
In [product_sync_service.py](file:///d:/DishIQ/backend/app/services/product_sync_service.py):
- **Primary Identity Lookup**: Matches by `(store_id, source_product_id)` when the provider returns a unique SKU ID.
- **Secondary Identity Lookup**: Matches by `(store_id, name, package_quantity, package_unit)`.
- **Package Integrity**: Different package sizes (e.g., 200g vs 500g) are never merged into a single product record. Each package quantity and unit constitutes its own row in `grocery_products`.

### 3.2 Chronological Price History Ingestion & Deduplication
- **Chronological Insertion**: When a live product price changes or is first observed, a new `ProductPrice` row is inserted with `observed_at`, `currency="INR"`, `price_freshness="PROVIDER_LIVE"`, and `data_source_type="live"`. Historical rows are never mutated in-place.
- **Deduplication**: If the most recent price observation for a product is identical in amount, redundant duplicate rows are avoided.
- **Demo & Cache Protection**: Products with `price_freshness="DEMO"` or `price_freshness="CACHED"` are strictly prevented from inserting records into live price history.

### 3.3 Safe Caching Lifecycle & Stale Fallback
In [registry.py](file:///d:/DishIQ/backend/app/grocery_sources/registry.py):
- **Cache Key Format**: `f"{provider_keys}:{query.lower().strip()}"` to isolate queries across provider combinations.
- **Fresh Cache Hit (`age <= 300s`)**: Returns cloned results with `price_freshness="CACHED"` for live items, ensuring cached prices are never falsely presented as fresh live data.
- **Provider Failure & Stale Fallback (`300s < age <= 1800s`)**: If external providers fail or time out, the registry returns stale cached data with `price_freshness="CACHED"` and explanatory metadata (`failures["_cache"] = "Returned stale cached data due to provider error"`).
- **Automatic Purging**: Entries older than 1800s are automatically purged.

### 3.4 API Endpoints & Background Sync
In [grocery.py](file:///d:/DishIQ/backend/app/api/grocery.py):
- Added `background_tasks: BackgroundTasks` to `/api/grocery/match` and `/api/grocery/compare` for asynchronous database synchronization.
- Added optional `pincode` parameter for localized provider searching.
- Added `GET /api/grocery/products/{product_id}/price-history` returning typed `ProductPriceHistoryResponse` with chronological observations, currency, freshness, and 404 error handling for missing items.

---

## 4. Test & Verification Suite

### 4.1 Phase 7 Automated Test Suite
A dedicated test suite was implemented in [test_grocery_catalogue_and_caching.py](file:///d:/DishIQ/backend/tests/test_grocery_catalogue_and_caching.py):
1. `test_package_size_identity_separation_no_merging`: Validates that 200g and 500g products of identical brand and name are preserved as distinct entities with distinct pricing.
2. `test_primary_identity_resolution_via_source_product_id`: Validates that repeated syncs of the same SKU update attributes without creating duplicate product rows.
3. `test_price_history_recording_and_deduplication`: Verifies initial price insertion, deduplication of identical prices on subsequent syncs, and creation of chronological price records when price changes.
4. `test_demo_and_cached_products_never_create_live_price_history`: Ensures DEMO and CACHED products never create live price history entries.
5. `test_grocery_provider_registry_caching_and_freshness`: Verifies cache hit avoids provider re-query and sets `price_freshness="CACHED"`.
6. `test_grocery_provider_registry_stale_cache_fallback`: Verifies fallback to stale cache on provider network failure.
7. `test_api_product_price_history_endpoint`: Verifies HTTP 200 response structure and 404 handling.

### 4.2 Test Execution Metrics
- **Phase 7 Tests**: **7 passed / 7** (100%)
- **Swiggy Instamart Tests**: **40 passed / 40** (100%)
- **Full Backend Pytest Suite**: **406 passed / 406** (100% green)
- **Frontend Vitest Suite**: **268 passed / 268** across 30 test files (100% green)
- **Frontend Production Build**: `tsc && vite build` succeeded in 10.04s with zero TypeScript or packaging errors.

---

## 5. Artifacts and Modified Files Summary

| File | Status | Description |
|---|---|---|
| `backend/alembic/versions/004_grocery_catalogue_and_price_history.py` | Created | Migration for product source ID, price freshness, currency, and composite indexes |
| `backend/app/models/grocery.py` | Modified | Updated `GroceryProduct` (source_product_id, ordered prices relationship, latest_price) and `ProductPrice` (currency, price_freshness) |
| `backend/app/schemas/grocery.py` | Modified | Added `price_freshness` to `ProductPriceRead`, added `ProductPriceHistoryResponse` |
| `backend/app/services/product_sync_service.py` | Modified | Package-aware identity resolution, deduplicated price history ingestion |
| `backend/app/grocery_sources/registry.py` | Modified | In-memory cache with fresh TTL, stale fallback, and freshness marking |
| `backend/app/services/grocery_service.py` | Modified | Added `get_price_history` service method |
| `backend/app/api/grocery.py` | Modified | Added BackgroundTasks, pincode parameter, and `GET /products/{product_id}/price-history` |
| `backend/tests/test_grocery_catalogue_and_caching.py` | Created | 7 unit and integration tests covering Phase 7 requirements |
| `backend/tests/test_live_cart.py` | Modified | Added cache reset fixture for unit test isolation |

---

## 6. Next Steps & Phase 8 Transition

Phase 7 is complete. All safety constraints, data integrity guarantees, caching rules, and regression suites are green.

Per project guidelines, execution is stopped here to await user review and explicit approval before commencing **Phase 8: Cart Optimization, Cheapest Basket, and Multi-Store Routing**.
