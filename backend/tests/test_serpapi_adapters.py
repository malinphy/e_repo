"""Tests for SerpAPI adapters with mocked HTTP (no network)."""
from __future__ import annotations

from typing import Any

import pytest

from ecommerce_agent.tools.serpapi import client as client_module
from ecommerce_agent.tools.serpapi.client import SerpAPIClient, SerpAPIError
from ecommerce_agent.tools.serpapi.engines import (
    AmazonAdapter,
    EbayAdapter,
    GoogleShoppingAdapter,
    WalmartAdapter,
)
from ecommerce_agent.tools.serpapi.factory import (
    available_engines,
    build_all_engines,
    build_engine,
)


class _FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text
        self.reason_phrase = "Bad Request"

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


class _FakeHttpxClient:
    payload: dict[str, Any] = {}
    last_params: dict[str, Any] = {}
    status_code: int = 200
    text: str = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> "_FakeHttpxClient":
        return self

    def __exit__(self, *args: Any) -> bool:
        return False

    def get(self, url: str, params: dict[str, Any] | None = None) -> _FakeResponse:
        type(self).last_params = {"url": url, **(params or {})}
        return _FakeResponse(type(self).payload, type(self).status_code, type(self).text)


@pytest.fixture()
def fake_http(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(client_module.httpx, "Client", _FakeHttpxClient)
    _FakeHttpxClient.payload = {}
    _FakeHttpxClient.status_code = 200
    _FakeHttpxClient.text = ""
    return _FakeHttpxClient


def test_available_engines_lists_all_four() -> None:
    assert available_engines() == ["amazon", "ebay", "google_shopping", "walmart"]


def test_client_sends_engine_params_and_api_key(fake_http) -> None:
    SerpAPIClient(api_key="secret").search("amazon", {"k": "usb hub", "num": 5})
    assert fake_http.last_params["engine"] == "amazon"
    assert fake_http.last_params["k"] == "usb hub"
    assert fake_http.last_params["api_key"] == "secret"
    assert fake_http.last_params["num"] == 5
    assert fake_http.last_params["url"] == SerpAPIClient.BASE_URL


def test_google_shopping_normalizes_shopping_results(fake_http) -> None:
    fake_http.payload = {
        "shopping_results": [
            {"title": "Hub", "price": "$10", "source": "Best Buy", "link": "http://a", "rating": 4.2, "reviews": 12}
        ]
    }
    adapter = build_engine("google_shopping", SerpAPIClient(api_key="k"))
    assert isinstance(adapter, GoogleShoppingAdapter)
    results = adapter.search("hub")
    assert results == [
        {"title": "Hub", "price": "$10", "source": "Best Buy", "link": "http://a", "rating": 4.2, "reviews": 12}
    ]


@pytest.mark.parametrize(
    ("name", "expected_cls", "expected_price"),
    [
        ("amazon", AmazonAdapter, "$10"),
        ("ebay", EbayAdapter, "$10"),
        # Walmart exposes a numeric offer price, so it is formatted as currency.
        ("walmart", WalmartAdapter, "$10.00"),
    ],
)
def test_organic_result_engines_normalize(
    fake_http, name: str, expected_cls: type, expected_price: str
) -> None:
    # Each engine's real payload shape is covered by the normalizer tests below.
    fake_http.payload = {
        "organic_results": [
            {
                "title": "Hub",
                "price": {"raw": "$10", "extracted": 10.0},
                "link": "http://a",
                "product_page_url": "http://a",
                "primary_offer": {"offer_price": 10.0, "currency": "USD"},
                "rating": 4.0,
                "reviews": 7,
            }
        ]
    }
    adapter = build_engine(name, SerpAPIClient(api_key="k"))
    assert isinstance(adapter, expected_cls)
    results = adapter.search("hub")
    assert results[0]["source"] == name
    assert results[0]["title"] == "Hub"
    assert results[0]["price"] == expected_price


@pytest.mark.parametrize(
    ("name", "expected_param"),
    [
        ("google_shopping", "q"),
        ("amazon", "k"),
        ("ebay", "_nkw"),
        ("walmart", "query"),
    ],
)
def test_each_engine_sends_its_own_query_param(
    fake_http, name: str, expected_param: str
) -> None:
    """SerpAPI names the query differently per engine; using ``q`` returns 400."""
    adapter = build_engine(name, SerpAPIClient(api_key="k"))
    adapter.search("basketball shoes", num=5)
    assert fake_http.last_params[expected_param] == "basketball shoes"
    if expected_param != "q":
        assert "q" not in fake_http.last_params
    assert fake_http.last_params["num"] == 5


def test_missing_results_key_returns_empty_list(fake_http) -> None:
    fake_http.payload = {}
    adapter = build_engine("amazon", SerpAPIClient(api_key="k"))
    assert adapter.search("hub") == []


def test_build_all_engines_returns_every_adapter() -> None:
    adapters = build_all_engines("k")
    assert sorted(adapters) == available_engines()
    assert all(isinstance(a, type(adapters[a.engine])) for a in adapters.values())


def test_amazon_uses_extracted_price_when_display_price_missing(fake_http) -> None:
    fake_http.payload = {
        "organic_results": [
            {"title": "Shoe", "extracted_price": 68.97, "link": "http://a", "rating": 4.5, "reviews": 54}
        ]
    }
    results = build_engine("amazon", SerpAPIClient(api_key="k")).search("shoe")
    assert results[0]["price"] == "$68.97"
    assert results[0]["link"] == "http://a"


def test_ebay_reads_dict_price(fake_http) -> None:
    fake_http.payload = {
        "organic_results": [
            {
                "title": "adidas Harden",
                "link": "http://ebay/1",
                "price": {"raw": "$115.49", "extracted": 115.49},
                "condition": "New (Other)",
            }
        ]
    }
    results = build_engine("ebay", SerpAPIClient(api_key="k")).search("harden")
    assert results[0]["price"] == "$115.49"
    assert results[0]["link"] == "http://ebay/1"
    assert results[0]["rating"] is None
    assert results[0]["reviews"] is None


def test_walmart_reads_product_page_url_and_primary_offer(fake_http) -> None:
    fake_http.payload = {
        "organic_results": [
            {
                "title": "Little &amp; Big Boys Sneakers",
                "product_page_url": "http://walmart/1",
                "primary_offer": {"offer_price": 20.98, "currency": "USD"},
                "rating": 4.6,
                "reviews": 1169,
            }
        ]
    }
    results = build_engine("walmart", SerpAPIClient(api_key="k")).search("sneakers")
    assert results[0]["title"] == "Little & Big Boys Sneakers"
    assert results[0]["price"] == "$20.98"
    assert results[0]["link"] == "http://walmart/1"
    assert results[0]["rating"] == 4.6


def test_every_engine_matches_the_shared_product_contract(fake_http) -> None:
    """``synthesize`` ranks on this contract, so keys must never be missing."""
    fake_http.payload = {"organic_results": [], "shopping_results": []}
    for name in available_engines():
        adapter = build_engine(name, SerpAPIClient(api_key="k"))
        fake_http.payload = {
            "organic_results": [{"title": "T", "price": "$1", "link": "l"}],
            "shopping_results": [{"title": "T", "price": "$1", "link": "l"}],
        }
        for product in adapter.search("t"):
            assert set(product) == {"title", "price", "source", "link", "rating", "reviews"}


def test_client_error_message_never_contains_the_api_key(fake_http) -> None:
    fake_http.status_code = 400
    fake_http.payload = None
    fake_http.text = "Missing query `k` or `node` parameter."

    with pytest.raises(SerpAPIError) as excinfo:
        SerpAPIClient(api_key="super-secret-key").search("amazon", {"k": "shoes"})

    message = str(excinfo.value)
    assert "super-secret-key" not in message
    assert "Missing query" in message
    assert "400" in message


def test_client_reports_serpapi_error_body(fake_http) -> None:
    fake_http.status_code = 400
    fake_http.payload = {"error": "Missing query `_nkw` parameter."}

    with pytest.raises(SerpAPIError) as excinfo:
        SerpAPIClient(api_key="k").search("ebay", {"_nkw": "shoes"})

    assert "Missing query `_nkw` parameter." in str(excinfo.value)


def test_serpapi_error_is_scrubbed_even_if_body_echoes_the_key(fake_http) -> None:
    fake_http.status_code = 401
    fake_http.payload = {"error": "Invalid API key: secret-key-123"}

    with pytest.raises(SerpAPIError) as excinfo:
        SerpAPIClient(api_key="secret-key-123").search("amazon", {"k": "shoes"})

    assert "secret-key-123" not in str(excinfo.value)

