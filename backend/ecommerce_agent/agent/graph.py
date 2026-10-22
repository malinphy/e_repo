"""LangGraph wiring: parse_query -> plan_tools -> execute_tools -> synthesize -> persist."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .deps import AgentDeps
from .nodes.execute_tools import make_execute_tools_node
from .nodes.load_history import make_load_history_node
from .nodes.parse_query import make_parse_query_node
from .nodes.persist import make_persist_node
from .nodes.plan_tools import make_plan_tools_node
from .nodes.synthesize import make_synthesize_node
from .state import AgentState


def build_graph(deps: AgentDeps):
    """Build and compile the e-commerce agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("load_history", make_load_history_node(deps))
    graph.add_node("parse_query", make_parse_query_node(deps))
    graph.add_node("plan_tools", make_plan_tools_node(deps))
    graph.add_node("execute_tools", make_execute_tools_node(deps))
    graph.add_node("synthesize", make_synthesize_node(deps))
    graph.add_node("persist", make_persist_node(deps))

    graph.add_edge(START, "load_history")
    graph.add_edge("load_history", "parse_query")
    graph.add_edge("parse_query", "plan_tools")
    graph.add_edge("plan_tools", "execute_tools")
    graph.add_edge("execute_tools", "synthesize")
    graph.add_edge("synthesize", "persist")
    graph.add_edge("persist", END)

    return graph.compile()
