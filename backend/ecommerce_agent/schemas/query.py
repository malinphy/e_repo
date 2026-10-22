"""Pydantic schemas for parsed queries and agent I/O."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ParsedQuery(BaseModel):
    """Structured interpretation of a user's shopping query."""

    keywords: str = Field(description="Core product keywords to search for")
    engines: list[str] = Field(
        default_factory=list,
        description="Marketplace engines to search: google_shopping, amazon, ebay, walmart",
    )
    max_price: float | None = Field(default=None, description="Maximum price filter, if stated")
    currency: str | None = Field(default=None, description="Currency code, if stated")
    intent: str = Field(default="product_search", description="Detected user intent")
