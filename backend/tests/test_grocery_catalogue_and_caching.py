"""
DishIQ Phase 7 — Grocery Catalogue, Caching, and Price History Tests

Verifies:
1. Package size and variant identity separation (distinct package sizes are never merged).
2. Primary identity resolution via store_id and source_product_id.
3. Chronological price history observation recording and deduplication of identical prices.
4. Prevention of live price history creation for DEMO and CACHED items.
5. In-memory caching lifecycle: hit, miss, freshness marking, and stale cache fallback on provider failure.
6. API endpoint GET /api/grocery/products/{product_id}/price-history.
"""
import time
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.grocery_sources.base_provider import BaseGroceryProvider
from app.grocery_sources.models import NormalizedGroceryProduct
from app.grocery_sources.registry import GroceryProviderRegistry, clear_grocery_cache
from app.models.grocery import GroceryProduct, GroceryStore, ProductPrice
from app.services.product_sync_service import sync_live_products
from tests.conftest import TestingSessionLocal


class MockProvider(BaseGroceryProvider):
    def __init__(self, name: str, products=None, fail: bool = False):
        self._name = name
        self._products = products or []
        self._fail = fail
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._name

    async def search_products(self, query: str):
        self.call_count += 1
        if self._fail:
            raise ConnectionError(f"Simulated network timeout for {self._name}")
        return self._products

    async def get_product_details(self, product_id: str):
        for p in self._products:
            if getattr(p, "source_product_id", None) == product_id:
                return p
        return None

    async def get_current_price(self, product_id: str):
        p = await self.get_product_details(product_id)
        return p.price if p else None


@pytest.fixture(autouse=True)
def clean_cache():
    clear_grocery_cache()
    yield
    clear_grocery_cache()


def test_package_size_identity_separation_no_merging(seeded_db):
    """
    Ensure products with the same name and brand but different package sizes
    (e.g. 200g vs 500g) are NOT merged into a single product record.
    """
    store_name = "Fresh Mart Test"
    prod_200g = NormalizedGroceryProduct(
        source_platform="swiggy_instamart",
        source_product_id="swiggy_paneer_200",
        store_name=store_name,
        product_name="Amul Fresh Paneer",
        brand="Amul",
        category="Dairy",
        package_quantity=200.0,
        package_unit="g",
        price=90.0,
        currency="INR",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="PROVIDER_LIVE",
    )
    prod_500g = NormalizedGroceryProduct(
        source_platform="swiggy_instamart",
        source_product_id="swiggy_paneer_500",
        store_name=store_name,
        product_name="Amul Fresh Paneer",
        brand="Amul",
        category="Dairy",
        package_quantity=500.0,
        package_unit="g",
        price=210.0,
        currency="INR",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="PROVIDER_LIVE",
    )

    with patch("app.services.product_sync_service.SessionLocal", TestingSessionLocal):
        sync_live_products([prod_200g, prod_500g])

    db = TestingSessionLocal()
    try:
        # Query products from DB
        store = db.query(GroceryStore).filter(GroceryStore.name == store_name).first()
        assert store is not None

        products = (
            db.query(GroceryProduct)
            .filter(
                GroceryProduct.store_id == store.id,
                GroceryProduct.name == "Amul Fresh Paneer"
            )
            .all()
        )

        # Must be 2 distinct products, not merged into 1
        assert len(products) == 2
        quantities = {p.package_quantity for p in products}
        assert 200.0 in quantities
        assert 500.0 in quantities

        # Each has its own distinct price
        p_200 = next(p for p in products if p.package_quantity == 200.0)
        p_500 = next(p for p in products if p.package_quantity == 500.0)
        assert p_200.latest_price == 90.0
        assert p_500.latest_price == 210.0
    finally:
        db.close()


def test_primary_identity_resolution_via_source_product_id(seeded_db):
    """
    Ensure subsequent syncs with the same source_product_id update the product
    rather than creating duplicate rows.
    """
    store_name = "Blinkit Identity Test"
    sku_id = "blinkit_milk_1l"

    prod_initial = NormalizedGroceryProduct(
        source_platform="quickcommerce",
        source_product_id=sku_id,
        store_name=store_name,
        product_name="Nandini Toned Milk 1L",
        brand="Nandini",
        category="Dairy",
        package_quantity=1.0,
        package_unit="L",
        price=42.0,
        currency="INR",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="PROVIDER_LIVE",
    )

    with patch("app.services.product_sync_service.SessionLocal", TestingSessionLocal):
        sync_live_products([prod_initial])

    db = TestingSessionLocal()
    try:
        store = db.query(GroceryStore).filter(GroceryStore.name == store_name).first()
        assert store is not None
        initial_count = (
            db.query(GroceryProduct)
            .filter(GroceryProduct.store_id == store.id, GroceryProduct.source_product_id == sku_id)
            .count()
        )
        assert initial_count == 1

        # Second sync with slight name tweak or category update
        prod_updated = NormalizedGroceryProduct(
            source_platform="quickcommerce",
            source_product_id=sku_id,
            store_name=store_name,
            product_name="Nandini Fresh Toned Milk 1L",
            brand="Nandini",
            category="Fresh Dairy",
            package_quantity=1.0,
            package_unit="L",
            price=42.0,
            currency="INR",
            retrieved_at=datetime.now(timezone.utc),
            price_freshness="PROVIDER_LIVE",
        )

        with patch("app.services.product_sync_service.SessionLocal", TestingSessionLocal):
            sync_live_products([prod_updated])

        updated_count = (
            db.query(GroceryProduct)
            .filter(GroceryProduct.store_id == store.id, GroceryProduct.source_product_id == sku_id)
            .count()
        )
        assert updated_count == 1  # No duplicate row created
    finally:
        db.close()


def test_price_history_recording_and_deduplication(seeded_db):
    """
    Ensure:
    1. First live observation inserts price record.
    2. Repeated observation with identical price does NOT append redundant row.
    3. Price change observation inserts a new chronological price record.
    """
    store_name = "Price History Test Store"
    sku_id = "test_tomato_1kg"

    prod_day1 = NormalizedGroceryProduct(
        source_platform="swiggy_instamart",
        source_product_id=sku_id,
        store_name=store_name,
        product_name="Fresh Hybrid Tomato",
        brand="Farm Fresh",
        category="Vegetables",
        package_quantity=1.0,
        package_unit="kg",
        price=35.0,
        currency="INR",
        retrieved_at=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
        price_freshness="PROVIDER_LIVE",
    )

    with patch("app.services.product_sync_service.SessionLocal", TestingSessionLocal):
        # Day 1: First observation (₹35)
        sync_live_products([prod_day1])

    db = TestingSessionLocal()
    try:
        store = db.query(GroceryStore).filter(GroceryStore.name == store_name).first()
        assert store is not None
        product = (
            db.query(GroceryProduct)
            .filter(GroceryProduct.store_id == store.id, GroceryProduct.source_product_id == sku_id)
            .first()
        )
        assert product is not None
        assert len(product.prices) == 1
        assert product.prices[0].price == 35.0
        assert product.prices[0].price_freshness == "PROVIDER_LIVE"

        # Day 2: Same price (₹35) -> Deduplication must kick in
        prod_day2 = NormalizedGroceryProduct(
            source_platform="swiggy_instamart",
            source_product_id=sku_id,
            store_name=store_name,
            product_name="Fresh Hybrid Tomato",
            brand="Farm Fresh",
            category="Vegetables",
            package_quantity=1.0,
            package_unit="kg",
            price=35.0,
            currency="INR",
            retrieved_at=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc),
            price_freshness="PROVIDER_LIVE",
        )
        with patch("app.services.product_sync_service.SessionLocal", TestingSessionLocal):
            sync_live_products([prod_day2])

        db.refresh(product)
        assert len(product.prices) == 1  # Still 1 price row, no duplication!

        # Day 3: Price increase (₹40) -> New price observation appended
        prod_day3 = NormalizedGroceryProduct(
            source_platform="swiggy_instamart",
            source_product_id=sku_id,
            store_name=store_name,
            product_name="Fresh Hybrid Tomato",
            brand="Farm Fresh",
            category="Vegetables",
            package_quantity=1.0,
            package_unit="kg",
            price=40.0,
            currency="INR",
            retrieved_at=datetime(2026, 10, 17, 10, 0, tzinfo=timezone.utc),
            price_freshness="PROVIDER_LIVE",
        )
        with patch("app.services.product_sync_service.SessionLocal", TestingSessionLocal):
            sync_live_products([prod_day3])

        db.refresh(product)
        assert len(product.prices) == 2  # 2 chronological records
        assert product.prices[0].price == 35.0
        assert product.prices[1].price == 40.0
        assert product.latest_price == 40.0
    finally:
        db.close()


def test_demo_and_cached_products_never_create_live_price_history(seeded_db):
    """
    Ensure products marked as DEMO or CACHED never append records to live price history.
    """
    store_name = "Safety Test Store"
    sku_id = "safety_item_1"

    demo_prod = NormalizedGroceryProduct(
        source_platform="demo",
        source_product_id=sku_id,
        store_name=store_name,
        product_name="Safety Demo Rice",
        brand="Generic",
        category="Grains",
        package_quantity=1.0,
        package_unit="kg",
        price=60.0,
        currency="INR",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="DEMO",
    )

    cached_prod = NormalizedGroceryProduct(
        source_platform="swiggy_instamart",
        source_product_id=sku_id,
        store_name=store_name,
        product_name="Safety Demo Rice",
        brand="Generic",
        category="Grains",
        package_quantity=1.0,
        package_unit="kg",
        price=65.0,
        currency="INR",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="CACHED",
    )

    with patch("app.services.product_sync_service.SessionLocal", TestingSessionLocal):
        sync_live_products([demo_prod, cached_prod])

    db = TestingSessionLocal()
    try:
        store = db.query(GroceryStore).filter(GroceryStore.name == store_name).first()
        if store:
            product = (
                db.query(GroceryProduct)
                .filter(GroceryProduct.store_id == store.id, GroceryProduct.source_product_id == sku_id)
                .first()
            )
            if product:
                # Neither DEMO nor CACHED should have created a live price observation
                live_prices = [p for p in product.prices if p.data_source_type == "live"]
                assert len(live_prices) == 0
    finally:
        db.close()


@pytest.mark.asyncio
async def test_grocery_provider_registry_caching_and_freshness():
    """
    Verify GroceryProviderRegistry caching lifecycle:
    1. First search: provider called.
    2. Second search within TTL: served from cache, provider not called.
    3. Live items in cached results have price_freshness='CACHED'.
    """
    live_product = NormalizedGroceryProduct(
        source_platform="mock_live",
        source_product_id="live_101",
        store_name="Live Mart",
        product_name="Organic Spinach",
        price=25.0,
        currency="INR",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="PROVIDER_LIVE",
    )

    provider = MockProvider("mock_live", [live_product])
    registry = GroceryProviderRegistry()
    registry.register(provider)

    # 1. First search -> Provider called
    results1, failures1 = await registry.search_all_providers("spinach")
    assert provider.call_count == 1
    assert len(results1) == 1
    assert results1[0].price_freshness == "PROVIDER_LIVE"
    assert not failures1

    # 2. Second search -> Served from cache
    results2, failures2 = await registry.search_all_providers("spinach")
    assert provider.call_count == 1  # Provider NOT called again!
    assert len(results2) == 1
    # Cached live results must be marked as CACHED, never falsely as PROVIDER_LIVE
    assert results2[0].price_freshness == "CACHED"
    assert not failures2


@pytest.mark.asyncio
async def test_grocery_provider_registry_stale_cache_fallback():
    """
    Verify that when all providers fail/timeout, a stale cache entry within
    GROCERY_CACHE_STALE_TTL_SECONDS is returned as fallback with warning metadata.
    """
    live_product = NormalizedGroceryProduct(
        source_platform="flaky_live",
        source_product_id="flaky_101",
        store_name="Flaky Mart",
        product_name="Curry Leaves",
        price=10.0,
        currency="INR",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="PROVIDER_LIVE",
    )

    provider = MockProvider("flaky_live", [live_product], fail=False)
    registry = GroceryProviderRegistry()
    registry.register(provider)

    # Prime the cache
    results, _ = await registry.search_all_providers("curry leaves")
    assert len(results) == 1
    assert results[0].product_name == "Curry Leaves"

    # Now make provider flaky/failing
    provider._fail = True

    # Simulate TTL expiration but within stale TTL window
    from app.grocery_sources.registry import _PROVIDER_CACHE
    cache_key = "flaky_live:curry leaves"
    assert cache_key in _PROVIDER_CACHE
    # Set timestamp 400 seconds ago (> 300s TTL, but < 1800s stale TTL)
    _PROVIDER_CACHE[cache_key]["timestamp"] = time.time() - 400

    # Search again: provider will fail, registry falls back to stale cache
    fallback_results, failures = await registry.search_all_providers("curry leaves")
    assert len(fallback_results) == 1
    assert fallback_results[0].product_name == "Curry Leaves"
    assert fallback_results[0].price_freshness == "CACHED"
    assert "_cache" in failures
    assert "stale" in failures["_cache"].lower()


def test_api_product_price_history_endpoint(client, seeded_db):
    """
    Verify GET /api/grocery/products/{product_id}/price-history returns 200 with
    chronological prices, and 404 for unknown products.
    """
    # Find an existing product from seeded db
    product = seeded_db.query(GroceryProduct).first()
    assert product is not None

    response = client.get(f"/api/grocery/products/{product.id}/price-history")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == product.id
    assert data["product_name"] == product.name
    assert "history_count" in data
    assert isinstance(data["prices"], list)
    if data["prices"]:
        assert "price" in data["prices"][0]
        assert "currency" in data["prices"][0]
        assert "observed_at" in data["prices"][0]

    # Test 404 for nonexistent product
    res_404 = client.get("/api/grocery/products/non-existent-uuid-12345/price-history")
    assert res_404.status_code == 404
    err_body = res_404.json()
    err_msg = err_body.get("error", {}).get("message") or err_body.get("detail", "")
    assert "not found" in err_msg.lower()
