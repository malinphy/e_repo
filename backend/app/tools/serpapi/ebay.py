"""eBay SerpAPI engine adapter."""
from __future__ import annotations

from typing import Any, Dict, List
from ...schemas.product import Product
from .base import BaseEngineAdapter


class EbayAdapter(BaseEngineAdapter):
    """Adapter for eBay marketplace search via SerpAPI."""

    engine_name = "ebay"
    query_param_name = "_nkw"

    def parse_response(self, raw_data: Dict[str, Any]) -> List[Product]:
        products: List[Product] = []
        items = raw_data.get("organic_results") or []

        for item in items:
            title = item.get("title")
            if not title:
                continue

            item_id = str(item.get("epid") or item.get("item_id") or abs(hash(title)))

            price_info = item.get("price") or {}
            raw_price = price_info.get("extracted") if isinstance(price_info, dict) else price_info
            if not raw_price:
                raw_price = item.get("price")
            price = self.extract_price(raw_price)

            rating = self.extract_rating(item.get("rating"))
            reviews = item.get("reviews") if isinstance(item.get("reviews"), int) else None

            url = item.get("link") or f"https://www.ebay.com/itm/{item_id}"
            image = item.get("thumbnail")
            snippet = item.get("condition") or item.get("shipping")

            products.append(
                Product(
                    id=f"ebay_{item_id}",
                    title=title,
                    price=price,
                    currency="USD",
                    source="ebay",
                    url=url,
                    rating=rating,
                    reviews_count=reviews,
                    image=image,
                    snippet=snippet,
                )
            )

        return products
