"""load_context node: populates active cart and user context into ShopState."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...core.database import SessionLocal
from ...models.cart import Cart
from ...models.chat import ChatMessage, ChatThread
from ...models.user import User
from ..state import ShopState

logger = logging.getLogger(__name__)


def load_context_node(state: ShopState) -> Dict[str, Any]:
    """Pre-loads the user's active cart and context from SQLite before routing.

    Ensures the user, thread, and cart records exist in SQLite, then passes the frozen
    cart snapshot, last_results, and IDs (user_id, thread_id, chat_id) to downstream nodes.
    """
    user_id = state.get("user_id") or "guest_user"
    thread_id = state.get("thread_id") or "default_thread"
    chat_id = state.get("chat_id") or f"chat_{uuid.uuid4().hex[:8]}"

    db = SessionLocal()
    try:
        # 1. Ensure user exists
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            user = User(id=user_id, name="Guest User")
            db.add(user)
            db.flush()

        # 2. Ensure chat_thread exists in DB
        thread = db.scalar(select(ChatThread).where(ChatThread.thread_id == thread_id))
        if not thread:
            thread = ChatThread(thread_id=thread_id, user_id=user_id, title="Shopping Chat")
            db.add(thread)
            db.flush()

        # 3. Load or create user cart with eager loaded items
        cart = db.scalar(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items))
        )
        if not cart:
            cart = Cart(user_id=user_id)
            db.add(cart)
            db.commit()
            db.refresh(cart)
        else:
            db.commit()

        cart_items_list = [
            {
                "item_id": item.id,
                "product_id": item.product_id,
                "title": item.title,
                "source": item.source,
                "price": item.price_snapshot,
                "quantity": item.quantity,
                "currency": item.currency,
                "url": item.product_url,
                "image": item.image_url,
            }
            for item in (cart.items or [])
        ]

        # 4. Maintain or restore last_results from recent DB messages if missing in state
        last_results = state.get("last_results") or []
        if not last_results:
            last_msg_with_products = db.scalar(
                select(ChatMessage)
                .where(
                    ChatMessage.thread_id == thread_id,
                    ChatMessage.role == "assistant",
                    ChatMessage.metadata_json.isnot(None),
                )
                .order_by(ChatMessage.created_at.desc())
            )
            if last_msg_with_products and last_msg_with_products.metadata_json:
                last_results = last_msg_with_products.metadata_json.get("products") or []

        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "chat_id": chat_id,
            "cart": cart_items_list,
            "last_results": last_results,
        }
    except Exception as exc:
        logger.exception("Failed to load user context from DB: %s", exc)
        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "chat_id": chat_id,
            "cart": state.get("cart") or [],
            "last_results": state.get("last_results") or [],
            "error": f"load_context error: {exc}",
        }
    finally:
        db.close()
