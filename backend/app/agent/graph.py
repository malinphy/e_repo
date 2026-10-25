"""Main Agent Coordinator Graph."""
from __future__ import annotations

import logging
from typing import Any, Dict, Literal
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from sqlalchemy import select

from ..core.database import SessionLocal
from ..models.chat import ChatMessage
from .nodes.chitchat import chitchat_node
from .nodes.load_context import load_context_node
from .nodes.router import router_node
from .state import ShopState
from .subgraphs.cart.graph import build_cart_subgraph
from .subgraphs.checkout.checkout_node import checkout_node
from .subgraphs.qa.graph import build_qa_subgraph
from .subgraphs.search.graph import build_search_subgraph

logger = logging.getLogger(__name__)


def route_after_router(state: ShopState) -> Literal["search", "cart", "qa", "chitchat", "checkout"]:
    """Conditional routing based on structured intent."""
    intent = state.get("intent") or "search"
    if intent in ("search", "cart", "qa", "chitchat", "checkout"):
        return intent
    return "search"


def persist_turn_node(state: ShopState) -> Dict[str, Any]:
    """Saves user message, assistant reply, and structured products into SQLite."""
    thread_id = state.get("thread_id")
    messages = state.get("messages") or []
    intent = state.get("intent")

    if not thread_id or len(messages) < 2:
        return {}

    user_msg = messages[-2].content if len(messages) >= 2 else ""
    assistant_msg = messages[-1].content

    # Prepare structured metadata (store last_results and search_query only on search turns)
    metadata: Dict[str, Any] = {}
    if intent == "search":
        if state.get("last_results"):
            metadata["products"] = state.get("last_results")
        if state.get("search_query"):
            metadata["search_query"] = state.get("search_query")

    db = SessionLocal()
    try:
        from datetime import datetime, timezone
        from ..models.chat import ChatThread

        # 1. Update thread updated_at and refine title if default
        thread = db.scalar(select(ChatThread).where(ChatThread.thread_id == thread_id))
        if thread:
            thread.updated_at = datetime.now(timezone.utc)
            if not thread.title or thread.title in ("Shopping Chat", "Chat", "New Chat"):
                thread.title = str(user_msg)[:50].strip()

        # 2. Save user message
        db.add(ChatMessage(thread_id=thread_id, role="user", content=str(user_msg), intent=intent))
        # 3. Save assistant message with structured products metadata
        db.add(
            ChatMessage(
                thread_id=thread_id,
                role="assistant",
                content=str(assistant_msg),
                intent=intent,
                metadata_json=metadata if metadata else None,
            )
        )
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

    # 1. Register Nodes & Subgraphs
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("router", router_node)
    workflow.add_node("search", build_search_subgraph())
    workflow.add_node("cart", build_cart_subgraph())
    workflow.add_node("qa", build_qa_subgraph())
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node("checkout", checkout_node)
    workflow.add_node("persist_turn", persist_turn_node)

    # 2. Add Edges
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "router")

    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "search": "search",
            "cart": "cart",
            "qa": "qa",
            "chitchat": "chitchat",
            "checkout": "checkout",
        },
    )

    workflow.add_edge("search", "persist_turn")
    workflow.add_edge("cart", "persist_turn")
    workflow.add_edge("qa", "persist_turn")
    workflow.add_edge("chitchat", "persist_turn")
    workflow.add_edge("checkout", "persist_turn")
    workflow.add_edge("persist_turn", END)

    memory = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=memory)
