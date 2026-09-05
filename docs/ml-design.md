# DishIQ Machine Learning Architecture & Design

## 1. Subsystem Boundaries

The Machine Learning subsystem in DishIQ is decoupled from traditional REST backend business logic. It handles probabilistic, natural language, semantic, and recommendation tasks:

1. **Recipe Semantic Search & Preference Scorer**
2. **Ingredient Normalization & Parsing Engine**
3. **Grocery Product Entity Matcher**
4. **AI Kitchen Memory & Learning Pipeline**

---

## 2. ML Engine Components

### 2.1 Recipe Ranking & Semantic Recommendation Engine
- **Technology**: `Scikit-Learn` (`TfidfVectorizer`, `cosine_similarity`), `Joblib`.
- **Function**: Converts query text and recipe titles/descriptions/ingredients into dense TF-IDF feature vectors (`max_features=500`, `ngram_range=(1, 2)`).
- **Centralized Scoring Configuration**: Located in `backend/app/core/recommendation_config.py`:
  $$\text{Score} = \text{BaseScore} + w_{\text{sim}} \cdot \text{CosSim} + w_{\text{pantry}} \cdot \text{PantryOverlap} + w_{\text{diet}} \cdot \text{DietMatch} + w_{\text{rating}} \cdot \left(\frac{\text{Rating}}{5.0}\right) + w_{\text{time}} \cdot \text{TimeLimitMatch}$$
  where:
  - $w_{\text{sim}} = 0.80$
  - $w_{\text{pantry}} = 0.25$
  - $w_{\text{diet}} = 0.20$
  - $w_{\text{rating}} = 0.10$
  - $w_{\text{time}} = 0.15$
  - $\text{BaseScore} = 0.50$

### 2.2 Model Artifact & Metadata Specification
Model artifacts reside in `ml/artifacts/`:
- `recipe_tfidf.joblib`: Contains vectorizer, sparse matrix, recipe IDs, and recipe metadata.
- `metadata.json`: Captures metadata schema:
  ```json
  {
    "model_name": "DishIQ Recipe TF-IDF Recommender",
    "model_version": "1.0.0",
    "algorithm": "TF-IDF + Cosine Similarity",
    "feature_count": 500,
    "dataset_version": "1.0.0",
    "training_timestamp": "2026-08-04T22:09:00Z",
    "sklearn_version": "1.4.0",
    "artifact_filename": "recipe_tfidf.joblib",
    "total_recipes": 15
  }
  ```

### 2.3 Structured Event Logging
All model loading and recommendation queries emit structured JSON log events via `app.core.logging`:
- `ML Recommender Model loaded successfully`: Artifact path, feature dimension, load duration.
- `Recommendation query completed`: Query text, dietary filter, candidates evaluated count, recommendations returned count, total duration in ms.

---

## 3. Training & Model Artifact Management

- Models are trained offline via `python ml/training/train_recipe_recommender.py` and serialized under `ml/artifacts/`.
- Evaluated via `python ml/evaluation/evaluate_model.py` generating `ml/evaluation/report.json`.
- Model loading is managed asynchronously during FastAPI application startup to eliminate per-request loading latency.
