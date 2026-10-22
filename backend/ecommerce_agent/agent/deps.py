"""Dependency container injected into graph nodes (Factory + DI)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from sqlalchemy.orm import Session

from ..tools.serpapi.base import SerpAPIEngineAdapter


class ChatModelProtocol(Protocol):
    def invoke(self, input: Any, **kwargs: Any) -> Any: ...


@dataclass
class AgentDeps:
    """Runtime dependencies for the agent graph.

    Attributes:
        engines: Mapping of engine name -> adapter.
        llm_factory: Callable returning a LangChain chat model (or None to skip LLM).
        session_factory: Callable returning a SQLAlchemy Session.
    """

    engines: dict[str, SerpAPIEngineAdapter]
    llm_factory: Callable[[], ChatModelProtocol | None]
    session_factory: Callable[[], Session]
