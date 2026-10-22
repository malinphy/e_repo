"""History and run-inspection endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..agent.deps import AgentDeps
from ..repositories.agent_runs_repo import AgentRunRepository
from ..repositories.search_history_repo import SearchHistoryRepository
from .deps import get_agent_deps
from .schemas import RunOut, SearchHistoryOut

router = APIRouter(tags=["history"])


@router.get("/search/history", response_model=list[SearchHistoryOut])
def search_history(
    user_id: str = Query(min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    deps: AgentDeps = Depends(get_agent_deps),
) -> list[SearchHistoryOut]:
    session = deps.session_factory()
    try:
        rows = SearchHistoryRepository(session).list_for_user(user_id, limit=limit)
        return [SearchHistoryOut.from_orm_row(row) for row in rows]
    finally:
        session.close()


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, deps: AgentDeps = Depends(get_agent_deps)) -> RunOut:
    session = deps.session_factory()
    try:
        row = AgentRunRepository(session).get(run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
        return RunOut.from_orm_row(row)
    finally:
        session.close()
