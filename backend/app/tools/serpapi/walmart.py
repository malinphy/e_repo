"""Walmart SerpAPI engine adapter."""
from __future__ import annotations

from typing import Any, Dict, List
from ...schemas.product import Product
from .base import BaseEngineAdapter


class WalmartAdapter(BaseEngineAdapter):
    """Adapter for Walmart marketplace search via SerpAPI."""

    engine_name = "walmart"
    query_param_name = "query"

    def parse_response(self, raw_data: Dict[str, Any]) -> List[Product]:
        products: List[Product] = []
        items = raw_data.get("organic_results") or []

        for item in items:
            title = item.get("title")
            if not title:
                continue

            item_id = str(item.get("us_item_id") or item.get("product_id") or abs(hash(title)))
            primary_offer = item.get("primary_offer") or {}
            raw_price = primary_offer.get("offer_price") or item.get("price")
            price = self.extract_price(raw_price)

            rating = self.extract_rating(item.get("rating"))
            reviews = item.get("reviews") if isinstance(item.get("reviews"), int) else None

            url = item.get("product_page_url") or item.get("link") or f"https://www.walmart.com/ip/{item_id}"
            image = item.get("thumbnail") or item.get("image")
            snippet = item.get("description")

            products.append(
                Product(
                    id=f"walmart_{item_id}",
                    title=title,
                    price=price,
                    currency="USD",
                    source="walmart",
                    url=url,
                    rating=rating,
                    reviews_count=reviews,
                    image=image,
                    snippet=snippet,
                )
            )

        return products
