"""SerpAPI engine adapter (Adapter + Template Method patterns)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .client import SerpAPIClient


class SerpAPIEngineAdapter(ABC):
    """Adapter for a single SerpAPI engine (google_shopping, amazon, ebay, walmart).

    Subclasses declare ``engine`` and ``query_param`` and implement
    :meth:`normalize`; :meth:`search` is the template method that builds the
    engine-specific request and normalizes the response. Every SerpAPI engine
    names its query parameter differently, so this cannot be hardcoded.
    """

    engine: str
    query_param: str

    def __init__(self, client: SerpAPIClient) -> None:
        self._client = client

    def search(
        self, query: str, num: int | None = None, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Return a normalized list of product dicts."""
        params: dict[str, Any] = {self.query_param: query, **kwargs}
        if num is not None:
            params["num"] = num
        raw = self._client.search(self.engine, params)
        return self.normalize(raw)

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Map a raw SerpAPI payload to the shared product contract."""
