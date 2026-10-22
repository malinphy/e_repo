"""Search and chat endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..agent.deps import AgentDeps
from ..agent.runner import run_agent
from ..repositories.chat_thread_repo import ChatThreadRepository
from ..services.engine_search import product_rows
from .deps import get_agent_deps, get_agent_graph
from .schemas import ChatRequest, ChatResponse, SearchRequest, SearchResponse

_DEFAULT_THREAD_TITLE = "New conversation"

router = APIRouter(tags=["agent"])


def _execute(
    query: str,
    user_id: str | None,
    deps: AgentDeps,
    graph: Any,
    thread_id: int | None = None,
) -> dict[str, Any]:
    return run_agent(
        query=query, user_id=user_id, thread_id=thread_id, deps=deps, graph=graph
    )


def _grouped(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        engine: product_rows(engine, hits)
        for engine, hits in (state.get("results") or {}).items()
    }


def _resolve_thread(
    thread_id: int | None, user_id: str | None, deps: AgentDeps
) -> int | None:
    """Return the thread to attach this turn to.

    * explicit ``thread_id`` that exists → validate ownership and reuse it;
    * explicit ``thread_id`` that does not exist → start a fresh thread (if a
      ``user_id`` is available) instead of failing, and return its new id;
    * no ``thread_id`` but a ``user_id`` → create a fresh thread for that user;
    * neither → stay thread-less (stateless chat, legacy behavior).
    """
    session = deps.session_factory()
    try:
        threads = ChatThreadRepository(session)

        if thread_id is not None:
            thread = threads.get(thread_id)
            if thread is not None:
                if user_id is not None and user_id != thread.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="user_id does not match thread owner",
                    )
                return thread.id
            # Non-existent thread id: fall through and create a fresh one.

        if user_id is not None:
            thread = threads.create(user_id=user_id, title=_DEFAULT_THREAD_TITLE)
            session.commit()
            return thread.id

        return None
    finally:
        session.close()


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    deps: AgentDeps = Depends(get_agent_deps),
    graph: Any = Depends(get_agent_graph),
) -> SearchResponse:
    state = _execute(payload.query, payload.user_id, deps, graph, thread_id=payload.thread_id)
    return SearchResponse(
        run_id=state.get("run_id"),
        thread_id=state.get("thread_id"),
        query=state.get("query", payload.query),
        engines=state.get("engines") or [],
        answer=state.get("answer", ""),
        products=state.get("products") or [],
        results=_grouped(state),
        engine_errors=state.get("engine_errors") or {},
        error=state.get("error"),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    deps: AgentDeps = Depends(get_agent_deps),
    graph: Any = Depends(get_agent_graph),
) -> ChatResponse:
    thread_id = _resolve_thread(payload.thread_id, payload.user_id, deps)
    state = _execute(payload.message, payload.user_id, deps, graph, thread_id=thread_id)
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
