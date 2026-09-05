# DishIQ System Architecture & Design

## 1. Modular Architecture Overview

DishIQ is structured into four cleanly decoupled tiers:

1. **Frontend Tier (React + Vite + TypeScript + Tailwind CSS)**
   - Single Page Application (SPA) offering recipe search, grocery comparison dashboards, shopping list management, interactive cooking assistant UI, and AI Kitchen Memory settings.
2. **Backend Services Tier (Python + FastAPI + SQLAlchemy + PostgreSQL)**
   - RESTful API gateway handling business logic, session management, user preferences, pantry CRUD, and orchestration between ML services and database persistence.
3. **Machine Learning Subsystem (Scikit-learn + Sentence Transformers + Pandas + Joblib)**
   - Isolated ML services for recipe semantic vector embedding, smart ranking, ingredient NLP normalization, product match scoring, and preference decay learning.
4. **Model Context Protocol Tier (Python MCP SDK)**
   - Dedicated MCP tool server exposing structured tools (`search_recipes`, `compare_store_prices`, `get_pantry_inventory`) to AI assistants and LLM orchestrators.

---

## 2. System Architecture Diagram

```mermaid
graph TD
    subgraph Frontend["Frontend Tier (React / TypeScript / Tailwind)"]
        UI[User Interface & SPA]
        CookUI[Interactive Cooking Assistant]
        MemUI[AI Kitchen Memory Dashboard]
    end

    subgraph Backend["Backend Tier (FastAPI Gateway)"]
        API[FastAPI Router / REST API]
        Auth[Auth & User Service]
        PantrySvc[Pantry & Inventory Service]
        GrocerySvc[Grocery & Comparison Service]
        MemorySvc[Kitchen Memory Engine]
        DB[(PostgreSQL / SQLAlchemy ORM)]
    end

    subgraph MLTier["Machine Learning Subsystem"]
        Ranker[Recipe Ranking & Scorer]
        NLP[Ingredient Normalizer]
        Matcher[Product Matcher]
        MemML[Preference & Memory Model]
    end

    subgraph MCPTier["Model Context Protocol Server"]
        MCPServer[Python MCP SDK Server]
        RecipeTools[Recipe Tools]
        GroceryTools[Grocery Tools]
        PantryTools[Pantry Tools]
    end

    subgraph DataSources["External / Mock Providers"]
        DemoGrocery[Demonstration Grocery Data Provider]
        FutureAPI[Future Official Retailer Adapters]
    end

    UI -->|HTTP / REST| API
    CookUI -->|HTTP / REST| API
    MemUI -->|HTTP / REST| API

    API --> DB
    PantrySvc --> DB
    GrocerySvc --> DB
    MemorySvc --> DB

    API --> MLTier
    Ranker --> MLTier
    Matcher --> MLTier
    
    MCPServer --> RecipeTools
    MCPServer --> GroceryTools
    MCPServer --> PantryTools
    
    RecipeTools --> API
    GroceryTools --> API
    PantryTools --> API

    GrocerySvc --> DemoGrocery
    GrocerySvc -.-> FutureAPI
```

---

## 3. Workflow Diagram (MVP 12-Step Pipeline)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Frontend (React)
    participant API as FastAPI Backend
    participant ML as ML Subsystem
    participant DB as PostgreSQL DB
    participant Demo as Demo Grocery Provider

    User->>FE: 1. Search for a dish ("Paneer Bhurji")
    FE->>API: GET /api/v1/recipes/search?q=Paneer+Bhurji
    API->>ML: Semantic Search & Ranking Query
    ML-->>API: Ranked Recipe Candidates
    API-->>FE: 2. Return Ranked Recipes
    User->>FE: 3. Select Recipe
    FE->>API: GET /api/v1/recipes/{id}
    API->>ML: 4. Extract & Normalize Ingredients
    ML-->>API: Normalized Ingredient Schema
    API->>DB: 5. Query User Pantry Inventory
    DB-->>API: Active Pantry Items
    API->>Demo: 6. Search Missing Ingredients in Catalogs
    Demo-->>API: Store Product Candidates
    API->>ML: 7. Run Product Matching & Store Price Compare
    ML-->>API: Store Price Comparison Matrix
    API->>API: 8. Generate Economical Shopping Cart
    API-->>FE: Return Recipe Details, Pantry Match & Cart Plan
    User->>FE: 9. Launch Interactive Cooking Assistant Mode
    FE->>API: POST /api/v1/cooking/start
    User->>FE: 10. Complete Cooking & Submit Feedback
    FE->>API: POST /api/v1/feedback
    API->>ML: 11. Update User & Family Preference Models
    API->>DB: 12. Persist AI Kitchen Memory & Deduct Pantry Stock
    API-->>FE: Confirmation & Next Proactive Recommendation
```

---

## 4. Architectural Guarantees

1. **Demonstration Data Isolation**: Demo grocery pricing data is strictly isolated within mock providers. Live scraping of non-authorized grocery websites is prohibited.
2. **Stateless Backend**: FastAPI backend instance is stateless, allowing horizontal scaling. Session state is managed via secure tokens and database persistence.
3. **Model Decoupling**: ML models are loaded asynchronously and executed via standard Python service interfaces, allowing independent model upgrades without API breaking changes.
