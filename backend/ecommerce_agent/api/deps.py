"""FastAPI dependency providers."""
from __future__ import annotations

from typing import Any

from fastapi import Request

from ..agent.deps import AgentDeps


def get_agent_deps(request: Request) -> AgentDeps:
    return request.app.state.agent_deps


def get_agent_graph(request: Request) -> Any:
    return request.app.state.agent_graph
