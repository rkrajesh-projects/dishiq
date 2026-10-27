import math
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.grocery_repository import GroceryRepository
from app.schemas.grocery import GroceryStoreRead, GroceryProductRead, ProductPriceHistoryResponse, ProductPriceHistoryItem
from app.schemas.pagination import PaginatedResponse
from app.product_matching.schemas import MatchIngredientsResponse
from app.core.config import settings


class GroceryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = GroceryRepository(db)

    def list_stores(self, page: int = 1, page_size: int = 10) -> PaginatedResponse[GroceryStoreRead]:
        items, total = self.repo.get_stores(page=page, page_size=page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        store_reads = [GroceryStoreRead.model_validate(item) for item in items]
        
        return PaginatedResponse[GroceryStoreRead](
            items=store_reads,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def list_products(
        self,
        store_id: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedResponse[GroceryProductRead]:
        items, total = self.repo.get_products(
            store_id=store_id,
            category=category,
            page=page,
            page_size=page_size
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        product_reads = [GroceryProductRead.model_validate(item) for item in items]
        
        return PaginatedResponse[GroceryProductRead](
            items=product_reads,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def match_products_for_ingredient(
        self,
        ingredient: str,
        limit: int = 10,
        threshold: Optional[float] = None,
        sort_by_price: bool = False,
        sort_by: str = "default",
        live_mode: bool = False,
        pincode: Optional[str] = None,
        background_tasks = None,
        timeout: Optional[float] = None,
    ) -> MatchIngredientsResponse:
        if not ingredient or not ingredient.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ingredient query parameter cannot be empty or whitespace-only.",
            )

        from app.product_matching.matcher import ProductMatcher
        from app.services.price_comparison_service import PriceComparisonService
        from app.grocery_sources import GroceryProviderRegistry
        from app.grocery_sources.factory import get_configured_providers
        import asyncio

        # Create localized request registry
        request_registry = GroceryProviderRegistry()
        
        # Load providers cleanly
        configured_providers = get_configured_providers(
            db=self.db, 
            live_mode=live_mode, 
            pincode=pincode
        )
        
        for provider in configured_providers:
            request_registry.register(provider)

        effective_timeout = timeout if timeout is not None else getattr(settings, "GROCERY_SEARCH_TIMEOUT_SECONDS", 4.0)

        # Asynchronously fetch products from all registered providers
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                normalized_products, failures = pool.submit(
                    asyncio.run,
                    request_registry.search_all_providers(
                        ingredient.strip(),
                        timeout=effective_timeout,
                        force_refresh=live_mode,
                    ),
                ).result()
        else:
            normalized_products, failures = asyncio.run(
                request_registry.search_all_providers(
                    ingredient.strip(),
                    timeout=effective_timeout,
                    force_refresh=live_mode,
                )
            )
        
        # Phase 23: Background DB Sync
        if live_mode and normalized_products and background_tasks:
            from app.services.product_sync_service import sync_live_products
            background_tasks.add_task(sync_live_products, normalized_products)

        # Convert NormalizedGroceryProduct list into matching-compatible dict representation
        product_list = []
        for np in normalized_products:
            p_dict = np.model_dump()
            p_dict["product_id"] = np.source_product_id
            if hasattr(np, "embedding"):
                p_dict["embedding"] = getattr(np, "embedding")
            product_list.append(p_dict)

        matcher = ProductMatcher()
        response = matcher.match_products(
            ingredient_text=ingredient.strip(),
            products=product_list,
            threshold=threshold,
            top_k=limit,
        )

        # Apply price comparison, unit price normalization, and best_option selection
        processed_results, best_option, comparison_mode = PriceComparisonService.compare_and_rank_prices(
            results=response.results,
            sort_by_price=sort_by_price,
            sort_by=sort_by,
        )

        response.results = processed_results
        response.best_option = best_option
        response.comparison_mode = comparison_mode
        if processed_results:
            response.price_freshness = processed_results[0].get("price_freshness") if isinstance(processed_results[0], dict) else getattr(processed_results[0], "price_freshness", "UNKNOWN")
        else:
            response.price_freshness = "UNKNOWN"
        response.data_source = "live" if live_mode else "demo"
        return response

    def compare_grocery_prices(
        self,
        ingredient: str,
        limit: int = 10,
        threshold: Optional[float] = None,
        sort_by: str = "best_value",
        live_mode: bool = False,
        pincode: Optional[str] = None,
        background_tasks = None,
    ) -> MatchIngredientsResponse:
        """
        Match products and rank them by price ascending (cheapest first).
        """
        return self.match_products_for_ingredient(
            ingredient=ingredient,
            limit=limit,
            threshold=threshold,
            sort_by_price=True,
            sort_by=sort_by,
            live_mode=live_mode,
            pincode=pincode,
            background_tasks=background_tasks
        )

    def get_price_history(self, product_id: str) -> ProductPriceHistoryResponse:
        """
        Retrieve chronological price history observations for a given grocery product.
        """
        from app.models.grocery import GroceryProduct
        product = self.db.query(GroceryProduct).filter(GroceryProduct.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id '{product_id}' not found."
            )

        history_items = [
            ProductPriceHistoryItem(
                id=p.id,
                price=p.price,
                delivery_fee=p.delivery_fee,
                currency=getattr(p, "currency", "INR"),
                price_freshness=getattr(p, "price_freshness", "CACHED"),
                data_source_type=p.data_source_type,
                observed_at=p.observed_at,
            )
            for p in (product.prices or [])
        ]

        return ProductPriceHistoryResponse(
            product_id=product.id,
            product_name=product.name,
            store_name=product.store.name if product.store else "Unknown Store",
            brand=product.brand,
            package_quantity=product.package_quantity,
            package_unit=product.package_unit,
            current_price=product.latest_price,
            history_count=len(history_items),
            prices=history_items,
        )
