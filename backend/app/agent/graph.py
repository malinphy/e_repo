"""Main Agent Coordinator Graph."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Literal
import aiosqlite
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from ..core.config import get_settings
from .nodes.chitchat import chitchat_node
from .nodes.load_context import load_context_node
from .nodes.router import router_node
from .state import ShopState
from .subgraphs.cart.graph import build_cart_subgraph
from .subgraphs.checkout.checkout_node import checkout_node
from .subgraphs.qa.graph import build_qa_subgraph
from .subgraphs.search.graph import build_search_subgraph

logger = logging.getLogger(__name__)

_checkpointer_by_loop: dict[asyncio.AbstractEventLoop, tuple[AsyncSqliteSaver, aiosqlite.Connection]] = {}
_graph_by_loop: dict[asyncio.AbstractEventLoop, Any] = {}


async def get_sqlite_checkpointer() -> AsyncSqliteSaver:
    """Returns an AsyncSqliteSaver bound to the current running event loop."""
    loop = asyncio.get_running_loop()
    if loop not in _checkpointer_by_loop:
        settings = get_settings()
        db_path = settings.checkpoints_db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(db_path)
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        _checkpointer_by_loop[loop] = (saver, conn)
    return _checkpointer_by_loop[loop][0]


def route_after_router(state: ShopState) -> Literal["search", "cart", "qa", "chitchat", "checkout"]:
    """Conditional routing based on structured intent."""
    intent = state.get("intent") or "search"
    if intent in ("search", "cart", "qa", "chitchat", "checkout"):
        return intent
    return "search"


def build_shop_graph(checkpointer: Any | None = None):
    """Build and compile the main E-Commerce Shop Graph without redundant persist nodes."""
    workflow = StateGraph(ShopState)

    # 1. Register Nodes & Subgraphs
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("router", router_node)
    workflow.add_node("search", build_search_subgraph())
    workflow.add_node("cart", build_cart_subgraph())
    workflow.add_node("qa", build_qa_subgraph())
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node("checkout", checkout_node)

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

    # All subgraphs flow directly to END (checkpointer persists state automatically)
    workflow.add_edge("search", END)
    workflow.add_edge("cart", END)
    workflow.add_edge("qa", END)
    workflow.add_edge("chitchat", END)
    workflow.add_edge("checkout", END)

    memory = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=memory)


async def get_compiled_shop_graph():
    """Returns the compiled shop graph configured with the loop's AsyncSqliteSaver."""
    loop = asyncio.get_running_loop()
    if loop not in _graph_by_loop:
        checkpointer = await get_sqlite_checkpointer()
        _graph_by_loop[loop] = build_shop_graph(checkpointer=checkpointer)
    return _graph_by_loop[loop]
