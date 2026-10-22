"""plan_tools node: decide which SerpAPI engines to execute."""
from __future__ import annotations

from typing import Any

from ..deps import AgentDeps
from ..state import AgentState


def make_plan_tools_node(deps: AgentDeps):
    def plan_tools(state: AgentState) -> dict[str, Any]:
        parsed = state.get("parsed") or {}
        requested = [e for e in parsed.get("engines", []) if e in deps.engines]
        selected = requested or list(deps.engines.keys())
        return {"engines": selected}

    return plan_tools
