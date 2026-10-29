"""Chat endpoint and thread management routing requests to the LangGraph agent."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import delete, select

from ..agent.graph import build_shop_graph, get_compiled_shop_graph
from ..core.database import SessionLocal
from ..models.chat import ChatMessage, ChatThread
from ..models.user import User
from ..schemas.api import ChatRequest, ChatResponse, CheckoutResumeRequest
from ..schemas.product import Product

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


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
    """Processes user message through LangGraph with strict thread isolation backed by SqliteSaver."""
    user_id = request.user_id or "guest_user"
    thread_id = request.thread_id or f"th_{uuid.uuid4().hex[:10]}"
    chat_id = f"chat_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    db = SessionLocal()
    try:
        # 0. Ensure user exists in DB
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            user = User(id=user_id, name="Guest User")
            db.add(user)
            db.flush()

        # 1. Thread entity handling in DB
        thread = db.scalar(select(ChatThread).where(ChatThread.thread_id == thread_id))
        if not thread:
            title = request.message[:50].strip()
            thread = ChatThread(thread_id=thread_id, user_id=user_id, title=title)
            db.add(thread)
            db.commit()
            db.refresh(thread)
    finally:
        db.close()

    # Get compiled graph backed by persistent AsyncSqliteSaver
    graph = await get_compiled_shop_graph()

    state_input = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": user_id,
        "thread_id": thread_id,
        "chat_id": chat_id,
    }

    # Check if thread has an active interrupt awaiting human approval
    current_state_check = await graph.aget_state(config)
    has_active_interrupt = bool(
        current_state_check
        and current_state_check.tasks
        and any(task.interrupts for task in current_state_check.tasks)
    )

    pending_action = None
    try:
        if has_active_interrupt:
            lowered = request.message.strip().lower()
            if any(w in lowered for w in ("yes", "approve", "confirm", "ok", "pay", "buy")):
                result = await graph.ainvoke(Command(resume={"approved": True}), config=config)
            elif any(w in lowered for w in ("no", "cancel", "abort", "stop", "decline")):
                result = await graph.ainvoke(Command(resume={"approved": False}), config=config)
            else:
                # Cancel pending checkout and continue with new query
                await graph.ainvoke(Command(resume={"approved": False}), config=config)
                result = await graph.ainvoke(state_input, config=config)
        else:
            result = await graph.ainvoke(state_input, config=config)
    except Exception as exc:
        logger.exception("Error executing chat graph: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent graph execution failed: {exc}")

    # Check if execution paused on a new LangGraph interrupt (HITL)
    if result.get("__interrupt__"):
        interrupt_info = result["__interrupt__"][0].value
        pending_action = interrupt_info
        reply_text = interrupt_info.get("summary_message") or interrupt_info.get("prompt") or "Awaiting approval for your action."

        # Persist the interrupt prompt to chat_messages
        db = SessionLocal()
        try:
            db.add(ChatMessage(thread_id=thread_id, role="user", content=str(request.message), intent="checkout"))
            db.add(
                ChatMessage(
                    thread_id=thread_id,
                    role="assistant",
                    content=str(reply_text),
                    intent="checkout",
                    metadata_json={"pending_action": pending_action},
                )
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to persist interrupted chat message: %s", exc)
        finally:
            db.close()
    else:
        # Extract assistant reply from messages
        messages = result.get("messages") or []
        reply_text = messages[-1].content if messages else "Unable to generate reply."

        # Persist normal conversation turn to SQLite for sidebar and search lookups
        db = SessionLocal()
        try:
            thread = db.scalar(select(ChatThread).where(ChatThread.thread_id == thread_id))
            if thread:
                thread.updated_at = datetime.now(timezone.utc)
                if not thread.title or thread.title in ("Shopping Chat", "Chat", "New Chat", "New Shopping Chat"):
                    thread.title = str(request.message)[:50].strip()

            metadata = None
            if result.get("intent") == "search":
                metadata = {}
                if result.get("last_results"):
                    metadata["products"] = result.get("last_results")
                if result.get("search_query"):
                    metadata["search_query"] = result.get("search_query")

            db.add(ChatMessage(thread_id=thread_id, role="user", content=str(request.message), intent=result.get("intent")))
            db.add(
                ChatMessage(
                    thread_id=thread_id,
                    role="assistant",
                    content=str(reply_text),
                    intent=result.get("intent"),
                    metadata_json=metadata,
                )
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to persist chat turn in API: %s", exc)
        finally:
            db.close()

    # Parse last_results into validated Product objects ONLY for search turns
    validated_products: list[Product] = []
    if result.get("intent") == "search":
        raw_products = result.get("last_results") or []
        for item in raw_products:
            try:
                validated_products.append(Product.model_validate(item))
            except Exception:
                pass

    return ChatResponse(
        reply=str(reply_text),
        intent=result.get("intent") or "checkout" if pending_action else (result.get("intent") or "unknown"),
        user_id=user_id,
        thread_id=thread_id,
        chat_id=chat_id,
        products=validated_products,
        cart=result.get("cart") or [],
        pending_action=pending_action,
    )


@router.post("/resume", response_model=ChatResponse, summary="Resume checkout approval via button click (Human-in-the-Loop)")
async def resume_checkout_endpoint(request: CheckoutResumeRequest) -> ChatResponse:
    """Resumes an interrupted LangGraph checkout workflow when the user clicks an action button."""
    config = {"configurable": {"thread_id": request.thread_id}}
    chat_id = f"chat_{uuid.uuid4().hex[:8]}"
    user_id = request.user_id or "guest_user"

    graph = await get_compiled_shop_graph()

    # Verify that an active interrupt is waiting on this thread
    current_state = await graph.aget_state(config)
    has_interrupt = bool(
        current_state
        and current_state.tasks
        and any(task.interrupts for task in current_state.tasks)
    )

    if not has_interrupt:
        raise HTTPException(
            status_code=400,
            detail=f"No active pending action/approval found for thread '{request.thread_id}'."
        )

    try:
        result = await graph.ainvoke(
            Command(resume={"approved": request.approved}),
            config=config,
        )
    except Exception as exc:
        logger.exception("Error resuming checkout graph: %s", exc)
        raise HTTPException(status_code=500, detail=f"Checkout resume failed: {exc}")

    messages = result.get("messages") or []
    reply_text = messages[-1].content if messages else "Action completed."

    # Persist decision to thread history
    db = SessionLocal()
    try:
        decision_text = "Approved checkout order." if request.approved else "Cancelled checkout order."
        db.add(ChatMessage(thread_id=request.thread_id, role="user", content=decision_text, intent="checkout"))
        db.add(ChatMessage(thread_id=request.thread_id, role="assistant", content=str(reply_text), intent="checkout"))
        db.commit()
    except Exception as exc:
        db.rollback()
    finally:
        db.close()

    validated_products: list[Product] = []

    return ChatResponse(
        reply=str(reply_text),
        intent="checkout",
        user_id=user_id,
        thread_id=request.thread_id,
        chat_id=chat_id,
        products=validated_products,
        cart=result.get("cart") or [],
        pending_action=None,
    )


class CreateThreadRequest(BaseModel):
    user_id: Optional[str] = "guest_user"
    title: Optional[str] = "New Chat"


@router.post("/threads", response_model=ThreadSummary, summary="Create a new chat thread (ChatGPT 'New Chat' button)")
async def create_new_thread(req: Optional[CreateThreadRequest] = None):
    """Creates a new isolated chat thread for the user."""
    user_id = (req.user_id if req else None) or "guest_user"
    title = (req.title if req else None) or "New Shopping Chat"
    thread_id = f"th_{uuid.uuid4().hex[:10]}"

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            user = User(id=user_id, name="Guest User")
            db.add(user)
            db.flush()

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
                title=t.title or "Chat",
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
