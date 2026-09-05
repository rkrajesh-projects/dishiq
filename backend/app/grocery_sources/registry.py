import asyncio
from typing import Dict, List, Tuple
from app.grocery_sources.base_provider import BaseGroceryProvider
from app.grocery_sources.models import NormalizedGroceryProduct

class GroceryProviderRegistry:
    """
    Registry management class for registering, unregistering, and searching
    multiple grocery providers in a thread-safe and isolated manner.
    """

    def __init__(self):
        self._providers: Dict[str, BaseGroceryProvider] = {}

    def register(self, provider: BaseGroceryProvider) -> None:
        """Register a new grocery data provider."""
        self._providers[provider.provider_name] = provider

    def unregister(self, provider_name: str) -> None:
        """Unregister an existing grocery data provider by name."""
        self._providers.pop(provider_name, None)

    def get_provider(self, provider_name: str) -> BaseGroceryProvider:
        """Retrieve a registered provider by name, raising ValueError if not found."""
        if provider_name not in self._providers:
            raise ValueError(f"Grocery provider '{provider_name}' is not registered.")
        return self._providers[provider_name]

    def list_providers(self) -> List[str]:
        """List the names of all registered providers."""
        return list(self._providers.keys())

    async def search_all_providers(
        self, query: str, timeout: float = 5.0
    ) -> Tuple[List[NormalizedGroceryProduct], Dict[str, str]]:
        """
        Query all registered providers in parallel.
        If any provider fails or times out, it is isolated and reported as failed,
        allowing successful providers' results to be combined and returned.
        """
        results: List[NormalizedGroceryProduct] = []
        failures: Dict[str, str] = {}

        if not self._providers:
            return results, failures

        provider_names = list(self._providers.keys())
        tasks = []

        for name in provider_names:
            provider = self._providers[name]
            tasks.append(
                asyncio.wait_for(provider.search_products(query), timeout=timeout)
            )

        # Gather results with return_exceptions=True to ensure errors are isolated
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        for name, outcome in zip(provider_names, outcomes):
            if isinstance(outcome, Exception):
                failures[name] = f"{type(outcome).__name__}: {str(outcome)}"
            else:
                results.extend(outcome)

        return results, failures

# Standing global registry instance
registry = GroceryProviderRegistry()
