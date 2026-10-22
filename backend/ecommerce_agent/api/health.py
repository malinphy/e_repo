"""Health endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..agent.deps import AgentDeps
from .. import __version__
from .deps import get_agent_deps
from .schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(deps: AgentDeps = Depends(get_agent_deps)) -> HealthOut:
    return HealthOut(
        status="ok",
        version=__version__,
        engines=sorted(deps.engines.keys()),
    )
