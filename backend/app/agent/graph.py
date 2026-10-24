"""Main Agent Coordinator Graph."""
from __future__ import annotations

import logging
from typing import Any, Dict, Literal
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..core.database import SessionLocal
from ..models.chat import ChatMessage
from .nodes.chitchat import chitchat_node
from .nodes.load_context import load_context_node
from .nodes.router import router_node
from .state import ShopState
from .subgraphs.search.graph import build_search_subgraph

logger = logging.getLogger(__name__)


def route_after_router(state: ShopState) -> Literal["search", "chitchat", "placeholder_stage4"]:
    """Conditional routing based on structured intent."""
    intent = state.get("intent") or "search"
    if intent == "search":
        return "search"
    if intent == "chitchat":
        return "chitchat"
    return "placeholder_stage4"


def placeholder_stage4_node(state: ShopState) -> Dict[str, Any]:
    """Temporary placeholder for Stage 4 modules (Cart & QA)."""
    intent = state.get("intent")
    if intent == "cart":
        msg = "🛒 **Sepet Yönetimi**: Aşama 4'te bağlanacaktır. (Ürün ekleme, çıkarma ve sepet görüntüleme)."
    elif intent == "qa":
        msg = "🔍 **Ürün Detay Soru-Cevap**: Aşama 4'te bağlanacaktır. (Ürün garantisi, özellikleri ve detayları)."
    elif intent == "checkout":
        msg = "💳 **Sipariş / Ödeme**: Aşama 5'te Human-in-the-loop onayı ile bağlanacaktır."
    else:
        msg = "Talebiniz alındı."
    return {"messages": [AIMessage(content=msg)]}


def persist_turn_node(state: ShopState) -> Dict[str, Any]:
    """Saves user message and final assistant reply into SQLite chat_messages table."""
    thread_id = state.get("thread_id")
    messages = state.get("messages") or []
    intent = state.get("intent")

    if not thread_id or len(messages) < 2:
        return {}

    user_msg = messages[-2].content if len(messages) >= 2 else ""
    assistant_msg = messages[-1].content

    db = SessionLocal()
    try:
        # Save user message
        db.add(ChatMessage(thread_id=thread_id, role="user", content=str(user_msg), intent=intent))
        # Save assistant message
        db.add(ChatMessage(thread_id=thread_id, role="assistant", content=str(assistant_msg), intent=intent))
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to persist chat message: %s", exc)
    finally:
        db.close()

    return {}


def build_shop_graph(checkpointer: Any | None = None):
    """Build and compile the main E-Commerce Shop Graph."""
    workflow = StateGraph(ShopState)

    # 1. Register Nodes
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("router", router_node)
    workflow.add_node("search", build_search_subgraph())
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node("placeholder_stage4", placeholder_stage4_node)
    workflow.add_node("persist_turn", persist_turn_node)

    # 2. Add Edges
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "router")

    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "search": "search",
            "chitchat": "chitchat",
            "placeholder_stage4": "placeholder_stage4",
        },
    )

    workflow.add_edge("search", "persist_turn")
    workflow.add_edge("chitchat", "persist_turn")
    workflow.add_edge("placeholder_stage4", "persist_turn")
    workflow.add_edge("persist_turn", END)

    memory = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=memory)
