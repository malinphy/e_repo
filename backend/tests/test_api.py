"""Tests for FastAPI endpoints (/health, /api/chat, /api/search)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.product import Product

client = TestClient(app)


def test_health_check_endpoint():
    """Verify GET /health returns 200 status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


def test_root_endpoint():
    """Verify GET / returns links to docs and endpoints."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["docs_url"] == "/docs"


def test_chat_endpoint_chitchat():
    """Verify POST /api/chat responds to greetings."""
    payload = {
        "message": "hello how are you",
        "user_id": "api_test_user",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "chitchat"
    assert data["user_id"] == "api_test_user"
    assert len(data["reply"]) > 0
    assert data["thread_id"] is not None


def test_chat_search_flow_and_subsequent_search_api_lookup():
    """Verify that chat search findings are directly accessible via /api/search."""
    sample_product = Product(
        id="walmart_api_1",
        title="Nike Air Force 1 07",
        price=110.0,
        source="walmart",
        url="https://walmart.com/item/af1",
        rating=4.8,
    )

    with patch("backend.app.agent.subgraphs.search.serp_fetch._fetch_single_engine", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [sample_product]

        # 1. User performs a search in Chat
        chat_payload = {
            "message": "search for nike air force shoes",
            "user_id": "user_tennis_test",
            "thread_id": "thread_tennis_101",
        }
        chat_res = client.post("/api/chat", json=chat_payload)
        assert chat_res.status_code == 200
        chat_data = chat_res.json()

        assert chat_data["intent"] == "search"
        assert len(chat_data["products"]) >= 1
        assert chat_data["products"][0]["title"] == "Nike Air Force 1 07"

        # 2. Later, user / client calls /api/search (GET or POST) with that thread_id
        # It must NOT perform a new search, but return the chat's discovered products!
        search_res = client.get("/api/search?thread_id=thread_tennis_101&user_id=user_tennis_test")
        assert search_res.status_code == 200
        search_data = search_res.json()

        assert search_data["thread_id"] == "thread_tennis_101"
        assert search_data["total_results"] >= 1
        assert search_data["products"][0]["title"] == "Nike Air Force 1 07"
        assert search_data["products"][0]["price"] == 110.0
        assert "Nike Air Force" in search_data["formatted_message"]


def test_conversation_memory_continuity():
    """Verify conversation memory continuity between turns on the same thread."""
    thread_id = "mem_test_thread"
    user_id = "mem_user"

    # Turn 1
    r1 = client.post("/api/chat", json={"message": "hello", "thread_id": thread_id, "user_id": user_id})
    assert r1.status_code == 200
    assert r1.json()["thread_id"] == thread_id

    # Turn 2
    r2 = client.post("/api/chat", json={"message": "what is in my cart?", "thread_id": thread_id, "user_id": user_id})
    assert r2.status_code == 200
    assert r2.json()["thread_id"] == thread_id
    assert r2.json()["intent"] == "cart"


def test_thread_isolation_like_chatgpt():
    """Verify ChatGPT-style thread isolation and management."""
    user_id = "chatgpt_user_1"

    # 1. Explicitly create a new thread (like clicking 'New Chat' in ChatGPT)
    new_thread_res = client.post("/api/chat/threads", json={"user_id": user_id, "title": "Headphones Search"})
    assert new_thread_res.status_code == 200
    thread_a = new_thread_res.json()["thread_id"]
    assert thread_a.startswith("th_")

    # 2. Chat on Thread A (Turn 1 & 2)
    r_a1 = client.post("/api/chat", json={"message": "hello", "thread_id": thread_a, "user_id": user_id})
    assert r_a1.status_code == 200
    assert r_a1.json()["thread_id"] == thread_a

    r_a2 = client.post("/api/chat", json={"message": "what is in my cart?", "thread_id": thread_a, "user_id": user_id})
    assert r_a2.status_code == 200

    # 3. Verify messages in Thread A
    msg_a_res = client.get(f"/api/chat/threads/{thread_a}/messages")
    assert msg_a_res.status_code == 200
    msgs_a = msg_a_res.json()
    assert len(msgs_a) >= 4  # 2 user messages + 2 assistant replies

    # 4. Open a brand NEW Thread B (Thread B history must be completely isolated and empty!)
    new_thread_b_res = client.post("/api/chat/threads", json={"user_id": user_id, "title": "New Chat"})
    assert new_thread_b_res.status_code == 200
    thread_b = new_thread_b_res.json()["thread_id"]
    assert thread_b != thread_a

    # Thread B initially has 0 messages
    msg_b_res = client.get(f"/api/chat/threads/{thread_b}/messages")
    assert msg_b_res.status_code == 200
    assert len(msg_b_res.json()) == 0

    # Send first message in Thread B
    r_b1 = client.post("/api/chat", json={"message": "hi there", "thread_id": thread_b, "user_id": user_id})
    assert r_b1.status_code == 200
    assert r_b1.json()["thread_id"] == thread_b

    # Verify Thread B now only has its own messages (2: 1 user, 1 assistant), NOT Thread A's!
    msg_b_res_after = client.get(f"/api/chat/threads/{thread_b}/messages")
    assert len(msg_b_res_after.json()) == 2

    # 5. List all threads for this user (Sidebar)
    threads_res = client.get(f"/api/chat/threads?user_id={user_id}")
    assert threads_res.status_code == 200
    thread_ids = [t["thread_id"] for t in threads_res.json()]
    assert thread_a in thread_ids
    assert thread_b in thread_ids

