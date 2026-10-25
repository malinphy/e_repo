"""router node: classifies user intent into search, qa, cart, checkout, or chitchat."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from ...core.config import get_settings
from ...schemas.intent import CartIntentDetails, IntentType, RouterOutput, SearchQuery
from ..state import ShopState

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are an e-commerce assistant router.
Analyze the user's latest message considering the conversation history, available cart, and previously shown products.

Classify the intent into EXACTLY ONE of the following:
1. 'search': User wants to find, discover, browse, or buy new products (e.g. 'find running shoes under $100', 'iphone 15 ara').
2. 'qa': User is asking a question about a product from the previously shown products (last_results) (e.g. 'does the 2nd one have warranty?', 'ilk ürün su geçirmez mi?', 'tell me more about the sony headphones').
3. 'cart': User wants to view, add, or remove items from their cart (e.g. 'add the 2nd one to cart', 'sepetime ekle', 'sepetimde ne var', 'remove the shoes').
4. 'checkout': User wants to proceed to purchase / pay for what is currently in their cart (e.g. 'checkout', 'satın al', 'siparişi tamamla', 'ödeme yap').
5. 'chitchat': Greetings, small talk, gratitude, or off-topic conversation (e.g. 'hello', 'how are you', 'teşekkürler', 'hava nasıl').

Context:
- Number of previously shown products in last_results: {num_products}
{products_summary}
- Number of items in cart: {num_cart_items}
{cart_summary}

If the user refers to 'the 2nd one', 'this item', or asks about details, and previous products exist, choose 'qa' or 'cart' accordingly!
"""


def _heuristic_classify(
    query: str,
    has_last_results: bool,
    has_cart_items: bool,
) -> RouterOutput:
    """Deterministic fallback classification when LLM is not configured or fails."""
    lowered = query.strip().lower()

    # Checkout check
    checkout_terms = ("checkout", "satın al", "satin al", "sipariş ver", "siparis ver", "ödeme yap", "odeme yap", "buy now")
    if any(term in lowered for term in checkout_terms):
        return RouterOutput(intent="checkout", reasoning="Detected checkout keywords")

    # Cart check
    cart_terms = ("sepet", "cart", "basket", "sepete ekle", "sepete at", "sepetten çıkar", "sepetten cikar", "add to cart", "remove from cart")
    if any(term in lowered for term in cart_terms):
        action = "view"
        if any(w in lowered for w in ("ekle", "at", "add")):
            action = "add"
        elif any(w in lowered for w in ("çıkar", "cikar", "sil", "remove", "delete")):
            action = "remove"
        return RouterOutput(
            intent="cart",
            cart_action=CartIntentDetails(action=action, item_reference=lowered),
            reasoning="Detected cart keywords",
        )

    # QA check (if there are previous products and user asks about one or comparison)
    qa_terms = (
        "garanti", "warranty", "özellik", "ozellik", "renk", "color", "farkı ne", "farki ne",
        "şarj", "sarj", "detay", "cheapest", "cheaper", "expensive", "en ucuz", "en pahalı",
        "en pahali", "fiyatı", "hangisi", "which", "best", "en iyi", "compare", "karşılaştır"
    )
    is_referring_item = any(ref in lowered for ref in ("1.", "2.", "3.", "ilk", "ikinci", "üçüncü", "1st", "2nd", "3rd", "bu ürün", "hangisi", "which", "cheapest", "en ucuz"))
    if has_last_results and (is_referring_item or any(term in lowered for term in qa_terms)):
        return RouterOutput(
            intent="qa",
            qa_target_reference=lowered,
            reasoning="Detected reference/question regarding previously shown products",
        )

    # Chitchat check
    greetings = ("merhaba", "selam", "günaydın", "gunaydin", "iyi günler", "hello", "hi", "hey", "teşekkür", "tesekkur", "thanks", "thank you")
    if any(w == lowered or lowered.startswith(w + " ") for w in greetings):
        return RouterOutput(intent="chitchat", reasoning="Detected greeting / chitchat")

    # Default to search
    return RouterOutput(
        intent="search",
        search_query=SearchQuery(keywords=query.strip()),
        reasoning="Defaulted to product search",
    )


def router_node(state: ShopState) -> Dict[str, Any]:
    """Routes the conversation to search, qa, cart, checkout, or chitchat."""
    messages: List[BaseMessage] = state.get("messages") or []
    last_query = messages[-1].content if messages else ""
    if not isinstance(last_query, str):
        last_query = str(last_query)

    last_results = state.get("last_results") or []
    cart_items = state.get("cart") or []

    settings = get_settings()

    # If no OpenAI API key is available, use heuristic router
    if not settings.OPENAI_API_KEY:
        decision = _heuristic_classify(last_query, bool(last_results), bool(cart_items))
    else:
        try:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=settings.OPENAI_API_KEY,
            )
            structured_router = llm.with_structured_output(RouterOutput)

            # Build compact context summaries for LLM prompt
            products_summary = ""
            if last_results:
                products_summary = "Recently shown products:\n" + "\n".join(
                    f"{idx+1}. {p.get('title')} - ${p.get('price')} ({p.get('source')})"
                    for idx, p in enumerate(last_results[:5])
                )

            cart_summary = ""
            if cart_items:
                cart_summary = "Current cart items:\n" + "\n".join(
                    f"- {c.get('title')} (Qty: {c.get('quantity')}, ${c.get('price')})"
                    for c in cart_items
                )

            prompt = ROUTER_SYSTEM_PROMPT.format(
                num_products=len(last_results),
                products_summary=products_summary,
                num_cart_items=len(cart_items),
                cart_summary=cart_summary,
            ) + f"\nUser Message: {last_query}"

            decision: RouterOutput = structured_router.invoke(prompt)

        except Exception as exc:
            logger.warning("LLM router invocation failed, falling back to heuristic: %s", exc)
            decision = _heuristic_classify(last_query, bool(last_results), bool(cart_items))

    # Convert SearchQuery to dict if present
    search_query_dict = decision.search_query.model_dump() if decision.search_query else None

    # Preserve or update pending_action
    pending_action = state.get("pending_action")
    if decision.intent == "checkout":
        pending_action = {"type": "checkout", "status": "pending_approval"}
    elif decision.intent == "cart" and decision.cart_action:
        pending_action = {"type": "cart", "action": decision.cart_action.model_dump()}

    return {
        "intent": decision.intent,
        "search_query": search_query_dict,
        "pending_action": pending_action,
    }
