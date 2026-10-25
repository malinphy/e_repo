"""Shopping cart business operations and deterministic reference resolution."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from ....core.database import SessionLocal
from ....models.cart import Cart, CartItem
from ....models.user import User

logger = logging.getLogger(__name__)

_NUMBER_RE = re.compile(r"(\d+)")
_ORDINAL_MAP = {
    "1st": 1, "first": 1,
    "2nd": 2, "second": 2,
    "3rd": 3, "third": 3,
    "4th": 4, "fourth": 4,
    "5th": 5, "fifth": 5,
}


def resolve_product_reference(
    reference: Optional[str],
    candidates: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Deterministically identifies candidate product from last_results using index, ordinal, superlative, or title."""
    if not candidates:
        return None

    if not reference or not reference.strip():
        # Default to the first candidate if user simply said 'add to cart'
        return candidates[0]

    lowered = reference.strip().lower()

    # 1. Check superlatives: 'cheapest', 'lowest price'
    if any(k in lowered for k in ("cheapest", "lowest price")):
        return min(candidates, key=lambda p: (p.get("price") or 999999.0))

    if any(k in lowered for k in ("most expensive", "highest price")):
        return max(candidates, key=lambda p: (p.get("price") or 0.0))

    # 2. Check ordinal words ('second', '2nd', 'first')
    for word, pos in _ORDINAL_MAP.items():
        if word in lowered:
            idx = pos - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]

    # 3. Check numeric digits: '2nd item', '1'
    match = _NUMBER_RE.search(lowered)
    if match:
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx]

    # 4. Check title substring match
    for prod in candidates:
        title = (prod.get("title") or "").lower()
        # Find if significant words from reference are in title
        ref_words = [w for w in re.findall(r"\w+", lowered) if len(w) > 2 and w not in ("product", "item", "add", "cart")]
        if ref_words and any(w in title for w in ref_words):
            return prod

    # Fallback to first if only 1 candidate exists
    return candidates[0] if len(candidates) == 1 else None


def add_item_to_cart(
    user_id: str,
    product: Dict[str, Any],
    quantity: int = 1,
) -> List[Dict[str, Any]]:
    """Adds or updates an item in the user's cart in SQLite with a frozen price_snapshot."""
    db = SessionLocal()
    try:
        # Ensure user and cart exist
        cart = db.scalar(select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items)))
        if not cart:
            user = db.scalar(select(User).where(User.id == user_id))
            if not user:
                db.add(User(id=user_id, name="Guest User"))
                db.flush()
            cart = Cart(user_id=user_id)
            db.add(cart)
            db.commit()
            db.refresh(cart)

        product_id = str(product.get("id") or product.get("product_id") or "prod_unknown")
        title = str(product.get("title") or "Unknown Product")
        source = str(product.get("source") or "marketplace")
        price = float(product.get("price") or 0.0)
        currency = str(product.get("currency") or "USD")
        url = str(product.get("url") or "")
        image = str(product.get("image") or "")

        # Check if product is already in cart
        existing_item = next((i for i in (cart.items or []) if i.product_id == product_id), None)
        if existing_item:
            existing_item.quantity += quantity
        else:
            new_item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                title=title,
                source=source,
                quantity=max(1, quantity),
                price_snapshot=price,  # FROZEN SNAPSHOT
                currency=currency,
                product_url=url,
                image_url=image,
            )
            db.add(new_item)

        db.commit()
        db.refresh(cart)

        return [
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
            for item in cart.items
        ]
    finally:
        db.close()


def remove_item_from_cart(
    user_id: str,
    item_reference: Optional[str],
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Removes an item from cart matching product_id, title, or index."""
    db = SessionLocal()
    try:
        cart = db.scalar(select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items)))
        if not cart or not cart.items:
            return False, "Your cart is already empty.", []

        items = list(cart.items)
        target_item: Optional[CartItem] = None

        if item_reference:
            lowered = item_reference.strip().lower()
            if any(w in lowered for w in ("all", "clear", "empty", "everything")):
                # Clear entire cart
                db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
                db.commit()
                return True, "All items have been removed from your cart.", []

            # 1. Match direct item_id (primary key) or product_id (exact)
            for it in items:
                if str(it.id) == lowered or it.product_id.lower() == lowered:
                    target_item = it
                    break

            # 2. Match title keywords / substring
            if not target_item:
                for it in items:
                    if lowered in it.title.lower():
                        target_item = it
                        break

            # 3. Check ordinal match (first, second, 1st, 2nd...)
            if not target_item:
                for word, pos in _ORDINAL_MAP.items():
                    if word in lowered:
                        idx = pos - 1
                        if 0 <= idx < len(items):
                            target_item = items[idx]
                            break

            # 4. Check position index if referring to an ordinal/item index (e.g. "1st item", "2nd item" or standalone digit)
            if not target_item:
                match = _NUMBER_RE.search(lowered)
                if match:
                    idx = int(match.group(1)) - 1
                    if 0 <= idx < len(items):
                        target_item = items[idx]

        # If user did not provide an item reference, remove the most recent item
        elif items:
            target_item = items[-1]

        if target_item:
            removed_title = target_item.title
            db.delete(target_item)
            db.commit()
            db.refresh(cart)

            updated_items = [
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
                for item in cart.items
            ]
            return True, f"'{removed_title}' removed from cart.", updated_items

        return False, "Item to remove was not found in your cart.", []
    finally:
        db.close()


def format_cart_message(items: List[Dict[str, Any]]) -> str:
    """Format cart items into a clean markdown receipt list."""
    if not items:
        return "🛒 **Your cart is currently empty.** You can add products by saying *'add the 1st item to cart'*."

    total = sum((item.get("price") or 0.0) * (item.get("quantity") or 1) for item in items)
    currency = items[0].get("currency", "USD")

    lines = ["🛒 **Your Current Shopping Cart:**\n"]
    for idx, item in enumerate(items, start=1):
        price = item.get("price", 0.0)
        qty = item.get("quantity", 1)
        subtotal = price * qty
        source_badge = f"[{item.get('source', '').upper()}]"
        lines.append(
            f"{idx}. **{item.get('title')}**\n"
            f"   💵 ${price:.2f} × {qty} items = **${subtotal:.2f} {currency}** | {source_badge}"
        )

    lines.append(f"\n🏷️ **Total Amount: ${total:.2f} {currency}**")
    lines.append("💡 *To complete your purchase, simply say 'checkout' or 'buy now'.*")
    return "\n".join(lines)
