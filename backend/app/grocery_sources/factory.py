from typing import List, Optional
from sqlalchemy.orm import Session
from app.grocery_sources.base_provider import BaseGroceryProvider
from app.grocery_sources.demo_provider import DemoGroceryProvider
from app.grocery_sources.quickcommerce_provider import BlinkitProvider, ZeptoProvider
from app.grocery_sources.swiggy_instamart_provider import SwiggyInstamartMcpProvider
from app.core.config import settings

def get_configured_providers(
    db: Session,
    live_mode: bool = False,
    pincode: Optional[str] = None
) -> List[BaseGroceryProvider]:
    """
    Factory function to instantiate and return all active/configured providers
    based on application settings and request parameters.
    """
    providers: List[BaseGroceryProvider] = []
    
    # 1. Demo Provider
    if not live_mode:
        providers.append(DemoGroceryProvider(db))
        return providers
        

    # 2. Swiggy Instamart (MCP) - Legitimate authorized integration (Phase D)
    swiggy_provider = SwiggyInstamartMcpProvider()
    if getattr(swiggy_provider, "is_configured", False) or getattr(swiggy_provider, "is_available", False):
        providers.append(swiggy_provider)
        
    # Phase 23: Blinkit and Zepto Integrations
    blinkit = BlinkitProvider()
    if blinkit.is_available:
        providers.append(blinkit)
        
    zepto = ZeptoProvider()
    if zepto.is_available:
        providers.append(zepto)

            
    return providers
