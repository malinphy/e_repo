"""Per-engine result endpoints.

Two views of the same data:

* ``GET /amazon``, ``GET /ebay``, ``GET /google_shopping``, ``GET /walmart``
  (aliased as ``GET /engines/{engine}``) — what one marketplace returned for
  the **last chat or search run**, read from the database. No query, no SerpAPI
  call, no LLM call: these are the endpoints a frontend polls after
  ``POST /chat``.
* ``POST /engines/{engine}/search`` and ``POST /engines/search`` — ad-hoc raw
  searches that bypass the agent pipeline. Useful for debugging one
  marketplace; every call costs real SerpAPI credits.

Use ``GET /runs/{run_id}/engines/{engine}`` (or ``GET /amazon?run_id=…``) to
read an older run instead of the latest one.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..agent.deps import AgentDeps
from ..repositories.agent_runs_repo import AgentRunRepository
from ..repositories.engine_results_repo import EngineResultsRepository
from ..services.engine_search import EngineSearchService, product_rows
from .deps import get_agent_deps
from .schemas import (
    EngineSearchRequest,
    EngineSearchResponse,
    EnginesOut,
    MultiEngineSearchRequest,
    MultiEngineSearchResponse,
    ProductOut,
    RunEngineOut,
)

router = APIRouter(tags=["engines"])


def get_engine_service(deps: AgentDeps = Depends(get_agent_deps)) -> EngineSearchService:
    return EngineSearchService(deps.engines)


def _require_known(service: EngineSearchService, names: list[str]) -> None:
    unknown = [name for name in names if not service.has(name)]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"unknown engine(s): {', '.join(unknown)}; "
                f"available: {', '.join(service.available) or 'none'}"
            ),
        )


@router.get("/engines", response_model=EnginesOut)
def list_engines(service: EngineSearchService = Depends(get_engine_service)) -> EnginesOut:
    """Names accepted by the per-engine search endpoints."""
    return EnginesOut(engines=service.available)


_RUN_ID_DESCRIPTION = "Read this run instead of the most recent one."


def _read_engine_result(
    engine: str,
    run_id: int | None,
    service: EngineSearchService,
    deps: AgentDeps,
) -> RunEngineOut:
    """Shared implementation behind every per-engine read endpoint."""
    _require_known(service, [engine])

    session = deps.session_factory()
    try:
        repo = EngineResultsRepository(session)
        call = (
            repo.call_for_run(run_id, engine)
            if run_id is not None
            else repo.latest_call(engine)
        )
        if call is None:
            detail = (
                f"engine '{engine}' did not run for run {run_id}"
                if run_id is not None
                else f"no results stored for engine '{engine}' yet; ask via POST /chat first"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

        run = AgentRunRepository(session).get(call.run_id)
        rows = repo.products_for_run(call.run_id, engine)
        return RunEngineOut(
            run_id=call.run_id,
            engine=engine,
            query=run.query if run is not None else "",
            result_count=call.result_count,
            error=call.error,
            created_at=call.created_at,
            products=[ProductOut.from_orm_row(row) for row in rows],
        )
    finally:
        session.close()


def _engine_reader(engine: str):
    """Build one fixed, per-marketplace GET route (``GET /amazon``, …)."""

    def read_latest(
        run_id: int | None = Query(default=None, ge=1, description=_RUN_ID_DESCRIPTION),
        service: EngineSearchService = Depends(get_engine_service),
        deps: AgentDeps = Depends(get_agent_deps),
    ) -> RunEngineOut:
        return _read_engine_result(engine, run_id, service, deps)

    read_latest.__name__ = f"read_{engine}"
    read_latest.__doc__ = (
        f"Products the {engine} marketplace returned for the last chat/search run."
    )
    return read_latest


@router.get("/engines/{engine}", response_model=RunEngineOut)
def latest_engine_result(
    engine: str,
    run_id: int | None = Query(default=None, ge=1, description=_RUN_ID_DESCRIPTION),
    service: EngineSearchService = Depends(get_engine_service),
    deps: AgentDeps = Depends(get_agent_deps),
) -> RunEngineOut:
    """Products one marketplace returned for the last chat/search run.

    The question comes from the chat request, not from this endpoint: results are
    read back from the database that ``POST /chat`` and ``POST /search`` write.
    """
    return _read_engine_result(engine, run_id, service, deps)


# Fixed, frontend-friendly read routes: GET /amazon, GET /ebay, …
for _engine in ("amazon", "ebay", "google_shopping", "walmart"):
    router.add_api_route(
        f"/{_engine}",
        _engine_reader(_engine),
        methods=["GET"],
        response_model=RunEngineOut,
        name=f"read_{_engine}",
        summary=f"Latest {_engine} results from the last chat/search run",
    )


@router.post("/engines/search", response_model=MultiEngineSearchResponse)
def search_all_engines(
    payload: MultiEngineSearchRequest,
    service: EngineSearchService = Depends(get_engine_service),
) -> MultiEngineSearchResponse:
    """Query several engines (default: all of them) in one request."""
    selected = payload.engines if payload.engines is not None else service.available
    _require_known(service, selected)

    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}
    for outcome in service.search_many(payload.query, selected, num=payload.num):
        results[outcome.engine] = product_rows(outcome.engine, outcome.products)
        if outcome.error:
            errors[outcome.engine] = outcome.error

    return MultiEngineSearchResponse(
        query=payload.query,
        engines=list(results),
        count=sum(len(items) for items in results.values()),
        results=results,
        errors=errors,
    )


@router.post("/engines/{engine}/search", response_model=EngineSearchResponse)
def search_single_engine(
    engine: str,
    payload: EngineSearchRequest,
    service: EngineSearchService = Depends(get_engine_service),
) -> EngineSearchResponse:
    """Query one engine and return its normalized products.

    An upstream SerpAPI failure is reported in ``error`` with HTTP 200, so a
    client can show "this marketplace is unavailable" without retry loops.
    """
    _require_known(service, [engine])

    outcome = service.search(engine, payload.query, num=payload.num)
    rows = product_rows(outcome.engine, outcome.products)
    return EngineSearchResponse(
        engine=outcome.engine,
        query=payload.query,
        query_param=service.query_param(engine),
        count=len(rows),
        products=rows,
        error=outcome.error,
    )
