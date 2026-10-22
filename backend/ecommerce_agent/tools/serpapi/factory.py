"""SerpAPI engine factory (Factory pattern)."""
from __future__ import annotations

from .base import SerpAPIEngineAdapter
from .client import SerpAPIClient
from .engines import AmazonAdapter, EbayAdapter, GoogleShoppingAdapter, WalmartAdapter


_ENGINES: dict[str, type[SerpAPIEngineAdapter]] = {
    "google_shopping": GoogleShoppingAdapter,
    "amazon": AmazonAdapter,
    "ebay": EbayAdapter,
    "walmart": WalmartAdapter,
}


def build_engine(name: str, client: SerpAPIClient) -> SerpAPIEngineAdapter:
    cls = _ENGINES[name]
    return cls(client)


def available_engines() -> list[str]:
    return sorted(_ENGINES.keys())


def build_all_engines(api_key: str) -> dict[str, SerpAPIEngineAdapter]:
    client = SerpAPIClient(api_key=api_key)
    return {name: build_engine(name, client) for name in available_engines()}
