"""Chat thread and message endpoints for multi-user conversation support."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..agent.deps import AgentDeps
from ..agent.runner import run_agent
from ..repositories.chat_message_repo import ChatMessageRepository
from ..repositories.chat_thread_repo import ChatThreadRepository
from ..services.engine_search import product_rows
from .deps import get_agent_deps, get_agent_graph
from .schemas import (
    ChatMessageOut,
    ChatResponse,
    ChatThreadOut,
    CreateThreadRequest,
    SendMessageRequest,
    ThreadHistoryOut,
)

router = APIRouter(tags=["chat"])


def _grouped(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        engine: product_rows(engine, hits)
        for engine, hits in (state.get("results") or {}).items()
    }


@router.post("/users/{user_id}/threads", response_model=ChatThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(
    user_id: str,
    payload: CreateThreadRequest,
    deps: AgentDeps = Depends(get_agent_deps),
) -> ChatThreadOut:
    """Create a new chat thread for a user."""
    if payload.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id in path and body do not match",
        )
    session = deps.session_factory()
    try:
        thread = ChatThreadRepository(session).create(user_id=user_id, title=payload.title)
        session.commit()
        return ChatThreadOut.from_orm_row(thread)
    finally:
        session.close()


@router.get("/users/{user_id}/threads", response_model=list[ChatThreadOut])
def list_threads(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    deps: AgentDeps = Depends(get_agent_deps),
) -> list[ChatThreadOut]:
    """List recent chat threads for a user."""
    session = deps.session_factory()
    try:
        threads = ChatThreadRepository(session).list_for_user(user_id, limit=limit)
        return [ChatThreadOut.from_orm_row(t) for t in threads]
    finally:
        session.close()


@router.post("/chat/{thread_id}/message", response_model=ChatResponse)
def send_message(
    thread_id: int,
    payload: SendMessageRequest,
    deps: AgentDeps = Depends(get_agent_deps),
    graph: Any = Depends(get_agent_graph),
) -> ChatResponse:
    """Send a message in a thread and run the agent with conversation context."""
    session = deps.session_factory()
    try:
        thread = ChatThreadRepository(session).get(thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="thread not found")
        if payload.user_id is not None and payload.user_id != thread.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id does not match thread owner",
            )
    finally:
        session.close()

    state = run_agent(
        query=payload.message,
        user_id=payload.user_id or thread.user_id,
        thread_id=thread_id,
        deps=deps,
        graph=graph,
    )
    return ChatResponse(
        run_id=state.get("run_id"),
            thread_id=state.get("thread_id"),
            query=state.get("query", payload.message),
            answer=state.get("answer", ""),
            products=state.get("products") or [],
            results=_grouped(state),
            engine_errors=state.get("engine_errors") or {},
            error=state.get("error"),
        )


@router.get("/chat/{thread_id}/history", response_model=ThreadHistoryOut)
def get_thread_history(
    thread_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    deps: AgentDeps = Depends(get_agent_deps),
) -> ThreadHistoryOut:
    """Return all messages in a chat thread, oldest first."""
    session = deps.session_factory()
    try:
        thread = ChatThreadRepository(session).get(thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="thread not found")
        messages = ChatMessageRepository(session).list_for_thread(thread_id, limit=limit)
        return ThreadHistoryOut(
            thread_id=thread_id,
            messages=[ChatMessageOut.from_orm_row(m) for m in messages],
        )
    finally:
        session.close()