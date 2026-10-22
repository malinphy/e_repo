"""cart node: add/remove/show items in a user's shopping cart.

The cart is user-scoped (one active cart per ``user_id``), with line items
storing a frozen product snapshot (JSON) plus a quantity. Because cart intents
run *instead of* a search, the node resolves "which product" references (e.g.
"add the 2nd one", "remove nike air force") against the user's most recent
search run, read back from the database.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ...repositories.cart_repo import CartRepository
from ...repositories.engine_results_repo import EngineResultsRepository
from ..deps import AgentDeps
from ..state import AgentState

logger = logging.getLogger(__name__)

_POSITION_RE = re.compile(r"(\d+)")


def _product_dict(row: Any) -> dict[str, Any]:
    return {
        "title": row.title,
        "price": row.price,
        "source": row.source,
        "link": row.link,
        "rating": row.rating,
        "reviews": row.reviews,
        "engine": row.engine,
    }


def _resolve_reference(
        reference: str | None, candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
        """Pick candidate products matching the user's ``item_reference``.

        Rules, in order:
        * explicit "all"/"hepsi"/"tümü" -> every candidate;
        * a leading integer -> that 1-based position;
        * a title substring -> matching products;
        * an explicit but non-matching reference -> empty (don't guess);
        * no reference at all -> the first candidate (auto-pick).
        """
        candidates = [c for c in candidates if c.get("title")]

        if reference and reference.strip().lower() in ("all", "hepsi", "tümü"):
            return candidates

        if reference:
            match = _POSITION_RE.search(reference)
            if match:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(candidates):
                    return [candidates[idx]]
                return []

            needle = reference.strip().lower()
            return [c for c in candidates if needle in (c.get("title") or "").lower()]

        return candidates[:1]


def _format_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return "Your cart is empty."
    lines = ["Your cart:"]
    for i, item in enumerate(items, start=1):
        p = item["product"]
        lines.append(
            f"{i}. {p.get('title')} — {p.get('price')} × {item['quantity']} "
            f"({p.get('source') or p.get('engine')})"
        )
    return "\n".join(lines)


def make_cart_node(deps: AgentDeps):
    def cart(state: AgentState) -> dict[str, Any]:
        intent = state.get("intent")
        user_id = state.get("user_id")
        parsed = state.get("parsed") or {}
        reference = parsed.get("item_reference")

        if not user_id:
            return {"answer": "I need to know who you are (user_id) to manage your cart."}

        session = deps.session_factory()
        try:
            repo = CartRepository(session)
            if intent == "show_cart":
                items = repo.list_items(user_id)
                answer = _format_items(
                    [{"product": i.product, "quantity": i.quantity} for i in items]
                )
                session.commit()
                return {"answer": answer}

            # add_cart / remove_cart: resolve the target product from the last
            # search run, since no search happened in this turn.
            rows = EngineResultsRepository(session).products_for_latest_run(user_id)
            candidates_list = [_product_dict(r) for r in rows]
            targets = _resolve_reference(reference, candidates_list)

            if not targets:
                answer = (
                    "I couldn't find that item. First search for a product, then "
                    "say 'add the 1st one' or name the item."
                )
                session.commit()
                return {"answer": answer}

            if intent == "add_cart":
                for target in targets:
                    repo.add(user_id, target)
                session.commit()
                noun = "item" if len(targets) == 1 else f"{len(targets)} items"
                return {"answer": f"Added {noun} to your cart."}

            if intent == "remove_cart":
                for target in targets:
                    repo.remove(user_id, target)
                session.commit()
                noun = "item" if len(targets) == 1 else f"{len(targets)} items"
                return {"answer": f"Removed {noun} from your cart."}

            return {"answer": "Sorry, I don't understand that cart action."}
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            session.rollback()
            logger.exception("cart operation failed: %s", exc)
            return {"answer": "Sorry, something went wrong managing your cart."}
        finally:
            session.close()

    return cart