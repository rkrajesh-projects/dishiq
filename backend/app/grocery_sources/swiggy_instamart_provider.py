import re
import json
import httpx
from datetime import datetime, timezone
from typing import List, Optional
from app.grocery_sources.base_provider import BaseGroceryProvider
from app.grocery_sources.models import NormalizedGroceryProduct
from app.core.config import settings

class SwiggyInstamartMcpProvider(BaseGroceryProvider):
    """
    Real-time grocery provider adapter connecting to the official Swiggy Instamart MCP Server.
    Uses standard JSON-RPC 2.0 requests to query tools like 'search_products' over SSE/HTTP.
    """

    @property
    def provider_name(self) -> str:
        return "swiggy_instamart"

    @property
    def is_configured(self) -> bool:
        """
        Returns True if required credentials or access tokens are present in application settings.
        """
        return bool(
            (settings.SWIGGY_INSTAMART_CLIENT_ID and settings.SWIGGY_INSTAMART_CLIENT_SECRET)
            or settings.SWIGGY_INSTAMART_ACCESS_TOKEN
        )

    async def search_products(self, query: str) -> List[NormalizedGroceryProduct]:
        """
        Asynchronously search products on Swiggy Instamart via MCP JSON-RPC call.
        """
        if not self.is_configured:
            raise RuntimeError("Swiggy Instamart MCP is not configured. Access credentials missing.")

        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        url = settings.SWIGGY_INSTAMART_MCP_URL or "https://mcp.swiggy.com/im"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if settings.SWIGGY_INSTAMART_ACCESS_TOKEN:
            headers["Authorization"] = f"Bearer {settings.SWIGGY_INSTAMART_ACCESS_TOKEN}"

        # standard JSON-RPC 2.0 payload to invoke MCP search tool
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_products",
                "arguments": {
                    "query": cleaned_query,
                    "addressId": settings.SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID or "default_address"
                }
            },
            "id": 1
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code in (401, 403):
                    raise RuntimeError(f"Swiggy Instamart authentication failed (HTTP {response.status_code}).")
                response.raise_for_status()

                resp_json = response.json()
                if "error" in resp_json:
                    err_msg = resp_json["error"].get("message") or "Unknown JSON-RPC error"
                    raise RuntimeError(f"Swiggy Instamart MCP returned tool error: {err_msg}")

                result = resp_json.get("result", {})
                raw_products = []

                # Parse the response payload
                if "content" in result and isinstance(result["content"], list):
                    for item in result["content"]:
                        if item.get("type") == "text":
                            try:
                                text_data = json.loads(item.get("text", "{}"))
                                if "products" in text_data:
                                    raw_products = text_data["products"]
                                elif isinstance(text_data, list):
                                    raw_products = text_data
                            except Exception:
                                pass
                elif "products" in result:
                    raw_products = result["products"]
                elif isinstance(result, list):
                    raw_products = result

                normalized_products: List[NormalizedGroceryProduct] = []
                for rp in raw_products:
                    if isinstance(rp, dict):
                        normalized_products.append(self._normalize_mcp_product(rp))

                return normalized_products

        except httpx.HTTPError as e:
            raise RuntimeError(f"Swiggy Instamart connection failure: {str(e)}")

    async def get_product_details(self, product_id: str) -> Optional[NormalizedGroceryProduct]:
        """
        Asynchronously retrieve detailed product information (placeholder / future support).
        """
        return None

    async def get_current_price(self, product_id: str) -> Optional[float]:
        """
        Asynchronously retrieve real-time price updates for a product (placeholder / future support).
        """
        return None

    def _normalize_mcp_product(self, rp: dict) -> NormalizedGroceryProduct:
        """
        Normalize raw Swiggy Instamart product dictionary properties into a standard Pydantic model.
        """
        pid = str(rp.get("spinId") or rp.get("productId") or rp.get("product_id") or rp.get("id") or "")
        name = str(rp.get("name") or rp.get("product_name") or rp.get("productName") or "")
        brand = rp.get("brand") or "Generic"
        category = rp.get("category") or "Uncategorized"

        price_val = rp.get("offerPrice") or rp.get("price") or rp.get("mrp")
        availability = rp.get("inStock") or rp.get("in_stock") or rp.get("available")
        if availability is None:
            availability = True

        size_str = rp.get("packageSize") or rp.get("package_size") or rp.get("quantity") or rp.get("size")
        qty = 1.0
        unit = "pack"
        if size_str:
            size_str = str(size_str).strip()
            match = re.match(r"^([\d\.]+)\s*([a-zA-Z\s]+)$", size_str)
            if match:
                try:
                    qty = float(match.group(1))
                    unit = match.group(2).strip()
                except ValueError:
                    pass
            else:
                unit = size_str

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
            currency="INR",
            availability=bool(availability),
            product_url=rp.get("product_url") or rp.get("productUrl"),
            retrieved_at=datetime.now(timezone.utc),
            price_freshness="LIVE"
        )
