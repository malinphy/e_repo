"""execute_tools node: run the selected engine adapters and flatten results."""
from __future__ import annotations

from typing import Any

from ..deps import AgentDeps
from ..state import AgentState
from ...services.engine_search import EngineSearchService, product_rows

RESULTS_PER_ENGINE = 10


def make_execute_tools_node(deps: AgentDeps):
    service = EngineSearchService(deps.engines)

    def execute_tools(state: AgentState) -> dict[str, Any]:
        parsed = state.get("parsed") or {}
        keywords = parsed.get("keywords") or state.get("query", "")
        selected = state.get("engines") or service.available

        results: dict[str, list[dict[str, Any]]] = {}
        products: list[dict[str, Any]] = []
        engine_errors: dict[str, str] = {}

        for outcome in service.search_many(keywords, selected, num=RESULTS_PER_ENGINE):
            results[outcome.engine] = outcome.products
            if outcome.error:
                engine_errors[outcome.engine] = outcome.error
            products.extend(product_rows(outcome.engine, outcome.products))

        update: dict[str, Any] = {
            "results": results,
            "products": products,
            "engine_errors": engine_errors,
        }
        if engine_errors and not products:
            update["error"] = "; ".join(f"{name}: {msg}" for name, msg in engine_errors.items())
        return update

    return execute_tools
