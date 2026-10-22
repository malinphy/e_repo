"""Cart repository: user-scoped cart with line-item management."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.cart import Cart, CartItem

# Keys used to identify a product within a cart for dedup / lookup.
_IDENTITY_KEYS = ("link", "engine", "title")


def _identity(product: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(product.get(k) for k in _IDENTITY_KEYS if product.get(k) is not None)


class CartRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self, user_id: str) -> Cart:
        """Return the user's cart, creating it on first use."""
        cart = self._session.scalars(
            select(Cart).where(Cart.user_id == user_id)
        ).first()
        if cart is None:
            cart = Cart(user_id=user_id)
            self._session.add(cart)
            self._session.flush()
        return cart

    def list_items(self, user_id: str) -> list[CartItem]:
        cart = self.get_or_create(user_id)
        stmt = (
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .order_by(CartItem.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def add(
        self, user_id: str, product: dict[str, Any], quantity: int = 1
    ) -> CartItem | None:
        """Add a product to the cart. If an identical item exists, bump quantity.

        Returns None when the product has no identifying fields (nothing to add).
        """
        ident = _identity(product)
        if not any(ident):
            return None

        cart = self.get_or_create(user_id)
        for item in self.list_items(user_id):
            if _identity(item.product) == ident:
                item.quantity += quantity
                self._session.flush()
                return item

        item = CartItem(cart_id=cart.id, product=product, quantity=quantity)
        self._session.add(item)
        self._session.flush()
        return item

    def remove(
        self, user_id: str, product: dict[str, Any], quantity: int | None = None
    ) -> bool:
        """Remove a product (or decrement its quantity) from the cart.

        ``quantity=None`` removes the whole line; a positive value decrements
        by that amount and drops the line when it reaches zero.
        """
        ident = _identity(product)
        if not any(ident):
            return False

        for item in self.list_items(user_id):
            if _identity(item.product) == ident:
                if quantity is None or item.quantity <= quantity:
                    self._session.delete(item)
                else:
                    item.quantity -= quantity
                self._session.flush()
                return True
        return False

    def clear(self, user_id: str) -> None:
        cart = self.get_or_create(user_id)
        for item in self.list_items(user_id):
            self._session.delete(item)
        self._session.flush()