import abc
from typing import List, Optional
from app.grocery_sources.models import NormalizedGroceryProduct

class BaseGroceryProvider(abc.ABC):
    """
    Abstract Base Class for all external real-time grocery platforms or
    internal seed database adapters.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """
        Return the unique identifier code for this provider (e.g. 'quickmart', 'demo').
        """
        pass

    @property
    def is_available(self) -> bool:
        """
        Return whether this provider is correctly configured and available for use.
        Defaults to True unless overridden.
        """
        return True

    @abc.abstractmethod
    async def search_products(self, query: str) -> List[NormalizedGroceryProduct]:
        """
        Asynchronously search products on the platform and return them in a
        normalized representation.
        """
        pass

    @abc.abstractmethod
    async def get_product_details(self, product_id: str) -> Optional[NormalizedGroceryProduct]:
        """
        Asynchronously retrieve detailed product information for a single product ID.
        """
        pass

    @abc.abstractmethod
    async def get_current_price(self, product_id: str) -> Optional[float]:
        """
        Asynchronously check the current price of a single product in real-time.
        """
        pass
