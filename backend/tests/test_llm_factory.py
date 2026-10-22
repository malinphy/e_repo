"""Tests for the LLM provider Strategy + Factory."""
from __future__ import annotations

from typing import Any

import pytest
from langchain_openai import ChatOpenAI

from ecommerce_agent.common.llm.base import LLMProvider
from ecommerce_agent.common.llm.factory import (
    available_providers,
    build_llm_provider,
    register_provider,
)
from ecommerce_agent.common.llm.openai_provider import OpenAIProvider


def test_openai_is_registered() -> None:
    assert "openai" in available_providers()


def test_build_llm_provider_returns_openai_provider() -> None:
    provider = build_llm_provider("openai", api_key="sk-test")
    assert isinstance(provider, OpenAIProvider)


def test_unknown_provider_raises_key_error() -> None:
    with pytest.raises(KeyError):
        build_llm_provider("does-not-exist")


def test_openai_provider_builds_chat_model() -> None:
    model = OpenAIProvider(api_key="sk-test", default_model="gpt-4o-mini").get_chat_model()
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4o-mini"


def test_get_chat_model_kwarg_overrides_default_model() -> None:
    provider = OpenAIProvider(api_key="sk-test", default_model="gpt-4o-mini")
    model = provider.get_chat_model(model="gpt-4o")
    assert model.model_name == "gpt-4o"


def test_register_provider_extends_factory() -> None:
    class DummyProvider(LLMProvider):
        name = "dummy"

        def get_chat_model(self, **kwargs: Any) -> Any:  # pragma: no cover - trivial
            return None

    register_provider("dummy", DummyProvider)
    try:
        assert isinstance(build_llm_provider("dummy"), DummyProvider)
    finally:
        from ecommerce_agent.common.llm import factory

        factory._PROVIDERS.pop("dummy", None)
