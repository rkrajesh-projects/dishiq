# DishIQ: Intelligent Meal Planning, Grocery Comparison, Cooking Assistant, and AI Kitchen Memory

DishIQ is an AI-powered kitchen intelligence platform that unifies recipe discovery, smart recipe ranking, ingredient normalization, multi-store grocery price comparison, economical shopping cart optimization, interactive cooking guidance, and persistent **AI Kitchen Memory**.

---

## 🌟 Key Features

- **Smart Recipe Discovery & Ranking**: Find recipes semantic-matched to user cravings using a TF-IDF & multi-factor recommendation engine scored based on dietary restrictions, ratings, and active pantry stock.
- **Ingredient Extraction & Normalization**: Automatically parse raw ingredient strings into structured canonical units and quantities.
- **Grocery Price Comparison**: Compare product prices across demonstration grocery stores in Indian Rupees (INR) to find the best deals.
- **Economical Shopping Plan**: Generate optimized multi-store or single-store shopping carts balancing total cost (in ₹) and store convenience.
- **Interactive Step-by-Step Cooking**: Voice & UI step assistant with active timers and progress tracking.
- **AI Kitchen Memory**: Proactively recommends meals based on recorded pantry inventory, family preferences, budget target (in ₹), and cooking history.

> **Notice**: All grocery store pricing data in current demonstration mode is mock/demo retail data in Indian Rupees (INR) created for evaluation. It does not represent live store web-scraping.

---

## 🇮🇳 Indian Currency & Localization (INR)

DishIQ is standardized for the Indian market:
- All product prices, delivery fees, and shopping cart totals use **Indian Rupees (INR)**.
- Backend API endpoints return structured price responses:
  ```json
  {
    "price": 95.00,
    "currency": "INR",
    "delivery_fee": 0.00
  }
  ```
- Frontend formatting uses `Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" })` displaying prices cleanly as **₹95**, **₹412**, **₹1,250**, and **₹5,499**.
- User Profile budgets (Weekly: ₹2,500, Monthly: ₹10,000) and Pantry Inventory Stock Values are tracked in INR.

---

## ⚙️ Centralized ML Recommendation Configuration

Recommendation scoring weights are configured in `backend/app/core/recommendation_config.py`:
- `base_score`: `0.50`
- `cosine_similarity_weight`: `0.80` (TF-IDF vector similarity boost)
- `ingredient_overlap_weight`: `0.25` (Per matching pantry item)
- `dietary_match_weight`: `0.20` (Dietary compatibility bonus)
- `rating_weight`: `0.10` (Average rating score multiplier)
- `cooking_time_weight`: `0.15` (Cooking time limit bonus)

---

## 🤖 ML Subsystem & Model Artifacts

- **Model Artifact**: `ml/artifacts/recipe_tfidf.joblib` (Contains trained `TfidfVectorizer` and sparse document matrix).
- **Model Metadata**: `ml/artifacts/metadata.json` (Captures `model_name`, `model_version`, `algorithm`, `feature_count`, `sklearn_version`, and `training_timestamp`).
- **Offline Training Script**: `python ml/training/train_recipe_recommender.py`
- **Evaluation Script**: `python ml/evaluation/evaluate_model.py`

---

## 📊 Structured JSON Logging

All backend request latencies, exceptions, and ML model evaluation events emit structured JSON log entries:
- **Model Load Event**: Logs artifact path, feature dimension, and load duration.
- **Recommendation Request Event**: Logs search query, dietary filter, candidates evaluated, results returned, and total calculation latency in milliseconds.

---

## 🛠 Tech Stack

- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, TanStack React Query, Axios, React Error Boundary, Vitest
- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic
- **Machine Learning**: Scikit-learn (TF-IDF, Cosine Similarity), Pandas, Joblib
- **MCP**: Python MCP SDK
- **Testing**: Pytest, Vitest

---

## 📁 Repository Structure

```
dishiq/
├── backend/            # FastAPI REST backend & services
│   ├── app/
│   │   ├── api/        # REST API endpoints (recipes, stores, products, recommendations)
│   │   ├── core/       # Configuration, logging, exception handling, recommendation_config
│   │   ├── db/         # Session & DB setup, seed script
│   │   ├── models/     # Database entities (SQLAlchemy ORM)
│   │   ├── repositories/# Data access abstraction
│   │   ├── schemas/    # Pydantic schemas
│   │   └── services/   # Business logic & RecommendationService
│   └── tests/          # Pytest test suite
├── docs/               # System & Architecture documentation
├── data/               # Seed data & demonstration grocery catalogs
├── ml/                 # Machine learning models, training, evaluation & artifacts
│   ├── artifacts/      # recipe_tfidf.joblib & metadata.json
│   ├── evaluation/     # evaluate_model.py & report.json
│   ├── training/       # train_recipe_recommender.py
│   ├── utils/          # feature_engineering.py
│   └── tests/          # test_ml_pipeline.py
├── mcp-server/         # Model Context Protocol tool server
├── frontend/           # React + Vite + TypeScript frontend application
├── docker-compose.yml  # Container orchestration setup
├── .env.example        # Environment configuration template
└── README.md
```

---

## 🚀 Quickstart (Docker Setup)

DishIQ runs via a unified Docker Compose stack.

### 1. Environment Setup
Create a `.env` file from the example template:
```bash
cp .env.example .env
```
Ensure the following variables (found in `.env.example`) are set:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

### 2. Run the Stack
Start all services and build images using Docker Compose:
```bash
docker compose up --build -d
```
> **Note**: Database migrations and initial seed data are automatically applied on container startup via the backend's `docker-entrypoint.sh`. No manual steps are needed!

### Default Ports
- **Frontend UI**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **PostgreSQL**: `localhost:5432`
- **MCP Server**: Internal only (accessed via backend)

---

## 🧪 Testing

DishIQ includes comprehensive test suites across all layers. Run them using the following commands:

- **Backend (Pytest)**:
  ```bash
  cd backend && pytest
  ```
- **Frontend (Vitest)**:
  ```bash
  cd frontend && npm test
  ```
- **MCP Server (Pytest)**:
  ```bash
  cd mcp-server && pytest
  ```
- **E2E Tests (Playwright)**:
  ```bash
  cd e2e && npx playwright test
  ```

---

## 🛒 Demo Data Disclaimer

All grocery prices, store names, and product data shown in DishIQ are **demonstration datasets (in INR)** and do not represent live retailer prices. DishIQ does not scrape or integrate with restricted grocery platforms. The current prices are purely for demonstration and evaluation purposes.

---

## ⚠️ Known Limitations

- **Real-time Grocery Integration**: Live real-time grocery price integration (planned for Phase 13) is deferred. The system currently uses `DemoGroceryProvider` with seeded demonstration data.
- **Cart Optimization Latency**: The `POST /api/cart/optimize` endpoint currently takes ~15-20 seconds to respond due to sequential per-ingredient product matching. This is a known performance issue planned for a future optimization pass, not a correctness bug.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📚 Documentation

For full architectural, API, database, ML, and MCP design specs, refer to the `docs/` folder:
- [Requirements Specification](docs/requirements.md)
- [Architecture & Workflow](docs/architecture.md)
- [API Specification](docs/api-design.md)
- [Database Schema Design](docs/database-design.md)
- [ML Architecture](docs/ml-design.md)
- [MCP Tools Design](docs/mcp-design.md)
- [Phase Implementation Roadmap](docs/phase-plan.md)
