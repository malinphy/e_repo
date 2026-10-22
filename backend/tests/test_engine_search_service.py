"""Unit tests for the engine search service (failure isolation + flattening)."""
from __future__ import annotations

from typing import Any

import pytest

from ecommerce_agent.services.engine_search import (
    EngineSearchResult,
    EngineSearchService,
    product_rows,
)
from ecommerce_agent.tools.serpapi.base import SerpAPIEngineAdapter
from ecommerce_agent.tools.serpapi.client import SerpAPIClient
from ecommerce_agent.tools.serpapi.factory import build_engine
from tests.conftest import FakeAdapter

LEAKY_KEY = "deadbeef" * 5  # 40 hex chars, key-shaped


class RecordingAdapter(SerpAPIEngineAdapter):
    engine = "recorder"
    query_param = "q"

    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []

    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def search(self, query: str, num: int | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append((query, num))
        return [{"title": f"hit for {query}"}]


class LeakyAdapter(SerpAPIEngineAdapter):
    engine = "leaky"
    query_param = "q"

    def __init__(self) -> None:
        pass

    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def search(self, query: str, num: int | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError(f"GET https://serpapi.com/search?engine=x&api_key={LEAKY_KEY}")


@pytest.fixture()
def service() -> EngineSearchService:
    return EngineSearchService(
        {
            "google_shopping": FakeAdapter("google_shopping", price="$19.99"),
            "amazon": FakeAdapter("amazon", price="$9.99"),
        }
    )


def test_available_is_sorted(service: EngineSearchService) -> None:
    assert service.available == ["amazon", "google_shopping"]


def test_has_reports_configured_engines(service: EngineSearchService) -> None:
    assert service.has("amazon") is True
    assert service.has("walmart") is False


def test_search_returns_products(service: EngineSearchService) -> None:
    result = service.search("amazon", "usb hub", num=3)

    assert result.ok is True
    assert result.engine == "amazon"
    assert result.products[0]["title"] == "amazon usb hub"


def test_search_forwards_query_and_num() -> None:
    adapter = RecordingAdapter()
    service = EngineSearchService({adapter.engine: adapter})

    service.search("recorder", "usb hub", num=7)

    assert adapter.calls == [("usb hub", 7)]


def test_search_unknown_engine_reports_error_instead_of_raising(service: EngineSearchService) -> None:
    result = service.search("walmart", "usb hub")

    assert result.ok is False
    assert result.products == []
    assert "unknown engine" in (result.error or "")


def test_search_isolates_adapter_failure(service: EngineSearchService) -> None:
    service = EngineSearchService({"amazon": FakeAdapter("amazon", fail=True)})

    result = service.search("amazon", "usb hub")

    assert result.ok is False
    assert "amazon is down" in (result.error or "")


def test_search_redacts_secrets_from_failure_text() -> None:
    service = EngineSearchService({"leaky": LeakyAdapter()})

    result = service.search("leaky", "usb hub")

    assert result.ok is False
    assert LEAKY_KEY not in (result.error or "")
    assert "api_key=***" in (result.error or "")


def test_search_many_defaults_to_every_engine(service: EngineSearchService) -> None:
    outcomes = service.search_many("usb hub")

    assert [o.engine for o in outcomes] == ["amazon", "google_shopping"]
    assert all(o.ok for o in outcomes)


def test_search_many_keeps_requested_order(service: EngineSearchService) -> None:
    outcomes = service.search_many("usb hub", ["google_shopping", "amazon"])

    assert [o.engine for o in outcomes] == ["google_shopping", "amazon"]


def test_search_many_skips_unknown_engines(service: EngineSearchService) -> None:
    outcomes = service.search_many("usb hub", ["amazon", "walmart"])

    assert [o.engine for o in outcomes] == ["amazon"]


def test_query_param_comes_from_the_adapter(service: EngineSearchService) -> None:
    real = EngineSearchService({"amazon": build_engine("amazon", SerpAPIClient(api_key="k"))})

    assert real.query_param("amazon") == "k"
    assert service.query_param("amazon") is None  # FakeAdapter declares no query_param
    assert service.query_param("walmart") is None


def test_product_rows_stamps_engine_and_skips_error_entries() -> None:
    rows = product_rows("amazon", [{"title": "a"}, {"error": "nope"}])

    assert rows == [{"title": "a", "engine": "amazon"}]


def test_engine_search_result_ok_flag() -> None:
    assert EngineSearchResult("amazon").ok is True
    assert EngineSearchResult("amazon", error="boom").ok is False
