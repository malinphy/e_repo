"""chitchat node: replies to greetings and off-topic conversation."""
from __future__ import annotations

import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ...core.config import get_settings
from ..state import ShopState

logger = logging.getLogger(__name__)

CHITCHAT_FALLBACKS = {
    "merhaba": "Merhaba! Alışveriş asistanınıza hoş geldiniz. Hangi ürünü aramak veya incelemek istersiniz?",
    "selam": "Selam! Bugün size en uygun fiyatlı ve kaliteli ürünleri bulmak için buradayım. Ne aramıştınız?",
    "teşekkür": "Rica ederim, her zaman buradayım! Başka bir ürün aramak isterseniz söylemeniz yeterli.",
    "sağol": "Rica ederim! İyi alışverişler dilerim.",
}


def chitchat_node(state: ShopState) -> Dict[str, Any]:
    """Generates a friendly conversation reply without executing marketplace searches."""
    messages = state.get("messages") or []
    last_text = messages[-1].content if messages else ""
    if not isinstance(last_text, str):
        last_text = str(last_text)

    lowered = last_text.strip().lower()

    # Quick heuristic check
    for key, reply in CHITCHAT_FALLBACKS.items():
        if key in lowered:
            return {"messages": [AIMessage(content=reply)]}

    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        reply_content = (
            "Merhaba! Ben sizin akıllı alışveriş asistanınızım. "
            "Walmart, eBay, Amazon ve Google Shopping üzerinde ürün arayabilir, "
            "fiyatları karşılaştırabilir ve sepetinize ekleyebilirsiniz. Ne aramak istersiniz?"
        )
    else:
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=settings.OPENAI_API_KEY)
            prompt = (
                "You are a friendly and helpful e-commerce shopping assistant. "
                "Respond naturally, concisely, and warmly to the user's greeting or small talk in their language (Turkish/English). "
                "Remind them subtly that they can search for products, compare prices, or manage their cart.\n"
                f"User message: {last_text}"
            )
            response = llm.invoke(prompt)
            reply_content = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.warning("LLM chitchat failed: %s", exc)
            reply_content = "Merhaba! Size hangi ürünü bulmamı istersiniz?"

    return {"messages": [AIMessage(content=reply_content)]}
