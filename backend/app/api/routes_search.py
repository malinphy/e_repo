"""Search results endpoint returning products previously discovered in the chat session."""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from ..core.database import SessionLocal
from ..models.chat import ChatMessage, ChatThread
from ..schemas.api import SearchResultsResponse
from ..schemas.product import Product

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Search"])


class SearchLookupPayload(BaseModel):
    """Payload to look up chat search results."""
    thread_id: Optional[str] = None
    user_id: Optional[str] = "guest_user"


def _get_chat_search_results(thread_id: Optional[str], user_id: str) -> SearchResultsResponse:
    """Fetch the latest products discovered during the chat conversation without executing a new search."""
    db = SessionLocal()
    try:
        msg = None
        if thread_id:
            msg = db.scalar(
                select(ChatMessage)
                .where(
                    ChatMessage.thread_id == thread_id,
                    ChatMessage.role == "assistant",
                    ChatMessage.metadata_json.isnot(None),
                )
                .order_by(ChatMessage.created_at.desc())
            )

        # Fallback to the latest search across user's threads if not found by thread_id
        if not msg and user_id:
            msg = db.scalar(
                select(ChatMessage)
                .join(ChatThread, ChatMessage.thread_id == ChatThread.thread_id)
                .where(
                    ChatThread.user_id == user_id,
                    ChatMessage.role == "assistant",
                    ChatMessage.metadata_json.isnot(None),
                )
                .order_by(ChatMessage.created_at.desc())
            )

        if not msg or not msg.metadata_json:
            return SearchResultsResponse(
                thread_id=thread_id or "none",
                user_id=user_id,
                query=None,
                total_results=0,
                products=[],
                formatted_message="Bu sohbette henüz bir arama yapılmadı veya ürün bulunamadı.",
            )

        raw_products = msg.metadata_json.get("products") or []
        search_query_info = msg.metadata_json.get("search_query") or {}
        query_text = search_query_info.get("keywords") if isinstance(search_query_info, dict) else None

        validated_products: list[Product] = []
        for p in raw_products:
            try:
                validated_products.append(Product.model_validate(p))
            except Exception:
                pass

        return SearchResultsResponse(
            thread_id=msg.thread_id,
            user_id=user_id,
            query=query_text,
            total_results=len(validated_products),
            products=validated_products,
            formatted_message=msg.content,
        )
    finally:
        db.close()


@router.get("", response_model=SearchResultsResponse, summary="Get search results discovered in chat session (GET)")
async def get_chat_search_results(
    thread_id: Optional[str] = Query(None, description="Chat thread ID to retrieve search results for"),
    user_id: str = Query("guest_user", description="User ID"),
) -> SearchResultsResponse:
    """Returns the products returned by the search node during the chat conversation.

    Does NOT execute a new query to SerpAPI. Purely retrieves the chat's search findings.
    """
    return _get_chat_search_results(thread_id, user_id)


@router.post("", response_model=SearchResultsResponse, summary="Get search results discovered in chat session (POST)")
async def post_chat_search_results(payload: SearchLookupPayload) -> SearchResultsResponse:
    """Alternative POST endpoint to look up search results from a chat thread."""
    return _get_chat_search_results(payload.thread_id, payload.user_id or "guest_user")
