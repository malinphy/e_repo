"""supervisor node: decide user intent, select engines, then route to a worker.

The supervisor is the routing brain of the graph. It reads the raw query plus
any loaded conversation history, uses the LLM (with a deterministic heuristic
fallback) to produce a structured ``ParsedQuery``, then:
* writes the detected ``intent`` (an explicit, structured field a router can
  branch on — never free-text LLM output);
* selects which SerpAPI engines the ``search`` worker should run.

Recognized intents (see ``schemas/query.Intent``):

* ``search``       -> route to the ``search`` worker
* ``chit_chat``    -> route to the ``synthesize`` node (LLM replies, no search)
* ``add_cart`` / ``remove_cart`` / ``show_cart`` -> cart worker
"""
from __future__ import annotations

import logging
from typing import Any

from ...schemas.query import Intent, ParsedQuery
from ...tools.serpapi.factory import available_engines
from ..deps import AgentDeps
from ..state import AgentState

logger = logging.getLogger(__name__)

SEARCH = "search"
CHIT_CHAT = "chit_chat"
ADD_CART = "add_cart"
REMOVE_CART = "remove_cart"
SHOW_CART = "show_cart"

VALID_INTENTS: set[str] = {SEARCH, CHIT_CHAT, ADD_CART, REMOVE_CART, SHOW_CART}

_SYSTEM_PROMPT = (
    "You are a shopping assistant supervisor. Read the user's request (and any "
    "conversation history) and classify it into exactly one intent:\n"
    "- 'search': the user wants to find/browse products (default for any "
    "shopping-related request).\n"
    "- 'chit_chat': greetings, small talk, thanks, or anything unrelated to "
    "shopping (no product search needed).\n"
    "- 'add_cart': the user wants to add an item to their cart.\n"
    "- 'remove_cart': the user wants to remove an item from their cart.\n"
    "- 'show_cart': the user wants to see what is in their cart.\n"
    "For 'add_cart' and 'remove_cart', also fill 'item_reference' with whatever "
    "identifies the product the user means (a position like '1st'/'2..', a "
    "title, or 'all'). "
    "Pick engines only from: {engines} when the intent is 'search'. "
    "Return the core product keywords (empty for non-search intents), the "
    "engines worth searching, and any stated max price / currency."
)


def _heuristic(query: str) -> ParsedQuery:
    """Deterministic fallback used when no LLM is available.

    Keyword matching distinguishes search / chit-chat / cart intents so the
    router still works without an LLM. Matching is on whole words to avoid
    substring false positives (e.g. "hi" inside "nothing").
    """
    import re

    text = query.strip()
    if not text:
        return ParsedQuery(keywords=text, engines=[], intent="chit_chat")

    lowered = text.lower()

    # Cart intents before the general search/chit-chat checks.
    show_cart_phrases = (
        "sepetim", "sepetimde", "sepette", "sepeti göster", "sepeti goster",
        "my cart", "show cart", "basket", "what's in my cart", "sepetimde ne var",
    )
    for phrase in show_cart_phrases:
        if _whole_word(phrase, lowered):
            return ParsedQuery(keywords=text, engines=[], intent="show_cart")

    add_cart_phrases = ("sepete ekle", "sepete at", "add to cart", "add to basket")
    for phrase in add_cart_phrases:
        if _whole_word(phrase, lowered):
            return ParsedQuery(keywords=text, engines=[], intent="add_cart")

    remove_cart_phrases = (
        "sepetten çıkar", "sepetten cikar", "sepetten sil",
        "remove from cart", "remove from basket", "remove cart",
    )
    for phrase in remove_cart_phrases:
        if _whole_word(phrase, lowered):
            return ParsedQuery(keywords=text, engines=[], intent="remove_cart")

    chit_chat_phrases = (
        "hello", "hi", "hey", "merhaba", "selam", "thanks", "thank you",
        "how are you", "günaydın", "iyi günler", "tesekkur", "teşekkür",
    )
    for phrase in chit_chat_phrases:
        if _whole_word(phrase, lowered):
            return ParsedQuery(keywords=text, engines=[], intent="chit_chat")

    return ParsedQuery(keywords=text, engines=available_engines(), intent="search")


def _whole_word(phrase: str, lowered: str) -> bool:
    import re

    pattern = r"(?<![a-zçğıöşü])" + re.escape(phrase) + r"(?![a-zçğıöşü])"
    return re.search(pattern, lowered) is not None


def _llm_parse(
    llm: Any, query: str, message_history: list[dict[str, str]]
) -> ParsedQuery:
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


def _normalize_intent(parsed: ParsedQuery) -> str:
    """Coerce the LLM's intent field into a known, routable value."""
    intent = (parsed.intent or "").strip()
    return intent if intent in VALID_INTENTS else SEARCH


def make_supervisor_node(deps: AgentDeps):
    def supervisor(state: AgentState) -> dict[str, Any]:
        query = state.get("query", "")
        message_history = state.get("message_history") or []
        llm = deps.llm_factory()

        if llm is None:
            parsed = _heuristic(query)
        else:
            try:
                parsed = _llm_parse(llm, query, message_history)
            except Exception as exc:  # noqa: BLE001 - degrade gracefully on LLM failure
                logger.warning("LLM supervision failed, using heuristic: %s", exc)
                parsed = _heuristic(query)

        if not parsed.keywords:
            parsed.keywords = query.strip()

        intent = _normalize_intent(parsed)

        # Select engines to run only when searching.
        if intent == SEARCH:
            requested = [e for e in parsed.engines if e in deps.engines]
            selected = requested or list(deps.engines.keys())
        else:
            selected = []

        return {
            "parsed": parsed.model_dump(),
            "intent": intent,
            "engines": selected,
        }

    return supervisor


def route_after_supervisor(state: AgentState) -> str:
    """Route on a structured intent field, not on LLM free text."""
    intent = state.get("intent") or SEARCH
    if intent == SEARCH:
        return SEARCH
    if intent == CHIT_CHAT:
        return CHIT_CHAT
    if intent in (ADD_CART, REMOVE_CART, SHOW_CART):
        return "cart"
    return SEARCH