"""
Archana's Kitchen educational recipe scraper for DishIQ.

Purpose:
    Collect publicly available recipe metadata and structured recipe data
    for learning / research purposes.

IMPORTANT:
    - Does NOT bypass Cloudflare/CAPTCHA.
    - Does NOT use authentication.
    - Stops on repeated 403/429 responses.
    - Uses a conservative request delay.
    - Saves progress so the scraper can resume.
    - Maximum 1000 recipes.

Output:
    data/raw/archanas_kitchen/
        recipes.csv
        recipes.json
        state.json
        failed_urls.csv

Run:
    python backend/scripts/scrape_archanas_kitchen.py

Optional:
    python backend/scripts/scrape_archanas_kitchen.py --max-recipes 1000
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urldefrag

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


# ============================================================
# Configuration
# ============================================================

BASE_URL = "https://www.archanaskitchen.com"

START_URLS = [
    "https://www.archanaskitchen.com/category/recipes",
    "https://www.archanaskitchen.com/category/recipes/indian",
]

OUTPUT_DIR = Path("data/raw/archanas_kitchen")

RECIPES_CSV = OUTPUT_DIR / "recipes.csv"
RECIPES_JSON = OUTPUT_DIR / "recipes.json"
STATE_FILE = OUTPUT_DIR / "state.json"
FAILED_FILE = OUTPUT_DIR / "failed_urls.csv"

DEFAULT_MAX_RECIPES = 1000

# Be conservative.
MIN_DELAY = 3.0
MAX_DELAY = 6.0

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "DishIQ-Educational-Research-Scraper/1.0 "
    "(learning project; respectful low-rate crawling)"
)


# ============================================================
# Session
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-IN,en;q=0.8",
    }
)


# ============================================================
# Utility functions
# ============================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        value = ", ".join(str(x) for x in value)

    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_url(url: str) -> str:
    """
    Normalize URL while preserving query-free canonical page URL.
    """

    if not url:
        return ""

    url = urljoin(BASE_URL, url)
    url, _ = urldefrag(url)

    parsed = urlparse(url)

    if parsed.netloc.lower() != urlparse(BASE_URL).netloc.lower():
        return ""

    path = parsed.path.rstrip("/")

    if not path:
        path = "/"

    return f"https://www.archanaskitchen.com{path}"


def is_archanas_url(url: str) -> bool:
    normalized = normalize_url(url)

    if not normalized:
        return False

    return urlparse(normalized).netloc == urlparse(BASE_URL).netloc


def looks_like_recipe_url(url: str) -> bool:
    """
    Heuristic filter.

    Archana's Kitchen has many category/navigation pages, so we avoid
    obvious non-recipe URLs. Final confirmation happens through JSON-LD.
    """

    path = urlparse(url).path.lower()

    excluded = [
        "/category/",
        "/tag/",
        "/author/",
        "/search",
        "/contact",
        "/about",
        "/privacy",
        "/terms",
        "/login",
        "/register",
    ]

    if any(x in path for x in excluded):
        return False

    return len(path.strip("/").split("/")) >= 1


def polite_delay() -> None:
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


# ============================================================
# State
# ============================================================

def load_state() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not STATE_FILE.exists():
        return {
            "queue": START_URLS.copy(),
            "visited": [],
            "recipe_urls": [],
            "collected": [],
            "failed": [],
            "blocked": False,
            "last_run": None,
        }

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "queue": START_URLS.copy(),
            "visited": [],
            "recipe_urls": [],
            "collected": [],
            "failed": [],
            "blocked": False,
            "last_run": None,
        }


def save_state(state: dict) -> None:
    state["last_run"] = utc_now()

    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ============================================================
# HTTP
# ============================================================

def fetch(url: str) -> tuple[str | None, int | None]:
    """
    Fetch a page.

    Returns:
        html, status_code

    On 403 / 429:
        caller should stop crawling.
    """

    polite_delay()

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        status = response.status_code

        if status in (403, 429):
            print()
            print("=" * 70)
            print(f"ACCESS RESTRICTED: HTTP {status}")
            print(url)
            print("Stopping scraper without bypassing the restriction.")
            print("=" * 70)

            return None, status

        if status >= 400:
            return None, status

        return response.text, status

    except requests.RequestException as exc:
        print(f"Request error: {url}")
        print(exc)

        return None, None


# ============================================================
# JSON-LD
# ============================================================

def extract_jsonld(soup: BeautifulSoup) -> list[Any]:
    results = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        raw = script.string or script.get_text()

        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
            results.append(data)
        except json.JSONDecodeError:
            continue

    return results


def flatten_jsonld(data: Any) -> list[dict]:
    """
    Flatten JSON-LD structures containing:
        - objects
        - @graph
        - lists
    """

    output = []

    if isinstance(data, dict):

        if "@graph" in data:
            output.extend(flatten_jsonld(data["@graph"]))

        else:
            output.append(data)

    elif isinstance(data, list):

        for item in data:
            output.extend(flatten_jsonld(item))

    return output


def get_recipe_jsonld(soup: BeautifulSoup) -> dict | None:

    scripts = extract_jsonld(soup)

    for script_data in scripts:

        for item in flatten_jsonld(script_data):

            item_type = item.get("@type")

            if isinstance(item_type, list):
                types = item_type
            else:
                types = [item_type]

            if "Recipe" in types:
                return item

    return None


# ============================================================
# JSON-LD field extraction
# ============================================================

def get_person_name(value: Any) -> str:

    if isinstance(value, dict):
        return clean_text(value.get("name"))

    if isinstance(value, list):

        names = []

        for item in value:

            if isinstance(item, dict):
                name = clean_text(item.get("name"))

                if name:
                    names.append(name)

            else:
                names.append(clean_text(item))

        return ", ".join(names)

    return clean_text(value)


def get_rating(recipe: dict) -> str:

    rating = recipe.get("aggregateRating")

    if not isinstance(rating, dict):
        return ""

    return clean_text(
        rating.get("ratingValue")
    )


def get_review_count(recipe: dict) -> str:

    rating = recipe.get("aggregateRating")

    if not isinstance(rating, dict):
        return ""

    return clean_text(
        rating.get("reviewCount")
        or rating.get("ratingCount")
    )


def extract_image(recipe: dict) -> str:

    image = recipe.get("image")

    if isinstance(image, str):
        return image

    if isinstance(image, list) and image:
        first = image[0]

        if isinstance(first, str):
            return first

        if isinstance(first, dict):
            return clean_text(first.get("url"))

    if isinstance(image, dict):
        return clean_text(image.get("url"))

    return ""


def extract_instructions(recipe: dict) -> list[str]:

    instructions = recipe.get("recipeInstructions", [])

    result = []

    if isinstance(instructions, str):
        return [clean_text(instructions)]

    if isinstance(instructions, list):

        for step in instructions:

            if isinstance(step, str):

                text = clean_text(step)

                if text:
                    result.append(text)

            elif isinstance(step, dict):

                text = clean_text(
                    step.get("text")
                    or step.get("name")
                )

                if text:
                    result.append(text)

    elif isinstance(instructions, dict):

        text = clean_text(
            instructions.get("text")
            or instructions.get("name")
        )

        if text:
            result.append(text)

    return result


def extract_ingredients(recipe: dict) -> list[str]:

    ingredients = recipe.get("recipeIngredient", [])

    if isinstance(ingredients, str):
        return [clean_text(ingredients)]

    if not isinstance(ingredients, list):
        return []

    return [
        clean_text(item)
        for item in ingredients
        if clean_text(item)
    ]


# ============================================================
# Page parsing
# ============================================================

def extract_links(soup: BeautifulSoup, current_url: str) -> list[str]:

    links = []

    for anchor in soup.find_all("a", href=True):

        href = anchor.get("href")

        if not href:
            continue

        url = normalize_url(
            urljoin(current_url, href)
        )

        if not url:
            continue

        if not is_archanas_url(url):
            continue

        links.append(url)

    return list(dict.fromkeys(links))


def parse_recipe(
    html: str,
    url: str,
) -> dict | None:

    soup = BeautifulSoup(html, "lxml")

    recipe = get_recipe_jsonld(soup)

    if not recipe:
        return None

    name = clean_text(recipe.get("name"))

    if not name:
        return None

    author = get_person_name(recipe.get("author"))

    ingredients = extract_ingredients(recipe)
    instructions = extract_instructions(recipe)

    record = {
        # Identity
        "recipe_name": name,
        "source_name": "Archana's Kitchen",
        "source_url": url,
        "canonical_url": url,

        # Attribution
        "author": author,

        # Classification
        "recipe_category": clean_text(
            recipe.get("recipeCategory")
        ),
        "recipe_cuisine": clean_text(
            recipe.get("recipeCuisine")
        ),
        "keywords": clean_text(
            recipe.get("keywords")
        ),

        # Timing
        "prep_time": clean_text(
            recipe.get("prepTime")
        ),
        "cook_time": clean_text(
            recipe.get("cookTime")
        ),
        "total_time": clean_text(
            recipe.get("totalTime")
        ),

        # Servings
        "recipe_yield": clean_text(
            recipe.get("recipeYield")
        ),

        # Rating
        "rating": get_rating(recipe),
        "review_count": get_review_count(recipe),

        # Nutrition
        "calories": "",
        "fat_content": "",
        "protein_content": "",
        "carbohydrate_content": "",

        # Media
        "image_url": extract_image(recipe),

        # Recipe data
        "ingredients": json.dumps(
            ingredients,
            ensure_ascii=False,
        ),

        "instructions": json.dumps(
            instructions,
            ensure_ascii=False,
        ),

        # Dataset metadata
        "collected_at": utc_now(),
        "data_source_type": "public_web",
        "verification_status": "source_attributed",
    }

    nutrition = recipe.get("nutrition")

    if isinstance(nutrition, dict):

        record["calories"] = clean_text(
            nutrition.get("calories")
        )

        record["fat_content"] = clean_text(
            nutrition.get("fatContent")
        )

        record["protein_content"] = clean_text(
            nutrition.get("proteinContent")
        )

        record["carbohydrate_content"] = clean_text(
            nutrition.get("carbohydrateContent")
        )

    return record


# ============================================================
# Save recipe
# ============================================================

def save_recipe(record: dict) -> None:

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing = []

    if RECIPES_JSON.exists():

        try:
            existing = json.loads(
                RECIPES_JSON.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            existing = []

    existing_urls = {
        item.get("canonical_url")
        for item in existing
    }

    if record["canonical_url"] not in existing_urls:
        existing.append(record)

    RECIPES_JSON.write_text(
        json.dumps(
            existing,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # CSV
    df = pd.DataFrame(existing)

    df.to_csv(
        RECIPES_CSV,
        index=False,
        encoding="utf-8-sig",
    )


def save_failed(url: str, status: Any, reason: str) -> None:

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exists = FAILED_FILE.exists()

    with FAILED_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        if not exists:
            writer.writerow(
                [
                    "url",
                    "status",
                    "reason",
                    "failed_at",
                ]
            )

        writer.writerow(
            [
                url,
                status,
                reason,
                utc_now(),
            ]
        )


# ============================================================
# Main crawler
# ============================================================

def crawl(max_recipes: int) -> None:

    state = load_state()

    if state.get("blocked"):
        print(
            "Previous run stopped because access was restricted."
        )
        print(
            "Review the saved state before attempting another run."
        )
        return

    queue = list(
        dict.fromkeys(
            state.get("queue", START_URLS)
        )
    )

    visited = set(
        state.get("visited", [])
    )

    recipe_urls = set(
        state.get("recipe_urls", [])
    )

    collected = set(
        state.get("collected", [])
    )

    failed = set(
        state.get("failed", [])
    )

    print()
    print("=" * 70)
    print("DishIQ — Archana's Kitchen Educational Scraper")
    print("=" * 70)
    print(f"Maximum recipes: {max_recipes}")
    print(f"Existing collected: {len(collected)}")
    print(f"Queue size: {len(queue)}")
    print("=" * 70)

    while queue and len(collected) < max_recipes:

        url = queue.pop(0)

        if url in visited:
            continue

        visited.add(url)

        print()
        print(f"[QUEUE] {len(queue)} remaining")
        print(f"[VISIT] {url}")

        html, status = fetch(url)

        if status in (403, 429):

            state["blocked"] = True

            state["queue"] = queue
            state["visited"] = list(visited)
            state["recipe_urls"] = list(recipe_urls)
            state["collected"] = list(collected)
            state["failed"] = list(failed)

            save_state(state)

            save_failed(
                url,
                status,
                "Access restriction / rate limit",
            )

            print()
            print("Crawler stopped safely.")
            print("State has been saved.")
            return

        if html is None:

            failed.add(url)

            save_failed(
                url,
                status,
                "Request failed",
            )

            state["queue"] = queue
            state["visited"] = list(visited)
            state["recipe_urls"] = list(recipe_urls)
            state["collected"] = list(collected)
            state["failed"] = list(failed)

            save_state(state)

            continue

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        # ----------------------------------------------------
        # Recipe detection
        # ----------------------------------------------------

        if looks_like_recipe_url(url):

            record = parse_recipe(
                html,
                url,
            )

            if record:

                canonical = record[
                    "canonical_url"
                ]

                recipe_urls.add(canonical)

                if canonical not in collected:

                    save_recipe(record)

                    collected.add(canonical)

                    print(
                        f"[RECIPE] {record['recipe_name']}"
                    )

                    print(
                        f"[COUNT] {len(collected)}/{max_recipes}"
                    )

        # ----------------------------------------------------
        # Discover more URLs
        # ----------------------------------------------------

        links = extract_links(
            soup,
            url,
        )

        for link in links:

            if link in visited:
                continue

            if link in queue:
                continue

            queue.append(link)

        # ----------------------------------------------------
        # Save state after every page
        # ----------------------------------------------------

        state["queue"] = queue
        state["visited"] = list(visited)
        state["recipe_urls"] = list(recipe_urls)
        state["collected"] = list(collected)
        state["failed"] = list(failed)

        save_state(state)

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    state["queue"] = queue
    state["visited"] = list(visited)
    state["recipe_urls"] = list(recipe_urls)
    state["collected"] = list(collected)
    state["failed"] = list(failed)
    state["blocked"] = False

    save_state(state)

    print()
    print("=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Recipes collected : {len(collected)}")
    print(f"Recipe URLs found : {len(recipe_urls)}")
    print(f"Pages visited     : {len(visited)}")
    print(f"Failed pages      : {len(failed)}")
    print()
    print(f"CSV  : {RECIPES_CSV}")
    print(f"JSON : {RECIPES_JSON}")
    print(f"State: {STATE_FILE}")
    print("=" * 70)


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--max-recipes",
        type=int,
        default=DEFAULT_MAX_RECIPES,
        help="Maximum number of recipes to collect.",
    )

    args = parser.parse_args()

    max_recipes = max(
        1,
        min(
            args.max_recipes,
            1000,
        ),
    )

    crawl(max_recipes)


if __name__ == "__main__":
    main()
