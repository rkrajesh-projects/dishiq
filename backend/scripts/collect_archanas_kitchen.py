"""
DishIQ - Exhaustive Archana's Kitchen Resumable Crawler
"""
import os
import sys
import argparse
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError
import re
import json
import time
from datetime import datetime, timezone
import traceback

# Path setup
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_DIR = os.path.join(REPO_ROOT, 'backend')
CACHE_DIR = os.path.join(REPO_ROOT, 'data', 'raw', 'archanas_kitchen')
STATE_FILE = os.path.join(CACHE_DIR, 'state.json')

sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from app.db.session import SessionLocal
from app.services.dataset_pipeline import DatasetPipeline, ImportedRecipe, NormalizedIngredient, Provenance

DATASET_VERSION = "archanas-kitchen-v2-exhaustive"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
BASE_URL = "https://www.archanaskitchen.com"

# --- URL NORMALIZATION ---
def normalize_url(url: str) -> str:
    # Remove fragments
    url = url.split('#')[0]
    # Remove tracking params
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    clean_query = {k: v for k, v in query.items() if not k.startswith('utm_') and k != 'gclid'}
    clean_url = parsed._replace(query=urllib.parse.urlencode(clean_query, doseq=True)).geturl()
    return clean_url.rstrip('/')

def is_recipe_url(url: str) -> bool:
    return '-recipe' in url and '/category/' not in url and '/tag/' not in url

# --- PARSING HELPERS ---
def parse_iso_duration(duration_str):
    if not duration_str: return 0
    try:
        minutes = 0
        if duration_str.startswith('PT'):
            time_part = duration_str[2:]
            h_match = re.search(r'(\d+)H', time_part)
            if h_match: minutes += int(h_match.group(1)) * 60
            m_match = re.search(r'(\d+)M', time_part)
            if m_match: minutes += int(m_match.group(1))
            return minutes
    except Exception:
        pass
    return 0

def clean_html(raw_html):
    return re.sub(re.compile('<.*?>'), '', str(raw_html)).strip()

def parse_ingredient_line(raw_text: str) -> NormalizedIngredient:
    qty, unit, name = 1.0, "unknown", raw_text.strip()
    match = re.match(r'^([\d\.\/]+)\s+(cup|tsp|tbsp|g|kg|ml|l|piece|pieces|clove|cloves|pinch)s?\s+(.*)$', raw_text.lower().strip())
    if match:
        num_str = match.group(1)
        try:
            if '/' in num_str:
                num, den = num_str.split('/')
                qty = float(num) / float(den)
            else: qty = float(num_str)
        except: pass
        unit = match.group(2)
        name = match.group(3).strip()
    return NormalizedIngredient(raw_text=raw_text, canonical_name=name[:200], quantity=qty, unit=unit)

# --- CRAWLER STATE ---
class CrawlState:
    def __init__(self):
        self.pending_urls = [BASE_URL + "/category/recipes/indian"]
        self.visited_urls = []
        self.failed_urls = {} # url -> {error, attempts}
        self.recipe_urls_discovered = set()
        self.recipes_inserted = 0
        self.recipes_updated = 0
        self.recipes_skipped = 0
        
    def load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.pending_urls = data.get('pending_urls', self.pending_urls)
                    self.visited_urls = data.get('visited_urls', [])
                    self.failed_urls = data.get('failed_urls', {})
                    self.recipe_urls_discovered = set(data.get('recipe_urls_discovered', []))
                    self.recipes_inserted = data.get('recipes_inserted', 0)
                    self.recipes_updated = data.get('recipes_updated', 0)
                    self.recipes_skipped = data.get('recipes_skipped', 0)
                print(f"Loaded state: {len(self.pending_urls)} pending, {len(self.visited_urls)} visited.")
            except Exception as e:
                print(f"Error loading state: {e}")

    def save(self):
        data = {
            'pending_urls': list(self.pending_urls),
            'visited_urls': list(self.visited_urls),
            'failed_urls': self.failed_urls,
            'recipe_urls_discovered': list(self.recipe_urls_discovered),
            'recipes_inserted': self.recipes_inserted,
            'recipes_updated': self.recipes_updated,
            'recipes_skipped': self.recipes_skipped,
            'last_saved': datetime.now(timezone.utc).isoformat()
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

# --- THE CRAWLER ---
class ArchanasCrawler:
    def __init__(self, state: CrawlState, db, limit=None):
        self.state = state
        self.db = db
        self.pipeline = DatasetPipeline(db)
        self.limit = limit
        self.processed_count = 0
        self.delay = 1.5 # Respectful rate limit

    def fetch_page(self, url: str) -> str:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')

    def extract_links(self, html: str, current_url: str):
        links = re.findall(r'href="([^"]+)"', html)
        for link in links:
            if link.startswith('/'):
                link = BASE_URL + link
            elif not link.startswith('http'):
                continue
                
            if "archanaskitchen.com" not in link:
                continue
                
            clean_link = normalize_url(link)
            
            # Skip assets
            if any(ext in clean_link for ext in ['.jpg', '.png', '.css', '.js']):
                continue
                
            if clean_link not in self.state.visited_urls and clean_link not in self.state.pending_urls:
                # Add to queue if it's a category, pagination, or recipe
                if is_recipe_url(clean_link):
                    self.state.recipe_urls_discovered.add(clean_link)
                    self.state.pending_urls.append(clean_link)
                elif '/category/' in clean_link or '/recipes/' in clean_link or '?page=' in clean_link:
                    self.state.pending_urls.append(clean_link)

    def extract_recipe(self, html: str, url: str) -> ImportedRecipe:
        json_ld_matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        recipe_data = None
        for match in json_ld_matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Recipe': recipe_data = item
                elif isinstance(data, dict):
                    if data.get('@type') == 'Recipe': recipe_data = data
            except: continue
                
        if not recipe_data:
            raise Exception("No JSON-LD Recipe found")
            
        name = recipe_data.get('name', 'Unknown')
        author_obj = recipe_data.get('author')
        author_name = "Unknown"
        if isinstance(author_obj, list) and len(author_obj) > 0: author_name = author_obj[0].get('name', 'Unknown')
        elif isinstance(author_obj, dict): author_name = author_obj.get('name', 'Unknown')
        elif isinstance(author_obj, str): author_name = author_obj
            
        verification_status, verification_level = "UNKNOWN", "NONE"
        if "Archana" in author_name:
            verification_status, verification_level = "SOURCE_AUTHORED", "CHEF"
        elif author_name != "Unknown":
            verification_status = "SOURCE_AUTHORED"
            
        ingredients = [parse_ingredient_line(clean_html(i)) for i in recipe_data.get('recipeIngredient', []) if i.strip()]
        
        instructions = []
        for inst in recipe_data.get('recipeInstructions', []):
            if isinstance(inst, dict) and inst.get('@type') == 'HowToStep':
                instructions.append(clean_html(inst.get('text', '')))
            elif isinstance(inst, str):
                instructions.append(clean_html(inst))
                
        prep_time = parse_iso_duration(recipe_data.get('prepTime', ''))
        cook_time = parse_iso_duration(recipe_data.get('cookTime', ''))
        try: servings = int(re.search(r'\d+', str(recipe_data.get('recipeYield', '4'))).group())
        except: servings = 4
            
        cuisine_list = recipe_data.get('recipeCuisine', [])
        cuisine = cuisine_list[0] if isinstance(cuisine_list, list) and cuisine_list else cuisine_list if cuisine_list else "Indian"
        
        prov = Provenance(
            source_name="Archana's Kitchen", source_url=url, source_recipe_id=url.split('/')[-1],
            source_license="UNKNOWN", author=author_name, dataset_version=DATASET_VERSION,
            verification_status=verification_status, verification_level=verification_level
        )
        
        return ImportedRecipe(
            name=clean_html(name)[:255], cuisine=clean_html(cuisine)[:100], dietary_type="Standard",
            is_indian_recipe=("indian" in str(cuisine).lower()), preparation_minutes=prep_time,
            cooking_minutes=cook_time, servings=servings, instructions=instructions,
            ingredients=ingredients, provenance=prov
        )

    def crawl(self):
        print(f"Starting exhaustive crawl. Limit: {self.limit or 'Unlimited'}")
        
        while self.state.pending_urls:
            if self.limit and self.processed_count >= self.limit:
                print("Crawl limit reached.")
                break
                
            url = self.state.pending_urls.pop(0)
            if url in self.state.visited_urls:
                continue
                
            print(f"[{self.processed_count+1}] Fetching: {url}")
            try:
                html = self.fetch_page(url)
                self.extract_links(html, url)
                
                if is_recipe_url(url):
                    recipe = self.extract_recipe(html, url)
                    manifest = self.pipeline.process_import([recipe], DATASET_VERSION)
                    if manifest["duplicates"] > 0:
                        self.state.recipes_skipped += 1
                        print("  -> Skipped (Duplicate)")
                    else:
                        self.state.recipes_inserted += manifest["inserted"] if "inserted" in manifest else manifest["valid_records"]
                        print("  -> Inserted Successfully")
                        
            except HTTPError as e:
                print(f"  -> HTTP Error: {e.code}")
                self.state.failed_urls[url] = {"error": str(e), "code": e.code}
                if e.code in [403, 429]:
                    print("HIT RATE LIMIT OR CLOUDFLARE BLOCK. Stopping crawl gracefully to preserve state.")
                    self.state.visited_urls.append(url)
                    self.state.save()
                    return
            except Exception as e:
                print(f"  -> Error: {e}")
                self.state.failed_urls[url] = {"error": str(e)}
                
            self.state.visited_urls.append(url)
            self.processed_count += 1
            self.state.save()
            time.sleep(self.delay)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--crawl-all", action="store_true")
    args = parser.parse_args()
    
    state = CrawlState()
    state.load()
    
    db = SessionLocal()
    try:
        limit = None if args.crawl_all else (args.limit or 10)
        crawler = ArchanasCrawler(state, db, limit=limit)
        crawler.crawl()
    finally:
        db.close()
        print(f"\nCrawl Summary:")
        print(f"Visited: {len(state.visited_urls)}")
        print(f"Pending: {len(state.pending_urls)}")
        print(f"Recipes Discovered: {len(state.recipe_urls_discovered)}")
        print(f"Recipes Inserted: {state.recipes_inserted}")

if __name__ == "__main__":
    main()
