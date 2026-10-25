"""qa_node: answers specific product questions using last_results and anti-hallucination prompts."""
from __future__ import annotations

import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ....core.config import get_settings
from ...state import ShopState
from ..cart.operations import resolve_product_reference

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """You are a helpful and completely honest shopping assistant.
A user is asking a question about a specific product they were previously shown.

Product Details:
- Title: {title}
- Price: ${price} {currency} ({source})
- Rating: {rating} ({reviews} reviews)
- Summary / Snippet: {snippet}
- Product URL: {url}

Rules:
1. Always state the product title ({title}) at the beginning of your response (e.g., "**{title}**: ...") and answer the user's question directly, clearly, and concisely in English.
2. ONLY use the verified facts from the product details above.
3. DO NOT invent, hallucinate, or assume features (e.g. warranty duration, battery life, waterproof rating) if not explicitly mentioned in the snippet.
4. If the requested information is not in the snippet, clearly state:
   "This information is not provided in the product summary; I recommend checking the seller's official product page." and provide the product URL.
"""


def qa_node(state: ShopState) -> Dict[str, Any]:
    """Answers user's questions about recently shown products with anti-hallucination guardrails."""
    last_results = state.get("last_results") or []
    messages = state.get("messages") or []
    user_query = messages[-1].content if messages else ""
    if not isinstance(user_query, str):
        user_query = str(user_query)

    if not last_results:
        reply = (
            "I could not find any previously listed products. "
            "Please specify what you would like to search for first (e.g. *'search for running shoes'*)."
        )
        return {"messages": [AIMessage(content=reply)]}

    # Resolve target product from user query (e.g. 'does the 2nd one have warranty?', 'mizuno shoes')
    target_product = resolve_product_reference(user_query, last_results)
    if not target_product:
        # Default to the first product if user asks a general QA question
        target_product = last_results[0]

    title = target_product.get("title", "Product")
    price = target_product.get("price", 0.0)
    currency = target_product.get("currency", "USD")
    source = target_product.get("source", "").upper()
    rating = target_product.get("rating") or "Not specified"
    reviews = target_product.get("reviews_count") or "0"
    snippet = target_product.get("snippet") or "No detailed description available."
    url = target_product.get("url") or ""

    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        # Heuristic / deterministic response without LLM
        reply = (
            f"📌 **{title}** ({source} - ${price:.2f} {currency})\n\n"
            f"**Product Details:** {snippet}\n\n"
            f"🔗 For more information: [Visit Seller Page]({url})"
        )
    else:
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=settings.OPENAI_API_KEY)
            prompt = QA_SYSTEM_PROMPT.format(
                title=title,
                price=price,
                currency=currency,
                source=source,
                rating=rating,
                reviews=reviews,
                snippet=snippet,
                url=url,
            ) + f"\nUser Question: {user_query}"

            response = llm.invoke(prompt)
            reply = response.content if hasattr(response, "content") else str(response)
            if title.lower() not in reply.lower():
                reply = f"📌 **{title}**:\n{reply}"
        except Exception as exc:
            logger.warning("LLM QA answer failed, using fallback: %s", exc)
            reply = (
                f"📌 **{title}** (${price:.2f} {currency})\n\n"
                f"**Available Details:** {snippet}\n\n"
                f"🔗 Details: [Product Link]({url})"
            )

    return {"messages": [AIMessage(content=reply)]}
