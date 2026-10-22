"""Tests for per-engine result persistence and the run-scoped read endpoints."""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ecommerce_agent.repositories.agent_runs_repo import AgentRunRepository
from ecommerce_agent.repositories.engine_results_repo import EngineResultsRepository


def _hit(title: str, price: str | None = "$9.99") -> dict[str, Any]:
    return {
        "title": title,
        "price": price,
        "source": "amazon",
        "link": f"https://example.com/{title}",
        "rating": 4.0,
        "reviews": 10,
    }


def _new_run(session: Session) -> int:
    run = AgentRunRepository(session).create("usb hub", user_id="u1")
    session.commit()
    return run.id


def test_replace_for_run_writes_calls_and_products(session_factory) -> None:
    session = session_factory()
    run_id = _new_run(session)
    repo = EngineResultsRepository(session)

    repo.replace_for_run(
        run_id,
        {"amazon": [_hit("a1"), _hit("a2")], "ebay": [_hit("e1")]},
    )
    session.commit()

    calls = repo.calls_for_run(run_id)
    assert [(c.engine, c.result_count) for c in calls] == [("amazon", 2), ("ebay", 1)]
    assert [p.title for p in repo.products_for_run(run_id, "amazon")] == ["a1", "a2"]
    assert [p.position for p in repo.products_for_run(run_id, "amazon")] == [0, 1]


def test_replace_for_run_is_idempotent(session_factory) -> None:
    session = session_factory()
    run_id = _new_run(session)
    repo = EngineResultsRepository(session)

    repo.replace_for_run(run_id, {"amazon": [_hit("a1"), _hit("a2")]})
    repo.replace_for_run(run_id, {"amazon": [_hit("a9")]})
    session.commit()

    assert [p.title for p in repo.products_for_run(run_id, "amazon")] == ["a9"]
    assert [c.result_count for c in repo.calls_for_run(run_id)] == [1]


def test_failed_engine_is_recorded_with_error(session_factory) -> None:
    session = session_factory()
    run_id = _new_run(session)
    repo = EngineResultsRepository(session)

    repo.replace_for_run(
        run_id,
        {"amazon": [], "walmart": []},
        {"walmart": "walmart is down"},
    )
    session.commit()

    call = repo.call_for_run(run_id, "walmart")
    assert call is not None
    assert call.error == "walmart is down"
    assert call.result_count == 0
    assert repo.products_for_run(run_id, "walmart") == []


def test_products_without_engine_marker_are_kept(session_factory) -> None:
    session = session_factory()
    run_id = _new_run(session)
    repo = EngineResultsRepository(session)

    repo.replace_for_run(run_id, {"amazon": [_hit("a1"), {"error": "boom"}]})
    session.commit()

    assert repo.call_for_run(run_id, "amazon").result_count == 1
    assert len(repo.products_for_run(run_id, "amazon")) == 1


def test_search_run_exposes_per_engine_results(client: TestClient) -> None:
    body = client.post("/search", json={"query": "usb hub", "user_id": "u1"}).json()
    run_id = body["run_id"]

    summary = client.get(f"/runs/{run_id}/engines")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["run_id"] == run_id
    assert payload["query"] == "usb hub"
    assert {item["engine"]: item["result_count"] for item in payload["engines"]} == {
        "amazon": 1,
        "google_shopping": 1,
    }

    amazon = client.get(f"/runs/{run_id}/engines/amazon")
    assert amazon.status_code == 200
    assert amazon.json()["products"] == [
        {
            "title": "amazon usb hub",
            "price": "$9.99",
            "source": "amazon",
            "link": "https://example.com/amazon",
            "rating": 4.5,
            "reviews": 100,
            "engine": "amazon",
        }
    ]


def test_search_response_groups_results_by_engine(client: TestClient) -> None:
    body = client.post("/search", json={"query": "usb hub"}).json()
    assert set(body["results"]) == {"amazon", "google_shopping"}
    assert body["results"]["amazon"][0]["engine"] == "amazon"
    assert body["results"]["amazon"][0]["price"] == "$9.99"
    assert body["engine_errors"] == {}


def test_search_response_reports_per_engine_errors(client: TestClient, engines) -> None:
    engines["amazon"]._fail = True
    body = client.post("/search", json={"query": "usb hub"}).json()
    assert body["results"]["amazon"] == []
    assert "amazon" in body["engine_errors"]
    assert body["results"]["google_shopping"]


def test_chat_result_is_readable_per_engine_without_a_query(client: TestClient) -> None:
    chat = client.post("/chat", json={"message": "nike ayakkabi", "user_id": "u1"}).json()
    run_id = chat["run_id"]

    # chat response already carries the split view
    assert set(chat["results"]) == {"amazon", "google_shopping"}
    assert chat["results"]["amazon"][0]["engine"] == "amazon"
    assert chat["query"] == "nike ayakkabi"

    # and the same data is readable per engine with no query at all
    response = client.get("/engines/amazon")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["query"] == "nike ayakkabi"
    assert body["engine"] == "amazon"
    assert body["result_count"] == 1
    assert body["products"] == chat["results"]["amazon"]

    other = client.get("/engines/google_shopping")
    assert other.json()["products"] == chat["results"]["google_shopping"]


def test_flat_engine_routes_mirror_param_route(client: TestClient) -> None:
    chat = client.post("/chat", json={"message": "nike ayakkabi", "user_id": "u1"}).json()
    run_id = chat["run_id"]

    assert client.get("/amazon").json() == client.get("/engines/amazon").json()
    assert client.get("/google_shopping").json() == client.get(
        "/engines/google_shopping"
    ).json()

    amazon = client.get("/amazon").json()
    assert amazon["run_id"] == run_id
    assert amazon["engine"] == "amazon"
    assert amazon["query"] == "nike ayakkabi"

    pinned = client.get("/amazon", params={"run_id": run_id}).json()
    assert pinned["run_id"] == run_id


def test_flat_engine_route_404_for_unconfigured_engine(client: TestClient) -> None:
    client.post("/chat", json={"message": "nike ayakkabi"})
    assert client.get("/ebay").status_code == 404


def test_latest_engine_result_follows_the_most_recent_chat(client: TestClient, engines) -> None:
    client.post("/chat", json={"message": "nike ayakkabi"})
    assert client.get("/engines/amazon").json()["query"] == "nike ayakkabi"

    engines["amazon"]._price = "$7.77"
    client.post("/chat", json={"message": "adidas ayakkabi"})

    body = client.get("/engines/amazon").json()
    assert body["query"] == "adidas ayakkabi"
    assert body["products"][0]["price"] == "$7.77"


def test_latest_engine_result_can_be_pinned_to_a_run(client: TestClient, engines) -> None:
    first = client.post("/chat", json={"message": "nike ayakkabi"}).json()["run_id"]
    engines["amazon"]._price = "$7.77"
    client.post("/chat", json={"message": "adidas ayakkabi"})

    body = client.get("/engines/amazon", params={"run_id": first}).json()
    assert body["run_id"] == first
    assert body["query"] == "nike ayakkabi"
    assert body["products"][0]["price"] == "$9.99"


def test_latest_engine_result_404_before_any_run(client: TestClient) -> None:
    response = client.get("/engines/amazon")
    assert response.status_code == 404
    assert "POST /chat" in response.json()["detail"]


def test_latest_engine_result_404_for_unknown_engine(client: TestClient) -> None:
    client.post("/chat", json={"message": "nike ayakkabi"})
    response = client.get("/engines/walmart")
    assert response.status_code == 404
    assert "available" in response.json()["detail"]


def test_latest_engine_result_reports_a_failed_engine(client: TestClient, engines) -> None:
    engines["amazon"]._fail = True
    client.post("/chat", json={"message": "nike ayakkabi"})

    body = client.get("/engines/amazon").json()
    assert body["products"] == []
    assert body["error"]


def test_run_engine_404_for_unknown_run(client: TestClient) -> None:
    assert client.get("/runs/9999/engines").status_code == 404
    assert client.get("/runs/9999/engines/amazon").status_code == 404


def test_run_engine_404_for_engine_that_did_not_run(client: TestClient) -> None:
    run_id = client.post("/search", json={"query": "usb hub"}).json()["run_id"]
    response = client.get(f"/runs/{run_id}/engines/walmart")
    assert response.status_code == 404
    assert "walmart" in response.json()["detail"]


def test_failed_engine_keeps_a_row(client: TestClient, engines) -> None:
    engines["amazon"]._fail = True
    run_id = client.post("/search", json={"query": "usb hub"}).json()["run_id"]

    summary = client.get(f"/runs/{run_id}/engines").json()
    amazon = next(item for item in summary["engines"] if item["engine"] == "amazon")
    assert amazon["result_count"] == 0
    assert amazon["error"]

    per_engine = client.get(f"/runs/{run_id}/engines/amazon").json()
    assert per_engine["products"] == []
    assert per_engine["error"]
