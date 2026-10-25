"""Structured intent and router schemas for LangGraph decision-making."""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

IntentType = Literal["search", "qa", "cart", "checkout", "chitchat"]
CartAction = Literal["add", "remove", "update_qty", "view"]
MarketplaceSource = Literal["walmart", "ebay", "amazon", "google_shopping"]


class SearchQuery(BaseModel):
    """Structured parameters extracted from user query for product search."""

    keywords: str = Field(description="Cleaned search keywords without conversational fluff")
    max_price: Optional[float] = Field(default=None, description="Maximum budget/price filter if requested")
    currency: Optional[str] = Field(default="USD", description="Currency specified by the user")
    brand: Optional[str] = Field(default=None, description="Specific brand mentioned (e.g. Nike, Apple)")
    marketplaces: List[MarketplaceSource] = Field(
        default_factory=lambda: ["walmart", "ebay", "amazon", "google_shopping"],
        description="Target marketplaces to fetch products from",
    )


class CartIntentDetails(BaseModel):
    """Details for shopping cart operations."""

    action: CartAction = Field(description="Action to perform: add, remove, update_qty, or view")
    item_reference: Optional[str] = Field(
        default=None,
        description="Reference to product from last_results (e.g. '2nd', 'first product', 'cheapest', 'nike')",
    )
    quantity: int = Field(default=1, description="Quantity to add, remove, or set")


class RouterOutput(BaseModel):
    """Strict structured output emitted by the Router LLM."""

    intent: IntentType = Field(
        description=(
            "Primary intent: 'search' (browse/find), 'qa' (ask about previous product), "
            "'cart' (add/remove/view cart), 'checkout' (buy/order), 'chitchat' (greeting/other)"
        ),
    )
    search_query: Optional[SearchQuery] = Field(
        default=None,
        description="Populated only when intent is 'search'",
    )
    cart_action: Optional[CartIntentDetails] = Field(
        default=None,
        description="Populated only when intent is 'cart'",
    )
    qa_target_reference: Optional[str] = Field(
        default=None,
        description="Target product reference when intent is 'qa' (e.g. '2nd product', 'warranty')",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Short 1-sentence explanation of why this intent was selected",
    )
