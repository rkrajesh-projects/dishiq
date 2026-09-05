"""
DishIQ Phase 6.1 — Build Precomputed Product Embeddings Script

Usage (from repository root or backend directory):
    python backend/scripts/build_product_embeddings.py
"""
import sys
import os

# Ensure backend and root are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.session import SessionLocal
from app.product_matching.cache import (
    build_product_embeddings_from_db,
    save_product_embeddings_artifact,
)


def main():
    print("=" * 60)
    print("Building Precomputed Grocery Product Embeddings Artifact...")
    print("=" * 60)

    db = SessionLocal()
    try:
        embeddings_data = build_product_embeddings_from_db(db)
        product_count = len(embeddings_data.get("products", {}))
        print(f"Computed embeddings for {product_count} products.")

        if product_count > 0:
            target_path = save_product_embeddings_artifact(embeddings_data)
            print(f"Artifact saved successfully: {target_path}")
        else:
            print("No grocery products found in database to encode.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
