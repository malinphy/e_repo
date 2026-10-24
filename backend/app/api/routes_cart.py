"""Cart API endpoints for viewing and managing shopping cart."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ..agent.subgraphs.cart.operations import (
    add_item_to_cart,
    format_cart_message,
    remove_item_from_cart,
)
from ..core.database import SessionLocal
from ..models.cart import Cart
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cart", tags=["Cart"])


class CartViewResponse(BaseModel):
    user_id: str
    total_items: int
    total_amount: float
    currency: str
    items: List[Dict[str, Any]]
    formatted_message: str


class CartRemovePayload(BaseModel):
    user_id: str = "guest_user"
    item_reference: Optional[str] = Field(None, description="Position index (e.g. '1', '2') or product title/id to remove")


@router.get("", response_model=CartViewResponse, summary="View user's active shopping cart")
async def get_cart(user_id: str = Query("guest_user", description="User ID")):
    """Returns active cart items and total amount for the user."""
    db = SessionLocal()
    try:
        cart = db.scalar(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items))
        )
        items = []
        if cart and cart.items:
            items = [
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

        total_amount = sum((i["price"] or 0.0) * (i["quantity"] or 1) for i in items)
        currency = items[0]["currency"] if items else "USD"

        return CartViewResponse(
            user_id=user_id,
            total_items=len(items),
            total_amount=round(total_amount, 2),
            currency=currency,
            items=items,
            formatted_message=format_cart_message(items),
        )
    finally:
        db.close()


@router.post("/remove", summary="Remove item from shopping cart")
async def remove_cart_item(payload: CartRemovePayload):
    """Removes an item from cart matching reference or index."""
    success, msg, updated_items = remove_item_from_cart(payload.user_id, payload.item_reference)
    return {
        "success": success,
        "message": msg,
        "user_id": payload.user_id,
        "total_items": len(updated_items),
        "items": updated_items,
    }
