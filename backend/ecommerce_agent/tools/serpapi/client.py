"""Thin SerpAPI HTTP client (transport for all engine adapters)."""
from __future__ import annotations

from typing import Any

import httpx


class SerpAPIError(RuntimeError):
    """SerpAPI returned an error.

    Deliberately built without the request URL: httpx error messages embed the
    full query string, which would leak ``api_key`` into logs and the database.
    """


class SerpAPIClient:
    """Minimal SerpAPI client. Uses httpx so it is easy to mock."""

    BASE_URL = "https://serpapi.com/search.json"
    _MAX_DETAIL = 300

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    def search(self, engine: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET the given engine with ``params`` (already engine-shaped)."""
        request_params = {"engine": engine, "api_key": self._api_key, **params}
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(self.BASE_URL, params=request_params)

        if response.status_code != 200:
            raise SerpAPIError(
                f"{engine} returned HTTP {response.status_code}: {self._detail(response)}"
            )
        return response.json()

    def _detail(self, response: httpx.Response) -> str:
        """Extract SerpAPI's ``error`` field, scrubbed and truncated."""
        detail = ""
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            detail = str(payload.get("error") or "")
        if not detail:
            detail = response.text or response.reason_phrase
        return self._scrub(detail)[: self._MAX_DETAIL]

    def _scrub(self, text: str) -> str:
        # Very short keys would mangle unrelated words, so only mask real ones.
        if len(self._api_key) >= 8 and self._api_key in text:
            return text.replace(self._api_key, "***")
        return text

