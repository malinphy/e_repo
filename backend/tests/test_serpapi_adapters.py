"""Tests for SerpAPI marketplace adapters (Walmart, eBay, Amazon, Google Shopping)."""
from __future__ import annotations

from backend.app.tools.serpapi.walmart import WalmartAdapter
from backend.app.tools.serpapi.ebay import EbayAdapter
from backend.app.tools.serpapi.amazon import AmazonAdapter
from backend.app.tools.serpapi.google_shopping import GoogleShoppingAdapter


def test_walmart_adapter_parsing():
    """Verify WalmartAdapter parses organic_results into Product models."""
    sample_data = {
        "organic_results": [
            {
                "us_item_id": "112233",
                "title": "Apple AirPods Pro",
                "primary_offer": {"offer_price": 199.99},
                "rating": 4.8,
                "reviews": 1200,
                "thumbnail": "https://walmart.com/img1.jpg",
                "product_page_url": "https://walmart.com/ip/112233",
                "description": "Noise cancelling earbuds",
            }
        ]
    }
    adapter = WalmartAdapter()
    products = adapter.parse_response(sample_data)

    assert len(products) == 1
    p = products[0]
    assert p.id == "walmart_112233"
    assert p.title == "Apple AirPods Pro"
    assert p.price == 199.99
    assert p.source == "walmart"
    assert p.rating == 4.8


def test_ebay_adapter_parsing():
    """Verify EbayAdapter parses organic_results into Product models."""
    sample_data = {
        "organic_results": [
            {
                "epid": "445566",
                "title": "Sony WH-1000XM5",
                "price": {"extracted": 298.00},
                "rating": 4.7,
                "link": "https://ebay.com/itm/445566",
                "thumbnail": "https://ebay.com/img2.jpg",
                "condition": "Brand New",
            }
        ]
    }
    adapter = EbayAdapter()
    products = adapter.parse_response(sample_data)

    assert len(products) == 1
    p = products[0]
    assert p.id == "ebay_445566"
    assert p.title == "Sony WH-1000XM5"
    assert p.price == 298.00
    assert p.source == "ebay"


def test_amazon_adapter_parsing():
    """Verify AmazonAdapter parses organic_results into Product models."""
    sample_data = {
        "organic_results": [
            {
                "asin": "B08N5WRWNW",
                "title": "MacBook Air M1",
                "price": {"extracted": 749.00},
                "rating": 4.9,
                "reviews_count": 5400,
                "link": "https://amazon.com/dp/B08N5WRWNW",
                "thumbnail": "https://amazon.com/macbook.jpg",
            }
        ]
    }
    adapter = AmazonAdapter()
    products = adapter.parse_response(sample_data)

    assert len(products) == 1
    p = products[0]
    assert p.id == "amazon_B08N5WRWNW"
    assert p.title == "MacBook Air M1"
    assert p.price == 749.00
    assert p.source == "amazon"


def test_google_shopping_adapter_parsing():
    """Verify GoogleShoppingAdapter parses shopping_results into Product models."""
    sample_data = {
        "shopping_results": [
            {
                "product_id": "goog_7788",
                "title": "Samsung Galaxy S24",
                "extracted_price": 799.99,
                "rating": 4.6,
                "link": "https://google.com/shopping/product/7788",
                "thumbnail": "https://google.com/galaxy.jpg",
            }
        ]
    }
    adapter = GoogleShoppingAdapter()
    products = adapter.parse_response(sample_data)

    assert len(products) == 1
    p = products[0]
    assert p.id == "google_shopping_goog_7788"
    assert p.title == "Samsung Galaxy S24"
    assert p.price == 799.99
    assert p.source == "google_shopping"
