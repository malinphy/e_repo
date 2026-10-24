"""Cart Subgraph construction and compilation."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from ...state import ShopState
from .cart_node import cart_node


def build_cart_subgraph():
    """Build and compile the Cart Subgraph.

    Flow:
        START -> cart_node -> END
    """
    subgraph = StateGraph(ShopState)
    subgraph.add_node("cart_node", cart_node)
    subgraph.add_edge(START, "cart_node")
    subgraph.add_edge("cart_node", END)
    return subgraph.compile()
