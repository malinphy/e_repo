"""Search Subgraph construction and compilation."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .normalize_rank import normalize_rank_node
from .query_rewriter import query_rewriter_node
from .serp_fetch import serp_fetch_node
from .state import SearchSubgraphState


def build_search_subgraph():
    """Build and compile the Search Subgraph.

    Flow:
        START -> query_rewriter -> serp_fetch -> normalize_rank -> END
    """
    subgraph = StateGraph(SearchSubgraphState)

    subgraph.add_node("query_rewriter", query_rewriter_node)
    subgraph.add_node("serp_fetch", serp_fetch_node)
    subgraph.add_node("normalize_rank", normalize_rank_node)

    subgraph.add_edge(START, "query_rewriter")
    subgraph.add_edge("query_rewriter", "serp_fetch")
    subgraph.add_edge("serp_fetch", "normalize_rank")
    subgraph.add_edge("normalize_rank", END)

    return subgraph.compile()
