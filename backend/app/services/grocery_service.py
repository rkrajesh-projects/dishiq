import math
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.grocery_repository import GroceryRepository
from app.schemas.grocery import GroceryStoreRead, GroceryProductRead
from app.schemas.pagination import PaginatedResponse
from app.product_matching.schemas import MatchIngredientsResponse


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
    ) -> MatchIngredientsResponse:
        if not ingredient or not ingredient.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ingredient query parameter cannot be empty or whitespace-only.",
            )

        from app.product_matching.matcher import ProductMatcher
        from app.services.price_comparison_service import PriceComparisonService
        from app.grocery_sources import GroceryProviderRegistry, DemoGroceryProvider
        import asyncio

        # Create localized request registry populated with DemoGroceryProvider
        request_registry = GroceryProviderRegistry()
        request_registry.register(DemoGroceryProvider(self.db))

        # Instantiate SwiggyInstamartMcpProvider and register if configured
        from app.grocery_sources import SwiggyInstamartMcpProvider
        swiggy_provider = SwiggyInstamartMcpProvider()
        if swiggy_provider.is_configured:
            request_registry.register(swiggy_provider)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Asynchronously fetch products from all registered providers
        normalized_products, failures = loop.run_until_complete(
            request_registry.search_all_providers(ingredient.strip())
        )

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
        )

        response.results = processed_results
        response.best_option = best_option
        response.comparison_mode = comparison_mode
        return response

    def compare_grocery_prices(
        self,
        ingredient: str,
        limit: int = 10,
        threshold: Optional[float] = None,
    ) -> MatchIngredientsResponse:
        """
        Match products and rank them by price ascending (cheapest first).
        """
        return self.match_products_for_ingredient(
            ingredient=ingredient,
            limit=limit,
            threshold=threshold,
            sort_by_price=True,
        )
