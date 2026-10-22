"""LLM provider abstraction (Strategy pattern)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Strategy interface for chat model providers."""

    name: str

    @abstractmethod
    def get_chat_model(self, **kwargs: Any) -> Any:
        """Return a LangChain-compatible chat model instance."""
