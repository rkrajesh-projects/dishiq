# DishIQ — Phase 6: Live Swiggy Instamart Integration Verification & Hardening Report

**Project:** DishIQ — Intelligent Meal Planning, Grocery Comparison, and Cooking Assistant  
**Date:** October 18, 2026  
**Status:** PASS  

---

## 1. Executive Summary & Objective

Phase 6 focused on auditing, validating, hardening, and verifying the existing **Swiggy Instamart Model Context Protocol (MCP)** integration and **OAuth 2.1 + PKCE** authorization lifecycle in DishIQ.

The integration enables DishIQ to perform real-time grocery product searches and multi-store price comparisons across live quick-commerce inventories in Indian Rupees (INR, ₹).

### Key Accomplishments
1. **OAuth 2.1 & PKCE Hardening:** Verified RFC 7636 PKCE S256 challenge generation, Dynamic Client Registration (RFC 7591 fallback), CSRF state lifecycle (15-min TTL with replay prevention), and atomic token storage. Fixed a latent `NameError` in `refresh_tokens()` where omitted refresh tokens in provider responses would silently fail.
2. **MCP JSON-RPC 2.0 Provider Verification:** Confirmed `tools/call` for `search_products` and `get_addresses` across nested `variations` and flat product structures, guest coordinate fallbacks, and automatic token refresh on HTTP 401/403 or JSON-RPC code `-32001`.
3. **Confirmed Live Grocery API Verification:** Re-verified live queries (`GET /api/v1/grocery/compare?ingredient=milk&live_mode=true`) producing real-time responses with `data_source: "live"`, `price_freshness: "PROVIDER_LIVE"`, and 28 live matches from Swiggy Instamart.
4. **Frontend & Demo Mode Integrity:** Verified live mode product rendering, loading/empty/error states, retry capability, and distinct labeling between live quick-commerce data and demo retail datasets.
5. **Zero Regression Test Baseline:** 40 focused Swiggy tests pass, 399 backend tests pass (0 failures), 268 frontend Vitest tests pass across 30 suites (0 failures), and the frontend production build succeeds with 0 errors.

---

## 2. Integration Architecture Map

The end-to-end integration follows this verified runtime pipeline:

```mermaid
flowchart TD
    User["User in Browser"] -->|1. Searches 'milk' & enables Live Mode| FE["Frontend UI (React / TanStack Query)"]
    FE -->|2. GET /api/v1/grocery/compare?ingredient=milk&live_mode=true| API["FastAPI Backend (app/api/grocery.py)"]
    API -->|3. compare_grocery_prices(live_mode=True)| GS["GroceryService"]
    GS -->|4. get_configured_providers(live_mode=True)| Factory["Provider Factory"]
    Factory -->|5. Instantiates SwiggyInstamartMcpProvider| Prov["SwiggyInstamartMcpProvider"]
    Prov -->|6. Retrieves Bearer token or coordinates| Storage["SwiggyTokenStorage / SwiggyOAuthManager"]
    Prov -->|7. POST https://mcp.swiggy.com/im (tools/call search_products)| SwiggyMCP["Swiggy Instamart MCP Server"]
    SwiggyMCP -->|8. Returns JSON-RPC 2.0 with product variations| Prov
    Prov -->|9. Normalizes into NormalizedGroceryProduct| Matcher["ProductMatcher (all-MiniLM-L6-v2)"]
    Matcher -->|10. Semantic cosine similarity & unit pricing (₹)| Ranker["PriceComparisonService"]
    Ranker -->|11. Returns GroceryCompareResponse (PROVIDER_LIVE)| FE
    FE -->|12. Renders LIVE PRICE badge & Swiggy product cards| User
```

---

## 3. Files Inspected and Modified

### Files Inspected
- `backend/app/grocery_sources/swiggy_oauth.py`: OAuth 2.1 lifecycle, PKCE, token persistence, DCR.
- `backend/app/api/swiggy_auth.py`: OAuth login initiation, callback handler, address listing with privacy masking.
- `backend/app/grocery_sources/swiggy_instamart_provider.py`: MCP adapter, coordinate validation, error parsing.
- `backend/app/core/config.py`: Environment configuration and validation.
- `backend/app/grocery_sources/factory.py`: Provider factory and live vs. demo provider selection.
- `backend/app/grocery_sources/registry.py`: Parallel provider querying and TTL caching.
- `backend/app/api/grocery.py`: FastAPI routes for matching and price comparison.
- `backend/app/services/grocery_service.py`: Service orchestration and price ranking.
- `frontend/src/api/grocery.ts`: Axios client functions for grocery comparison and matching.
- `frontend/src/hooks/useGrocery.ts`: React Query hooks with isolated live vs. demo query keys.
- `frontend/src/components/grocery/GroceryPriceComparison.tsx`: Comparison UI, store filters, live badges.
- `frontend/src/pages/GroceryPage.tsx`: Top-level grocery page with live mode toggle banner.

### Files Modified
- `backend/app/grocery_sources/swiggy_oauth.py`: Fixed `NameError` in `refresh_tokens()` by referencing `ref_tok` instead of undefined `refresh_token` when provider does not rotate the refresh token.
- `backend/tests/test_swiggy_oauth.py`: Added automated test `test_refresh_token_without_rotation_preserves_existing_refresh_token`.
- `frontend/src/__tests__/GroceryPriceComparison.test.tsx`: Added test `15. Renders Demo Dataset badge in demo mode and does not label demo data as LIVE PRICE`.

---

## 4. OAuth 2.1, PKCE, and DCR Audit Results

| Check | Requirement | Verification Result |
|---|---|---|
| **State Generation** | Secure random, unguessable anti-CSRF token | `secrets.token_urlsafe(32)` generated per request |
| **State Validation** | Strict matching upon callback | Checked against `_pending_states`. Invalid or missing state raises HTTP 400 |
| **State Replay Prevention** | State must be single-use | One-time pop (`self._pending_states.pop(state)`) on exchange |
| **State Expiration** | Enforce TTL on authorization requests | Expired states cleared automatically after 900 seconds (15 min) |
| **PKCE Verifier** | RFC 7636 compliant high-entropy secret | `secrets.token_urlsafe(64)` ($\approx 86$ chars, within $43 \le \text{len} \le 128$) |
| **PKCE Challenge** | S256 transformation | `base64url(sha256(verifier)).rstrip("=")` |
| **Dynamic Client Registration** | RFC 7591 client discovery | Attempts POST `https://mcp.swiggy.com/auth/register` when client ID not pre-configured |
| **Token Storage Security** | Atomic, persistent, unexposed | Stored in `ml/artifacts/swiggy_oauth_tokens.json` via `.tmp` file and `os.replace` |
| **Token Leakage Prevention** | Zero token strings in logs or public API | `GET /api/v1/swiggy/status` returns booleans (`has_access_token`, `has_refresh_token`) only |
| **Token Refresh Hardening** | Support rotated and non-rotated refresh tokens | Resolved scoping issue (`new_ref or ref_tok`), retaining refresh credentials safely |

---

## 5. MCP Provider Verification Results

| Check | Target | Verification Result |
|---|---|---|
| **JSON-RPC Protocol** | `tools/call` for `search_products` and `get_addresses` | Standard JSON-RPC 2.0 payloads with structured arguments |
| **Schema Normalization** | Official nested `variations` & flat products | Accurately extracts `spinId`, `offerPrice`, `mrp`, `isInStockAndAvailable`, and package sizes |
| **Guest Location Support** | Coordinate-based delivery location | Uses `latitude` and `longitude` when `addressId` is absent |
| **Coordinate Validation** | Geographic bounds & numeric validity | Enforces paired coordinates, $-90 \le \text{lat} \le 90$, $-180 \le \text{lng} \le 180$ |
| **Unauthorized Recovery** | HTTP 401/403 & JSON-RPC `-32001` | Intercepts session expiration and performs automatic token refresh with single retry |
| **Rate Limiting** | HTTP 429 | Raises explicit `RuntimeError("Swiggy Instamart rate limit exceeded (HTTP 429).")` |
| **Failure Isolation** | Network errors or provider outages | Provider errors are isolated per-provider; never converted into fabricated products |

---

## 6. Live Smoke Test & Grocery Comparison API Verification

Live smoke testing was executed against `GET /api/v1/grocery/compare?ingredient=milk&live_mode=true`:

- **HTTP Status:** `200 OK`
- **Latency:** $\approx 1.08\text{ s}$ (after SentenceTransformer warmup)
- **Top-Level Metadata:**
  - `data_source`: `"live"`
  - `price_freshness`: `"PROVIDER_LIVE"`
  - `total_matches`: `28`
  - `comparison_mode`: `"package_price"`
- **Sample Result Items (Sanitized):**
  - **Product:** Akshayakalpa Organic High Protein Milk
  - **Price:** ₹99.00
  - **Store:** Swiggy Instamart
  - **Data Source Type:** `Swiggy Instamart`
  - **Price Freshness:** `PROVIDER_LIVE`
  - **Availability:** `true`

---

## 7. Frontend Verification & Demo Fallback

The frontend implementation was evaluated across 10 critical user states:
1. **Search Submission:** Submitting an ingredient (e.g. `milk`, `paneer`) triggers query execution.
2. **Live Mode Request:** Explicit `live_mode=true` parameter is passed to API client and included in React Query cache key.
3. **Loading State:** Skeleton comparison grid rendered while `isPending` is true.
4. **Live Product Rendering:** Products display genuine `product_name`, `store_name`, `price`, and `package_unit`.
5. **No Undefined Values:** Numeric currency formatter `formatINR()` guards against null/NaN values.
6. **Empty State:** Helpful empty state rendered when 0 results match the query.
7. **Error State:** Distinct rose banner rendered on failure with accessible retry button.
8. **Retry Action:** Retry button invokes React Query `refetch()` directly.
9. **Demo Data Transparency:** In demo mode (`live_mode=false`), the banner shows "Demo Mode Active" and products display the amber `Demo Dataset` badge.
10. **Zero Mislabeling:** Tests confirm `LIVE PRICE` badge is never rendered for demo data.

---

## 8. Security and Privacy Audit Findings

1. **Tokens and Secrets Exposure:** None. `GET /api/v1/swiggy/status` and `GET /api/v1/grocery/compare` contain no bearer tokens, client secrets, or private keys.
2. **Phone Number Sanitization:** In `GET /api/v1/swiggy/addresses`, customer phone numbers are masked (`******3210`).
3. **Log Sanitization:** `SensitiveDataFilter` in `app/core/logging.py` redacts `code`, `state`, and `token` parameters from access logs.
4. **Git Repository Cleanliness:** Neither `.env` nor `swiggy_oauth_tokens.json` are tracked by Git; both are explicitly listed in `.gitignore`.
5. **Request Timeouts:** All HTTP requests specify explicit timeouts (`5.0s` / `10.0s`).

---

## 9. Automated Testing Results

### 9.1 Focused Swiggy Tests
- **Command:** `backend/venv/Scripts/pytest.exe backend/tests/test_swiggy_oauth.py backend/tests/test_swiggy_instamart_provider.py`
- **Result:** **40 passed, 1 warning in 21.41s** (Exit code: 0)

### 9.2 Grocery & Cart Comparison Tests
- **Command:** `backend/venv/Scripts/pytest.exe backend/tests/test_price_comparison.py backend/tests/test_grocery_sources.py backend/tests/test_cart_api.py`
- **Result:** **28 passed, 9 warnings in 29.30s** (Exit code: 0)

### 9.3 Full Backend Test Suite
- **Command:** `backend/venv/Scripts/pytest.exe backend/tests`
- **Result:** **399 passed, 16 warnings in 70.20s** (Exit code: 0)

### 9.4 Full Frontend Test Suite
- **Command:** `npx vitest run`
- **Result:** **30 test files passed (30/30), 268 tests passed (268/268) in 6.15s** (Exit code: 0)

### 9.5 Frontend Production Build
- **Command:** `npm run build` (`tsc && vite build`)
- **Result:** **Build successful in 2.88s (0 TypeScript errors)** (Exit code: 0)

---

## 10. Phase Status & Next Phase Readiness

- **Status:** **PASS**
- **Existing Behaviors Preserved:** All OAuth 2.1 PKCE mechanisms, Swiggy Instamart live search, demo mode fallback, recipe catalogue, ML recommendation models, and UI styling intact.
- **Recommended Next Phase:** **Phase 7: Multi-Store Cart Optimization & Checkout Routing**.
