"""Google Shopping SerpAPI engine adapter."""
from __future__ import annotations

from typing import Any, Dict, List
from ...schemas.product import Product
from .base import BaseEngineAdapter


class GoogleShoppingAdapter(BaseEngineAdapter):
    """Adapter for Google Shopping search via SerpAPI."""

    engine_name = "google_shopping"
    query_param_name = "q"

    def parse_response(self, raw_data: Dict[str, Any]) -> List[Product]:
        products: List[Product] = []
        items = raw_data.get("shopping_results") or []

        for item in items:
            title = item.get("title")
            if not title:
                continue

            product_id = str(item.get("product_id") or abs(hash(title)))
            raw_price = item.get("extracted_price") or item.get("price")
            price = self.extract_price(raw_price)

            rating = self.extract_rating(item.get("rating"))
            reviews = item.get("reviews") if isinstance(item.get("reviews"), int) else None

            url = item.get("link") or item.get("product_link") or ""
            image = item.get("thumbnail")
            snippet = item.get("snippet") or item.get("source")

            products.append(
                Product(
                    id=f"google_shopping_{product_id}",
                    title=title,
                    price=price,
                    currency="USD",
                    source="google_shopping",
                    url=url,
                    rating=rating,
                    reviews_count=reviews,
                    image=image,
                    snippet=snippet,
                )
            )

        return products
