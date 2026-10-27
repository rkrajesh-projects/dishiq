import logging
from datetime import datetime, timezone
from typing import List, Optional
import numpy as np

from app.db.session import SessionLocal
from app.grocery_sources.models import NormalizedGroceryProduct
from app.models.grocery import GroceryProduct, GroceryStore, ProductPrice
from app.product_matching.cache import load_product_embeddings_artifact, save_product_embeddings_artifact

logger = logging.getLogger("dishiq.product_sync")


def sync_live_products(normalized_products: List[NormalizedGroceryProduct]):
    """
    Background task to sync live quick-commerce products into the local DB.
    1. Resolves product identity by (store_id, source_product_id) or (store_id, name, package_quantity, package_unit).
       Distinct package sizes (e.g. 500g vs 1kg) are preserved as separate products.
    2. Records genuine price history observations when prices change, deduplicating identical consecutive observations.
       Demo prices and cached reads never create live price history records.
    3. Re-computes SentenceTransformer embeddings for new products and updates the artifact cache.
    """
    if not normalized_products:
        return

    logger.info(f"Background Sync: Processing {len(normalized_products)} live products.")
    db = SessionLocal()

    try:
        new_products_for_embedding = []

        for np_prod in normalized_products:
            # Skip invalid products
            if not np_prod.product_name or not np_prod.store_name:
                continue

            # 1. Resolve Store
            store = db.query(GroceryStore).filter(GroceryStore.name == np_prod.store_name).first()
            if not store:
                store = GroceryStore(
                    name=np_prod.store_name,
                    store_type="Quick Commerce",
                    is_demo_store=False
                )
                db.add(store)
                db.flush()

            # 2. Resolve Product Identity
            # Primary lookup: by store_id and source_product_id (provider SKU / ID)
            product: Optional[GroceryProduct] = None
            if np_prod.source_product_id:
                product = db.query(GroceryProduct).filter(
                    GroceryProduct.store_id == store.id,
                    GroceryProduct.source_product_id == np_prod.source_product_id
                ).first()

            # Secondary fallback lookup: by store_id, product_name, package_quantity, and package_unit
            if not product:
                qty = np_prod.package_quantity if np_prod.package_quantity is not None else 1.0
                unit = np_prod.package_unit or "pack"
                product = db.query(GroceryProduct).filter(
                    GroceryProduct.store_id == store.id,
                    GroceryProduct.name == np_prod.product_name,
                    GroceryProduct.package_quantity == qty,
                    GroceryProduct.package_unit == unit
                ).first()

            is_new = False
            if not product:
                product = GroceryProduct(
                    store_id=store.id,
                    source_product_id=np_prod.source_product_id,
                    name=np_prod.product_name,
                    normalized_name=np_prod.product_name.lower().strip(),
                    brand=np_prod.brand or "Generic",
                    category=np_prod.category or "Uncategorized",
                    package_quantity=np_prod.package_quantity if np_prod.package_quantity is not None else 1.0,
                    package_unit=np_prod.package_unit or "pack",
                    in_stock=np_prod.availability
                )
                db.add(product)
                db.flush()
                is_new = True
                new_products_for_embedding.append(product)
            else:
                # Update attributes safely without overwriting package identity
                if np_prod.source_product_id and not product.source_product_id:
                    product.source_product_id = np_prod.source_product_id
                if np_prod.brand and np_prod.brand != "Generic":
                    product.brand = np_prod.brand
                if np_prod.category and np_prod.category != "Uncategorized":
                    product.category = np_prod.category
                product.in_stock = np_prod.availability
                product.updated_at = datetime.now(timezone.utc)

            # 3. Price History Ingestion
            # Rules:
            # - Never record demo prices into live price history
            # - Never create price history rows on cache hits (CACHED)
            # - Price must be valid and numeric (> 0)
            if (
                np_prod.price_freshness == "PROVIDER_LIVE"
                and np_prod.price is not None
                and np_prod.price > 0
            ):
                # Retrieve most recent price observation
                latest_price_rec = (
                    db.query(ProductPrice)
                    .filter(ProductPrice.product_id == product.id)
                    .order_by(ProductPrice.observed_at.desc())
                    .first()
                )

                # Deduplicate: if the most recent price is identical, do not append a duplicate row
                if not latest_price_rec or float(latest_price_rec.price) != float(np_prod.price):
                    obs_time = np_prod.retrieved_at or datetime.now(timezone.utc)
                    if obs_time.tzinfo is None:
                        obs_time = obs_time.replace(tzinfo=timezone.utc)

                    new_price_rec = ProductPrice(
                        product_id=product.id,
                        price=float(np_prod.price),
                        delivery_fee=0.0,
                        currency=np_prod.currency or "INR",
                        price_freshness="PROVIDER_LIVE",
                        observed_at=obs_time,
                        data_source_type="live"
                    )
                    db.add(new_price_rec)

        db.commit()

        # 4. Generate Embeddings for newly added products
        if new_products_for_embedding:
            logger.info(f"Background Sync: Generating embeddings for {len(new_products_for_embedding)} new products.")

            # Extract names for embedding
            product_texts = []
            for p in new_products_for_embedding:
                brand = p.brand or ""
                product_texts.append(f"{brand} {p.name}".strip())

            # Encode using warm ProductEncoder singleton
            from app.product_matching.encoder import get_encoder
            encoder = get_encoder()
            embs = encoder.encode_texts(product_texts)

            norms = np.linalg.norm(embs, axis=1, keepdims=True)
            embs_normalized = np.divide(embs, norms, out=np.zeros_like(embs), where=norms != 0)

            # Add dynamically to the joblib Cache used by ProductMatcher
            cache = load_product_embeddings_artifact()
            if cache and "products" in cache:
                for idx, p in enumerate(new_products_for_embedding):
                    cache["products"][str(p.id)] = {
                        "product_id": str(p.id),
                        "product_name": p.name,
                        "name": p.name,
                        "brand": p.brand,
                        "category": p.category,
                        "store_id": str(p.store_id),
                        "package_quantity": p.package_quantity,
                        "package_unit": p.package_unit,
                        "embedding": embs_normalized[idx]
                    }
                save_product_embeddings_artifact(cache)

            logger.info("Background Sync: Embedding cache updated.")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to sync live products: {e}", exc_info=True)
    finally:
        db.close()
