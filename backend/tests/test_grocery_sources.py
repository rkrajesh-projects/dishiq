import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.grocery_sources import (
    NormalizedGroceryProduct,
    BaseGroceryProvider,
    GroceryProviderRegistry,
    DemoGroceryProvider,
    McpGroceryProvider,
)
from app.models.grocery import GroceryStore, GroceryProduct, ProductPrice

# Dummy provider class for testing BaseGroceryProvider abstract class behavior
class MockGroceryProvider(BaseGroceryProvider):
    def __init__(self, name: str, should_fail: bool = False):
        self._name = name
        self.should_fail = should_fail

    @property
    def provider_name(self) -> str:
        return self._name

    async def search_products(self, query: str):
        if self.should_fail:
            raise RuntimeError(f"Platform {self._name} timed out or failed.")
        
        # Return mock normalized product
        return [
            NormalizedGroceryProduct(
                source_platform=self._name,
                source_product_id="mock_id_123",
                store_name="Mock Store",
                product_name=f"Mock {query} product",
                brand="MockBrand",
                category="MockCategory",
                package_quantity=200.0,
                package_unit="grams",
                price=100.0,
                currency="INR",
                availability=True,
                product_url="http://mock.url",
                retrieved_at=datetime.now(timezone.utc),
                price_freshness="LIVE",
            )
        ]

    async def get_product_details(self, product_id: str):
        return None

    async def get_current_price(self, product_id: str):
        return 100.0


def test_normalized_product_validation():
    """Test 2: Normalized product validation rules."""
    # Valid model validation
    valid_product = NormalizedGroceryProduct(
        source_platform="quickmart",
        source_product_id="p999",
        store_name="Demo QuickMart",
        product_name="Paneer Blocks",
        brand="Amul",
        category="Dairy",
        package_quantity=200.0,
        package_unit="g",
        price=95.0,
        currency="INR",
        availability=True,
        product_url="http://quickmart.test/paneer",
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="LIVE",
    )
    assert valid_product.source_product_id == "p999"
    assert valid_product.price_freshness == "LIVE"

    # Invalid validation: missing required field (source_product_id)
    with pytest.raises(ValidationError):
        NormalizedGroceryProduct(
            source_platform="quickmart",
            store_name="Demo QuickMart",
            product_name="Paneer Blocks",
            retrieved_at=datetime.now(timezone.utc),
        )


def test_provider_registry_registration():
    """Test 3: Provider registry registration behavior."""
    registry = GroceryProviderRegistry()
    p1 = MockGroceryProvider("provider_1")
    
    registry.register(p1)
    assert "provider_1" in registry.list_providers()
    assert registry.get_provider("provider_1") == p1


def test_provider_lookup_and_unknown_provider():
    """Test 4 & 5: Provider lookup and unknown provider error handling."""
    registry = GroceryProviderRegistry()
    
    # Try looking up unregistered provider
    with pytest.raises(ValueError) as exc:
        registry.get_provider("non_existent")
    assert "is not registered" in str(exc.value)


@pytest.mark.asyncio
async def test_provider_failure_isolation():
    """Test 8: Provider failure isolation (one failure doesn't break comparison)."""
    registry = GroceryProviderRegistry()
    p_ok = MockGroceryProvider("provider_ok")
    p_fail = MockGroceryProvider("provider_fail", should_fail=True)

    registry.register(p_ok)
    registry.register(p_fail)

    # Search query
    results, failures = await registry.search_all_providers("paneer")

    # The search succeeded overall
    assert len(results) == 1
    assert results[0].source_platform == "provider_ok"
    
    # Failure was isolated and reported
    assert "provider_fail" in failures
    assert "RuntimeError" in failures["provider_fail"]


@pytest.mark.asyncio
async def test_empty_provider_results():
    """Test 9: Handing empty provider list or empty search results."""
    registry = GroceryProviderRegistry()
    
    results, failures = await registry.search_all_providers("paneer")
    assert results == []
    assert failures == {}


def test_invalid_null_optional_product_fields():
    """Test 10: Validation of optional/null fields in NormalizedGroceryProduct."""
    p = NormalizedGroceryProduct(
        source_platform="demo",
        source_product_id="p1",
        store_name="Store",
        product_name="Paneer",
        brand=None,         # null option
        category=None,      # null option
        package_quantity=None,
        package_unit=None,
        price=None,
        currency="INR",
        availability=True,
        product_url=None,
        retrieved_at=datetime.now(timezone.utc),
        price_freshness="UNKNOWN",
    )
    # Default fallbacks or allowed None values
    assert p.brand == "Generic"
    assert p.category == "Uncategorized"
    assert p.price is None
    assert p.price_freshness == "UNKNOWN"


def test_demo_provider_retrieval(seeded_db: Session):
    """Test 6 & 7: Demo provider retrieval and price freshness metadata."""
    # Seed a demo store and product
    store = GroceryStore(name="Test Reg Store", store_type="Supermarket")
    seeded_db.add(store)
    seeded_db.commit()

    product = GroceryProduct(
        store_id=store.id,
        name="Reg Paneer 100g",
        normalized_name="paneer",
        brand="Amul",
        category="Dairy",
        package_quantity=100.0,
        package_unit="g",
        in_stock=True,
    )
    seeded_db.add(product)
    seeded_db.commit()

    price = ProductPrice(
        product_id=product.id,
        price=50.0,
        data_source_type="demo",
    )
    seeded_db.add(price)
    seeded_db.commit()

    # Query using DemoGroceryProvider
    provider = DemoGroceryProvider(seeded_db)
    assert provider.provider_name == "demo"

    import asyncio
    loop = asyncio.get_event_loop()
    
    # Query with unique prefix to prevent collision with other seeded Paneer items
    results = loop.run_until_complete(provider.search_products("Reg Paneer"))

    assert len(results) == 1
    p_normalized = results[0]
    assert p_normalized.product_name == "Reg Paneer 100g"
    assert p_normalized.price == 50.0
    assert p_normalized.price_freshness == "CACHED"
    assert isinstance(p_normalized.retrieved_at, datetime)

    # Test single product details lookup
    details = loop.run_until_complete(provider.get_product_details(product.id))
    assert details is not None
    assert details.product_name == "Reg Paneer 100g"
    assert details.price == 50.0
