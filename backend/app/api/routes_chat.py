"""Chat endpoint and thread management routing requests to the LangGraph agent."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy import delete, select

from ..agent.graph import build_shop_graph
from ..core.database import SessionLocal
from ..models.chat import ChatMessage, ChatThread
from ..schemas.api import ChatRequest, ChatResponse
from ..schemas.product import Product

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Pre-compiled agent graph instance
_agent_graph = build_shop_graph()


class ThreadSummary(BaseModel):
    thread_id: str
    user_id: str
    title: Optional[str]
    created_at: str
    updated_at: str


class ThreadMessageItem(BaseModel):
    id: str
    role: str
    content: str
    intent: Optional[str]
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("", response_model=ChatResponse, summary="Send message to shopping assistant (ChatGPT-style thread isolation)")
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Processes user message through LangGraph with strict thread isolation.

    - If `thread_id` is provided: Loads and continues the history OF THAT SPECIFIC THREAD ONLY.
    - If `thread_id` is empty/null: Automatically starts a NEW thread (like clicking 'New Chat' in ChatGPT)
      and returns the new `thread_id` for the client to use in subsequent turns.
    """
    user_id = request.user_id or "guest_user"
    is_new_thread = not bool(request.thread_id)
    thread_id = request.thread_id or f"th_{uuid.uuid4().hex[:10]}"
    chat_id = f"chat_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    db = SessionLocal()
    try:
        # 1. Thread entity handling in DB
        thread = db.scalar(select(ChatThread).where(ChatThread.thread_id == thread_id))
        if not thread:
            # Generate title from first message
            title = request.message[:50].strip()
            thread = ChatThread(thread_id=thread_id, user_id=user_id, title=title)
            db.add(thread)
            db.commit()
            db.refresh(thread)

        # 2. Strict thread history restoration (isolated to this thread_id only)
        current_graph_state = _agent_graph.get_state(config)
        existing_in_state = current_graph_state.values.get("messages") if current_graph_state else None

        input_messages = []
        if not existing_in_state:
            db_history = db.scalars(
                select(ChatMessage)
                .where(ChatMessage.thread_id == thread_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(30)
            ).all()
            for m in db_history:
                if m.role == "user":
                    input_messages.append(HumanMessage(content=m.content))
                elif m.role == "assistant":
                    input_messages.append(AIMessage(content=m.content))
    finally:
        db.close()

    input_messages.append(HumanMessage(content=request.message))

    state_input = {
        "messages": input_messages,
        "user_id": user_id,
        "thread_id": thread_id,
        "chat_id": chat_id,
    }

    try:
        result = await _agent_graph.ainvoke(state_input, config=config)
    except Exception as exc:
        logger.exception("Error executing chat graph: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent graph execution failed: {exc}")

    # Extract assistant reply from messages
    messages = result.get("messages") or []
    reply_text = messages[-1].content if messages else "Yanıt üretilemedi."

    # Parse last_results into validated Product objects
    raw_products = result.get("last_results") or []
    validated_products: list[Product] = []
    for item in raw_products:
        try:
            validated_products.append(Product.model_validate(item))
        except Exception:
            pass

    return ChatResponse(
        reply=str(reply_text),
        intent=result.get("intent") or "unknown",
        user_id=user_id,
        thread_id=thread_id,
        chat_id=chat_id,
        products=validated_products,
        cart=result.get("cart") or [],
    )


class CreateThreadRequest(BaseModel):
    user_id: Optional[str] = "guest_user"
    title: Optional[str] = "Yeni Sohbet"


@router.post("/threads", response_model=ThreadSummary, summary="Create a new chat thread (ChatGPT 'New Chat' button)")
async def create_new_thread(req: Optional[CreateThreadRequest] = None):
    """Creates a new isolated chat thread for the user."""
    user_id = (req.user_id if req else None) or "guest_user"
    title = (req.title if req else None) or "Yeni Sohbet"
    thread_id = f"th_{uuid.uuid4().hex[:10]}"

    db = SessionLocal()
    try:
        thread = ChatThread(thread_id=thread_id, user_id=user_id, title=title)
        db.add(thread)
        db.commit()
        db.refresh(thread)
        return ThreadSummary(
            thread_id=thread.thread_id,
            user_id=thread.user_id,
            title=thread.title,
            created_at=thread.created_at.isoformat() if thread.created_at else "",
            updated_at=thread.updated_at.isoformat() if thread.updated_at else "",
        )
    finally:
        db.close()


@router.get("/threads", response_model=List[ThreadSummary], summary="List all chat threads for a user (Sidebar)")
async def list_user_threads(user_id: str = Query("guest_user", description="User ID")):
    """Returns all conversations owned by the user, sorted with the most recent first."""
    db = SessionLocal()
    try:
        threads = db.scalars(
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.updated_at.desc())
        ).all()
        return [
            ThreadSummary(
                thread_id=t.thread_id,
                user_id=t.user_id,
                title=t.title or "Sohbet",
                created_at=t.created_at.isoformat() if t.created_at else "",
                updated_at=t.updated_at.isoformat() if t.updated_at else "",
            )
            for t in threads
        ]
    finally:
        db.close()


@router.get("/threads/{thread_id}/messages", response_model=List[ThreadMessageItem], summary="Get messages of a specific thread")
async def get_thread_messages(thread_id: str):
    """Returns all conversation history for a specific thread_id."""
    db = SessionLocal()
    try:
        messages = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at.asc())
        ).all()
        return [
            ThreadMessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                created_at=m.created_at.isoformat() if m.created_at else "",
                metadata=m.metadata_json,
            )
            for m in messages
        ]
    finally:
        db.close()


@router.delete("/threads/{thread_id}", summary="Delete a chat thread and its messages")
async def delete_thread(thread_id: str):
    """Deletes a thread and all associated messages from SQLite."""
    db = SessionLocal()
    try:
        db.execute(delete(ChatThread).where(ChatThread.thread_id == thread_id))
        db.commit()
        return {"status": "success", "message": f"Thread '{thread_id}' deleted."}
    finally:
        db.close()
