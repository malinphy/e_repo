"""Tests for the raw per-engine search endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from ecommerce_agent.agent.deps import AgentDeps
from tests.conftest import FakeAdapter


def test_list_engines_returns_configured_names(client: TestClient) -> None:
    response = client.get("/engines")

    assert response.status_code == 200
    assert response.json() == {"engines": ["amazon", "google_shopping"]}


def test_single_engine_search_returns_products(client: TestClient) -> None:
    response = client.post("/engines/amazon/search", json={"query": "usb hub", "num": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "amazon"
    assert body["query"] == "usb hub"
    assert body["count"] == 1
    assert body["error"] is None
    assert body["products"][0]["title"] == "amazon usb hub"
    assert body["products"][0]["engine"] == "amazon"
    assert body["products"][0]["price"] == "$9.99"


def test_single_engine_search_unknown_engine_is_404(client: TestClient) -> None:
    response = client.post("/engines/walmart/search", json={"query": "usb hub"})

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "walmart" in detail
    assert "amazon" in detail


def test_single_engine_search_reports_upstream_failure_as_200(
    client: TestClient, deps: AgentDeps
) -> None:
    deps.engines["amazon"] = FakeAdapter("amazon", fail=True)

    response = client.post("/engines/amazon/search", json={"query": "usb hub"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["products"] == []
    assert "amazon is down" in body["error"]


def test_single_engine_search_validates_payload(client: TestClient) -> None:
    assert client.post("/engines/amazon/search", json={"query": ""}).status_code == 422
    assert client.post("/engines/amazon/search", json={"query": "hub", "num": 0}).status_code == 422
    assert client.post("/engines/amazon/search", json={"query": "hub", "num": 101}).status_code == 422


def test_multi_engine_search_defaults_to_all_engines(client: TestClient) -> None:
    response = client.post("/engines/search", json={"query": "usb hub"})

    assert response.status_code == 200
    body = response.json()
    assert body["engines"] == ["amazon", "google_shopping"]
    assert body["count"] == 2
    assert body["errors"] == {}
    assert set(body["results"]) == {"amazon", "google_shopping"}
    assert body["results"]["google_shopping"][0]["price"] == "$19.99"


def test_multi_engine_search_honours_requested_subset(client: TestClient) -> None:
    response = client.post(
        "/engines/search", json={"query": "usb hub", "engines": ["google_shopping"]}
    )

    assert response.status_code == 200
    assert response.json()["engines"] == ["google_shopping"]


def test_multi_engine_search_unknown_engine_is_404(client: TestClient) -> None:
    response = client.post("/engines/search", json={"query": "hub", "engines": ["amazon", "nope"]})

    assert response.status_code == 404
    assert "nope" in response.json()["detail"]


def test_multi_engine_search_isolates_one_failing_engine(
    client: TestClient, deps: AgentDeps
) -> None:
    deps.engines["amazon"] = FakeAdapter("amazon", fail=True)

    response = client.post("/engines/search", json={"query": "usb hub"})

    assert response.status_code == 200
    body = response.json()
    assert body["results"]["amazon"] == []
    assert body["count"] == 1
    assert "amazon is down" in body["errors"]["amazon"]


def test_engine_routes_do_not_persist_runs(client: TestClient) -> None:
    client.post("/engines/amazon/search", json={"query": "usb hub"})

    assert client.get("/runs/1").status_code == 404
