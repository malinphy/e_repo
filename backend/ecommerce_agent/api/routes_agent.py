"""Search and chat endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..agent.deps import AgentDeps
from ..agent.runner import run_agent
from ..services.engine_search import product_rows
from .deps import get_agent_deps, get_agent_graph
from .schemas import ChatRequest, ChatResponse, SearchRequest, SearchResponse

router = APIRouter(tags=["agent"])


def _execute(
    query: str,
    user_id: str | None,
    deps: AgentDeps,
    graph: Any,
) -> dict[str, Any]:
    return run_agent(query=query, user_id=user_id, deps=deps, graph=graph)


def _grouped(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        engine: product_rows(engine, hits)
        for engine, hits in (state.get("results") or {}).items()
    }


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    deps: AgentDeps = Depends(get_agent_deps),
    graph: Any = Depends(get_agent_graph),
) -> SearchResponse:
    state = _execute(payload.query, payload.user_id, deps, graph)
    return SearchResponse(
        run_id=state.get("run_id"),
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
    state = _execute(payload.message, payload.user_id, deps, graph)
    return ChatResponse(
        run_id=state.get("run_id"),
        query=state.get("query", payload.message),
        answer=state.get("answer", ""),
        products=state.get("products") or [],
        results=_grouped(state),
        engine_errors=state.get("engine_errors") or {},
        error=state.get("error"),
    )
