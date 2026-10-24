"""Tests for Cart and Product QA Subgraphs (Stage 4)."""
from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from backend.app.agent.graph import build_shop_graph
from backend.app.agent.subgraphs.cart.operations import (
    add_item_to_cart,
    format_cart_message,
    remove_item_from_cart,
    resolve_product_reference,
)


def test_resolve_product_reference():
    """Verify deterministic resolution of items using indices, superlatives, and titles."""
    candidates = [
        {"id": "p1", "title": "Nike Air Force 1", "price": 110.0},
        {"id": "p2", "title": "Adidas Ultraboost Light", "price": 85.0},
        {"id": "p3", "title": "Puma Suede Classic", "price": 140.0},
    ]

    # 1. Numeric index
    assert resolve_product_reference("2. ürünü ekle", candidates)["id"] == "p2"
    assert resolve_product_reference("1st one", candidates)["id"] == "p1"
    assert resolve_product_reference("3", candidates)["id"] == "p3"

    # 2. Superlatives
    assert resolve_product_reference("en ucuzunu ekle", candidates)["id"] == "p2"
    assert resolve_product_reference("en pahalı olan", candidates)["id"] == "p3"

    # 3. Title keywords
    assert resolve_product_reference("ultraboost", candidates)["id"] == "p2"
    assert resolve_product_reference("puma", candidates)["id"] == "p3"


def test_cart_database_operations():
    """Verify adding, updating and removing cart items in SQLite."""
    user_id = "test_user_cart_ops"
    product = {
        "id": "prod_phone_1",
        "title": "Google Pixel 8",
        "price": 699.0,
        "source": "google_shopping",
        "currency": "USD",
        "url": "https://store.google.com/pixel8",
    }

    # 1. Add item
    cart_items = add_item_to_cart(user_id, product, quantity=1)
    assert len(cart_items) == 1
    assert cart_items[0]["product_id"] == "prod_phone_1"
    assert cart_items[0]["price"] == 699.0

    # 2. Add same item again (quantity should increment)
    cart_items = add_item_to_cart(user_id, product, quantity=2)
    assert len(cart_items) == 1
    assert cart_items[0]["quantity"] == 3

    # 3. Format cart message
    receipt = format_cart_message(cart_items)
    assert "Google Pixel 8" in receipt
    assert "$2097.00" in receipt

    # 4. Remove item
    success, msg, remaining = remove_item_from_cart(user_id, "pixel")
    assert success is True
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_chat_cart_add_flow_end_to_end():
    """Verify chat resolves '2. ürünü ekle' against last_results and updates state/cart."""
    app = build_shop_graph()
    thread_id = "th_cart_flow_1"
    config = {"configurable": {"thread_id": thread_id}}

    candidates = [
        {"id": "c1", "title": "Gaming Mouse A", "price": 40.0, "source": "walmart"},
        {"id": "c2", "title": "Mechanical Keyboard B", "price": 90.0, "source": "amazon"},
    ]

    state_input = {
        "messages": [HumanMessage(content="2. ürünü sepetime ekle")],
        "user_id": "user_cart_flow",
        "thread_id": thread_id,
        "last_results": candidates,
    }

    result = await app.ainvoke(state_input, config=config)

    assert result["intent"] == "cart"
    assert len(result["cart"]) >= 1
    # Check that Keyboard B was added
    assert any(item["title"] == "Mechanical Keyboard B" for item in result["cart"])
    latest_reply = result["messages"][-1].content
    assert "Mechanical Keyboard B" in latest_reply
    assert "$90.00" in latest_reply


@pytest.mark.asyncio
async def test_chat_qa_flow_end_to_end():
    """Verify chat answers product questions based strictly on candidate details."""
    app = build_shop_graph()
    thread_id = "th_qa_flow_1"
    config = {"configurable": {"thread_id": thread_id}}

    candidates = [
        {
            "id": "c10",
            "title": "Sony WH-1000XM5",
            "price": 349.99,
            "source": "ebay",
            "rating": 4.9,
            "snippet": "Active noise cancelling with 30-hour battery life. 2-year manufacturer warranty.",
            "url": "https://sony.com/xm5",
        }
    ]

    state_input = {
        "messages": [HumanMessage(content="bu kulaklığın garantisi ve şarjı ne kadar?")],
        "user_id": "user_qa_flow",
        "thread_id": thread_id,
        "last_results": candidates,
    }

    result = await app.ainvoke(state_input, config=config)

    assert result["intent"] == "qa"
    latest_reply = result["messages"][-1].content
    assert "Sony WH-1000XM5" in latest_reply
    assert any(term in latest_reply.lower() for term in ("30", "garanti", "pil", "battery", "warranty"))
