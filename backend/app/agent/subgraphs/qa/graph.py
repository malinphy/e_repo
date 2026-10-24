"""Product QA Subgraph construction and compilation."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from ...state import ShopState
from .qa_node import qa_node


def build_qa_subgraph():
    """Build and compile the Product QA Subgraph.

    Flow:
        START -> qa_node -> END
    """
    subgraph = StateGraph(ShopState)
    subgraph.add_node("qa_node", qa_node)
    subgraph.add_edge(START, "qa_node")
    subgraph.add_edge("qa_node", END)
    return subgraph.compile()
