"""Repository for per-engine results of a run (Repository pattern)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models.engine_results import EngineCall, EngineProduct


def _as_float(value: Any) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


class EngineResultsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_run(
        self,
        run_id: int,
        results: Mapping[str, Sequence[Mapping[str, Any]]],
        errors: Mapping[str, str] | None = None,
    ) -> None:
        """Persist one run's per-engine results, replacing anything already stored.

        Idempotent: a re-executed ``persist`` node overwrites instead of
        duplicating rows.
        """
        errors = errors or {}
        self._session.execute(delete(EngineProduct).where(EngineProduct.run_id == run_id))
        self._session.execute(delete(EngineCall).where(EngineCall.run_id == run_id))

        for engine, hits in results.items():
            products = [hit for hit in hits if "error" not in hit]
            self._session.add(
                EngineCall(
                    run_id=run_id,
                    engine=engine,
                    result_count=len(products),
                    error=errors.get(engine),
                )
            )
            for position, hit in enumerate(products):
                self._session.add(
                    EngineProduct(
                        run_id=run_id,
                        engine=engine,
                        position=position,
                        title=_as_text(hit.get("title")),
                        price=_as_text(hit.get("price")),
                        source=_as_text(hit.get("source")),
                        link=_as_text(hit.get("link")),
                        rating=_as_float(hit.get("rating")),
                        reviews=_as_int(hit.get("reviews")),
                    )
                )
        self._session.flush()

    def calls_for_run(self, run_id: int) -> list[EngineCall]:
        stmt = select(EngineCall).where(EngineCall.run_id == run_id).order_by(EngineCall.engine)
        return list(self._session.scalars(stmt).all())

    def call_for_run(self, run_id: int, engine: str) -> EngineCall | None:
        stmt = select(EngineCall).where(
            EngineCall.run_id == run_id, EngineCall.engine == engine
        )
        return self._session.scalars(stmt).first()

    def products_for_run(self, run_id: int, engine: str) -> list[EngineProduct]:
        stmt = (
            select(EngineProduct)
            .where(EngineProduct.run_id == run_id, EngineProduct.engine == engine)
            .order_by(EngineProduct.position)
        )
        return list(self._session.scalars(stmt).all())

    def latest_call(self, engine: str) -> EngineCall | None:
        """Most recent recorded call for one engine, across all runs."""
        stmt = (
            select(EngineCall)
            .where(EngineCall.engine == engine)
            .order_by(EngineCall.run_id.desc(), EngineCall.id.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()
