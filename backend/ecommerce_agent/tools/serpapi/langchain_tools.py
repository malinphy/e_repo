"""Expose SerpAPI engine adapters as LangChain tools."""
from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from .base import SerpAPIEngineAdapter
from ...common.redaction import redact


def _make_runner(adapter: SerpAPIEngineAdapter):
    def _run(query: str, num_results: int = 10) -> str:
        results = adapter.search(query, num=num_results)
        return json.dumps(results[:num_results], ensure_ascii=False)

    return _run


def build_engine_tool(adapter: SerpAPIEngineAdapter) -> BaseTool:
    """Wrap one engine adapter as a LangChain tool."""
    return StructuredTool.from_function(
        func=_make_runner(adapter),
        name=f"search_{adapter.engine}",
        description=(
            f"Search products on {adapter.engine} via SerpAPI. "
            "Input: a product search query. Returns JSON list of products with "
            "title, price, source, link, rating, reviews."
        ),
    )


def build_engine_tools(engines: dict[str, SerpAPIEngineAdapter]) -> list[BaseTool]:
    return [build_engine_tool(adapter) for adapter in engines.values()]


def search_all_engines(
    engines: dict[str, SerpAPIEngineAdapter],
    query: str,
    num_results: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    """Call every engine adapter and collect normalized results."""
    collected: dict[str, list[dict[str, Any]]] = {}
    for name, adapter in engines.items():
        try:
            collected[name] = adapter.search(query, num=num_results)
        except Exception as exc:  # noqa: BLE001 - one engine failing must not kill the run
            collected[name] = [{"error": redact(str(exc))}]
    return collected
