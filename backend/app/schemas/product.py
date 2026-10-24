"""Unified Product schema for marketplace search results and QA."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class Product(BaseModel):
    """Normalized product structure across Walmart, eBay, Amazon, and Google Shopping."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique product identifier (e.g. walmart_123, ebay_456, amazon_789, google_shopping_101)")
    title: str = Field(description="Product title")
    price: float = Field(description="Price as numeric float")
    currency: str = Field(default="USD", description="Currency code (USD, TRY, etc.)")
    source: str = Field(description="Marketplace source: 'walmart', 'ebay', 'amazon', 'google_shopping'")
    url: str = Field(description="Direct URL to product page")
    rating: Optional[float] = Field(default=None, description="Average customer rating (0.0 - 5.0)")
    reviews_count: Optional[int] = Field(default=None, description="Number of reviews")
    image: Optional[str] = Field(default=None, description="Primary product image URL")
    snippet: Optional[str] = Field(default=None, description="Short product description / features")
