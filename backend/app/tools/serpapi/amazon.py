"""Amazon SerpAPI engine adapter."""
from __future__ import annotations

from typing import Any, Dict, List
from ...schemas.product import Product
from .base import BaseEngineAdapter


class AmazonAdapter(BaseEngineAdapter):
    """Adapter for Amazon search via SerpAPI."""

    engine_name = "amazon"
    query_param_name = "k"

    def parse_response(self, raw_data: Dict[str, Any]) -> List[Product]:
        products: List[Product] = []
        items = raw_data.get("organic_results") or []

        for item in items:
            title = item.get("title")
            if not title:
                continue

            asin = str(item.get("asin") or abs(hash(title)))

            price_info = item.get("price") or {}
            raw_price = price_info.get("extracted") if isinstance(price_info, dict) else price_info
            if not raw_price:
                raw_price = item.get("raw_price") or item.get("price")
            price = self.extract_price(raw_price)

            rating = self.extract_rating(item.get("rating"))
            reviews = item.get("reviews_count") if isinstance(item.get("reviews_count"), int) else None

            url = item.get("link") or f"https://www.amazon.com/dp/{asin}"
            image = item.get("thumbnail")
            snippet = item.get("snippet") or item.get("delivery")

            products.append(
                Product(
                    id=f"amazon_{asin}",
                    title=title,
                    price=price,
                    currency="USD",
                    source="amazon",
                    url=url,
                    rating=rating,
                    reviews_count=reviews,
                    image=image,
                    snippet=snippet,
                )
            )

        return products
