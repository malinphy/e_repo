"""serp_fetch node: fetches marketplace results concurrently with cache checking."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List
from ....services.cache_service import ProductCacheService
from ....tools.serpapi import get_all_adapters
from ....schemas.product import Product
from .state import SearchSubgraphState

logger = logging.getLogger(__name__)


async def _fetch_single_engine(
    engine: str,
    keywords: str,
    adapter: Any,
) -> List[Product]:
    """Check cache first; on miss, call SerpAPI adapter and populate cache."""
    # 1. Cache lookup
    cached = ProductCacheService.get(keywords, engine)
    if cached is not None:
        return cached

    # 2. SerpAPI call
    try:
        results = await adapter.search(keywords, num=10)
        if results:
            ProductCacheService.set(keywords, engine, results)
        return results
    except Exception as exc:
        logger.error("Error fetching from %s: %s", engine, exc)
        return []


async def serp_fetch_node(state: SearchSubgraphState) -> Dict[str, Any]:
    """Executes parallel searches across target marketplaces with cache optimization."""
    search_query = state.get("search_query") or {}
    keywords = search_query.get("keywords", "").strip()
    target_engines = search_query.get("marketplaces") or ["walmart", "ebay", "amazon", "google_shopping"]

    if not keywords:
        return {"raw_products": []}

    adapters = get_all_adapters()
    tasks = []

    for engine in target_engines:
        adapter = adapters.get(engine)
        if adapter:
            tasks.append(_fetch_single_engine(engine, keywords, adapter))

    # Parallel execution across all marketplaces
    results_per_engine = await asyncio.gather(*tasks, return_exceptions=True)

    all_products: List[Dict[str, Any]] = []
    for res in results_per_engine:
        if isinstance(res, list):
            for prod in res:
                all_products.append(prod.model_dump() if hasattr(prod, "model_dump") else prod)
        elif isinstance(res, Exception):
            logger.warning("Marketplace search task exception: %s", res)

    return {"raw_products": all_products}
