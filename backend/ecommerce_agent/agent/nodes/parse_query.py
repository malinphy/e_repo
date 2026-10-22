"""parse_query node: turn the raw user query into a ParsedQuery."""
from __future__ import annotations

import logging
from typing import Any

from ...schemas.query import ParsedQuery
from ...tools.serpapi.factory import available_engines
from ..deps import AgentDeps
from ..state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You extract structured shopping search parameters from a user request. "
    "Pick engines only from: {engines}. "
    "Return the core product keywords, the engines worth searching, "
    "and any stated max price / currency."
)


def _heuristic_parse(query: str) -> ParsedQuery:
    return ParsedQuery(keywords=query.strip(), engines=available_engines())


def _llm_parse(llm: Any, query: str, message_history: list[dict[str, str]]) -> ParsedQuery:
    structured = llm.with_structured_output(ParsedQuery)
    history_text = ""
    if message_history:
        history_text = "\n\nPrevious conversation:\n" + "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in message_history
        )
    prompt = (
        _SYSTEM_PROMPT.format(engines=", ".join(available_engines()))
        + history_text
        + f"\n\nCurrent user request: {query}"
    )
    parsed = structured.invoke(prompt)
    if isinstance(parsed, ParsedQuery):
        return parsed
    return ParsedQuery.model_validate(parsed)


def make_parse_query_node(deps: AgentDeps):
    def parse_query(state: AgentState) -> dict[str, Any]:
        query = state.get("query", "")
        message_history = state.get("message_history") or []
        llm = deps.llm_factory()
        if llm is None:
            parsed = _heuristic_parse(query)
        else:
            try:
                parsed = _llm_parse(llm, query, message_history)
            except Exception as exc:  # noqa: BLE001 - degrade gracefully on LLM failure
                logger.warning("LLM query parsing failed, using heuristic: %s", exc)
                parsed = _heuristic_parse(query)

        if not parsed.keywords:
            parsed.keywords = query.strip()

        return {"parsed": parsed.model_dump()}

    return parse_query
