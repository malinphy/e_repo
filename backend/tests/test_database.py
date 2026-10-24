"""Tests for SQLite database models and persistence."""
from __future__ import annotations

from datetime import datetime, timedelta
import pytest
from sqlalchemy import select

from backend.app.models.user import User
from backend.app.models.cart import Cart, CartItem
from backend.app.models.chat import ChatThread, ChatMessage
from backend.app.models.product_cache import ProductCache
from backend.app.models.order import Order, OrderItem


def test_user_creation_with_demographics(db_session):
    """Test user model with age, gender, and location."""
    user = User(
        id="usr_123",
        email="test@example.com",
        name="Ahmet",
        age=30,
        gender="male",
        location="Istanbul",
    )
    db_session.add(user)
    db_session.flush()

    fetched = db_session.scalar(select(User).where(User.id == "usr_123"))
    assert fetched is not None
    assert fetched.age == 30
    assert fetched.gender == "male"
    assert fetched.location == "Istanbul"


def test_cart_and_cart_items_with_price_snapshot(db_session):
    """Test cart creation and price_snapshot freezing."""
    user = User(id="usr_cart_test", email="cart@test.com")
    db_session.add(user)
    db_session.flush()

    cart = Cart(user_id=user.id)
    db_session.add(cart)
    db_session.flush()

    item = CartItem(
        cart_id=cart.id,
        product_id="walmart_999",
        title="Nike Air Force 1",
        source="walmart",
        quantity=2,
        price_snapshot=89.99,
        currency="USD",
    )
    db_session.add(item)
    db_session.flush()

    fetched_cart = db_session.scalar(select(Cart).where(Cart.id == cart.id))
    assert len(fetched_cart.items) == 1
    assert fetched_cart.items[0].price_snapshot == 89.99
    assert fetched_cart.items[0].quantity == 2


def test_product_cache_ttl(db_session):
    """Test ProductCache TTL expiration check."""
    expired_cache = ProductCache(
        query_hash="hash_old",
        query="running shoes",
        engine="walmart",
        results_json=[{"title": "Shoe A"}],
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    valid_cache = ProductCache(
        query_hash="hash_new",
        query="wireless mouse",
        engine="ebay",
        results_json=[{"title": "Mouse B"}],
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db_session.add_all([expired_cache, valid_cache])
    db_session.flush()

    assert expired_cache.is_expired() is True
    assert valid_cache.is_expired() is False


def test_chat_thread_and_messages(db_session):
    """Test chat thread creation and message linkage."""
    user = User(id="usr_chat", email="chat@test.com")
    thread = ChatThread(thread_id="th_100", user_id="usr_chat", title="Ayakkabı Arayışı")
    db_session.add_all([user, thread])
    db_session.flush()

    msg1 = ChatMessage(thread_id="th_100", role="user", content="Merhaba spor ayakkabı arıyorum")
    msg2 = ChatMessage(thread_id="th_100", role="assistant", content="İşte bulduğum ayakkabılar...", intent="search")
    db_session.add_all([msg1, msg2])
    db_session.flush()

    fetched_thread = db_session.scalar(select(ChatThread).where(ChatThread.thread_id == "th_100"))
    assert len(fetched_thread.messages) == 2
    assert fetched_thread.messages[0].role == "user"
    assert fetched_thread.messages[1].role == "assistant"
