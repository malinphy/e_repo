"""Tests for Stage 5 Checkout with Human-in-the-Loop Interrupt & Resume."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.cart import Cart, CartItem
from backend.app.models.order import Order, OrderItem
from backend.app.models.user import User

client = TestClient(app)


def _seed_cart_for_user(user_id: str, items: list[dict]):
    """Helper to seed items into the user's cart in SQLite."""
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            user = User(id=user_id, name="Test User")
            db.add(user)
            db.flush()

        cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
        if not cart:
            cart = Cart(user_id=user_id)
            db.add(cart)
            db.flush()

        # Clear existing items
        for it in list(cart.items):
            db.delete(it)
        db.flush()

        for it in items:
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=it["product_id"],
                title=it["title"],
                source=it.get("source", "walmart"),
                price_snapshot=it["price"],
                quantity=it.get("quantity", 1),
                currency=it.get("currency", "USD"),
            )
            db.add(cart_item)
        db.commit()
    finally:
        db.close()


def test_checkout_empty_cart():
    """Verify attempting to checkout an empty cart returns guidance without interrupt."""
    user_id = "user_empty_cart"
    thread_id = "thread_empty_cart"

    payload = {
        "message": "satın al",
        "user_id": user_id,
        "thread_id": thread_id,
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "boş" in data["reply"].lower()
    assert data["pending_action"] is None


def test_checkout_interrupt_and_button_resume_approval():
    """Verify that checkout pauses at LangGraph interrupt, and POST /resume completes order."""
    user_id = "user_hitl_buyer"
    thread_id = "thread_hitl_checkout_1"

    # 1. Seed 2 items into the cart ($120.00 + $80.00 = $200.00)
    _seed_cart_for_user(
        user_id,
        [
            {"product_id": "p_af1", "title": "Nike Air Force 1", "price": 120.0, "quantity": 1, "source": "walmart"},
            {"product_id": "p_sony", "title": "Sony Earbuds", "price": 80.0, "quantity": 1, "source": "amazon"},
        ],
    )

    # 2. User requests checkout
    res = client.post("/api/chat", json={"message": "siparişi tamamla", "user_id": user_id, "thread_id": thread_id})
    assert res.status_code == 200
    data = res.json()

    # Verify that graph interrupted and returned approval prompt
    assert data["intent"] == "checkout"
    assert data["pending_action"] is not None
    assert data["pending_action"]["action"] == "checkout_approval"
    assert data["pending_action"]["total_amount"] == 200.0
    assert len(data["pending_action"]["items"]) == 2
    assert "Ödeme Özeti" in data["reply"]

    # 3. User clicks [Siparişi Onayla] button on UI -> calls POST /api/chat/resume
    resume_payload = {
        "thread_id": thread_id,
        "user_id": user_id,
        "approved": True,
    }
    resume_res = client.post("/api/chat/resume", json=resume_payload)
    assert resume_res.status_code == 200
    resume_data = resume_res.json()

    # Verify receipt message and cleared cart
    assert "Başarıyla Alındı" in resume_data["reply"]
    assert "ORD-" in resume_data["reply"]
    assert resume_data["pending_action"] is None
    assert len(resume_data["cart"]) == 0

    # 4. Verify in SQLite that Order and OrderItems were created and Cart was purged
    db = SessionLocal()
    try:
        order = db.scalar(select(Order).where(Order.user_id == user_id, Order.thread_id == thread_id))
        assert order is not None
        assert order.total_amount == 200.0
        assert len(order.items) == 2

        cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
        assert cart is not None
        assert len(cart.items) == 0
    finally:
        db.close()


def test_checkout_interrupt_and_button_resume_cancel():
    """Verify that clicking [İptal Et] cancels checkout and preserves cart items."""
    user_id = "user_cancel_buyer"
    thread_id = "thread_hitl_cancel_1"

    _seed_cart_for_user(
        user_id,
        [{"product_id": "p_item", "title": "Denim Jacket", "price": 75.0, "quantity": 1}],
    )

    # 1. Trigger checkout interrupt
    res = client.post("/api/chat", json={"message": "satın al", "user_id": user_id, "thread_id": thread_id})
    assert res.status_code == 200
    assert res.json()["pending_action"] is not None

    # 2. User clicks [İptal Et]
    cancel_res = client.post("/api/chat/resume", json={"thread_id": thread_id, "user_id": user_id, "approved": False})
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()

    assert "İptal Edildi" in cancel_data["reply"]
    assert cancel_data["pending_action"] is None

    # Cart must still have the item!
    db = SessionLocal()
    try:
        cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
        assert len(cart.items) == 1
    finally:
        db.close()
