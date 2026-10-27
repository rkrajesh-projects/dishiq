import sqlite3

def run_migration():
    db_path = r"d:\DishIQ\backend\dishiq.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    columns_to_add = [
        ("source_recipe_id", "VARCHAR(255)"),
        ("source_license", "VARCHAR(255)"),
        ("author", "VARCHAR(255)"),
        ("verification_status", "VARCHAR(50) DEFAULT 'UNVERIFIED'"),
        ("verification_level", "VARCHAR(50) DEFAULT 'NONE'"),
        ("dataset_version", "VARCHAR(100)"),
        ("region", "VARCHAR(100)"),
        ("state", "VARCHAR(100)"),
        ("original_name", "VARCHAR(255)"),
        ("original_language", "VARCHAR(100)"),
        ("is_indian_recipe", "INTEGER DEFAULT 0"),
        ("collected_at", "DATETIME")
    ]
    
    # Get existing columns
    cur.execute("PRAGMA table_info(recipes)")
    existing_cols = [row[1] for row in cur.fetchall()]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            print(f"Adding column {col_name} to recipes table...")
            cur.execute(f"ALTER TABLE recipes ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column {col_name} already exists.")
            
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    run_migration()
