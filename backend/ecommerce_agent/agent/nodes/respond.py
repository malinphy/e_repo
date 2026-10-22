"""respond node: answer the non-search, non-cart intent (chit-chat) directly.

This is the worker for chit-chat: greetings/small talk get an LLM (or
fallback) reply without any SerpAPI search. It mirrors ``synthesize``'s
graceful degradation: no LLM is fine, and a failure never raises.
"""
from __future__ import annotations

import logging
from typing import Any

from ..deps import AgentDeps
from ..state import AgentState

logger = logging.getLogger(__name__)


def _fallback_reply(query: str) -> str:
    return f"Hi! How can I help you shop today? I'm not sure what you meant by '{query}'."


def make_respond_node(deps: AgentDeps):
    def respond(state: AgentState) -> dict[str, Any]:
        query = state.get("query", "")
        message_history = state.get("message_history") or []

        llm = deps.llm_factory()
        if llm is None:
            return {"answer": _fallback_reply(query)}

        history_text = ""
        if message_history:
            history_text = "\n\nPrevious conversation:\n" + "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}" for m in message_history
            )
        prompt = (
            "You are a friendly shopping assistant. Respond helpfully and "
            "concisely to the user's message. If they are greeting or making "
            "small talk, reply naturally without searching for products."
            + history_text
            + f"\n\nUser message: {query}"
        )
        try:
            response = llm.invoke(prompt)
            answer = getattr(response, "content", None) or str(response)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            logger.warning("LLM respond failed, using fallback: %s", exc)
            answer = _fallback_reply(query)

        return {"answer": answer}

    return respond