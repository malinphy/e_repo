"""execute_tools node: run the selected engine adapters and flatten results."""
from __future__ import annotations

import logging
from typing import Any

from ..deps import AgentDeps
from ..state import AgentState
from ...common.redaction import redact

logger = logging.getLogger(__name__)


def make_execute_tools_node(deps: AgentDeps):
    def execute_tools(state: AgentState) -> dict[str, Any]:
        parsed = state.get("parsed") or {}
        keywords = parsed.get("keywords") or state.get("query", "")
        selected = state.get("engines") or list(deps.engines.keys())

        results: dict[str, list[dict[str, Any]]] = {}
        products: list[dict[str, Any]] = []
        errors: list[str] = []

        for name in selected:
            adapter = deps.engines.get(name)
            if adapter is None:
                continue
            try:
                hits = adapter.search(keywords, num=10)
            except Exception as exc:  # noqa: BLE001 - isolate per-engine failures
                message = redact(f"{type(exc).__name__}: {exc}")
                logger.warning("engine %s failed: %s", name, message)
                errors.append(f"{name}: {message}")
                hits = []
            results[name] = hits
            for hit in hits:
                if "error" in hit:
                    continue
                products.append({**hit, "engine": name})

        update: dict[str, Any] = {"results": results, "products": products}
        if errors and not products:
            update["error"] = "; ".join(errors)
        return update

    return execute_tools
