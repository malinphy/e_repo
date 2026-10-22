"""Per-engine results of an agent run (one row per engine call, one per product)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..common.db.base import Base


class EngineCall(Base):
    """One marketplace query performed during a run.

    Even a failed engine gets a row, so the API can report "walmart is
    unavailable" instead of an indistinguishable empty list.
    """

    __tablename__ = "engine_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engine: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EngineProduct(Base):
    """A single normalized product returned by one engine during a run."""

    __tablename__ = "engine_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engine: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews: Mapped[int | None] = mapped_column(Integer, nullable=True)
