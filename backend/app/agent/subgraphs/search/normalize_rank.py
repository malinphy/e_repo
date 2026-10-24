"""normalize_rank node: filters, deduplicates, ranks products and updates last_results."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from langchain_core.messages import AIMessage

from .state import SearchSubgraphState

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    """Simplify title for deduplication comparison."""
    return "".join(c.lower() for c in title if c.isalnum() or c.isspace()).strip()


def normalize_rank_node(state: SearchSubgraphState) -> Dict[str, Any]:
    """Filters, deduplicates, ranks products and formats them into last_results."""
    raw_products = state.get("raw_products") or []
    search_query = state.get("search_query") or {}
    max_price = search_query.get("max_price")
    keywords = search_query.get("keywords", "")

    # 1. Deduplicate by simplified title
    seen_titles = set()
    deduped: List[Dict[str, Any]] = []
    for prod in raw_products:
        title = prod.get("title") or ""
        norm_title = _normalize_title(title[:40])  # first 40 chars
        if norm_title and norm_title not in seen_titles:
            seen_titles.add(norm_title)
            deduped.append(prod)

    # 2. Filter by max_price if specified
    filtered = deduped
    if max_price is not None and max_price > 0:
        within_budget = [p for p in deduped if 0 < (p.get("price") or 0.0) <= max_price]
        unpriced = [p for p in deduped if not p.get("price")]
        filtered = within_budget + unpriced

    # 3. Rank: products with valid ratings first, then by price ascending
    def sort_key(p: Dict[str, Any]):
        price = p.get("price") or 999999.0
        rating = p.get("rating") or 0.0
        return (-rating, price)

    ranked = sorted(filtered, key=sort_key)[:10]

    # 4. Generate user-friendly numbered list response
    if not ranked:
        reply_text = f"'{keywords}' araması için uygun ürün bulunamadı. Lütfen filtrelerinizi veya bütçenizi genişletmeyi deneyin."
    else:
        lines = [f"**'{keywords}'** için bulunan en popüler ürünler:\n"]
        for idx, item in enumerate(ranked, start=1):
            rating_str = f" ⭐ {item.get('rating')}" if item.get("rating") else ""
            source_badge = f"[{item.get('source', '').upper()}]"
            lines.append(
                f"{idx}. **{item.get('title')}**\n"
                f"   💵 **${item.get('price')} {item.get('currency', 'USD')}** | {source_badge}{rating_str}\n"
                f"   🔗 [Ürünü İncele]({item.get('url')})\n"
            )
        lines.append("\n💡 *Sepete eklemek için '1. ürünü ekle' diyebilir veya detaylar hakkında soru sorabilirsiniz.*")
        reply_text = "\n".join(lines)

    return {
        "last_results": ranked,
        "messages": [AIMessage(content=reply_text)],
    }
