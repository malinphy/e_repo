"""Pydantic schemas for parsed queries and agent I/O."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["search", "chit_chat", "add_cart", "remove_cart", "show_cart"]


class ParsedQuery(BaseModel):
    """Structured interpretation of a user's shopping query."""

    keywords: str = Field(description="Core product keywords to search for")
    engines: list[str] = Field(
        default_factory=list,
        description="Marketplace engines to search: google_shopping, amazon, ebay, walmart",
    )
    max_price: float | None = Field(default=None, description="Maximum price filter, if stated")
    currency: str | None = Field(default=None, description="Currency code, if stated")
    item_reference: str | None = Field(
        default=None,
        description=(
            "For add_cart/remove_cart: which product the user means, e.g. a "
            "position ('1st', '2.si'), a title fragment, or 'all'."
        ),
    )
    intent: Intent = Field(
        default="search",
        description=(
            "Detected user intent: 'search' (find products), 'chit_chat' (greeting/"
            "small talk/off-topic), 'add_cart' (add an item to the cart), "
            "'remove_cart' (remove an item from the cart), 'show_cart' (show the cart)."
        ),
    )
