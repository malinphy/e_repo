"""Checkout Subgraph definition."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from ...state import ShopState
from .checkout_node import checkout_node


def build_checkout_subgraph():
    """Build and compile the Checkout Subgraph with HITL interrupt support.

    Flow:
        START -> checkout_node (pauses at interrupt) -> END
    """
    subgraph = StateGraph(ShopState)
    subgraph.add_node("checkout_node", checkout_node)
    subgraph.add_edge(START, "checkout_node")
    subgraph.add_edge("checkout_node", END)
    return subgraph.compile()
