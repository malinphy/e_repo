"""Checkout business operations and database order persistence."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from ....core.database import SessionLocal
from ....models.cart import Cart, CartItem
from ....models.order import Order, OrderItem

logger = logging.getLogger(__name__)


def prepare_order_summary(
    cart_items: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float, str, str]:
    """Calculates order total, verifies cart items, and formats markdown summary."""
    if not cart_items:
        return [], 0.0, "USD", "Cannot proceed to checkout because your cart is empty."

    total = sum((item.get("price") or 0.0) * (item.get("quantity") or 1) for item in cart_items)
    currency = cart_items[0].get("currency", "USD") if cart_items else "USD"

    lines = [
        "💳 **Order & Checkout Summary**\n",
        "Items in your cart:",
    ]
    for idx, item in enumerate(cart_items, start=1):
        price = item.get("price") or 0.0
        qty = item.get("quantity") or 1
        subtotal = price * qty
        src = item.get("source", "").upper()
        lines.append(f"{idx}. **{item.get('title')}**\n   💵 ${price:.2f} × {qty} item{'s' if qty > 1 else ''} = **${subtotal:.2f} {currency}** [{src}]")

    lines.append(f"\n🏷️ **Total to Charge: ${total:.2f} {currency}**\n")
    lines.append("⚠️ *To complete your purchase, please click the button below or reply with **'Confirm'**.*")

    summary_text = "\n".join(lines)
    return cart_items, round(total, 2), currency, summary_text


def execute_checkout_order(
    user_id: str,
    thread_id: Optional[str],
    items: List[Dict[str, Any]],
    total_amount: float,
    currency: str = "USD",
) -> Tuple[str, str]:
    """Persists Order and OrderItems in SQLite, and purges the user's cart items."""
    db = SessionLocal()
    order_id = str(uuid.uuid4())
    display_id = f"ORD-{order_id[:8].upper()}"
    try:
        from ....models.user import User

        # 0. Ensure user exists in SQLite
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            user = User(id=user_id, name="Guest User")
            db.add(user)
            db.flush()

        # 1. Create Order
        order = Order(
            id=order_id,
            user_id=user_id,
            thread_id=thread_id,
            total_amount=total_amount,
            currency=currency,
            status="confirmed",
        )
        db.add(order)
        db.flush()

        # 2. Create OrderItems
        for item in items:
            order_item = OrderItem(
                id=str(uuid.uuid4()),
                order_id=order_id,
                product_id=str(item.get("product_id") or "prod_unknown"),
                title=str(item.get("title") or "Product"),
                source=str(item.get("source") or "unknown"),
                quantity=int(item.get("quantity") or 1),
                price_at_purchase=float(item.get("price") or 0.0),
                currency=currency,
                product_url=item.get("url"),
                image_url=item.get("image"),
            )
            db.add(order_item)

        # 3. Clear user's CartItems
        cart = db.scalar(select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items)))
        if cart:
            db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))

        db.commit()

        confirmation_message = (
            f"🎉 **Order Placed Successfully!**\n\n"
            f"📦 **Order Number:** `{display_id}`\n"
            f"💵 **Total Paid:** ${total_amount:.2f} {currency}\n"
            f"🛒 **Items:** {len(items)} product{'s' if len(items) > 1 else ''}\n\n"
            f"Your order has been recorded and your cart has been cleared. "
            f"Feel free to ask whenever you want to discover more products!"
        )
        return display_id, confirmation_message
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to execute checkout order: %s", exc)
        raise RuntimeError(f"Failed to place order: {exc}")
    finally:
        db.close()
