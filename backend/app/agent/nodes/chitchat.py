"""chitchat node: replies to greetings, small talk, and conversational history questions."""
from __future__ import annotations

import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ...core.config import get_settings
from ..state import ShopState

logger = logging.getLogger(__name__)

CHITCHAT_FALLBACKS = {
    "hello": "Hello! Welcome to your shopping assistant. What product would you like to search for or explore?",
    "hi": "Hi there! I am here to help you find the best deals and quality products today. What are you looking for?",
    "thanks": "You're very welcome! If you want to search for anything else, just let me know.",
    "thank you": "You're welcome! Enjoy your shopping.",
}


def chitchat_node(state: ShopState) -> Dict[str, Any]:
    """Generates a friendly conversation reply with full awareness of the conversation history."""
    messages = state.get("messages") or []
    if not messages:
        return {"messages": [AIMessage(content="Hello! How can I help you today?")]}

    last_text = messages[-1].content
    if not isinstance(last_text, str):
        last_text = str(last_text)

    lowered = last_text.strip().lower()

    # Fast heuristic only for first standalone greeting with no prior history
    if len(messages) <= 1:
        for key, reply in CHITCHAT_FALLBACKS.items():
            if lowered in (key, f"{key}!"):
                return {"messages": [AIMessage(content=reply)]}

    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        reply_content = (
            "Hello! I am your AI shopping assistant. "
            "I can search and compare products across Walmart, eBay, Amazon, and Google Shopping, "
            "manage your cart, and help you checkout. What would you like to find?"
        )
    else:
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, api_key=settings.OPENAI_API_KEY)
            system_prompt = SystemMessage(
                content=(
                    "You are a friendly and intelligent e-commerce shopping assistant with full awareness of the conversation history. "
                    "You have direct access to all previous messages in this conversation. "
                    "Respond helpfully, accurately, and concisely in English. "
                    "If the user asks about previous messages or questions (e.g. 'what was my first question?'), "
                    "inspect the conversation history provided and answer their question accurately."
                )
            )

            # Pass entire conversation history with system prompt so the LLM remembers everything!
            conversation = [system_prompt, *messages]
            response = llm.invoke(conversation)
            reply_content = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.warning("LLM chitchat failed: %s", exc)
            reply_content = "Hello! How can I help you today?"

    return {"messages": [AIMessage(content=reply_content)]}
