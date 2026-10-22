"""Shared LangGraph state schema."""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """State passed between graph nodes. All keys optional (partial updates)."""

    query: str
    user_id: str | None
    thread_id: int | None
    run_id: int | None
    message_history: list[dict[str, str]]
    intent: str
    parsed: dict[str, Any]
    engines: list[str]
    results: dict[str, list[dict[str, Any]]]
    products: list[dict[str, Any]]
    engine_errors: dict[str, str]
    answer: str
    error: str | None
