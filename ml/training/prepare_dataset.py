import os
import sys
import json
import sqlite3
import pandas as pd
import ast
import uuid
import re
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "backend", "dishiq.db")
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "archanas_kitchen", "recipes.csv")
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
DATA_DIR = os.path.join(ML_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
REPORTS_DIR = os.path.join(ML_DIR, "reports")
MODELS_DIR = os.path.join(ML_DIR, "models")
PRETRAINED_DIR = os.path.join(MODELS_DIR, "pretrained")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(SPLITS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(PRETRAINED_DIR, exist_ok=True)

def safe_parse_json(val):
    if pd.isna(val) or not val:
        return []
    if isinstance(val, list):
        return val
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return parsed
    except:
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                return parsed
        except:
            pass
    return [str(val)]

def clean_text(text):
    if pd.isna(text) or not text:
        return ""
    text = str(text)
    text = re.sub(r'<[^>]+>', '', text)  # remove HTML
    return text.strip()

def parse_iso_duration(duration_str):
    if pd.isna(duration_str) or not duration_str:
        return 0
    duration_str = str(duration_str).upper()
    minutes = 0
    try:
        if duration_str.startswith('PT'):
            time_part = duration_str[2:]
            h_match = re.search(r'(\d+)H', time_part)
            if h_match:
                minutes += int(h_match.group(1)) * 60
            m_match = re.search(r'(\d+)M', time_part)
            if m_match:
                minutes += int(m_match.group(1))
            return minutes
    except:
        pass
    return 0

def load_foodcom_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Get recipes
    df_recipes = pd.read_sql("SELECT * FROM recipes WHERE source_name = 'Food.com Dataset'", conn)
    
    # Get ingredients
    df_ingreds = pd.read_sql("""
        SELECT ri.recipe_id, i.canonical_name 
        FROM recipe_ingredients ri
        JOIN ingredients i ON ri.ingredient_id = i.id
    """, conn)
    
    # Group ingredients
    ing_map = df_ingreds.groupby("recipe_id")["canonical_name"].apply(list).to_dict()
    
    conn.close()
    
    records = []
    for _, row in df_recipes.iterrows():
        recipe_id = row["id"]
        
        # Parse instructions
        instructions = []
        inst_data = safe_parse_json(row["instructions"])
        for step in inst_data:
            if isinstance(step, dict) and "text" in step:
                instructions.append(clean_text(step["text"]))
            else:
                instructions.append(clean_text(step))
                
        ingredients = ing_map.get(recipe_id, [])
        
        records.append({
            "recipe_id": recipe_id,
            "recipe_name": clean_text(row["name"]),
            "description": clean_text(row["description"]),
            "ingredients": json.dumps(ingredients),
            "instructions": json.dumps(instructions),
            "cuisine": clean_text(row["cuisine"]) if not pd.isna(row["cuisine"]) else "Unknown",
            "diet": clean_text(row["dietary_type"]) if not pd.isna(row["dietary_type"]) else "Unknown",
            "cooking_time": (row["preparation_minutes"] or 0) + (row["cooking_minutes"] or 0),
            "rating": float(row["average_rating"]) if not pd.isna(row["average_rating"]) else 0.0,
            "dataset_source": "foodcom"
        })
        
    return pd.DataFrame(records)

def load_archanas_data():
    if not os.path.exists(CSV_PATH):
        print(f"Warning: CSV not found at {CSV_PATH}")
        return pd.DataFrame()
        
    df = pd.read_csv(CSV_PATH)
    records = []
    for _, row in df.iterrows():
        ingredients = safe_parse_json(row.get("ingredients", "[]"))
        instructions = safe_parse_json(row.get("instructions", "[]"))
        
        cooking_time = parse_iso_duration(row.get("prep_time")) + parse_iso_duration(row.get("cook_time"))
        
        cuisine = clean_text(row.get("recipe_cuisine", "Indian"))
        if not cuisine:
            cuisine = "Indian"
            
        diet = "Unknown" # Not explicitly in CSV in standard format, sometimes in keywords
        
        records.append({
            "recipe_id": str(uuid.uuid4()), # Generate stable-ish IDs or use canonical_url
            "recipe_name": clean_text(row.get("recipe_name", "")),
            "description": "", # Doesn't have explicit description in CSV, maybe in keywords
            "ingredients": json.dumps(ingredients),
            "instructions": json.dumps(instructions),
            "cuisine": cuisine,
            "diet": diet,
            "cooking_time": cooking_time,
            "rating": float(row.get("rating", 0.0)) if not pd.isna(row.get("rating")) else 0.0,
            "dataset_source": "archanas_kitchen"
        })
        
    return pd.DataFrame(records)

def main():
    print("=== Phase 14A: ML Dataset Preparation ===")
    
    # 1. Load Data
    print("Loading Food.com data...")
    df_foodcom = load_foodcom_data()
    print(f"Found {len(df_foodcom)} Food.com recipes.")
    
    print("Loading Archana's Kitchen data...")
    df_archanas = load_archanas_data()
    print(f"Found {len(df_archanas)} Archana's Kitchen recipes.")
    
    combined_count_before = len(df_foodcom) + len(df_archanas)
    
    df_combined = pd.concat([df_foodcom, df_archanas], ignore_index=True)
    
    # 2. Duplicate Detection
    df_combined['normalized_name'] = df_combined['recipe_name'].str.lower().str.replace(r'[^a-z0-9\s]', '', regex=True).str.strip()
    
    # Exact duplicates by normalized name
    exact_duplicates = df_combined.duplicated(subset=['normalized_name'], keep=False)
    dup_groups = df_combined[exact_duplicates].groupby('normalized_name')
    
    exact_duplicate_count = df_combined.duplicated(subset=['normalized_name'], keep='first').sum()
    
    # We will remove exact normalized name duplicates to prevent leakage
    df_cleaned = df_combined.drop_duplicates(subset=['normalized_name'], keep='first').copy()
    
    retained_count = len(df_cleaned)
    foodcom_retained = len(df_cleaned[df_cleaned['dataset_source'] == 'foodcom'])
    archanas_retained = len(df_cleaned[df_cleaned['dataset_source'] == 'archanas_kitchen'])
    
    duplicate_report = {
        "total_recipes_before_cleaning": combined_count_before,
        "exact_duplicates_removed": int(exact_duplicate_count),
        "recipes_retained": retained_count,
        "foodcom_retained_count": foodcom_retained,
        "archanas_kitchen_retained_count": archanas_retained,
        "combined_retained_count": retained_count
    }
    
    with open(os.path.join(REPORTS_DIR, "duplicate_analysis.json"), 'w') as f:
        json.dump(duplicate_report, f, indent=2)
        
    print(f"Removed {exact_duplicate_count} exact duplicates. Retained {retained_count} recipes.")
    
    # 3. Train/Val/Test Split
    # Target: 70% Train, 15% Val, 15% Test. Seed = 42
    
    # Split 1: Train (70%) and Temp (30%)
    df_train, df_temp = train_test_split(
        df_cleaned, 
        test_size=0.30, 
        random_state=42, 
        stratify=df_cleaned['dataset_source'] # Stratify to keep representation
    )
    
    # Split 2: Val (50% of Temp = 15%) and Test (50% of Temp = 15%)
    df_val, df_test = train_test_split(
        df_temp, 
        test_size=0.50, 
        random_state=42, 
        stratify=df_temp['dataset_source']
    )
    
    # Ensure no leakage
    train_ids = set(df_train['recipe_id'])
    val_ids = set(df_val['recipe_id'])
    test_ids = set(df_test['recipe_id'])
    
    leakage_check_1 = len(train_ids.intersection(val_ids))
    leakage_check_2 = len(train_ids.intersection(test_ids))
    leakage_check_3 = len(val_ids.intersection(test_ids))
    assert leakage_check_1 == 0 and leakage_check_2 == 0 and leakage_check_3 == 0, "DATA LEAKAGE DETECTED!"
    
    # Save artifacts
    df_cleaned.drop(columns=['normalized_name']).to_csv(os.path.join(PROCESSED_DIR, "cleaned_combined_dataset.csv"), index=False)
    df_train.drop(columns=['normalized_name']).to_csv(os.path.join(SPLITS_DIR, "train_dataset.csv"), index=False)
    df_val.drop(columns=['normalized_name']).to_csv(os.path.join(SPLITS_DIR, "val_dataset.csv"), index=False)
    df_test.drop(columns=['normalized_name']).to_csv(os.path.join(SPLITS_DIR, "test_dataset.csv"), index=False)
    
    # Dataset Report
    dataset_report = {
        "total_recipes": retained_count,
        "dataset_sources": {
            "foodcom": foodcom_retained,
            "archanas_kitchen": archanas_retained
        },
        "splits": {
            "train_count": len(df_train),
            "validation_count": len(df_val),
            "test_count": len(df_test)
        },
        "missing_values": df_cleaned.isnull().sum().to_dict(),
        "random_seed": 42,
        "leakage_check_passed": True
    }
    
    with open(os.path.join(REPORTS_DIR, "dataset_report.json"), 'w') as f:
        json.dump(dataset_report, f, indent=2)
        
    print("Dataset splits saved successfully. Zero data leakage confirmed.")
    
    # 4. Pretrained Model Download (Sentence Transformers)
    print("Downloading/Caching Pretrained Sentence Transformer Model...")
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model = SentenceTransformer(model_name, cache_folder=PRETRAINED_DIR)
    
    model_metadata = {
        "model_name": model_name,
        "model_type": "SentenceTransformer",
        "source": "HuggingFace Hub",
        "embedding_dimension": model.get_sentence_embedding_dimension(),
        "library_version": "2.2.2", 
        "download_status": "CACHED_LOCALLY",
        "cache_location": PRETRAINED_DIR
    }
    
    with open(os.path.join(PRETRAINED_DIR, "pretrained_registry.json"), 'w') as f:
        json.dump(model_metadata, f, indent=2)
        
    print("Pretrained model cached successfully.")
    print("=== Pipeline Complete ===")

if __name__ == "__main__":
    main()
