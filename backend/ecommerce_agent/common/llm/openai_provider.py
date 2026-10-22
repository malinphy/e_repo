"""OpenAI chat model provider."""
from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._default_model = default_model

    def get_chat_model(self, **kwargs: Any) -> ChatOpenAI:
        model = kwargs.pop("model", self._default_model)
        return ChatOpenAI(api_key=self._api_key, model=model, **kwargs)
