# RECIPE DATA PROVENANCE

## Origin and Tracing
Every recipe imported into DishIQ retains its original identity:
* `source_name`: The entity that provided the dataset (e.g., "Archana's Kitchen").
* `source_recipe_id`: The canonical slug or ID used by the origin system.
* `source_url`: Where the recipe can be viewed externally.
* `source_license`: The copyright/license. (Archana's Kitchen is `UNKNOWN` for redistribution; for fair-use academic purposes only).
* `author`: The person or organization that created the recipe (extracted from JSON-LD).
* `dataset_version`: Tracks which import run populated the recipe (e.g., `archanas-kitchen-v1`).

## Verification Tiers
* **CHEF_VERIFIED**: Explicitly verified by a recognized professional.
* **SOURCE_AUTHORED**: Published by a reputable source and authored by a known entity (e.g., Archana Doshi).
* **UNVERIFIED**: Community submissions.

## Update & Deduplication Strategy
If `collect_archanas_kitchen.py --update-existing` is run, recipes are strictly deduplicated by matching `source_recipe_id` against existing records. Instead of inserting duplicate rows, the pipeline skips or updates metadata cleanly. This protects DishIQ user feedback linked to the primary key.
