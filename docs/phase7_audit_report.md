# DishIQ Phase 7 — Source Audit, Docker Verification, Fixes & End-to-End Testing Report

**Audit Date:** October 15, 2026  
**Auditor:** Antigravity Pair Programming Agent  
**Target Project:** DishIQ (`D:\DishIQ`)  
**Core Features:** Multi-store grocery comparison, cart optimization, live provider integration, product & price database synchronization.

---

## 1. Executive Summary

An independent, evidence-based source and runtime audit of Phase 7 (Multi-Store Grocery Comparison & Shopping Cart Optimization) was performed against the actual DishIQ codebase, PostgreSQL database schema, running Docker containers, FastAPI REST endpoints, and automated Pytest suites.

### Key Audit Outcomes:
1. **ProductEncoder Singleton:** **PASS**. Verified that `ProductEncoder.get_encoder()` caches the underlying `all-MiniLM-L6-v2` `SentenceTransformer` instance across calls within the process (`id(m1) == id(m2) == id(m3)`). The previous hardcoded Windows path `d:/DishIQ/ml/models/pretrained` was eliminated in favor of portable singleton reuse.
2. **Cart Comparison Arithmetic:** **PASS**. Evaluated against the controlled 3-ingredient test basket (Paneer 200g, Tomato 500g, Onion 1,000g). Every line cost ($packages \times package\_price$), subtotal, delivery fee, and grand total was independently calculated and verified to match API responses with 100% precision.
3. **Cart Optimization Strategies:** **PASS**. Verified all 3 strategies (`cheapest_single_store`, `cheapest_split_cart`, `fastest_available`). Single-store selects the cheapest complete basket (`Demo LocalGrocer` at ₹191.50). Split-cart correctly enforces the `CART_MIN_SPLIT_SAVING=50.0` threshold and maximum store limit (`CART_MAX_STORES=2`), suppressing split carts when additional delivery fees make splitting uneconomical. Availability ranking explicitly avoids fabricating delivery ETAs.
4. **Live Provider Integrations:** **PASS (Negative Path) / NOT VERIFIED (Commercial Live Data)**. MCP JSON-RPC 2.0 communication structure, timeout isolation (5.0s `TimeoutError` captured without application crash), and fallback handling were verified. Because real commercial credentials for Swiggy Instamart and QuickCommerce APIs are absent (using dummy placeholders), live commercial data access is documented as unverified without fabrication.
5. **Database & Embedding Synchronization:** **PASS**. Discovered and fixed a defect in `product_sync_service.py` where an incomplete live provider update (`price=None`) would overwrite existing valid prices with `0.0`. Added atomic file replacement (`.tmp` -> `os.replace`) in `cache.py` to prevent corruption of `product_embeddings.joblib`. Idempotency and price preservation were verified in isolated tests.
6. **Docker Environment & Test Suite:** **PASS**. All 3 containers (`dishiq-backend`, `dishiq-frontend`, `dishiq-db`) are healthy and operational. Container Pytest suite executed **102 tests** (including 3 new regression tests) with **102 passed, 0 failed**.

---

## 2. Repository Commit & Working-Tree Status

- **Branch:** `main`
- **Head Commit:** `b8976e2` (`DishIQ: complete Phase 0-12 - full app, tests, Docker, and documentation`)
- **Git Status:** Working tree contains modified source files and untracked artifacts from earlier phases (all user changes preserved).
- **Environment:**
  - Host OS: Windows 10/11
  - Python (Host): Python 3.13 / `.venv` (Python 3.10)
  - Docker Engine: 29.8.0
  - Docker Compose: 5.5.1
  - Container Base Image: `python:3.10-slim`
  - Container Service Names:
    - Backend: `dishiq-backend` (Port 8001)
    - Frontend: `dishiq-frontend` (Port 3000)
    - Database: `dishiq-db` (PostgreSQL 15 Alpine, Port 5432)

---

## 3. Files Inspected & Changed

### Files Inspected:
- `backend/app/services/cart_optimization_service.py`
- `backend/app/api/cart.py`
- `backend/app/schemas/cart.py`
- `backend/app/services/grocery_service.py`
- `backend/app/services/price_comparison_service.py`
- `backend/app/product_matching/matcher.py`
- `backend/app/product_matching/encoder.py`
- `backend/app/product_matching/cache.py`
- `backend/app/product_matching/unit_pricing.py`
- `backend/app/grocery_sources/base_provider.py`
- `backend/app/grocery_sources/registry.py`
- `backend/app/grocery_sources/factory.py`
- `backend/app/grocery_sources/demo_provider.py`
- `backend/app/grocery_sources/swiggy_instamart_provider.py`
- `backend/app/grocery_sources/quickcommerce_provider.py`
- `backend/app/services/product_sync_service.py`
- `backend/app/models/grocery.py`
- `backend/app/core/config.py`
- `backend/Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

### Files Modified & Fix Rationale:
1. `backend/app/services/product_sync_service.py`:
   - *Rationale 1:* Removed hardcoded Windows path `d:/DishIQ/ml/models/pretrained` and replaced duplicate `SentenceTransformer` re-instantiation with `from app.product_matching.encoder import get_encoder; encoder = get_encoder()`. Reuses in-memory singleton.
   - *Rationale 2:* Fixed price overwriting bug on incomplete updates. When `np_prod.price is None`, existing valid prices on `ProductPrice` records are preserved rather than overwritten with `0.0`.
2. `backend/app/product_matching/cache.py`:
   - *Rationale:* Implemented atomic persistence in `save_product_embeddings_artifact`. Serializes to `temp_path = f"{target_path}.tmp"` followed by `os.replace(temp_path, target_path)`. Prevents corruption or partial truncation of `product_embeddings.joblib` during unexpected process interrupts.
3. `backend/tests/test_phase7_regression.py`:
   - *Rationale:* Created 3 focused regression tests covering `ProductEncoder` singleton identity, atomic artifact persistence, and product sync price preservation under incomplete payloads.

---

## 4. Audit Findings Classification

| Component / Requirement | Status | Evidence Summary |
| :--- | :--- | :--- |
| **ProductEncoder Singleton** | **PASS** | `id(m1) == id(m2) == id(m3) == 123644581166960`. No hardcoded paths. In-memory model shared. |
| **Controlled Basket Comparison** | **PASS** | All 4 stores (LocalGrocer ₹191.50, QuickMart ₹200.00, FreshBasket ₹225.50, MockLive ₹90.00) match arithmetic. |
| **Package & Unit Math** | **PASS** | Ceiling packaging verified (e.g., 500g needed from 1kg pack = 1 pack; 1000g needed from 500g pack = 2 packs). |
| **Single Store Strategy** | **PASS** | Selects `Demo LocalGrocer` (₹191.50). Evaluates full fulfillment (`complete=True`). |
| **Split Cart Strategy** | **PASS** | Evaluates combinations $\le 2$ stores; enforces ₹50 net savings threshold. Suppressed when not economical. |
| **Fastest Available Strategy**| **PASS** | Deterministic availability ranking without fabricated ETAs. |
| **Swiggy Instamart MCP** | **PASS (Negative)** | JSON-RPC 2.0 payload compliant; handles timeout (5s) cleanly; isolates provider failures. |
| **Blinkit / Zepto Adapters** | **PASS (Stub/Auth)**| Detects missing `QUICKCOMMERCE_API_KEY` and sets `is_available=False`. |
| **Live Commercial Data** | **NOT VERIFIED** | Valid partner credentials not available in environment; dummy keys present. No live data fabricated. |
| **Live/Demo Source Metadata**| **PASS** | Metadata reflects `data_source: "demo"` in demo mode and `"live"` in live mode with `UNKNOWN` freshness on timeout. |
| **Product & Price Sync** | **PASS** | PostgreSQL `grocery_products` & `product_prices` upsert tested; preserves valid prices; idempotent. |
| **Atomic Embeddings Cache** | **PASS** | Verified `.tmp` -> `os.replace` write pattern without corrupting `.joblib` artifacts. |
| **Docker Build & Health** | **PASS** | CPU-only PyTorch `2.14.1+cpu` verified; health endpoint HTTP 200 OK; containers running. |
| **Automated Tests** | **PASS** | 102/102 tests passed in container (0 failures). |

---

## 5. Evidence for ProductEncoder Singleton Fix

### Verification Test
Executed inside running container `dishiq-backend`:
```python
from app.product_matching.encoder import get_encoder, ProductEncoder

enc1 = get_encoder()
m1 = enc1.get_model(enc1.model_name)
enc2 = get_encoder()
m2 = enc2.get_model(enc2.model_name)
m3 = ProductEncoder.get_model(enc1.model_name)

assert id(m1) == id(m2) == id(m3)
```
### Output:
```
{"timestamp": "2026-10-15 16:40:19,592", "level": "INFO", "logger": "dishiq", "message": "Initializing SentenceTransformer model [all-MiniLM-L6-v2]..."}
{"timestamp": "2026-10-15 16:40:23,346", "level": "INFO", "logger": "dishiq", "message": "SentenceTransformer [all-MiniLM-L6-v2] loaded successfully (dim=384)."}
SUCCESS: ProductEncoder model singleton verified. Object ID: 123644581166960
Encoded shape: (2, 384)
SUCCESS: Vector generation verified.
```
- **Finding:** The model object ID is identical (`123644581166960`). Zero secondary model instances are spawned.

---

## 6. Cart Comparison Arithmetic & Optimization Verification

### Controlled Test Basket:
- Paneer: 200 g
- Tomato: 500 g
- Onion: 1,000 g

### Raw Database Prices in PostgreSQL:
| Store | Paneer (200g) | Roma Tomatoes (1kg) | Yellow Onions (1kg) | Default Delivery Fee |
| :--- | :--- | :--- | :--- | :--- |
| **Demo LocalGrocer** | ₹90.25 | ₹38.00 | ₹33.25 | ₹30.00 |
| **Demo QuickMart** | ₹95.00 | ₹40.00 | ₹35.00 | ₹30.00 |
| **Demo FreshBasket** | ₹109.25 | ₹46.00 | ₹40.25 | ₹30.00 |

### API Arithmetic Audit (`POST /api/v1/cart/compare?live_mode=false`):

#### 1. Demo LocalGrocer:
- Paneer: 1 pack @ ₹90.25 = ₹90.25
- Tomato: 1 pack @ ₹38.00 = ₹38.00
- Onion: 1 pack @ ₹33.25 = ₹33.25
- **Subtotal:** $90.25 + 38.00 + 33.25 = \mathbf{₹161.50}$ (API reported: ₹161.50 — Match: **True**)
- **Delivery Fee:** ₹30.00
- **Total:** $161.50 + 30.00 = \mathbf{₹191.50}$ (API reported: ₹191.50 — Match: **True**)
- **Fulfillment:** 3/3 items (`complete: True`)

#### 2. Demo QuickMart:
- Paneer: 1 pack @ ₹95.00 = ₹95.00
- Tomato: 1 pack @ ₹40.00 = ₹40.00
- Onion: 1 pack @ ₹35.00 = ₹35.00
- **Subtotal:** $95.00 + 40.00 + 35.00 = \mathbf{₹170.00}$ (API reported: ₹170.00 — Match: **True**)
- **Delivery Fee:** ₹30.00
- **Total:** $170.00 + 30.00 = \mathbf{₹200.00}$ (API reported: ₹200.00 — Match: **True**)
- **Fulfillment:** 3/3 items (`complete: True`)

#### 3. Demo FreshBasket:
- Paneer: 1 pack @ ₹109.25 = ₹109.25
- Tomato: 1 pack @ ₹46.00 = ₹46.00
- Onion: 1 pack @ ₹40.25 = ₹40.25
- **Subtotal:** $109.25 + 46.00 + 40.25 = \mathbf{₹195.50}$ (API reported: ₹195.50 — Match: **True**)
- **Delivery Fee:** ₹30.00
- **Total:** $195.50 + 30.00 = \mathbf{₹225.50}$ (API reported: ₹225.50 — Match: **True**)
- **Fulfillment:** 3/3 items (`complete: True`)

#### 4. Mock Live Store (Partial Store):
- Tomato: 1 pack @ ₹60.00 = ₹60.00
- Missing: Paneer, Onion
- **Subtotal:** ₹60.00, **Total:** ₹90.00, **Fulfillment:** 1/3 items (`complete: False`)

### Historical Totals Note:
The historical example numbers (₹240, ₹250, ₹240) were from an earlier mockup. The live database seeds produce ₹191.50, ₹200.00, and ₹225.50. Arithmetic checks on the current database are 100% verified.

### Cart Optimization Audit (`POST /api/v1/cart/optimize?live_mode=false`):
- **Recommended Strategy:** `cheapest_single_store`
- **Selected Store:** `Demo LocalGrocer`
- **Total Cost:** ₹191.50
- **Estimated Savings:** ₹0.00 (LocalGrocer is the cheapest baseline)
- **Stores Used:** 1
- **Split Cart Decision:** `Demo LocalGrocer` already holds the cheapest price for every single ingredient. Splitting across stores would incur two delivery fees ($2 \times ₹30 = ₹60$) without saving money on items, resulting in negative savings. `strategy_cheapest_split_cart` correctly returned `None` because savings were below `CART_MIN_SPLIT_SAVING=50.0`.
- **Alternatives Evaluated:** `fastest_available` (Total: ₹191.50).

---

## 7. Provider Integration & Live-Data Verification

### Settings Variable Inventory:
- `SWIGGY_INSTAMART_CLIENT_ID`: Configured (contains placeholder `dummy_id`)
- `SWIGGY_INSTAMART_CLIENT_SECRET`: Configured (contains placeholder)
- `SWIGGY_INSTAMART_ACCESS_TOKEN`: `None` (not configured)
- `SWIGGY_INSTAMART_MCP_URL`: `http://dummy-mcp-url` (dummy endpoint)
- `QUICKCOMMERCE_API_KEY`: `None` (not configured)
- `GROCERY_PROVIDER`: `"demo"`

### Live Mode Negative Path Audit (`POST /api/v1/cart/compare?live_mode=true`):
- **Command:** `res = requests.post("http://localhost:8001/api/v1/cart/compare?live_mode=true", json=basket)`
- **HTTP Status:** `200 OK`
- **Data Source Label:** `"live"`
- **Price Freshness:** `"UNKNOWN"`
- **Real Provider Attempt:** The backend attempted to contact `http://dummy-mcp-url`. `asyncio.wait_for` encountered a connection timeout after 5.0 seconds.
- **Error Isolation:**
  ```python
  Failures: {'swiggy_instamart': 'TimeoutError: '}
  ```
  The failure was isolated in the registry and logged. Zero mock or fake prices were injected.
- **Missing Items:** All 3 ingredients were reported as missing:
  ```json
  [
    {"ingredient_name": "Paneer", "reason": "No compatible in-stock product found at any store"},
    {"ingredient_name": "Tomato", "reason": "No compatible in-stock product found at any store"},
    {"ingredient_name": "Onion", "reason": "No compatible in-stock product found at any store"}
  ]
  ```

---

## 8. Database Synchronization & Embedding Persistence Results

### Defect Identified & Corrected:
In `backend/app/services/product_sync_service.py`:
- **Original Code:**
  ```python
  price_record.price = np_prod.price or 0.0
  ```
  If a provider returned product metadata with `price=None` (e.g. out of stock or price omitted), the existing valid price was overwritten with `0.0`.
- **Corrected Code:**
  ```python
  if np_prod.price is not None:
      price_record.price = np_prod.price
      price_record.data_source_type = "live"
  ```
- **Artifact Atomic Persistence:**
  In `backend/app/product_matching/cache.py`, `save_product_embeddings_artifact` now writes to `target_path + ".tmp"` and executes `os.replace(temp_path, target_path)`.

### Test Verification:
Executed automated test `test_product_sync_preserves_price_on_incomplete_data`:
- Product created with price ₹120.00.
- Synced incomplete live payload with `price=None` and `availability=False`.
- Verified `prod.in_stock == False` and `price_rec.price == 120.00` (price preserved).
- Executed second sync: verified no duplicate rows created (`count == 1`).

---

## 9. Docker Build, Container Health & Dependencies

- **Base Image:** `python:3.10-slim`
- **PyTorch Installed:** `2.14.1+cpu` (`torch.cuda.is_available() == False`). Replaced ~3.5 GB CUDA suite with ~196 MB CPU wheel from `https://download.pytorch.org/whl/cpu`.
- **Passlib & Bcrypt:** `passlib==1.7.4` and `bcrypt==3.2.2`. Registration, login, and password verification work with 0 errors.
- **Build Context:** Shrunk from **861.59 MB to 18.29 KB** via `.dockerignore` (transfers in 0.0s).
- **Service Status:**
  ```
  NAME              IMAGE            STATUS                    PORTS
  dishiq-backend    dishiq-backend   Up 50+ min                0.0.0.0:8001->8001/tcp
  dishiq-db         postgres:15      Up 50+ min (healthy)      0.0.0.0:5432->5432/tcp
  dishiq-frontend   dishiq-frontend  Up 25+ min                0.0.0.0:3000->80/tcp
  ```
- **Health Endpoints:**
  - `GET http://localhost:8001/api/health` -> `HTTP 200 OK` (`{"status":"ok","application":"DishIQ","version":"1.0.0"}`)
  - `GET http://localhost:8001/api/v1/health` -> `HTTP 200 OK` (`{"status":"ok","application":"DishIQ","version":"1.0.0"}`)

---

## 10. Actual Test Commands and Results

### Execution Command:
```powershell
docker exec dishiq-backend pytest \
  tests/test_cart_optimization.py \
  tests/test_cart_api.py \
  tests/test_live_cart.py \
  tests/test_swiggy_instamart_provider.py \
  tests/test_price_comparison.py \
  tests/test_grocery_matching_api.py \
  tests/test_phase7_regression.py
```

### Test Results Breakdown:
| Test File | Tests Collected | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/test_cart_optimization.py` | 55 | 55 | 0 | 0 | 0 |
| `tests/test_cart_api.py` | 15 | 15 | 0 | 0 | 6 |
| `tests/test_live_cart.py` | 6 | 6 | 0 | 0 | 0 |
| `tests/test_swiggy_instamart_provider.py` | 6 | 6 | 0 | 0 | 0 |
| `tests/test_price_comparison.py` | 12 | 12 | 0 | 0 | 0 |
| `tests/test_grocery_matching_api.py` | 5 | 5 | 0 | 0 | 0 |
| `tests/test_phase7_regression.py` | 3 | 3 | 0 | 0 | 0 |
| **Total Suite** | **102** | **102** | **0** | **0** | **6** |

**Execution Time:** 12.11 seconds.

---

## 11. End-to-End API Results

### End-to-End Scenario Flow:
1. **Health Verification:** `GET /api/v1/health` -> `200 OK`.
2. **User Authentication:** Registered test account and authenticated via `POST /api/v1/auth/login`. Bearer JWT access token returned.
3. **Cart Comparison (Demo):**
   - Endpoint: `POST /api/v1/cart/compare?live_mode=false`
   - Status: `200 OK`
   - Result: Returned 4 store breakdowns with package quantities and verified subtotals.
4. **Cart Optimization (Demo):**
   - Endpoint: `POST /api/v1/cart/optimize?live_mode=false`
   - Status: `200 OK`
   - Result: `cheapest_single_store` recommended (`Demo LocalGrocer`, ₹191.50).
5. **Live Negative Path:**
   - Endpoint: `POST /api/v1/cart/compare?live_mode=true`
   - Status: `200 OK`
   - Result: Correctly reported missing ingredients without crashing; no fabricated live prices.
6. **Active Cooking Session (Empty State):**
   - Endpoint: `GET /api/v1/cooking/sessions/active`
   - Status: `200 OK` (Body: `null`). The Home page displays normal empty state without errors.

---

## 12. Remaining Issues & Recommended Next Steps

### Remaining Limitations:
1. **Live Partner Access:** Real-time production pricing from Swiggy Instamart, Blinkit, and Zepto requires authorized commercial API keys and access tokens. Currently operating in demo mode or safe fallback mode when live mode is toggled.
2. **Delivery Fee Persistence:** In the demo database schema, delivery fees default to `CART_DEFAULT_DEMO_DELIVERY_FEE` (₹30.00). In a full production rollout, store delivery fee tiers (e.g. free delivery above ₹499) should be dynamic based on cart subtotal.

### Recommended Next Steps:
1. **Swiggy Instamart Developer Access:** Once partner credentials are obtained, populate `.env` with `SWIGGY_INSTAMART_ACCESS_TOKEN` and the production MCP endpoint URL.
2. **Frontend UI Exploration:** All core APIs are live, healthy, and verified. Users can explore meal planning, grocery comparison, and cooking session execution at `http://localhost:3000`.
