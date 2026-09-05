import pytest
import httpx
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.config import settings
from app.grocery_sources import (
    SwiggyInstamartMcpProvider,
    GroceryProviderRegistry,
    DemoGroceryProvider,
    NormalizedGroceryProduct
)

class TestSwiggyInstamartMcpProvider:

    def test_provider_initialization_config_absent(self):
        """Test configuration validation when API credentials are empty."""
        with patch.object(settings, "SWIGGY_INSTAMART_CLIENT_ID", None), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_SECRET", None), \
             patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", None):
            
            provider = SwiggyInstamartMcpProvider()
            assert provider.is_configured is False
            
            # search_products raises error when not configured
            with pytest.raises(RuntimeError) as exc:
                import asyncio
                asyncio.run(provider.search_products("paneer"))
            assert "Access credentials missing" in str(exc.value)

    def test_provider_initialization_config_present(self):
        """Test configuration validation when credentials are present."""
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "valid_token"):
            provider = SwiggyInstamartMcpProvider()
            assert provider.is_configured is True
            assert provider.provider_name == "swiggy_instamart"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_successful_search_normalization(self, mock_post):
        """Test raw Swiggy MCP product mapped cleanly to NormalizedGroceryProduct."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "products": [
                    {
                        "spinId": "swiggy_paneer_1",
                        "name": "Nandini Fresh Paneer 200 g",
                        "brand": "Nandini",
                        "category": "Dairy",
                        "store_name": "Instamart Store Bengaluru East",
                        "offerPrice": 92.50,
                        "mrp": 100.0,
                        "inStock": True,
                        "packageSize": "200 g",
                        "productUrl": "https://swiggy.com/im/nandini-paneer"
                    }
                ]
            },
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            results = await provider.search_products("paneer")

            assert len(results) == 1
            product = results[0]
            assert isinstance(product, NormalizedGroceryProduct)
            assert product.source_platform == "Swiggy Instamart"
            assert product.source_product_id == "swiggy_paneer_1"
            assert product.product_name == "Nandini Fresh Paneer 200 g"
            assert product.brand == "Nandini"
            assert product.category == "Dairy"
            assert product.store_name == "Instamart Store Bengaluru East"
            assert product.price == 92.50
            assert product.package_quantity == 200.0
            assert product.package_unit == "g"
            assert product.availability is True
            assert product.price_freshness == "LIVE"
            assert isinstance(product.retrieved_at, datetime)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_empty_results_safe(self, mock_post):
        """Test empty Swiggy Instamart response results returned safely."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "products": []
            },
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            results = await provider.search_products("non_existent")
            assert results == []

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_malformed_product_safe(self, mock_post):
        """Test missing/invalid fields in product do not crash normalization."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Product missing brand, category, quantity unit structure
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": [
                {
                    "id": "swiggy_broken",
                    "name": "Broken Product",
                    "price": 10.0
                }
            ],
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            results = await provider.search_products("broken")
            assert len(results) == 1
            p = results[0]
            assert p.source_product_id == "swiggy_broken"
            assert p.brand == "Generic"  # Fallback verified
            assert p.category == "Uncategorized"  # Fallback verified
            assert p.package_quantity == 1.0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_mcp_failures_isolated(self, mock_post):
        """Test connection errors, timeouts, and auth errors are handled safely."""
        # 1. Connection error
        mock_post.side_effect = httpx.ConnectError("Connection timed out")
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            with pytest.raises(RuntimeError) as exc:
                await provider.search_products("paneer")
            assert "connection failure" in str(exc.value)

        # 2. Authentication failure
        mock_post.side_effect = None
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        mock_post.return_value = mock_response_401
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            with pytest.raises(RuntimeError) as exc:
                await provider.search_products("paneer")
            assert "authentication failed" in str(exc.value)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_registry_integration_and_fallback(self, mock_post):
        """Test provider behaves cleanly within the registry workflow."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": [
                {
                    "spinId": "swiggy_p2",
                    "name": "Swiggy Paneer",
                    "price": 95.0
                }
            ],
            "id": 1
        }
        mock_post.return_value = mock_response

        # Registry searches both Swiggy and Demo in parallel
        registry = GroceryProviderRegistry()
        
        swiggy_provider = SwiggyInstamartMcpProvider()
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            registry.register(swiggy_provider)
            results, failures = await registry.search_all_providers("paneer")
            
            assert len(results) == 1
            assert results[0].source_platform == "Swiggy Instamart"
            assert results[0].price_freshness == "LIVE"
            assert failures == {}

    @pytest.mark.asyncio
    async def test_no_fake_live_data_on_demo_cache(self, seeded_db):
        """Test DemoProvider seed data is strictly marked as CACHED and not LIVE."""
        demo_provider = DemoGroceryProvider(seeded_db)
        results = await demo_provider.search_products("paneer")
        
        assert len(results) > 0
        for p in results:
            assert p.price_freshness == "CACHED"
            assert p.price_freshness != "LIVE"

