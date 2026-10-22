"""History and run-inspection endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..agent.deps import AgentDeps
from ..repositories.agent_runs_repo import AgentRunRepository
from ..repositories.engine_results_repo import EngineResultsRepository
from ..repositories.search_history_repo import SearchHistoryRepository
from .deps import get_agent_deps
from .schemas import (
    EngineCallOut,
    ProductOut,
    RunEngineOut,
    RunEnginesOut,
    RunOut,
    SearchHistoryOut,
)

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


@router.get("/runs/{run_id}/engines", response_model=RunEnginesOut)
def get_run_engines(run_id: int, deps: AgentDeps = Depends(get_agent_deps)) -> RunEnginesOut:
    """Per-marketplace summary of what each engine returned during this run."""
    session = deps.session_factory()
    try:
        run = AgentRunRepository(session).get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        calls = EngineResultsRepository(session).calls_for_run(run_id)
        return RunEnginesOut(
            run_id=run_id,
            query=run.query,
            engines=[EngineCallOut.from_orm_row(call) for call in calls],
        )
    finally:
        session.close()


@router.get("/runs/{run_id}/engines/{engine}", response_model=RunEngineOut)
def get_run_engine(
    run_id: int, engine: str, deps: AgentDeps = Depends(get_agent_deps)
) -> RunEngineOut:
    """Exactly what one marketplace returned during this run."""
    session = deps.session_factory()
    try:
        run = AgentRunRepository(session).get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")

        repo = EngineResultsRepository(session)
        call = repo.call_for_run(run_id, engine)
        if call is None:
            raise HTTPException(
                status_code=404,
                detail=f"engine '{engine}' did not run for run {run_id}",
            )

        rows = repo.products_for_run(run_id, engine)
        return RunEngineOut(
            run_id=run_id,
            engine=engine,
            query=run.query,
            result_count=call.result_count,
            error=call.error,
            created_at=call.created_at,
            products=[ProductOut.from_orm_row(row) for row in rows],
        )
    finally:
        session.close()

