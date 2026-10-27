import re
import json
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.grocery_sources.base_provider import BaseGroceryProvider
from app.grocery_sources.models import NormalizedGroceryProduct
from app.grocery_sources.swiggy_oauth import swiggy_token_storage, swiggy_oauth_manager, is_valid_credential
from app.core.config import settings


def validate_coordinates(
    latitude: Optional[Any], longitude: Optional[Any]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Validate that latitude and longitude are supplied together and fall within
    valid geographic ranges (-90 to 90 for latitude, -180 to 180 for longitude).
    Returns (float(latitude), float(longitude)) or (None, None).
    Raises ValueError if only one is supplied or if values are invalid/out of range.
    """
    if latitude is None and longitude is None:
        return None, None
    if latitude is None or longitude is None:
        raise ValueError("Both latitude and longitude must be supplied together.")

    try:
        lat = float(latitude)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid latitude value '{latitude}': must be a valid number.")

    try:
        lng = float(longitude)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid longitude value '{longitude}': must be a valid number.")

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude must be between -90.0 and 90.0, got {lat}.")

    if not (-180.0 <= lng <= 180.0):
        raise ValueError(f"Longitude must be between -180.0 and 180.0, got {lng}.")

    return lat, lng


def normalize_availability(val: Any, default: bool = True) -> bool:
    """
    Safely normalize availability representations from Swiggy Instamart payloads.

    Args:
        val: Raw availability value from provider payload (can be bool, int, float, str, or None).
        default: Fallback boolean value when `val` is None or unrecognized. Defaults to True
                 for standard catalog search results where items returned without explicit
                 out-of-stock indicators are assumed available.

    Returns:
        bool: Normalized boolean availability status.
    """
    if val is None:
        return default

    # Booleans are subclasses of int in Python, so check bool before int
    if isinstance(val, bool):
        return val

    if isinstance(val, (int, float)):
        if val == 0:
            return False
        if val == 1:
            return True
        return bool(val > 0)

    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned in ("true", "1", "yes", "y", "in_stock", "available"):
            return True
        if cleaned in ("false", "0", "no", "n", "out_of_stock", "unavailable"):
            return False
        return default

    return default


_normalize_availability = normalize_availability


class SwiggyInstamartMcpProvider(BaseGroceryProvider):
    normalize_availability = staticmethod(normalize_availability)
    _normalize_availability = staticmethod(normalize_availability)
    """
    Official Swiggy Instamart MCP Server Provider Adapter.
    Connects to the official Swiggy Instamart Model Context Protocol (MCP) server
    endpoint (https://mcp.swiggy.com/im) via JSON-RPC 2.0 tool calls.
    Supports official product schemas (including nested variations),
    guest coordinate queries, and automatic OAuth 2.1 token refresh.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        default_address_id: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._default_address_id = default_address_id
        val_lat, val_lng = validate_coordinates(latitude, longitude)
        self._latitude = val_lat
        self._longitude = val_lng

    @property
    def provider_name(self) -> str:
        return "swiggy_instamart"

    def _get_access_token(self) -> Optional[str]:
        return (
            self._access_token
            or swiggy_token_storage.get_access_token()
            or (settings.SWIGGY_INSTAMART_ACCESS_TOKEN if is_valid_credential(settings.SWIGGY_INSTAMART_ACCESS_TOKEN) else None)
        )

    def _get_refresh_token(self) -> Optional[str]:
        return (
            self._refresh_token
            or swiggy_token_storage.get_refresh_token()
            or (settings.SWIGGY_INSTAMART_REFRESH_TOKEN if is_valid_credential(settings.SWIGGY_INSTAMART_REFRESH_TOKEN) else None)
        )

    @property
    def is_configured(self) -> bool:
        """
        Returns True if access token, refresh token, or valid client credentials are configured.
        """
        return bool(
            self._get_access_token()
            or self._get_refresh_token()
            or (
                is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_ID)
                and is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_SECRET)
            )
        )

    @property
    def is_available(self) -> bool:
        """
        Overridden from BaseGroceryProvider to reflect real configuration availability.
        """
        return self.is_configured

    async def refresh_access_token(self) -> Optional[str]:
        """
        Refresh the OAuth 2.1 access token using official OAuth manager or fallback.
        """
        new_token = await swiggy_oauth_manager.refresh_tokens()
        if new_token:
            self._access_token = new_token
            return new_token
        return await self._direct_refresh_access_token()

    async def _direct_refresh_access_token(self) -> Optional[str]:
        """
        Direct refresh fallback querying POST https://mcp.swiggy.com/auth/token.
        """
        refresh_tok = self._get_refresh_token()
        if not refresh_tok:
            return None

        auth_url = settings.SWIGGY_INSTAMART_AUTH_URL or "https://mcp.swiggy.com/auth/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
        }
        if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_ID):
            payload["client_id"] = settings.SWIGGY_INSTAMART_CLIENT_ID
        if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_SECRET):
            payload["client_secret"] = settings.SWIGGY_INSTAMART_CLIENT_SECRET

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    auth_url,
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    new_acc = data.get("access_token")
                    new_ref = data.get("refresh_token")
                    if new_acc:
                        self._access_token = new_acc
                    if new_ref:
                        self._refresh_token = new_ref
                    return new_acc
        except Exception:
            pass
        return None

    async def get_addresses(self) -> List[Dict[str, Any]]:
        """
        Fetch saved addresses from Swiggy Instamart via MCP get_addresses tool.
        Returns list of address dictionaries, or empty list if none exist.
        """
        url = settings.SWIGGY_INSTAMART_MCP_URL
        if not url or "dummy" in url.lower():
            url = "https://mcp.swiggy.com/im"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        access_tok = self._get_access_token()
        if access_tok:
            headers["Authorization"] = f"Bearer {access_tok}"

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_addresses", "arguments": {}},
            "id": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("result", {})
                    # Check structuredContent
                    sc = data.get("structuredContent")
                    if isinstance(sc, dict) and "addresses" in sc and isinstance(sc["addresses"], list):
                        return sc["addresses"]
                    # Check content text fallback
                    content = data.get("content", [])
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            try:
                                parsed = json.loads(c.get("text", "{}"))
                                if isinstance(parsed, list):
                                    return parsed
                                if isinstance(parsed, dict) and "addresses" in parsed:
                                    return parsed["addresses"]
                            except Exception:
                                pass
        except Exception:
            pass
        return []

    async def search_products(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address_id: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> List[NormalizedGroceryProduct]:
        """
        Asynchronously search products on Swiggy Instamart via MCP JSON-RPC call.
        Supports query, optional guest coordinates (latitude/longitude), or signed-in addressId.
        """
        if not self.is_configured:
            raise RuntimeError("Swiggy Instamart MCP is not configured. Access credentials missing.")

        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        url = settings.SWIGGY_INSTAMART_MCP_URL
        if not url or "dummy" in url.lower():
            url = "https://mcp.swiggy.com/im"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        access_tok = self._get_access_token()
        if access_tok:
            headers["Authorization"] = f"Bearer {access_tok}"

        # Resolve coordinates:
        # If coordinates are explicitly supplied to search_products, validate them
        has_explicit_coords = (latitude is not None or longitude is not None)
        if has_explicit_coords:
            val_lat, val_lng = validate_coordinates(latitude, longitude)
        else:
            # Fall back to provider instance or environment configuration
            cfg_lat = self._latitude if self._latitude is not None else settings.SWIGGY_INSTAMART_LATITUDE
            cfg_lng = self._longitude if self._longitude is not None else settings.SWIGGY_INSTAMART_LONGITUDE
            val_lat, val_lng = validate_coordinates(cfg_lat, cfg_lng)

        configured_addr = self._default_address_id or settings.SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID

        # Construct official MCP search_products tool arguments
        arguments: Dict[str, Any] = {"query": cleaned_query}

        # 1. If explicit address_id was passed and is valid, use it
        if address_id is not None and is_valid_credential(address_id):
            arguments["addressId"] = str(address_id)
        # 2. If explicit coordinates were passed, forward them in guest-mode
        elif has_explicit_coords and val_lat is not None and val_lng is not None:
            arguments["latitude"] = val_lat
            arguments["longitude"] = val_lng
        # 3. If valid saved address is configured, use it
        elif is_valid_credential(configured_addr):
            arguments["addressId"] = str(configured_addr)
        # 4. When no valid saved addressId is configured, forward configured coordinates
        elif val_lat is not None and val_lng is not None:
            arguments["latitude"] = val_lat
            arguments["longitude"] = val_lng

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_products",
                "arguments": arguments,
            },
            "id": 1,
        }

        client_timeout = timeout if timeout is not None else getattr(settings, "SWIGGY_INSTAMART_TIMEOUT_SECONDS", 4.0)

        try:
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

                # Handle 401 / 403 with token refresh retry
                if response.status_code in (401, 403):
                    new_token = await self.refresh_access_token()
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        response = await client.post(url, json=payload, headers=headers)

                if response.status_code in (401, 403):
                    raise RuntimeError(f"Swiggy Instamart authentication failed (HTTP {response.status_code}).")
                if response.status_code == 429:
                    raise RuntimeError("Swiggy Instamart rate limit exceeded (HTTP 429).")
                response.raise_for_status()

                resp_json = response.json()
                if "error" in resp_json:
                    error_info = resp_json["error"]
                    err_code = error_info.get("code")
                    err_msg = error_info.get("message") or "Unknown JSON-RPC error"

                    # -32001 is official MCP unauthorized / session expired
                    if err_code == -32001 or "unauthorized" in err_msg.lower():
                        new_token = await self.refresh_access_token()
                        if new_token:
                            headers["Authorization"] = f"Bearer {new_token}"
                            response = await client.post(url, json=payload, headers=headers)
                            resp_json = response.json()
                            if "error" in resp_json:
                                retry_err = resp_json["error"].get("message") or "Unknown error"
                                raise RuntimeError(f"Swiggy Instamart MCP returned tool error: {retry_err}")
                        else:
                            raise RuntimeError(f"Swiggy Instamart authentication failed: {err_msg}")
                    else:
                        raise RuntimeError(f"Swiggy Instamart MCP returned tool error: {err_msg}")

                result = resp_json.get("result", {})
                if isinstance(result, dict) and result.get("isError"):
                    err_msg = "Swiggy Instamart tool execution failed"
                    content = result.get("content", [])
                    if content and isinstance(content, list) and isinstance(content[0], dict):
                        text_val = content[0].get("text", "")
                        if text_val:
                            first_line = text_val.strip().splitlines()[0]
                            if "addressid is required" in first_line.lower():
                                err_msg = (
                                    "addressId is required. Swiggy Instamart requires a delivery location. "
                                    "The authenticated Swiggy account currently has 0 saved delivery addresses. "
                                    "Please add a delivery address to your Swiggy account or provide delivery coordinates."
                                )
                            elif "not found" in first_line.lower() and "address" in first_line.lower():
                                err_msg = f"Delivery address error: {first_line}"
                            else:
                                err_msg = first_line
                    raise RuntimeError(f"Swiggy Instamart search failed: {err_msg}")

                raw_products = self._extract_products_from_result(result)

                normalized_products: List[NormalizedGroceryProduct] = []
                for rp in raw_products:
                    if not isinstance(rp, dict):
                        continue

                    # If product contains nested variations (official schema)
                    variations = rp.get("variations")
                    if variations and isinstance(variations, list):
                        for var in variations:
                            if isinstance(var, dict):
                                normalized = self._normalize_variation(rp, var)
                                normalized_products.append(normalized)
                    else:
                        normalized = self._normalize_flat_product(rp)
                        normalized_products.append(normalized)

                return normalized_products

        except httpx.HTTPError as e:
            raise RuntimeError(f"Swiggy Instamart connection failure: {str(e)}")

    def _extract_products_from_result(self, result: Any) -> list:
        """
        Extract raw products list from various JSON-RPC result structures
        (structuredContent, content[0].text, result.products, result.data.products, or direct list).
        """
        if isinstance(result, list):
            return result
        if not isinstance(result, dict):
            return []

        # Check structuredContent directly (official MCP structured return)
        if "structuredContent" in result and isinstance(result["structuredContent"], dict):
            found = self._find_products_in_dict(result["structuredContent"])
            if found is not None:
                return found

        # MCP content block wrapper
        if "content" in result and isinstance(result["content"], list):
            for item in result["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        text_data = json.loads(item.get("text", "{}"))
                        found = self._find_products_in_dict(text_data)
                        if found is not None:
                            return found
                    except Exception:
                        pass

        found = self._find_products_in_dict(result)
        return found if found is not None else []

    def _find_products_in_dict(self, data: Any) -> Optional[list]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("products", "items", "searchResults", "variations"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            if "data" in data and isinstance(data["data"], dict):
                inner_data = data["data"]
                for key in ("products", "items", "searchResults", "variations"):
                    if key in inner_data and isinstance(inner_data[key], list):
                        return inner_data[key]
        return None

    def _parse_quantity_unit(self, size_str: Optional[str]) -> Tuple[float, str]:
        """
        Parse package sizes such as '200 g', '200 g x 2',
        and '2 x 200 g' into total quantity and unit.
        """
        if size_str is None or not str(size_str).strip():
            return 1.0, "pack"

        clean = str(size_str).strip().lower()
        clean = clean.replace("?", "x").replace("?", "x")
        clean = re.sub(r"\s+", " ", clean)

        patterns = (
            r"^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s*x\s*(\d+(?:\.\d+)?)$",
            r"^(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$",
        )

        try:
            match = re.match(patterns[0], clean)
            if match:
                quantity = float(match.group(1)) * float(match.group(3))
                unit = match.group(2)
                return (quantity, unit) if quantity > 0 else (1.0, "pack")

            match = re.match(patterns[1], clean)
            if match:
                quantity = float(match.group(1)) * float(match.group(2))
                unit = match.group(3)
                return (quantity, unit) if quantity > 0 else (1.0, "pack")

            match = re.match(r"^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$", clean)
            if match:
                quantity = float(match.group(1))
                unit = match.group(2)
                return (quantity, unit) if quantity > 0 else (1.0, "pack")

        except (ValueError, OverflowError):
            pass

        return 1.0, clean

    def _normalize_variation(self, prod: dict, var: dict) -> NormalizedGroceryProduct:
        """
        Normalize an official nested variation item from Swiggy Instamart search results.
        """
        pid = str(var.get("spinId") or var.get("skuId") or prod.get("productId") or prod.get("id") or "")
        name = str(var.get("displayName") or prod.get("displayName") or prod.get("name") or "")
        brand = var.get("brandName") or prod.get("brand") or "Generic"
        category = prod.get("category") or "Uncategorized"
        store_name = prod.get("store_name") or prod.get("storeName") or "Swiggy Instamart"

        # Price parsing: variation price can be dict {mrp, offerPrice, unitLevelPrice} or scalar
        price_obj = var.get("price")
        if isinstance(price_obj, dict):
            offer_price = price_obj.get("offerPrice")
            mrp = price_obj.get("mrp")
        else:
            offer_price = var.get("offerPrice") or price_obj or var.get("price")
            mrp = var.get("mrp") or offer_price

        price_val = float(offer_price) if offer_price is not None else (float(mrp) if mrp is not None else None)
        mrp_val = float(mrp) if mrp is not None else price_val
        discount_val = (
            (mrp_val - price_val)
            if (mrp_val is not None and price_val is not None and mrp_val > price_val)
            else None
        )

        raw_avail = None
        for key in ("isInStockAndAvailable", "inStock", "isAvailable", "available"):
            val = var.get(key)
            if val is not None:
                raw_avail = val
                break

        if raw_avail is None:
            for key in ("isInStockAndAvailable", "inStock", "in_stock", "isAvailable", "isAvail", "available"):
                val = prod.get(key)
                if val is not None:
                    raw_avail = val
                    break

        availability = normalize_availability(raw_avail, default=True)

        size_str = (
            var.get("quantityDescription")
            or var.get("packageSize")
            or var.get("size")
            or prod.get("packageSize")
        )
        qty, unit = self._parse_quantity_unit(size_str)

        images = var.get("images") or prod.get("images")
        product_url = (
            var.get("productUrl")
            or prod.get("productUrl")
            or (images[0] if (images and isinstance(images, list)) else None)
        )

        location_val = (
            prod.get("location")
            or prod.get("serviceability")
            or settings.SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID
            or "default_address"
        )

        return NormalizedGroceryProduct(
            source_platform="Swiggy Instamart",
            source_product_id=pid,
            store_name=store_name,
            product_name=name,
            brand=brand,
            category=category,
            package_quantity=qty,
            package_unit=unit,
            price=price_val,
            mrp=mrp_val,
            discount=discount_val,
            currency="INR",
            availability=availability,
            location=location_val,
            product_url=product_url,
            retrieved_at=datetime.now(timezone.utc),
            price_freshness="PROVIDER_LIVE",
        )

    def _normalize_flat_product(self, rp: dict) -> NormalizedGroceryProduct:
        """
        Normalize legacy or flat Swiggy product dictionary into NormalizedGroceryProduct.
        """
        pid = str(rp.get("spinId") or rp.get("productId") or rp.get("product_id") or rp.get("id") or "")
        name = str(rp.get("name") or rp.get("product_name") or rp.get("productName") or rp.get("displayName") or "")
        brand = rp.get("brand") or rp.get("brandName") or "Generic"
        category = rp.get("category") or "Uncategorized"

        price_obj = rp.get("price")
        if isinstance(price_obj, dict):
            price_val = price_obj.get("offerPrice") or price_obj.get("price") or price_obj.get("mrp")
            mrp_val = price_obj.get("mrp") or price_val
        else:
            price_val = rp.get("offerPrice") or rp.get("price") or rp.get("mrp")
            mrp_val = rp.get("mrp") or rp.get("originalPrice") or price_val

        discount_val = None
        if mrp_val and price_val and float(mrp_val) > float(price_val):
            discount_val = float(mrp_val) - float(price_val)

        location_val = (
            rp.get("location")
            or rp.get("serviceability")
            or settings.SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID
            or "default_address"
        )

        raw_avail = None
        for key in ("isInStockAndAvailable", "inStock", "in_stock", "isAvailable", "isAvail", "available"):
            val = rp.get(key)
            if val is not None:
                raw_avail = val
                break

        availability = normalize_availability(raw_avail, default=True)

        size_str = (
            rp.get("quantityDescription")
            or rp.get("packageSize")
            or rp.get("package_size")
            or rp.get("quantity")
            or rp.get("size")
        )
        qty, unit = self._parse_quantity_unit(size_str)

        images = rp.get("images")
        product_url = (
            rp.get("product_url")
            or rp.get("productUrl")
            or (images[0] if (images and isinstance(images, list)) else None)
        )

        return NormalizedGroceryProduct(
            source_platform="Swiggy Instamart",
            source_product_id=pid,
            store_name=rp.get("store_name") or rp.get("storeName") or "Swiggy Instamart Store",
            product_name=name,
            brand=brand,
            category=category,
            package_quantity=qty,
            package_unit=unit,
            price=float(price_val) if price_val is not None else None,
            mrp=float(mrp_val) if mrp_val is not None else None,
            discount=float(discount_val) if discount_val is not None else None,
            currency="INR",
            availability=availability,
            location=location_val,
            product_url=product_url,
            retrieved_at=datetime.now(timezone.utc),
            price_freshness="PROVIDER_LIVE",
        )

    async def get_product_details(self, product_id: str) -> Optional[NormalizedGroceryProduct]:
        """
        Asynchronously retrieve detailed product information.
        """
        return None

    async def get_current_price(self, product_id: str) -> Optional[float]:
        """
        Asynchronously retrieve real-time price updates for a product.
        """
        return None
