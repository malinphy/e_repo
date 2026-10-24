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
        return [], 0.0, "USD", "Sepetiniz boş olduğu için ödeme adımına geçilemiyor."

    total = sum((item.get("price") or 0.0) * (item.get("quantity") or 1) for item in cart_items)
    currency = cart_items[0].get("currency", "USD") if cart_items else "USD"

    lines = [
        "💳 **Sipariş & Ödeme Özeti**\n",
        "Sepetinizdeki ürünler:",
    ]
    for idx, item in enumerate(cart_items, start=1):
        price = item.get("price") or 0.0
        qty = item.get("quantity") or 1
        subtotal = price * qty
        src = item.get("source", "").upper()
        lines.append(f"{idx}. **{item.get('title')}**\n   💵 ${price:.2f} × {qty} adet = **${subtotal:.2f} {currency}** [{src}]")

    lines.append(f"\n🏷️ **Tahsil Edilecek Toplam: ${total:.2f} {currency}**\n")
    lines.append("⚠️ *Siparişi tamamlamak ve ödemeyi onaylamak için lütfen aşağıdaki butonlara tıklayın veya sohbete **'Onaylıyorum'** yazın.*")

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
                title=str(item.get("title") or "Ürün"),
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
            f"🎉 **Siparişiniz Başarıyla Alındı!**\n\n"
            f"📦 **Sipariş Numarası:** `{display_id}`\n"
            f"💵 **Ödenen Tutar:** ${total_amount:.2f} {currency}\n"
            f"🛒 **Kalem Sayısı:** {len(items)} adet ürün\n\n"
            f"Siparişiniz sisteme kaydedildi ve sepetiniz temizlendi. "
            f"Yeni bir ürün aramak isterseniz bana her zaman yazabilirsiniz!"
        )
        return display_id, confirmation_message
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to execute checkout order: %s", exc)
        raise RuntimeError(f"Sipariş oluşturulamadı: {exc}")
    finally:
        db.close()
