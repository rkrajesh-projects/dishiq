from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from app.grocery_sources.base_provider import BaseGroceryProvider
from app.grocery_sources.models import NormalizedGroceryProduct
from app.models.grocery import GroceryProduct
from app.repositories.grocery_repository import GroceryRepository
from app.product_matching.cache import load_product_embeddings_artifact

class DemoGroceryProvider(BaseGroceryProvider):
    """
    Adapter provider class wrapping the local database-backed grocery repository
    or the loaded semantic embeddings cache to fit the BaseGroceryProvider interface.
    """

    def __init__(self, db: Session):
        self.repo = GroceryRepository(db)

    @property
    def provider_name(self) -> str:
        return "demo"

    async def search_products(self, query: str) -> List[NormalizedGroceryProduct]:
        """Search demo products matching the query."""
        query_lower = (query or "").lower().strip()
        
        # Optimize by getting only matching products from the database instead of the entire catalog
        db_products = self.repo.get_all_products()
        filtered_db_products = []
        for p in db_products:
            if not query_lower or query_lower in (p.name or "").lower() or query_lower in (p.normalized_name or "").lower():
                filtered_db_products.append(p)
                
        artifact_data = load_product_embeddings_artifact()
        products = []
        encoder = None

        for p in filtered_db_products:
            # Check if this product is cached in the artifact
            cached_p = None
            if artifact_data and "products" in artifact_data:
                cached_p = artifact_data["products"].get(str(p.id))

            if cached_p:
                # Preserve cached embeddings, but fill missing fields from the database.
                merged_p = dict(cached_p)

                if not merged_p.get("product_id"):
                    merged_p["product_id"] = str(p.id)

                if not merged_p.get("product_name"):
                    merged_p["product_name"] = p.name

                if not merged_p.get("name"):
                    merged_p["name"] = p.name

                if not merged_p.get("brand"):
                    merged_p["brand"] = p.brand

                if not merged_p.get("category"):
                    merged_p["category"] = p.category

                if not merged_p.get("store_id"):
                    merged_p["store_id"] = str(p.store_id) if p.store_id else None

                if not merged_p.get("store_name") and p.store:
                    merged_p["store_name"] = p.store.name

                if merged_p.get("price") is None:
                    merged_p["price"] = p.latest_price

                if not merged_p.get("package_quantity"):
                    merged_p["package_quantity"] = p.package_quantity

                if not merged_p.get("package_unit"):
                    merged_p["package_unit"] = p.package_unit

                products.append(merged_p)

            else:
                # Not cached -> convert database product to dict representation
                p_dict = {
                    "product_id": str(p.id),
                    "product_name": p.name,
                    "name": p.name,
                    "brand": p.brand,
                    "category": p.category,
                    "store_id": p.store_id,
                    "store_name": p.store.name if p.store else None,
                    "price": p.latest_price,
                    "package_quantity": p.package_quantity,
                    "package_unit": p.package_unit,
                    "normalized_name": p.normalized_name,
                }
                # Compute embedding on the fly for new/uncached products
                if encoder is None:
                    from app.product_matching.encoder import get_encoder
                    encoder = get_encoder()
                
                from app.product_matching.preprocessing import preprocess_product_for_matching
                matched_text = preprocess_product_for_matching(p.name, p.brand, p.category)
                p_dict["matched_text"] = matched_text
                p_dict["embedding"] = encoder.encode_texts([matched_text])[0]
                products.append(p_dict)

        normalized_list: List[NormalizedGroceryProduct] = []

        for p in products:
            normalized_list.append(self._normalize_product(p))

        return normalized_list

    async def get_product_details(self, product_id: str) -> Optional[NormalizedGroceryProduct]:
        """Retrieve details of a single demo product by ID."""
        artifact_data = load_product_embeddings_artifact()
        if artifact_data and "products" in artifact_data and artifact_data["products"]:
            p = artifact_data["products"].get(product_id)
            if p:
                return self._normalize_product(p)

        p_db = self.repo.db.query(GroceryProduct).filter(GroceryProduct.id == product_id).first()
        if not p_db:
            return None
        return self._normalize_product(p_db)

    async def get_current_price(self, product_id: str) -> Optional[float]:
        """Retrieve the price of a single demo product."""
        details = await self.get_product_details(product_id)
        return details.price if details else None

    def _normalize_product(self, p: Union[GroceryProduct, Dict[str, Any]]) -> NormalizedGroceryProduct:
        """Helper to convert a DB GroceryProduct model or cache dict to NormalizedGroceryProduct."""
        if isinstance(p, dict):
            p_id = str(p.get("product_id") or p.get("id") or "")
            store_id = p.get("store_id")
            p_name = str(p.get("product_name") or p.get("name") or "")
            brand = p.get("brand") or "Generic"
            category = p.get("category") or "Uncategorized"
            store_name = p.get("store_name") or "Demo Store"
            price_val = p.get("price")
            pkg_qty = p.get("package_quantity")
            pkg_unit = p.get("package_unit") or "pack"
            observed_at = p.get("retrieved_at") or p.get("observed_at") or datetime.now(timezone.utc)
            p_vec = p.get("embedding")
        else:
            p_id = str(p.id)
            store_id = str(p.store_id) if p.store_id else None
            p_name = str(p.name)
            brand = p.brand or "Generic"
            category = p.category or "Uncategorized"
            store_name = p.store.name if p.store else "Demo Store"
            price_val = p.latest_price
            pkg_qty = p.package_quantity
            pkg_unit = p.package_unit or "pack"
            observed_at = p.prices[0].observed_at if p.prices else datetime.now(timezone.utc)
            p_vec = getattr(p, "embedding", None)

        normalized = NormalizedGroceryProduct(
            source_platform="demo",
            source_product_id=p_id,
            store_id=store_id,
            store_name=store_name,
            product_name=p_name,
            brand=brand,
            category=category,
            package_quantity=pkg_qty,
            package_unit=pkg_unit,
            price=price_val,
            currency="INR",
            availability=True,
            product_url=None,
            retrieved_at=observed_at,
            price_freshness="DEMO", # Seed data is classified as DEMO
        )
        
        # Preserve semantic embedding in extra field if present
        if p_vec is not None:
            # We can store extra metadata on Pydantic models by using dictionary assignment,
            # or simply using model_config config dict setting to ignore extra attributes.
            object.__setattr__(normalized, "embedding", p_vec)

        return normalized
