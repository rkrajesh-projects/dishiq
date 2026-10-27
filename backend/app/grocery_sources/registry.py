import asyncio
import time
from typing import Dict, List, Tuple, Any, Optional
from app.core.config import settings
from app.grocery_sources.base_provider import BaseGroceryProvider
from app.grocery_sources.models import NormalizedGroceryProduct

# Module-level standing cache shared across provider registry instances
_PROVIDER_CACHE: Dict[str, Dict[str, Any]] = {}


def clear_grocery_cache() -> None:
    """Clear all in-memory grocery provider cache entries."""
    global _PROVIDER_CACHE
    _PROVIDER_CACHE.clear()


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

    def clear_cache(self) -> None:
        """Clear cache entries for this registry."""
        clear_grocery_cache()

    async def search_all_providers(
        self,
        query: str,
        timeout: float = 5.0,
        force_refresh: bool = False,
    ) -> Tuple[List[NormalizedGroceryProduct], Dict[str, str]]:
        """
        Query all registered providers in parallel.
        If any provider fails or times out, it is isolated and reported as failed,
        allowing successful providers' results to be combined and returned.

        Caching lifecycle:
        - Fresh hits (age <= GROCERY_CACHE_TTL_SECONDS) return cached results with
          price_freshness='CACHED' for live items, unless force_refresh=True.
        - force_refresh=True bypasses the fresh-cache shortcut and attempts providers.
        - On provider failure/timeout, stale cache entries (age <= GROCERY_CACHE_STALE_TTL_SECONDS)
          are returned as fallback with an explanatory warning.
        - Very old entries (> GROCERY_CACHE_STALE_TTL_SECONDS) are automatically purged.
        """
        global _PROVIDER_CACHE
        current_time = time.time()
        ttl = getattr(settings, "GROCERY_CACHE_TTL_SECONDS", 300)
        stale_ttl = getattr(settings, "GROCERY_CACHE_STALE_TTL_SECONDS", 1800)

        # 1. Purge expired stale entries
        expired_keys = [
            k for k, v in _PROVIDER_CACHE.items()
            if (current_time - v.get("timestamp", 0)) > stale_ttl
        ]
        for k in expired_keys:
            _PROVIDER_CACHE.pop(k, None)

        provider_keys = "-".join(sorted(self._providers.keys()))
        clean_query = (query or "").lower().strip()
        cache_key = f"{provider_keys}:{clean_query}"

        # 2. Check for fresh cache hit unless a fresh provider search is requested
        if not force_refresh and cache_key in _PROVIDER_CACHE:
            entry = _PROVIDER_CACHE[cache_key]
            age = current_time - entry.get("timestamp", 0)
            if age <= ttl:
                cached_results: List[NormalizedGroceryProduct] = []
                for item in entry.get("results", []):
                    cloned = item.model_copy()
                    if cloned.price_freshness == "PROVIDER_LIVE":
                        cloned.price_freshness = "CACHED"
                    cached_results.append(cloned)
                return cached_results, dict(entry.get("failures", {}))

        results: List[NormalizedGroceryProduct] = []
        failures: Dict[str, str] = {}

        if not self._providers:
            return results, failures

        provider_names = []
        tasks = []

        for name in list(self._providers.keys()):
            provider = self._providers[name]
            if not provider.is_available:
                continue
            provider_names.append(name)
            tasks.append(
                asyncio.wait_for(provider.search_products(query), timeout=timeout)
            )

        if not tasks:
            return results, failures

        # Gather results with return_exceptions=True to ensure errors are isolated
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        for name, outcome in zip(provider_names, outcomes):
            if isinstance(outcome, Exception):
                failures[name] = f"{type(outcome).__name__}: {str(outcome)}"
            else:
                results.extend(outcome)

        # 3. Handle outcome and fallback
        if results:
            # Store freshly retrieved results in cache
            _PROVIDER_CACHE[cache_key] = {
                "results": [item.model_copy() for item in results],
                "failures": failures,
                "timestamp": current_time,
            }
            return results, failures

        # 4. If all providers failed or returned nothing, check stale cache fallback
        if failures and cache_key in _PROVIDER_CACHE:
            entry = _PROVIDER_CACHE[cache_key]
            stale_results: List[NormalizedGroceryProduct] = []
            for item in entry.get("results", []):
                cloned = item.model_copy()
                if cloned.price_freshness == "PROVIDER_LIVE":
                    cloned.price_freshness = "CACHED"
                stale_results.append(cloned)

            fallback_failures = dict(failures)
            fallback_failures["_cache"] = "Returned stale cached data due to provider error"
            return stale_results, fallback_failures

        return results, failures


# Standing global registry instance
registry = GroceryProviderRegistry()
