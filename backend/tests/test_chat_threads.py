"""Tests for chat thread and message endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_thread(client: TestClient) -> None:
    response = client.post(
        "/users/demo/threads", json={"user_id": "demo", "title": "shoes"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == "demo"
    assert body["title"] == "shoes"
    assert "id" in body
    assert "created_at" in body


def test_create_thread_user_id_mismatch(client: TestClient) -> None:
    response = client.post(
        "/users/demo/threads", json={"user_id": "other", "title": "shoes"}
    )
    assert response.status_code == 400


def test_list_threads(client: TestClient) -> None:
    client.post("/users/demo/threads", json={"user_id": "demo", "title": "thread 1"})
    client.post("/users/demo/threads", json={"user_id": "demo", "title": "thread 2"})
    response = client.get("/users/demo/threads")
    assert response.status_code == 200
    bodies = response.json()
    assert len(bodies) == 2
    assert all(t["user_id"] == "demo" for t in bodies)


def test_send_message_creates_run_and_messages(client: TestClient) -> None:
    thread = client.post(
        "/users/demo/threads", json={"user_id": "demo", "title": "shoes"}
    ).json()
    thread_id = thread["id"]

    response = client.post(
        f"/chat/{thread_id}/message",
        json={"message": "nike ayakkabi", "user_id": "demo"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "nike ayakkabi"
    assert body["answer"]
    assert body["run_id"] is not None

    # history should contain user + assistant messages
    history = client.get(f"/chat/{thread_id}/history")
    assert history.status_code == 200
    msgs = history.json()["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "nike ayakkabi"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["run_id"] == body["run_id"]


def test_send_message_unknown_thread_is_404(client: TestClient) -> None:
    response = client.post(
        "/chat/99999/message", json={"message": "nike ayakkabi", "user_id": "demo"}
    )
    assert response.status_code == 404


def test_send_message_user_id_mismatch(client: TestClient) -> None:
    thread = client.post(
        "/users/demo/threads", json={"user_id": "demo", "title": "shoes"}
    ).json()
    response = client.post(
        f"/chat/{thread['id']}/message",
        json={"message": "nike ayakkabi", "user_id": "other"},
    )
    assert response.status_code == 400


def test_get_thread_history_unknown_thread_is_404(client: TestClient) -> None:
    response = client.get("/chat/99999/history")
    assert response.status_code == 404


def test_post_chat_body_accepts_thread_id_and_appends_history(client: TestClient) -> None:
    """POST /chat with a thread_id continues the same thread and stores history."""
    thread = client.post(
        "/users/demo/threads", json={"user_id": "demo", "title": "shoes"}
    ).json()
    thread_id = thread["id"]

    # First message via the plain /chat endpoint, passing thread_id in the body.
    first = client.post(
        "/chat", json={"message": "nike ayakkabi", "user_id": "demo", "thread_id": thread_id}
    )
    assert first.status_code == 200
    body = first.json()
    assert body["thread_id"] == thread_id
    assert body["run_id"] is not None

    # Second message must append to the same thread and surface its history.
    second = client.post(
        "/chat", json={"message": "adidas ayakkabi", "user_id": "demo", "thread_id": thread_id}
    )
    assert second.status_code == 200
    assert second.json()["thread_id"] == thread_id

    history = client.get(f"/chat/{thread_id}/history").json()["messages"]
    assert len(history) == 4  # user + assistant for each of two turns


def test_post_chat_unknown_thread_id_falls_back_to_new_thread(
    client: TestClient,
) -> None:
    """A stale/nonexistent thread_id no longer 404s: it starts a fresh thread."""
    response = client.post(
        "/chat", json={"message": "nike ayakkabi", "user_id": "demo", "thread_id": 99999}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] is not None
    assert body["thread_id"] != 99999


def test_post_chat_thread_belongs_to_other_user_is_400(client: TestClient) -> None:
    thread = client.post(
        "/users/demo/threads", json={"user_id": "demo", "title": "shoes"}
    ).json()
    response = client.post(
        "/chat",
        json={"message": "nike ayakkabi", "user_id": "other", "thread_id": thread["id"]},
    )
    assert response.status_code == 400


def test_post_chat_auto_creates_thread_for_new_user_turn(client: TestClient) -> None:
    """POST /chat with a user_id but no thread_id creates a thread and returns its id."""
    first = client.post("/chat", json={"message": "merhaba", "user_id": "alice"})
    assert first.status_code == 200
    thread_id = first.json()["thread_id"]
    assert thread_id is not None

    # continuing with the returned thread_id appends to the same thread
    second = client.post(
        "/chat", json={"message": "nike ayakkabi", "user_id": "alice", "thread_id": thread_id}
    )
    assert second.status_code == 200
    assert second.json()["thread_id"] == thread_id

    history = client.get(f"/chat/{thread_id}/history").json()["messages"]
    assert len(history) == 4  # two turns, user + assistant each