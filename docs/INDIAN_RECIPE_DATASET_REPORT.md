# INDIAN RECIPE DATASET REPORT

## Dataset Sources

| Source | Type | License | Records | Verification |
| ------ | ---- | ------- | ------: | ------------ |
| INDoRI_Sample | Authored/Research | CC-BY-4.0 | 3 | SOURCE_AUTHORED / VERIFIED |
| CommunityCookbook | User/Community | UNKNOWN | 1 | UNVERIFIED |

## Regional Coverage

* South Indian: 2
* North Indian: 2

State breakdown:
* Tamil Nadu: 1
* Punjab: 1
* Karnataka: 1

## Cuisine Coverage

* Indian: 4

## Dietary Coverage

* Vegetarian: 3
* Non-Vegetarian: 1

## Data Quality

* Total Records Processed: 4
* Valid Records: 4
* Invalid Records: 0
* Duplicates (on rerun): 4
* Missing ingredients: 0
* Missing instructions: 0
* Missing provenance: 0
* Verified (SOURCE_AUTHORED or higher): 3
* Unverified: 1

## Ingredient Quality

* Unique raw ingredients processed: 5
* Unique normalized ingredients: 5
* Unmapped ingredients: 0
* Unit coverage: `cup`, `tbsp`, `g`, `tsp` mapped successfully.

## ML Readiness

* **TF-IDF**: YES. Text fields (`name`, `description`, `ingredients`, `instructions`) are clean and present.
* **Sentence Transformers**: YES. Clear ingredient vectors and recipe titles.
* **Random Forest**: YES. Prep/cook times and serving sizes are strictly numeric. Dietary type is cleanly categorical. (Requires labels from usage for training).
* **K-Means**: YES. Sufficient numeric features available for structural clustering.
