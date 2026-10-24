"""API request and response schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .product import Product


class ChatRequest(BaseModel):
    """Payload for POST /api/chat."""

    message: str = Field(..., description="User message text", example="100 dolar altı bluetooth kulaklık ara")
    user_id: Optional[str] = Field(default="guest_user", description="Active user ID")
    thread_id: Optional[str] = Field(default=None, description="Optional thread/session ID for conversational memory")


class ChatResponse(BaseModel):
    """Response from POST /api/chat."""

    reply: str = Field(description="Assistant's formatted answer text")
    intent: str = Field(description="Detected user intent (search, chitchat, cart, etc.)")
    user_id: str = Field(description="User ID")
    thread_id: str = Field(description="Thread / Session ID")
    chat_id: str = Field(description="Specific turn ID")
    products: List[Product] = Field(default_factory=list, description="Structured product results returned from search subgraph")
    cart: List[Dict[str, Any]] = Field(default_factory=list, description="Current user cart snapshot")


class SearchResultsResponse(BaseModel):
    """Response from GET /api/search returning products discovered in the chat session."""

    thread_id: str = Field(description="Associated chat thread ID")
    user_id: str = Field(description="User ID")
    query: Optional[str] = Field(default=None, description="Last search query executed in this chat")
    total_results: int = Field(description="Number of products discovered in the latest chat search")
    products: List[Product] = Field(default_factory=list, description="List of structured products found in the chat")
    formatted_message: Optional[str] = Field(default=None, description="Markdown formatted message for display")
