"""query_rewriter node: extracts clean keywords, brand, budget, and target marketplaces."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict
from langchain_openai import ChatOpenAI

from ....core.config import get_settings
from ....schemas.intent import SearchQuery
from .state import SearchSubgraphState

logger = logging.getLogger(__name__)

_PRICE_EXTRACTOR = re.compile(
    r"(?:under|below|less than|maximum|max|budget)\s*[:$]?\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_NOISE_WORDS = re.compile(
    r"\b(find|search|show me|buy|look for|please|price|cost|recommend)\b",
    re.IGNORECASE,
)


def _heuristic_rewrite(text: str) -> SearchQuery:
    """Extract price and clean keywords using regex fallback."""
    max_price = None
    price_match = _PRICE_EXTRACTOR.search(text)
    if price_match:
        max_price = float(price_match.group(1).replace(",", "."))

    # Remove price clause and conversational filler words
    cleaned = _PRICE_EXTRACTOR.sub("", text)
    cleaned = _NOISE_WORDS.sub("", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    return SearchQuery(
        keywords=cleaned or text.strip(),
        max_price=max_price,
        marketplaces=["walmart", "ebay", "amazon", "google_shopping"],
    )


def query_rewriter_node(state: SearchSubgraphState) -> Dict[str, Any]:
    """Refines the user's raw message into a structured SearchQuery."""
    search_query_data = state.get("search_query") or {}
    messages = state.get("messages") or []
    raw_query = messages[-1].content if messages else ""
    if not isinstance(raw_query, str):
        raw_query = str(raw_query)

    # If keywords already extracted and valid, retain or enrich
    if search_query_data.get("keywords") and search_query_data.get("marketplaces"):
        return {"search_query": search_query_data}

    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        rewritten = _heuristic_rewrite(raw_query)
    else:
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.OPENAI_API_KEY)
            structured_rewriter = llm.with_structured_output(SearchQuery)
            prompt = (
                "You are an e-commerce search query rewriter. "
                "Extract the core product keywords (strip filler words and greetings), "
                "detect brand name, maximum budget/price, and pick relevant marketplaces.\n"
                f"User Message: {raw_query}"
            )
            rewritten: SearchQuery = structured_rewriter.invoke(prompt)
        except Exception as exc:
            logger.warning("LLM query rewrite failed, using heuristic: %s", exc)
            rewritten = _heuristic_rewrite(raw_query)

    return {"search_query": rewritten.model_dump()}
