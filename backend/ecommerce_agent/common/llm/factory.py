"""LLM provider factory (Factory pattern)."""
from __future__ import annotations

from typing import Any

from .base import LLMProvider
from .openai_provider import OpenAIProvider


_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
}


def build_llm_provider(name: str, **config: Any) -> LLMProvider:
    """Build an LLM provider by name. Raises KeyError for unknown providers."""
    cls = _PROVIDERS[name]
    return cls(**config)


def register_provider(name: str, cls: type[LLMProvider]) -> None:
    """Register a new provider (used by tests / future providers)."""
    _PROVIDERS[name] = cls


def available_providers() -> list[str]:
    return sorted(_PROVIDERS.keys())
