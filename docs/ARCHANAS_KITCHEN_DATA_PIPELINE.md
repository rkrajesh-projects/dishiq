# Archana's Kitchen Data Pipeline

## Overview
This pipeline safely collects, normalizes, and ingests recipes from [Archana's Kitchen](https://www.archanaskitchen.com/) into the DishIQ database. It builds a robust dataset layer specifically suited for Indian regional recipes, to be used in future ML features (TF-IDF, Sentence Transformers, Clustering).

## Architecture
```text
ARCHANA'S KITCHEN 
      ↓ [Public Category Pages]
SOURCE DISCOVERY (Pagination & URL filtering)
      ↓ 
RECIPE COLLECTION (Safe polling, no anti-bot bypass)
      ↓ [JSON-LD Extraction]
RAW SOURCE RECORD
      ↓
NORMALIZATION (Ingredients, units, HTML stripping)
      ↓
VALIDATION & DEDUPLICATION (By Canonical Name & Source ID)
      ↓
POSTGRESQL (DishIQ Database via DatasetPipeline)
```

## Source Handling & Legality
- **Rate Limiting**: Strictly enforces 1-second sleeps between requests to avoid overwhelming the server.
- **Access Limits**: Relies purely on publicly accessible HTML and `application/ld+json`. No APIs are exploited, and no captchas are bypassed.
- **Licensing**: Marked as `UNKNOWN` for public redistribution unless explicitly permitted by the source. All recipes retain provenance attribution linking directly to the original page.

## Normalization Details
1. **Ingredients**: Cleaned of HTML. A rudimentary quantity/unit extraction parses basic weights (e.g. `1 cup`) into `quantity=1`, `unit="cup"`. The raw string is fully preserved.
2. **Metadata**: 
   - `prepTime` & `cookTime` (ISO 8601 duration) parsed into integer minutes.
   - `recipeYield` parsed into an integer serving count.
3. **Verification**: 
   - Only tagged as `SOURCE_AUTHORED` or `CHEF` if the JSON-LD `author` field explicitly provides a recognized name (like "Archana Doshi").
   - Otherwise, `UNVERIFIED` is applied to avoid fabricating trust signals.

## Update Strategy
The collection script is idempotent. Rerunning `python backend/scripts/collect_archanas_kitchen.py --update-existing` will deduplicate by `source_recipe_id` and update any fresh metadata.
