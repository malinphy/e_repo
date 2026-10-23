"""LangGraph wiring: supervisor router -> worker -> synthesize/respond -> persist."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .deps import AgentDeps
from .nodes.cart import make_cart_node
from .nodes.execute_tools import make_execute_tools_node
from .nodes.load_history import make_load_history_node
from .nodes.persist import make_persist_node
from .nodes.respond import make_respond_node
from .nodes.supervisor import make_supervisor_node, route_after_supervisor
from .nodes.synthesize import make_synthesize_node
from .state import AgentState


def build_graph(deps: AgentDeps):
    """Build and compile the e-commerce agent graph.

    Flow: START -> load_history -> supervisor -(route on intent)->
      * intent ``search``         -> search -> synthesize -> persist -> END
      * intent ``chit_chat``      -> respond -> persist -> END
      * intent ``add_cart`` / ``remove_cart`` / ``show_cart`` -> cart -> persist -> END

    Routing branches on the structured ``intent`` field, never on LLM free text.
    """
    graph = StateGraph(AgentState)

    graph.add_node("load_history", make_load_history_node(deps))
    graph.add_node("supervisor", make_supervisor_node(deps))
    graph.add_node("search", make_execute_tools_node(deps))
    graph.add_node("synthesize", make_synthesize_node(deps))
    graph.add_node("respond", make_respond_node(deps))
    graph.add_node("cart", make_cart_node(deps))
    graph.add_node("persist", make_persist_node(deps))

    graph.add_edge(START, "load_history")
    graph.add_edge("load_history", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "search": "search",
            "chit_chat": "respond",
            "cart": "cart",
        },
    )

    graph.add_edge("search", "synthesize")
    graph.add_edge("synthesize", "persist")
    graph.add_edge("respond", "persist")
    graph.add_edge("cart", "persist")
    graph.add_edge("persist", END)

    return graph.compile()
