"""Concrete SerpAPI engine adapters.

Every engine uses a different query parameter and returns a different result
shape. Verified against live SerpAPI responses:

================= =========== ================== =============================
engine            query param result container   price shape
================= =========== ================== =============================
google_shopping   q           shopping_results   ``"price": "$19.99"``
amazon            k           organic_results    ``"price": "$68.97"``
ebay              _nkw        organic_results    ``{"raw", "extracted"}``
walmart           query       organic_results    ``primary_offer.offer_price``
================= =========== ================== =============================
"""
from __future__ import annotations

import html
from typing import Any

from .base import SerpAPIEngineAdapter


def _price_text(value: Any) -> str | None:
    """Coerce SerpAPI's mixed price shapes into a display string."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    if isinstance(value, dict):
        for key in ("raw", "offer_price", "extracted"):
            if key in value:
                return _price_text(value[key])
    return None


def _spread(
    entries: Any, source: str, source_field: str | None = None, **field_map: str
) -> list[dict[str, Any]]:
    """Map ``role=payload_field`` pairs onto the shared product contract.

    ``source`` falls back to the engine name, but keeps the merchant name when
    the payload exposes one (e.g. Google Shopping's ``source``).
    """
    items: list[dict[str, Any]] = []
    for entry in entries or []:
        item: dict[str, Any] = {
            role: entry.get(field) for role, field in field_map.items()
        }
        item["source"] = (entry.get(source_field) if source_field else None) or source
        for role in ("title", "price", "link", "rating", "reviews"):
            item.setdefault(role, None)
        if isinstance(item["title"], str):
            item["title"] = html.unescape(item["title"])
        item["price"] = _price_text(item["price"])
        items.append(item)
    return items


def normalize_shopping(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return _spread(
        raw.get("shopping_results"),
        "google_shopping",
        source_field="source",
        title="title",
        price="price",
        link="link",
        rating="rating",
        reviews="reviews",
    )


def normalize_amazon(raw: dict[str, Any]) -> list[dict[str, Any]]:
    entries = raw.get("organic_results")
    items = _spread(
        entries,
        "amazon",
        title="title",
        price="price",
        link="link",
        rating="rating",
        reviews="reviews",
    )
    for item, entry in zip(items, entries or []):
        # Some listings ship only the numeric price / a cleaned link.
        item["price"] = item["price"] or _price_text(entry.get("extracted_price"))
        item["link"] = item["link"] or entry.get("link_clean")
    return items


def normalize_ebay(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return _spread(
        raw.get("organic_results"),
        "ebay",
        title="title",
        price="price",
        link="link",
        rating="rating",
        reviews="reviews",
    )


def normalize_walmart(raw: dict[str, Any]) -> list[dict[str, Any]]:
    entries = raw.get("organic_results")
    items = _spread(
        entries,
        "walmart",
        source_field="seller_name",
        title="title",
        link="product_page_url",
        rating="rating",
        reviews="reviews",
    )
    for item, entry in zip(items, entries or []):
        item["price"] = _price_text(entry.get("primary_offer") or entry.get("price"))
    return items


class GoogleShoppingAdapter(SerpAPIEngineAdapter):
    engine = "google_shopping"
    query_param = "q"

    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        return normalize_shopping(raw)


class AmazonAdapter(SerpAPIEngineAdapter):
    engine = "amazon"
    query_param = "k"

    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        return normalize_amazon(raw)


class EbayAdapter(SerpAPIEngineAdapter):
    engine = "ebay"
    query_param = "_nkw"

    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        return normalize_ebay(raw)


class WalmartAdapter(SerpAPIEngineAdapter):
    engine = "walmart"
    query_param = "query"

    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        return normalize_walmart(raw)
