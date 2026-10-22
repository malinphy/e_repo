"""Run the SerpAPI engine adapters (Facade over the Adapter family).

Both the agent's ``execute_tools`` node and the raw per-engine routes need the
same three rules, so they live here once instead of in every caller:

* one failing engine must not hide the others;
* failure text is redacted before it reaches a log or an API response;
* adapter hits are flattened into product dicts stamped with their engine.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..common.redaction import redact
from ..tools.serpapi.base import SerpAPIEngineAdapter

logger = logging.getLogger(__name__)

DEFAULT_NUM = 10
MAX_NUM = 100


@dataclass(frozen=True)
class EngineSearchResult:
    """Outcome of searching one engine: hits, or a redacted error message."""

    engine: str
    products: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def product_rows(engine: str, hits: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten one engine's hits into product dicts stamped with ``engine``.

    An entry carrying an ``error`` key reports an engine-level failure rather
    than a product, so it is dropped.
    """
    return [{**hit, "engine": engine} for hit in hits if "error" not in hit]


class EngineSearchService:
    """Facade over ``{name: SerpAPIEngineAdapter}`` with failure isolation."""

    def __init__(self, engines: Mapping[str, SerpAPIEngineAdapter]) -> None:
        self._engines = dict(engines)

    @property
    def available(self) -> list[str]:
        return sorted(self._engines)

    def has(self, engine: str) -> bool:
        return engine in self._engines

    def query_param(self, engine: str) -> str | None:
        """SerpAPI's query parameter name for ``engine``, when the adapter declares one."""
        return getattr(self._engines.get(engine), "query_param", None)

    def search(
        self, engine: str, query: str, num: int = DEFAULT_NUM
    ) -> EngineSearchResult:
        """Search a single engine. Never raises for a normal adapter failure."""
        adapter = self._engines.get(engine)
        if adapter is None:
            return EngineSearchResult(engine=engine, error=f"unknown engine '{engine}'")
        try:
            hits = adapter.search(query, num=num)
        except Exception as exc:  # noqa: BLE001 - isolate per-engine failures
            message = redact(f"{type(exc).__name__}: {exc}")
            logger.warning("engine %s failed: %s", engine, message)
            return EngineSearchResult(engine=engine, error=message)
        return EngineSearchResult(engine=engine, products=list(hits or []))

    def search_many(
        self,
        query: str,
        engines: Iterable[str] | None = None,
        num: int = DEFAULT_NUM,
    ) -> list[EngineSearchResult]:
        """Search several engines in order; ``None`` means every configured engine.

        Unknown engine names are skipped — callers validate names up front.
        """
        names = list(engines) if engines is not None else self.available
        return [self.search(name, query, num) for name in names if name in self._engines]
