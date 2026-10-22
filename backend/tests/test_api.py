"""Tests for the FastAPI endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_engines(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engines"] == ["amazon", "google_shopping"]
    assert body["version"]


def test_root_redirects_to_docs(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"


def test_search_returns_answer_and_products(client: TestClient) -> None:
    response = client.post("/search", json={"query": "usb hub", "user_id": "u1"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "usb hub"
    assert body["engines"] == ["amazon", "google_shopping"]
    assert len(body["products"]) == 2
    assert body["run_id"] is not None
    assert body["answer"]


def test_search_validates_empty_query(client: TestClient) -> None:
    assert client.post("/search", json={"query": ""}).status_code == 422


def test_chat_returns_answer(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "cheap mouse", "user_id": "u1"})
    assert response.status_code == 200
    assert response.json()["answer"]


def test_chat_validates_missing_body(client: TestClient) -> None:
    assert client.post("/chat", json={}).status_code == 422


def test_history_lists_previous_searches(client: TestClient) -> None:
    client.post("/search", json={"query": "usb hub", "user_id": "u1"})
    client.post("/search", json={"query": "mouse", "user_id": "u1"})
    client.post("/search", json={"query": "keyboard", "user_id": "u2"})

    response = client.get("/search/history", params={"user_id": "u1"})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert {row["query"] for row in rows} == {"usb hub", "mouse"}
    assert rows[0]["engines"] == ["amazon", "google_shopping"]


def test_history_requires_user_id(client: TestClient) -> None:
    assert client.get("/search/history").status_code == 422


def test_get_run_returns_completed_run(client: TestClient) -> None:
    run_id = client.post("/search", json={"query": "usb hub", "user_id": "u1"}).json()["run_id"]
    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["query"] == "usb hub"


def test_get_run_404_for_unknown_id(client: TestClient) -> None:
    assert client.get("/runs/9999").status_code == 404
