"""Tests for Pydantic schemas and LangGraph ShopState."""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from langchain_core.messages import HumanMessage

from backend.app.schemas.product import Product
from backend.app.schemas.intent import RouterOutput, SearchQuery, CartIntentDetails
from backend.app.agent.state import ShopState


def test_product_schema_validation():
    """Verify Product schema creates immutable objects with proper types."""
    prod = Product(
        id="walmart_101",
        title="Gaming Keyboard",
        price=49.99,
        source="walmart",
        url="https://walmart.com/item/101",
        rating=4.5,
    )
    assert prod.id == "walmart_101"
    assert prod.price == 49.99
    assert prod.currency == "USD"
    assert prod.rating == 4.5

    # Check immutability (frozen config)
    with pytest.raises(ValidationError):
        prod.price = 39.99


def test_router_output_schema():
    """Verify RouterOutput with nested SearchQuery and CartIntentDetails."""
    output = RouterOutput(
        intent="search",
        search_query=SearchQuery(keywords="running shoes", max_price=100.0, brand="Nike"),
        reasoning="User specified brand and price",
    )
    assert output.intent == "search"
    assert output.search_query.keywords == "running shoes"
    assert output.search_query.max_price == 100.0
    assert output.search_query.brand == "Nike"


def test_shop_state_structure():
    """Verify ShopState attributes including user_id, thread_id, and chat_id."""
    state: ShopState = {
        "messages": [HumanMessage(content="Nike ayakkabı arıyorum")],
        "user_id": "usr_99",
        "thread_id": "th_99",
        "chat_id": "chat_turn_1",
        "intent": "search",
        "search_query": {"keywords": "Nike ayakkabı"},
        "last_results": [{"id": "p1", "title": "Nike Air Max", "price": 120.0}],
        "cart": [],
        "pending_action": None,
        "error": None,
    }
    assert state["user_id"] == "usr_99"
    assert state["thread_id"] == "th_99"
    assert state["chat_id"] == "chat_turn_1"
    assert len(state["last_results"]) == 1
