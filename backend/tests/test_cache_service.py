"""Tests for ProductCacheService with SQLite persistence."""
from __future__ import annotations

import time
from backend.app.schemas.product import Product
from backend.app.services.cache_service import ProductCacheService


def test_cache_set_and_get():
    """Verify storing products in cache and retrieving them."""
    products = [
        Product(
            id="walmart_test_1",
            title="Wireless Charger",
            price=29.99,
            source="walmart",
            url="https://walmart.com/item/1",
        )
    ]
    query = "wireless charger"
    engine = "walmart"

    # Save to cache
    ProductCacheService.set(query, engine, products, ttl_hours=1)

    # Retrieve from cache
    cached = ProductCacheService.get(query, engine)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].id == "walmart_test_1"
    assert cached[0].price == 29.99


def test_cache_miss_and_expiration():
    """Verify cache returns None for unknown query or expired records."""
    assert ProductCacheService.get("unknown_nonexistent_query", "ebay") is None

    # Test expired item (TTL of -1 hours)
    products = [
        Product(
            id="ebay_exp_1",
            title="Old Book",
            price=15.0,
            source="ebay",
            url="https://ebay.com/item/2",
        )
    ]
    ProductCacheService.set("vintage book", "ebay", products, ttl_hours=-1)

    # Should detect expiration and return None
    assert ProductCacheService.get("vintage book", "ebay") is None
