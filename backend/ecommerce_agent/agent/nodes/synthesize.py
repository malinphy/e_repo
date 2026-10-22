"""synthesize node: filter, rank and summarize the collected products."""
from __future__ import annotations

import logging
import re
from typing import Any

from ..deps import AgentDeps
from ..state import AgentState

logger = logging.getLogger(__name__)

_PRICE_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def _extract_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _PRICE_RE.search(str(value).replace(",", ""))
    return float(match.group(1)) if match else None


def _rank(products: list[dict[str, Any]], max_price: float | None) -> list[dict[str, Any]]:
    filtered = products
    if max_price is not None:
        within = [
            p
            for p in products
            if (price := _extract_price(p.get("price"))) is not None and price <= max_price
        ]
        unpriced = [p for p in products if _extract_price(p.get("price")) is None]
        filtered = within + unpriced

    return sorted(
        filtered,
        key=lambda p: (_extract_price(p.get("price")) is None, _extract_price(p.get("price")) or 0.0),
    )


def _fallback_answer(query: str, ranked: list[dict[str, Any]]) -> str:
    if not ranked:
        return f"No products found for '{query}'."
    lines = [f"Top results for '{query}':"]
    for idx, item in enumerate(ranked[:10], start=1):
        lines.append(
            f"{idx}. {item.get('title')} — {item.get('price')} ({item.get('source') or item.get('engine')})"
        )
    return "\n".join(lines)


def make_synthesize_node(deps: AgentDeps):
    def synthesize(state: AgentState) -> dict[str, Any]:
        parsed = state.get("parsed") or {}
        query = state.get("query", "")
        products = state.get("products") or []
        ranked = _rank(products, parsed.get("max_price"))

        llm = deps.llm_factory()
        if llm is None or not ranked:
            return {"answer": _fallback_answer(query, ranked)}

        listing = "\n".join(
            f"- {p.get('title')} | {p.get('price')} | {p.get('source') or p.get('engine')} | {p.get('rating')}"
            for p in ranked[:20]
        )
        prompt = (
            "You are a shopping assistant. Recommend the best options from these products. "
            "Be concise, mention price and marketplace. Do not invent products.\n\n"
            f"User request: {query}\n\nProducts:\n{listing}"
        )
        try:
            response = llm.invoke(prompt)
            answer = getattr(response, "content", None) or str(response)
        except Exception as exc:  # noqa: BLE001 - fall back to deterministic output
            logger.warning("LLM synthesis failed, using fallback: %s", exc)
            answer = _fallback_answer(query, ranked)

        return {"answer": answer, "products": ranked}

    return synthesize
