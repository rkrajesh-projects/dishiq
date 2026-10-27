# DishIQ — Phase 16: Final Demonstration Script

## 1. Overview & Objective

This document provides a verified, reproducible 5–10 minute demonstration script for **DishIQ: Intelligent Meal Planning, Grocery Comparison, and Cooking Assistant**.

The demonstration walks an evaluator or professor through the connected **Plan → Shop → Cook** workflow, demonstrating:
1. **Real Machine Learning Subsystem**: Hybrid recommendations combining TF-IDF lexical matching, 384-dimensional SentenceTransformer embeddings (`all-MiniLM-L6-v2`), Random Forest recipe suitability prediction, and K-Means cluster grouping.
2. **Ingredient Intelligence & Grocery Comparison**: Automatic ingredient normalization, multi-store price comparison in Indian Rupees (₹ INR), and clear provenance tracking (Demo vs Live).
3. **Interactive Kitchen Assistant**: Step-by-step progress tracking, real-time drift-free timers, and contextual AI Cooking Companion Q&A.
4. **Secure Multi-Tenant Account Experience**: Tenant data isolation, JWT authentication, and credential masking.

---

## 2. Prerequisites & Environment Configuration

### 2.1 System Prerequisites
- **Python**: 3.10+ (with virtual environment `.venv`)
- **Node.js**: v18+ with `npm`
- **Database**: SQLite (default `dishiq.db` for local demo) or PostgreSQL (for Docker)

### 2.2 Environment Setup
Ensure your `.env` is configured (copied from `.env.example`). For demonstration mode, external paid API keys are optional:

```env
APP_NAME=DishIQ
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8001
API_V1_STR=/api/v1
SECRET_KEY=DishIQ_Super_Secret_Key_Change_In_Production
DATABASE_URL=sqlite:///./dishiq.db
FRONTEND_URL=http://localhost:5173
GROCERY_PROVIDER=demo
AI_PROVIDER=demo
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
```

---

## 3. Exact Startup Commands

### Terminal 1: Backend API (Port 8001)
From the repository root (`D:\DishIQ`):
```powershell
# Activate Python virtual environment and launch Uvicorn
.venv\Scripts\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```
*Expected output*:
- Preloading SentenceTransformer model `[all-MiniLM-L6-v2]` (warm and ready).
- HybridRecommender loaded underlying models (TF-IDF, Semantic, Random Forest, K-Means).
- Uvicorn running on `http://127.0.0.1:8001`.

### Terminal 2: Frontend Client (Port 5173)
From the `frontend/` directory:
```powershell
cd frontend
$env:PATH = "C:\Program Files\nodejs;$env:PATH"
npm run dev
```
*Expected output*:
- Vite dev server running at `http://localhost:5173/`.

### Interactive URLs
- **Web Application UI**: `http://localhost:5173`
- **FastAPI Interactive Docs**: `http://localhost:8001/docs`
- **Application Health Probe**: `http://localhost:8001/api/v1/health`
- **Operational Metrics**: `http://localhost:8001/api/v1/health/metrics`

---

## 4. Step-by-Step Demonstration (Plan → Shop → Cook)

### Part 1: Authentication & Account Isolation (1 Minute)
1. Open `http://localhost:5173/login`.
2. Register a new user:
   - Name: `Demo Chef`
   - Email: `chef@example.com`
   - Password: `Password123!`
3. Log in. Notice the user avatar and profile in the header navigation bar.
4. Open a second Incognito browser window:
   - Unauthenticated requests to protected routes (`/meal-plan`, `/shopping-list`, `/cooking`) automatically redirect to `/login`.

---

### Part 2: Plan — Real ML Recommendation Pipeline (3 Minutes)
1. Navigate to **Recipes** (`/recipes` or search bar on Home page).
2. Enter the query:
   ```
   Paneer butter masala
   ```
3. **Inspect the Ranked Results**:
   - Notice the top ranked recipes: `Kashmiri Style Paneer Masala Recipe`, `Palak Paneer`, and `Paneer Bhurji`.
   - Each recipe card displays:
     - Match Score (e.g., `5.15`)
     - Explanations pill: `"High semantic ML relevance"`, `"High generic recipe suitability (4.5/5)"`.
4. **Demonstrate Semantic Generalization**:
   - Clear the search and type:
     ```
     cottage cheese curry
     ```
   - *Observation*: Notice that `Paneer Bhurji` ranks #1!
   - *Explanation to Evaluator*: The lexical TF-IDF model has zero character overlap between "cottage cheese" and "paneer", but the 384-dimensional SentenceTransformer neural embedding recognizes they are semantic synonyms in culinary contexts.
5. Click on **Palak Paneer** or **Kashmiri Style Paneer Masala Recipe** to view the recipe details:
   - Notice parsed canonical ingredients with normalized units.
   - Click **Add to Meal Plan** $\to$ select date and servings (e.g., 4 servings) $\to$ Save.

---

### Part 3: Shop — Ingredient Normalization & Grocery Comparison (2 Minutes)
1. Navigate to **Meal Plan** (`/meal-plan`).
2. Review the scheduled recipe with 4 servings.
3. Click **Generate Shopping List**:
   - The consolidation engine scales ingredient quantities proportionally based on servings.
   - Ingredients with identical canonical names across recipes are automatically aggregated into a single line item.
4. Click **Compare Grocery Prices**:
   - DishIQ queries the grocery catalogue for each item (e.g., `paneer`, `milk`, `garam masala`).
   - Prices are displayed strictly in **Indian Rupees (₹ INR)**.
   - Notice the provenance badges:
     - Demonstration stores display: `[DEMO DATA - MOCK RETAIL]`.
     - When Swiggy MCP is authenticated, live items display: `[SWIGGY INSTAMART LIVE]`.
   - The comparison engine calculates unit prices (₹/kg or ₹/L) to highlight the best value option.

---

### Part 4: Cook — Interactive Kitchen Assistant & AI Companion (3 Minutes)
1. On the recipe page, click **Start Cooking**.
2. **Preparation Phase**:
   - The screen shows the ingredient checklist scaled to your chosen servings.
   - Check off ingredients as you prepare them. Notice progress updates.
3. **Interactive Step-by-Step Guidance**:
   - Click **Next Step** to advance through instructions.
   - Notice step number and progress bar persistence.
4. **Active Timers**:
   - Click **Start Timer** (e.g., 5-minute simmer timer).
   - Notice the drift-free real-time countdown. Pause and resume the timer to verify state preservation.
5. **AI Cooking Companion**:
   - In the companion chat window, ask a contextual cooking question:
     ```
     What should I do if the gravy turns out too salty?
     ```
   - The companion analyzes the active recipe, step, and current ingredients, responding with actionable culinary guidance (e.g., add a splash of cream, a boiled potato, or extra curd to balance sodium levels).
6. Click **Finish Cooking**:
   - The session marks as completed, logs timestamped completion, and redirects cleanly.

---

## 5. Demonstrating Technical Depth to an Evaluator

When demonstrating DishIQ to a professor or technical evaluator, highlight these core engineering contributions:

### 1. Hybrid ML Architecture (Not Simple Regex / Hardcoded Responses)
- **Scoring Function**:
  $$\text{Final Score} = w_{\text{TF-IDF}} \cdot S_{\text{lexical}} + w_{\text{Semantic}} \cdot S_{\text{neural}} + w_{\text{RF}} \cdot \text{Suitability} + w_{\text{Pantry}} \cdot \text{Overlap}$$
- **Lexical Layer**: TF-IDF V2 (`recipe_tfidf_v2.joblib`, 1,040 recipes $\times$ 6,100 vocabulary features).
- **Semantic Layer**: Pre-trained SentenceTransformer (`all-MiniLM-L6-v2`) mapping recipes and grocery products into 384-dimensional dense vector space.
- **Suitability Regressor**: Random Forest model (`suitability_rf_model.joblib`) predicting recipe execution viability (1.0 to 5.0).
- **Clustering**: K-Means (`recipe_kmeans_v1.joblib`) grouping recipes into culinary flavor profiles.

### 2. Live Swiggy Instamart OAuth 2.1 + PKCE Integration
- Demonstrates official Model Context Protocol (MCP) tool integration.
- Strictly adheres to RFC 7636 PKCE with `code_challenge` (S256) and `code_verifier`.
- Secure credential management: tokens stored locally in encrypted JSON artifacts, never exposed in client API responses.
- Graceful degradation: seamlessly falls back to local demo retail catalog if user credentials expire or the MCP service is unavailable.

### 3. Reliability, Observability & Container Readiness
- **Security**: Non-root container execution (`USER dishiq`), request body size limit middleware (5MB DoS defense), defensive security headers.
- **Observability**: Request correlation tracing (`X-Request-ID`), structured JSON log emission, bounded in-memory metrics (`GET /api/v1/health/metrics`).
- **Data Integrity**: Multi-tenant database isolation, explicit session rollbacks on route exceptions, and idempotent Alembic migrations.

---

## 6. Cleanup Steps

To reset the demonstration state without losing development databases or training models:

```powershell
# 1. Stop backend and frontend processes (Ctrl+C in terminal windows)

# 2. To remove test accounts created during demo (optional):
# Simply delete test user rows from SQLite or leave them intact.
# The user's dishiq.db and ML artifacts are completely preserved.
```
