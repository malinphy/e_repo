"""HTTP client for SerpAPI requests with timeout and error handling."""
from __future__ import annotations

import logging
from typing import Any, Dict
import httpx

from ...core.config import get_settings

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"
DEFAULT_TIMEOUT = 15.0


class SerpAPIClient:
    """Async client for SerpAPI marketplace queries."""

    def __init__(self, api_key: str | None = None, timeout: float = DEFAULT_TIMEOUT):
        settings = get_settings()
        self.api_key = api_key or settings.SERPAPI_API_KEY
        self.timeout = timeout

    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send GET query to SerpAPI.

        Args:
            params: Parameters including engine, query, etc.

        Returns:
            Parsed JSON dictionary from SerpAPI.
        """
        request_params = {**params}
        if self.api_key:
            request_params["api_key"] = self.api_key

        engine = request_params.get("engine", "unknown")
        query = request_params.get("query") or request_params.get("q") or ""

        logger.info("Calling SerpAPI [engine=%s, query='%s']", engine, query)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(SERPAPI_URL, params=request_params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                logger.error("SerpAPI HTTP error %s: %s", exc.response.status_code, exc.response.text)
                return {"error": f"HTTP {exc.response.status_code}: {exc.response.text}"}
            except httpx.RequestError as exc:
                logger.error("SerpAPI request error: %s", exc)
                return {"error": f"Request failed: {exc}"}
            except Exception as exc:
                logger.exception("Unexpected error during SerpAPI call: %s", exc)
                return {"error": str(exc)}
