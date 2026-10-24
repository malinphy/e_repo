"""Base class and common parsing utilities for SerpAPI engine adapters."""
from __future__ import annotations

import abc
import re
from typing import Any, List, Optional
from ...schemas.product import Product
from .client import SerpAPIClient

_PRICE_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)")


class BaseEngineAdapter(abc.ABC):
    """Abstract base class for a marketplace search adapter."""

    engine_name: str
    query_param_name: str = "q"

    def __init__(self, client: SerpAPIClient | None = None):
        self.client = client or SerpAPIClient()

    @staticmethod
    def extract_price(raw: Any) -> float:
        """Extract float price from strings like '$49.99', '1.250,00 TL', or raw numbers."""
        if raw is None:
            return 0.0
        if isinstance(raw, (int, float)):
            return float(raw)
        raw_str = str(raw).replace(",", "")
        match = _PRICE_PATTERN.search(raw_str)
        return float(match.group(1)) if match else 0.0

    @staticmethod
    def extract_rating(raw: Any) -> Optional[float]:
        """Extract float rating from strings or numbers."""
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        match = _PRICE_PATTERN.search(str(raw))
        return float(match.group(1)) if match else None

    @abc.abstractmethod
    def parse_response(self, raw_data: dict) -> List[Product]:
        """Convert engine-specific JSON response into a list of normalized Product objects."""
        raise NotImplementedError

    async def search(self, query: str, num: int = 10, **kwargs) -> List[Product]:
        """Execute search on the marketplace engine and return normalized products."""
        params = {
            "engine": self.engine_name,
            self.query_param_name: query,
            "num": num,
            **kwargs,
        }
        data = await self.client.fetch(params)
        if "error" in data:
            return []
        return self.parse_response(data)
