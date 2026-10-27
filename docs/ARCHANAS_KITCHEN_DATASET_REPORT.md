# ARCHANA'S KITCHEN EXHAUSTIVE DATASET REPORT

## Summary & Coverage Limitation
This report covers the execution of the full exhaustive queue-based crawler (`collect_archanas_kitchen.py --crawl-all`).

**Coverage Status:** PARTIAL 

**Reason for Partial Coverage:**
The crawler is fully capable of exhaustive discovery (queue-based, handles pagination `?page=`, recursively maps category trees). However, the Archana's Kitchen website employs strict rate-limiting and anti-bot protection (Cloudflare). Extensive exhaustive crawls from our server IP quickly result in `403 Forbidden` and `429 Too Many Requests` blocks. 

Per the strict project guidelines ("Do NOT bypass authentication, bypass CAPTCHA, bypass anti-bot protection... If the website blocks collection: STOP and report the limitation"), we gracefully halted the crawler and preserved its queue state in `data/raw/archanas_kitchen/state.json`.

## Discovery Statistics (Pre-Block Sample)
* **Category pages & Pagination pages visited:** 16 (Before encountering rate limiting/blocks)
* **Recipe URLs discovered & queued:** 234 unique canonical URLs
* **Failed URLs:** 2 (403 Forbidden hits triggering safe shutdown)

## Import Statistics (From successfully fetched recipes prior to block)
* **Recipes collected:** 10
* **Recipes valid:** 10
* **Recipes invalid:** 0
* **Recipes inserted:** 10
* **Recipes updated/skipped:** 0
* **Duplicates prevented:** 0

## Metadata & Quality
* **Indian recipes:** 10 
* **Non-Indian recipes:** 0 (Crawler was seeded at `/category/recipes/indian`)
* **Missing ingredients/instructions:** 0
* **Missing metadata (Cuisine/Category/Author):** 0

*All numbers reflect the actual successful insertions before the defensive shutdown protocol triggered.*
