"""Tests for entry nodes: load_context and router."""
from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from backend.app.agent.nodes.load_context import load_context_node
from backend.app.agent.nodes.router import router_node, _heuristic_classify
from backend.app.agent.state import ShopState


def test_load_context_node_initializes_state():
    """Verify load_context populates user_id, thread_id, chat_id, and cart."""
    initial_state: ShopState = {
        "messages": [HumanMessage(content="selam")],
        "user_id": "test_user_node",
        "thread_id": "thread_node_1",
        "chat_id": None,
        "intent": None,
        "search_query": None,
        "last_results": [{"id": "prod_1", "title": "Test Product"}],
        "cart": [],
        "pending_action": None,
        "error": None,
    }

    result = load_context_node(initial_state)

    assert result["user_id"] == "test_user_node"
    assert result["thread_id"] == "thread_node_1"
    assert result["chat_id"] is not None
    assert result["chat_id"].startswith("chat_")
    assert isinstance(result["cart"], list)
    assert len(result["last_results"]) == 1


@pytest.mark.parametrize(
    "query,has_products,expected_intent",
    [
        ("iphone 15 pro max arıyorum", False, "search"),
        ("2. sıradakini sepete ekle", True, "cart"),
        ("sepetimi göster", False, "cart"),
        ("2. ürünün garantisi var mı?", True, "qa"),
        ("satın al ödeme yap", False, "checkout"),
        ("merhaba nasılsın", False, "chitchat"),
    ],
)
def test_heuristic_router_classifications(query: str, has_products: bool, expected_intent: str):
    """Test deterministic heuristic router fallback on key phrases."""
    decision = _heuristic_classify(
        query=query,
        has_last_results=has_products,
        has_cart_items=True,
    )
    assert decision.intent == expected_intent


def test_router_node_fallback_execution():
    """Test router_node processes messages and updates intent in state."""
    state: ShopState = {
        "messages": [HumanMessage(content="fiyatı 100 dolar altı ayakkabı bul")],
        "user_id": "u1",
        "thread_id": "t1",
        "chat_id": "c1",
        "intent": None,
        "search_query": None,
        "last_results": [],
        "cart": [],
        "pending_action": None,
        "error": None,
    }

    update = router_node(state)
    assert update["intent"] == "search"
    assert update["search_query"] is not None
