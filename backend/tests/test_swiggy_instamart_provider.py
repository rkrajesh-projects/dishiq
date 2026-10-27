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
from app.grocery_sources.swiggy_oauth import (
    SwiggyTokenStorage,
    swiggy_token_storage,
    swiggy_oauth_manager,
)
from app.grocery_sources.swiggy_instamart_provider import validate_coordinates, normalize_availability


@pytest.fixture(autouse=True)
def isolate_token_storage(tmp_path):
    """Ensure test suite operates in isolated sandbox and never mutates production token file."""
    fake_storage = SwiggyTokenStorage(file_path=str(tmp_path / "test_tokens.json"))
    with patch("app.grocery_sources.swiggy_oauth.swiggy_token_storage", fake_storage), \
         patch("app.grocery_sources.swiggy_instamart_provider.swiggy_token_storage", fake_storage), \
         patch.object(swiggy_oauth_manager, "storage", fake_storage):
        yield fake_storage


class TestSwiggyInstamartMcpProvider:

    def test_provider_initialization_config_absent(self):
        """Test configuration validation when API credentials are empty."""
        with patch.object(settings, "SWIGGY_INSTAMART_CLIENT_ID", None), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_SECRET", None), \
             patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", None), \
             patch.object(settings, "SWIGGY_INSTAMART_REFRESH_TOKEN", None):
            
            provider = SwiggyInstamartMcpProvider()
            assert provider.is_configured is False
            assert provider.is_available is False
            
            # search_products raises error when not configured
            with pytest.raises(RuntimeError) as exc:
                import asyncio
                asyncio.run(provider.search_products("paneer"))
            assert "Access credentials missing" in str(exc.value)

    def test_provider_initialization_config_present(self):
        """Test configuration validation when credentials or tokens are present."""
        # 1. Access token present
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "valid_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_REFRESH_TOKEN", None), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_ID", None), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_SECRET", None):
            provider = SwiggyInstamartMcpProvider()
            assert provider.is_configured is True
            assert provider.is_available is True
            assert provider.provider_name == "swiggy_instamart"

        # 2. Refresh token present
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", None), \
             patch.object(settings, "SWIGGY_INSTAMART_REFRESH_TOKEN", "refresh_tok_123"), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_ID", None), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_SECRET", None):
            provider = SwiggyInstamartMcpProvider()
            assert provider.is_configured is True
            assert provider.is_available is True

        # 3. Client ID and Client Secret present
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", None), \
             patch.object(settings, "SWIGGY_INSTAMART_REFRESH_TOKEN", None), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_ID", "client_1"), \
             patch.object(settings, "SWIGGY_INSTAMART_CLIENT_SECRET", "secret_1"):
            provider = SwiggyInstamartMcpProvider()
            assert provider.is_configured is True
            assert provider.is_available is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_successful_search_official_variations_schema(self, mock_post):
        """Test official Swiggy Instamart nested variations schema mapped cleanly."""
        import json
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "data": {
                                "products": [
                                    {
                                        "displayName": "Amul Fresh Malai Paneer",
                                        "brand": "Amul",
                                        "productId": "prod_paneer_root",
                                        "storeName": "Instamart Indiranagar Hub",
                                        "variations": [
                                            {
                                                "spinId": "spin_paneer_200g",
                                                "skuId": "sku_101",
                                                "displayName": "Amul Fresh Malai Paneer 200 g",
                                                "brandName": "Amul",
                                                "quantityDescription": "200 g",
                                                "price": {
                                                    "mrp": 100.0,
                                                    "offerPrice": 92.0,
                                                    "unitLevelPrice": "₹46.00/100g"
                                                },
                                                "isInStockAndAvailable": True,
                                                "productUrl": "https://swiggy.com/im/amul-paneer-200g"
                                            },
                                            {
                                                "spinId": "spin_paneer_500g",
                                                "skuId": "sku_102",
                                                "displayName": "Amul Fresh Malai Paneer 500 g",
                                                "brandName": "Amul",
                                                "quantityDescription": "500 g",
                                                "price": {
                                                    "mrp": 240.0,
                                                    "offerPrice": 220.0,
                                                    "unitLevelPrice": "₹44.00/100g"
                                                },
                                                "isInStockAndAvailable": True,
                                                "productUrl": "https://swiggy.com/im/amul-paneer-500g"
                                            }
                                        ]
                                    }
                                ]
                            }
                        })
                    }
                ]
            },
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            results = await provider.search_products("paneer")

            assert len(results) == 2
            v1, v2 = results[0], results[1]

            assert v1.source_platform == "Swiggy Instamart"
            assert v1.source_product_id == "spin_paneer_200g"
            assert v1.product_name == "Amul Fresh Malai Paneer 200 g"
            assert v1.brand == "Amul"
            assert v1.store_name == "Instamart Indiranagar Hub"
            assert v1.price == 92.0
            assert v1.mrp == 100.0
            assert v1.discount == 8.0
            assert v1.package_quantity == 200.0
            assert v1.package_unit == "g"
            assert v1.availability is True
            assert v1.price_freshness == "PROVIDER_LIVE"

            assert v2.source_product_id == "spin_paneer_500g"
            assert v2.price == 220.0
            assert v2.package_quantity == 500.0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_search_with_guest_coordinates(self, mock_post):
        """Test guest coordinate search (latitude, longitude) passes correctly in tool arguments."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"products": []},
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            await provider.search_products("milk", latitude=12.9716, longitude=77.5946)

            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs.get("json", {})
            args = payload["params"]["arguments"]
            assert args["query"] == "milk"
            assert args["latitude"] == 12.9716
            assert args["longitude"] == 77.5946
            assert "addressId" not in args

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_token_refresh_on_401(self, mock_post):
        """Test automatic token refresh upon HTTP 401 response and subsequent successful retry."""
        # Call 1: HTTP 401 Unauthorized
        resp_401 = MagicMock()
        resp_401.status_code = 401

        # Call 2 (token endpoint): HTTP 200 with new tokens
        resp_auth = MagicMock()
        resp_auth.status_code = 200
        resp_auth.json.return_value = {
            "access_token": "new_refreshed_access_token",
            "refresh_token": "new_refreshed_refresh_token",
            "expires_in": 2592000
        }

        # Call 3 (retry search): HTTP 200 with products
        resp_retry = MagicMock()
        resp_retry.status_code = 200
        resp_retry.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "products": [
                    {
                        "spinId": "spin_refreshed_1",
                        "name": "Nandini Milk 500 ml",
                        "price": 24.0,
                        "packageSize": "500 ml"
                    }
                ]
            },
            "id": 1
        }

        mock_post.side_effect = [resp_401, resp_auth, resp_retry]

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "expired_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_REFRESH_TOKEN", "valid_refresh_token"):
            provider = SwiggyInstamartMcpProvider()
            results = await provider.search_products("milk")

            assert len(results) == 1
            assert results[0].source_product_id == "spin_refreshed_1"
            assert results[0].price == 24.0
            # Verify the updated token was cached in provider instance
            assert provider._access_token == "new_refreshed_access_token"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_token_refresh_on_rpc_unauthorized_error(self, mock_post):
        """Test automatic token refresh upon JSON-RPC -32001 session error."""
        resp_rpc_err = MagicMock()
        resp_rpc_err.status_code = 200
        resp_rpc_err.json.return_value = {
            "jsonrpc": "2.0",
            "error": {"code": -32001, "message": "Session expired or unauthorized"},
            "id": 1
        }

        resp_auth = MagicMock()
        resp_auth.status_code = 200
        resp_auth.json.return_value = {
            "access_token": "reauthorized_token",
            "refresh_token": "reauthorized_refresh"
        }

        resp_success = MagicMock()
        resp_success.status_code = 200
        resp_success.json.return_value = {
            "jsonrpc": "2.0",
            "result": [{"spinId": "item_1", "name": "Item 1", "price": 50.0}],
            "id": 1
        }

        mock_post.side_effect = [resp_rpc_err, resp_auth, resp_success]

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "old_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_REFRESH_TOKEN", "refresh_tok"):
            provider = SwiggyInstamartMcpProvider()
            results = await provider.search_products("items")
            assert len(results) == 1
            assert results[0].source_product_id == "item_1"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_rate_limit_429(self, mock_post):
        """Test HTTP 429 returns clean rate-limiting exception."""
        resp_429 = MagicMock()
        resp_429.status_code = 429
        mock_post.return_value = resp_429

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            with pytest.raises(RuntimeError) as exc:
                await provider.search_products("bread")
            assert "rate limit" in str(exc.value).lower()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_successful_search_normalization(self, mock_post):
        """Test legacy flat Swiggy MCP product mapped cleanly to NormalizedGroceryProduct."""
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
            assert product.price_freshness == "PROVIDER_LIVE"
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
            assert p.brand == "Generic"
            assert p.category == "Uncategorized"
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

        # 2. Authentication failure without refresh token
        mock_post.side_effect = None
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        mock_post.return_value = mock_response_401
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_REFRESH_TOKEN", None):
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

        registry = GroceryProviderRegistry()
        swiggy_provider = SwiggyInstamartMcpProvider()
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            registry.register(swiggy_provider)
            results, failures = await registry.search_all_providers("paneer")
            
            assert len(results) == 1
            assert results[0].source_platform == "Swiggy Instamart"
            assert results[0].price_freshness == "PROVIDER_LIVE"
            assert failures == {}

    @pytest.mark.asyncio
    async def test_no_fake_live_data_on_demo_cache(self, seeded_db):
        """Test DemoProvider seed data is strictly marked as DEMO and not LIVE."""
        demo_provider = DemoGroceryProvider(seeded_db)
        results = await demo_provider.search_products("paneer")
        
        assert len(results) > 0
        for p in results:
            assert p.price_freshness == "DEMO"
            assert p.price_freshness != "PROVIDER_LIVE"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_search_products_tool_is_error_raises_clear_runtime_error(self, mock_post):
        """Verify that when Swiggy MCP returns isError: true, a descriptive RuntimeError is raised."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "addressId is required\nReport ID: ERR-1234\nSomething went wrong."
                    }
                ],
                "isError": True
            },
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            with pytest.raises(RuntimeError) as exc_info:
                await provider.search_products("milk")
            
            err = str(exc_info.value)
            assert "Swiggy Instamart search failed" in err
            assert "addressId is required" in err
            assert "delivery location" in err

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_search_products_structured_content_extraction(self, mock_post):
        """Verify products are extracted directly from official structuredContent object."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "structuredContent": {
                    "products": [
                        {
                            "productId": "prod_butter_1",
                            "displayName": "Amul Butter 500 g",
                            "price": {"offerPrice": 275.0, "mrp": 285.0},
                            "quantityDescription": "500 g",
                            "isInStockAndAvailable": True
                        }
                    ]
                }
            },
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            results = await provider.search_products("butter", latitude=12.97, longitude=77.59)
            assert len(results) == 1
            assert results[0].product_name == "Amul Butter 500 g"
            assert results[0].price == 275.0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_get_addresses_parsing(self, mock_post):
        """Verify get_addresses parses structuredContent addresses cleanly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "structuredContent": {
                    "addresses": [
                        {"id": "addr_999", "addressLine": "123 Main St"}
                    ],
                    "total": 1
                }
            },
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            addresses = await provider.get_addresses()
            assert len(addresses) == 1
            assert addresses[0]["id"] == "addr_999"

    def test_validate_coordinates_missing_one_raises_value_error(self):
        """Test validate_coordinates requires both latitude and longitude together."""
        with pytest.raises(ValueError) as exc1:
            validate_coordinates(12.9716, None)
        assert "Both latitude and longitude must be supplied together" in str(exc1.value)

        with pytest.raises(ValueError) as exc2:
            validate_coordinates(None, 77.5946)
        assert "Both latitude and longitude must be supplied together" in str(exc2.value)

        # Both None returns (None, None)
        assert validate_coordinates(None, None) == (None, None)

    def test_validate_coordinates_out_of_range(self):
        """Test validate_coordinates validates valid geographic ranges."""
        # Latitude out of bounds
        with pytest.raises(ValueError) as exc_lat_high:
            validate_coordinates(90.1, 77.59)
        assert "Latitude must be between -90.0 and 90.0" in str(exc_lat_high.value)

        with pytest.raises(ValueError) as exc_lat_low:
            validate_coordinates(-90.1, 77.59)
        assert "Latitude must be between -90.0 and 90.0" in str(exc_lat_low.value)

        # Longitude out of bounds
        with pytest.raises(ValueError) as exc_lng_high:
            validate_coordinates(12.97, 180.1)
        assert "Longitude must be between -180.0 and 180.0" in str(exc_lng_high.value)

        with pytest.raises(ValueError) as exc_lng_low:
            validate_coordinates(12.97, -180.1)
        assert "Longitude must be between -180.0 and 180.0" in str(exc_lng_low.value)

        # Boundary values are valid
        assert validate_coordinates(-90.0, -180.0) == (-90.0, -180.0)
        assert validate_coordinates(90.0, 180.0) == (90.0, 180.0)

    def test_validate_coordinates_non_numeric(self):
        """Test validate_coordinates rejects non-numeric or malformed values."""
        with pytest.raises(ValueError) as exc1:
            validate_coordinates("invalid_lat", 77.59)
        assert "must be a valid number" in str(exc1.value)

        with pytest.raises(ValueError) as exc2:
            validate_coordinates(12.97, "invalid_lng")
        assert "must be a valid number" in str(exc2.value)

    def test_provider_initialization_coordinate_validation(self):
        """Test provider initialization validates coordinate parameters."""
        # Missing one coordinate raises ValueError
        with pytest.raises(ValueError) as exc1:
            SwiggyInstamartMcpProvider(latitude=12.97)
        assert "Both latitude and longitude must be supplied together" in str(exc1.value)

        # Out of range coordinate raises ValueError
        with pytest.raises(ValueError) as exc2:
            SwiggyInstamartMcpProvider(latitude=95.0, longitude=77.59)
        assert "Latitude must be between -90.0 and 90.0" in str(exc2.value)

        # Valid coordinates are stored on instance
        provider = SwiggyInstamartMcpProvider(latitude=12.97, longitude=77.59)
        assert provider._latitude == 12.97
        assert provider._longitude == 77.59

    @pytest.mark.asyncio
    async def test_search_products_missing_one_coordinate_raises(self):
        """Test search_products raises ValueError when only one coordinate is passed."""
        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"):
            provider = SwiggyInstamartMcpProvider()
            with pytest.raises(ValueError) as exc1:
                await provider.search_products("milk", latitude=12.97, longitude=None)
            assert "Both latitude and longitude must be supplied together" in str(exc1.value)

            with pytest.raises(ValueError) as exc2:
                await provider.search_products("milk", latitude=None, longitude=77.59)
            assert "Both latitude and longitude must be supplied together" in str(exc2.value)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_search_with_configured_settings_coordinates(self, mock_post):
        """Test provider forwards coordinates configured via settings when no addressId is set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"products": []},
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID", None), \
             patch.object(settings, "SWIGGY_INSTAMART_LATITUDE", 13.0827), \
             patch.object(settings, "SWIGGY_INSTAMART_LONGITUDE", 80.2707):
            provider = SwiggyInstamartMcpProvider()
            await provider.search_products("milk")

            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            args = call_kwargs["json"]["params"]["arguments"]
            assert args["query"] == "milk"
            assert args["latitude"] == 13.0827
            assert args["longitude"] == 80.2707
            assert "addressId" not in args

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_explicit_coordinates_override_settings(self, mock_post):
        """Test explicit search coordinates take precedence over settings coordinates."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"products": []},
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID", None), \
             patch.object(settings, "SWIGGY_INSTAMART_LATITUDE", 13.0827), \
             patch.object(settings, "SWIGGY_INSTAMART_LONGITUDE", 80.2707):
            provider = SwiggyInstamartMcpProvider()
            await provider.search_products("milk", latitude=19.0760, longitude=72.8777)

            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            args = call_kwargs["json"]["params"]["arguments"]
            assert args["query"] == "milk"
            assert args["latitude"] == 19.0760
            assert args["longitude"] == 72.8777
            assert "addressId" not in args

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_saved_address_takes_precedence_over_configured_coordinates(self, mock_post):
        """Test configured saved addressId takes precedence over configured settings coordinates."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"products": []},
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID", "addr_indiranagar_42"), \
             patch.object(settings, "SWIGGY_INSTAMART_LATITUDE", 13.0827), \
             patch.object(settings, "SWIGGY_INSTAMART_LONGITUDE", 80.2707):
            provider = SwiggyInstamartMcpProvider()
            await provider.search_products("milk")

            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            args = call_kwargs["json"]["params"]["arguments"]
            assert args["query"] == "milk"
            assert args["addressId"] == "addr_indiranagar_42"
            assert "latitude" not in args
            assert "longitude" not in args

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_explicit_address_id_takes_highest_precedence(self, mock_post):
        """Test explicitly passed address_id overrides both coordinates and configured address."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"products": []},
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID", "addr_default"), \
             patch.object(settings, "SWIGGY_INSTAMART_LATITUDE", 13.0827), \
             patch.object(settings, "SWIGGY_INSTAMART_LONGITUDE", 80.2707):
            provider = SwiggyInstamartMcpProvider()
            await provider.search_products("milk", address_id="addr_custom_999", latitude=12.97, longitude=77.59)

            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            args = call_kwargs["json"]["params"]["arguments"]
            assert args["query"] == "milk"
            assert args["addressId"] == "addr_custom_999"
            assert "latitude" not in args
            assert "longitude" not in args

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_no_fake_address_id_sent_when_unconfigured(self, mock_post):
        """Test placeholder/dummy default_address is never sent to the official MCP server."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"products": []},
            "id": 1
        }
        mock_post.return_value = mock_response

        with patch.object(settings, "SWIGGY_INSTAMART_ACCESS_TOKEN", "mock_token"), \
             patch.object(settings, "SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID", "default_address"), \
             patch.object(settings, "SWIGGY_INSTAMART_LATITUDE", None), \
             patch.object(settings, "SWIGGY_INSTAMART_LONGITUDE", None):
            provider = SwiggyInstamartMcpProvider()
            await provider.search_products("milk")

            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            args = call_kwargs["json"]["params"]["arguments"]
            assert args["query"] == "milk"
            assert "addressId" not in args
            assert "latitude" not in args
            assert "longitude" not in args


class TestSwiggyAvailabilityNormalization:
    """
    Focused regression tests for Swiggy Instamart availability normalization:
    - Boolean True/False values
    - String values ('true', 'false', '1', '0', 'yes', 'no', etc.)
    - Numeric values (1, 0, 1.0, 0.0)
    - Fallback fields preserving explicit False values (not discarded by `or`)
    - Missing or unrecognized values
    """

    def test_normalize_availability_boolean_values(self):
        """Boolean True/False must remain unchanged."""
        assert normalize_availability(True) is True
        assert normalize_availability(False) is False

    def test_normalize_availability_numeric_values(self):
        """Numeric 1/0 and floats 1.0/0.0 must be mapped correctly."""
        assert normalize_availability(1) is True
        assert normalize_availability(0) is False
        assert normalize_availability(1.0) is True
        assert normalize_availability(0.0) is False
        assert normalize_availability(2) is True
        assert normalize_availability(-1) is False

    def test_normalize_availability_string_truthy_values(self):
        """Recognized truthy strings must normalize to True."""
        truthy_samples = [
            "true", "True", "TRUE", " true ",
            "1", " 1 ",
            "yes", "Yes", "YES", " yes ",
            "y", "Y",
            "available", "Available",
            "in_stock", "IN_STOCK"
        ]
        for val in truthy_samples:
            assert normalize_availability(val) is True, f"Failed for {val!r}"

    def test_normalize_availability_string_falsy_values(self):
        """Recognized falsy strings must normalize to False (never True via bool())."""
        falsy_samples = [
            "false", "False", "FALSE", " false ",
            "0", " 0 ",
            "no", "No", "NO", " no ",
            "n", "N",
            "unavailable", "Unavailable",
            "out_of_stock", "OUT_OF_STOCK"
        ]
        for val in falsy_samples:
            assert normalize_availability(val) is False, f"Failed for {val!r}"

    def test_normalize_availability_missing_and_unrecognized_values(self):
        """Missing or unrecognized values use the documented fallback."""
        # Missing (None) defaults to True in active search catalog context
        assert normalize_availability(None) is True
        assert normalize_availability(None, default=False) is False
        assert normalize_availability(None, default=True) is True

        # Unrecognized strings use fallback
        assert normalize_availability("unknown", default=True) is True
        assert normalize_availability("unknown", default=False) is False
        assert normalize_availability("random_text", default=True) is True
        assert normalize_availability("random_text", default=False) is False

        # Non-string/non-numeric objects use fallback
        assert normalize_availability({}, default=False) is False
        assert normalize_availability([], default=True) is True

    def test_normalize_variation_availability_types(self):
        """Verify _normalize_variation handles diverse availability types on variations."""
        provider = SwiggyInstamartMcpProvider()
        parent_prod = {"productId": "p1", "displayName": "Milk Parent"}

        cases = [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            (1, True),
            (0, False),
            (1.0, True),
            (0.0, False),
            (None, True),  # Missing field defaults to True
        ]

        for raw_val, expected in cases:
            var = {
                "spinId": "var_1",
                "displayName": "Milk 1L",
                "price": {"offerPrice": 50.0, "mrp": 55.0},
                "quantityDescription": "1 L",
            }
            if raw_val is not None:
                var["isInStockAndAvailable"] = raw_val

            norm = provider._normalize_variation(parent_prod, var)
            assert norm.availability is expected, f"Expected {expected} for variation raw {raw_val!r}, got {norm.availability}"

    def test_normalize_variation_preserves_explicit_false_in_fallbacks(self):
        """Verify fallback checks preserve explicit False and do not discard it via `or`."""
        provider = SwiggyInstamartMcpProvider()

        # Case 1: Variation has explicit inStock=False, parent has isAvail=True
        parent = {"productId": "p1", "displayName": "Product", "isAvail": True}
        var1 = {
            "spinId": "v1",
            "displayName": "Item 1",
            "inStock": False,  # isInStockAndAvailable is None
        }
        res1 = provider._normalize_variation(parent, var1)
        assert res1.availability is False, "Explicit False in var.inStock must not be discarded by parent.isAvail=True"

        # Case 2: Variation has string inStock="false", parent has inStock=True
        var2 = {
            "spinId": "v2",
            "displayName": "Item 2",
            "inStock": "false",
        }
        res2 = provider._normalize_variation(parent, var2)
        assert res2.availability is False, "String 'false' in var.inStock must not be discarded or coerced to True"

        # Case 3: Variation has numeric inStock=0, parent has inStock=1
        var3 = {
            "spinId": "v3",
            "displayName": "Item 3",
            "inStock": 0,
        }
        res3 = provider._normalize_variation(parent, var3)
        assert res3.availability is False, "Numeric 0 in var.inStock must evaluate to False"

        # Case 4: Variation has no availability, parent has explicit inStock=False, parent.isAvail=True
        parent_with_false = {"productId": "p2", "displayName": "Product 2", "inStock": False, "isAvail": True}
        var4 = {
            "spinId": "v4",
            "displayName": "Item 4",
        }
        res4 = provider._normalize_variation(parent_with_false, var4)
        assert res4.availability is False, "Explicit False in parent.inStock must not be bypassed by parent.isAvail=True"

    def test_normalize_flat_product_availability_types(self):
        """Verify _normalize_flat_product handles diverse availability types."""
        provider = SwiggyInstamartMcpProvider()

        cases = [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            (1, True),
            (0, False),
            (None, True),
        ]

        for raw_val, expected in cases:
            flat = {
                "productId": "flat_1",
                "name": "Flat Product",
                "price": 30.0,
            }
            if raw_val is not None:
                flat["isInStockAndAvailable"] = raw_val

            norm = provider._normalize_flat_product(flat)
            assert norm.availability is expected, f"Expected {expected} for flat raw {raw_val!r}, got {norm.availability}"

    def test_normalize_flat_product_preserves_explicit_false_in_fallbacks(self):
        """Verify fallback checks in _normalize_flat_product preserve explicit False."""
        provider = SwiggyInstamartMcpProvider()

        # Case 1: inStock is False, available is True
        flat1 = {
            "productId": "f1",
            "name": "Item 1",
            "inStock": False,
            "available": True,
        }
        res1 = provider._normalize_flat_product(flat1)
        assert res1.availability is False, "Explicit False in inStock must not be discarded by available=True"

        # Case 2: inStock is None, in_stock is "false", isAvail is True
        flat2 = {
            "productId": "f2",
            "name": "Item 2",
            "in_stock": "false",
            "isAvail": True,
        }
        res2 = provider._normalize_flat_product(flat2)
        assert res2.availability is False, "String 'false' in in_stock must not be discarded by isAvail=True"

        # Case 3: inStock is None, in_stock is 0, isAvail is 1
        flat3 = {
            "productId": "f3",
            "name": "Item 3",
            "in_stock": 0,
            "isAvail": 1,
        }
        res3 = provider._normalize_flat_product(flat3)
        assert res3.availability is False, "Numeric 0 in in_stock must not be discarded by isAvail=1"

        # Case 4: All fields missing -> default True
        flat4 = {
            "productId": "f4",
            "name": "Item 4",
        }
        res4 = provider._normalize_flat_product(flat4)
        assert res4.availability is True, "Missing availability fields must fallback to True"


