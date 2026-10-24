"""SerpAPI marketplace adapters registry and factory."""
from __future__ import annotations

from typing import Dict
from .base import BaseEngineAdapter
from .client import SerpAPIClient
from .walmart import WalmartAdapter
from .ebay import EbayAdapter
from .amazon import AmazonAdapter
from .google_shopping import GoogleShoppingAdapter


def get_all_adapters(client: SerpAPIClient | None = None) -> Dict[str, BaseEngineAdapter]:
    """Returns initialized mapping of all marketplace adapters."""
    shared_client = client or SerpAPIClient()
    return {
        "walmart": WalmartAdapter(client=shared_client),
        "ebay": EbayAdapter(client=shared_client),
        "amazon": AmazonAdapter(client=shared_client),
        "google_shopping": GoogleShoppingAdapter(client=shared_client),
    }


__all__ = [
    "BaseEngineAdapter",
    "SerpAPIClient",
    "WalmartAdapter",
    "EbayAdapter",
    "AmazonAdapter",
    "GoogleShoppingAdapter",
    "get_all_adapters",
]
