"""checkout node: handles order summary, LangGraph interrupt(), and order execution."""
from __future__ import annotations

import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from ...state import ShopState
from .operations import execute_checkout_order, prepare_order_summary

logger = logging.getLogger(__name__)


def checkout_node(state: ShopState) -> Dict[str, Any]:
    """Coordinates checkout flow with human-in-the-loop interrupt approval.

    1. Checks if cart has items. If empty, returns guidance.
    2. Formats order summary and calculates total amount.
    3. Calls LangGraph interrupt() pausing execution until the user approves or cancels.
    4. Upon approval: persists Order & OrderItems in SQLite, purges Cart, and returns receipt.
    5. Upon cancellation: returns notice that items remain safe in the cart.
    """
    user_id = state.get("user_id") or "guest_user"
    thread_id = state.get("thread_id")
    cart_items = state.get("cart") or []

    # 1. Cart empty check
    if not cart_items:
        msg = (
            "🛒 **Your cart is currently empty.**\n\n"
            "To proceed to checkout, please add at least one item to your cart. "
            "You can discover products by saying *'find headphones under $100'*."
        )
        return {
            "messages": [AIMessage(content=msg)],
            "pending_action": None,
        }

    # 2. Prepare order summary and total
    items, total_amount, currency, summary_text = prepare_order_summary(cart_items)

    interrupt_payload = {
        "action": "checkout_approval",
        "type": "checkout",
        "prompt": f"You have {len(items)} item(s) in your cart (Total: ${total_amount:.2f} {currency}). Do you confirm this order?",
        "summary_message": summary_text,
        "total_amount": total_amount,
        "currency": currency,
        "item_count": len(items),
        "items": items,
    }

    # 3. LangGraph Human-in-the-Loop Interrupt
    # Execution halts here until resumed via Command(resume={'approved': True/False})
    confirmation = interrupt(interrupt_payload)

    # 4. Handle resumption decision
    is_approved = False
    if isinstance(confirmation, bool):
        is_approved = confirmation
    elif isinstance(confirmation, dict):
        is_approved = bool(confirmation.get("approved"))

    if is_approved:
        # Create Order in SQLite & purge cart
        display_id, conf_msg = execute_checkout_order(
            user_id=user_id,
            thread_id=thread_id,
            items=items,
            total_amount=total_amount,
            currency=currency,
        )
        return {
            "messages": [AIMessage(content=conf_msg)],
            "cart": [],
            "pending_action": None,
        }
    else:
        cancel_msg = (
            "❌ **Order Cancelled**\n\n"
            "The checkout process was cancelled as requested. "
            "Your cart items remain saved so you can resume whenever you're ready."
        )
        return {
            "messages": [AIMessage(content=cancel_msg)],
            "pending_action": None,
        }
