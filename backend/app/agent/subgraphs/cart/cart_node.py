"""cart_node: executes deterministic cart actions (add, remove, view)."""
from __future__ import annotations

import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage

from ...state import ShopState
from .operations import (
    add_item_to_cart,
    format_cart_message,
    remove_item_from_cart,
    resolve_product_reference,
)

logger = logging.getLogger(__name__)


def cart_node(state: ShopState) -> Dict[str, Any]:
    """Handles cart operations deterministically with state-enforced user_id guardrail."""
    user_id = state.get("user_id") or "guest_user"
    last_results = state.get("last_results") or []
    current_cart = state.get("cart") or []
    messages = state.get("messages") or []
    last_query = messages[-1].content if messages else ""
    if not isinstance(last_query, str):
        last_query = str(last_query)

    # Determine action and reference from pending_action or heuristic
    pending_action = state.get("pending_action") or {}
    cart_details = pending_action.get("action") if pending_action.get("type") == "cart" else {}

    action = cart_details.get("action")
    item_ref = cart_details.get("item_reference")
    quantity = cart_details.get("quantity") or 1

    lowered = last_query.lower()
    if not action:
        if any(w in lowered for w in ("ekle", "at", "add")):
            action = "add"
        elif any(w in lowered for w in ("çıkar", "cikar", "sil", "remove", "delete")):
            action = "remove"
        else:
            action = "view"

    if not item_ref:
        item_ref = last_query

    # 1. ADD TO CART
    if action == "add":
        target_product = resolve_product_reference(item_ref, last_results)
        if not target_product:
            reply = (
                "⚠️ Hangi ürünü sepete eklemek istediğinizi tam anlayamadım. "
                "Lütfen *'1. ürünü ekle'* veya ürün adını belirterek tekrar deneyin."
            )
            return {"messages": [AIMessage(content=reply)]}

        updated_cart = add_item_to_cart(user_id, target_product, quantity=quantity)
        reply = (
            f"✅ **'{target_product.get('title')}'** (${target_product.get('price'):.2f}) "
            f"sepetinize {quantity} adet eklendi!\n\n"
            f"{format_cart_message(updated_cart)}"
        )
        return {
            "cart": updated_cart,
            "messages": [AIMessage(content=reply)],
            "pending_action": None,
        }

    # 2. REMOVE FROM CART
    if action == "remove":
        success, msg, updated_cart = remove_item_from_cart(user_id, item_ref)
        reply = f"🗑️ {msg}\n\n{format_cart_message(updated_cart)}"
        return {
            "cart": updated_cart,
            "messages": [AIMessage(content=reply)],
            "pending_action": None,
        }

    # 3. VIEW CART (DEFAULT)
    reply = format_cart_message(current_cart)
    return {
        "messages": [AIMessage(content=reply)],
        "pending_action": None,
    }
