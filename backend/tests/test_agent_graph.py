"""Tests for the LangGraph agent pipeline."""
from __future__ import annotations

from typing import Any
from types import SimpleNamespace

from ecommerce_agent.agent.deps import AgentDeps
from ecommerce_agent.agent.graph import build_graph
from ecommerce_agent.agent.runner import run_agent
from ecommerce_agent.repositories.search_history_repo import SearchHistoryRepository
from ecommerce_agent.schemas.query import ParsedQuery
from ecommerce_agent.tools.serpapi.base import SerpAPIEngineAdapter
from ecommerce_agent.tools.serpapi.factory import available_engines
from tests.conftest import FakeAdapter


class _StructuredRunner:
    def __init__(self, parsed: ParsedQuery) -> None:
        self._parsed = parsed

    def invoke(self, input: Any, **kwargs: Any) -> ParsedQuery:
        return self._parsed


class StructuredLLM:
    """LLM double that answers structured output and free text."""

    def __init__(self, parsed: ParsedQuery | None = None, answer: str = "LLM answer") -> None:
        self._parsed = parsed or ParsedQuery(keywords="fallback", engines=["amazon"])
        self._answer = answer
        self.invoke_calls = 0

    def with_structured_output(self, schema: Any) -> _StructuredRunner:
        return _StructuredRunner(self._parsed)

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        self.invoke_calls += 1
        return SimpleNamespace(content=self._answer)


class BoomLLM:
    def with_structured_output(self, schema: Any) -> "BoomLLM":
        raise RuntimeError("structured output unavailable")

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        raise RuntimeError("llm offline")


def _graph(deps: AgentDeps):
    return build_graph(deps)


def test_graph_runs_all_nodes_and_persists(deps: AgentDeps, session_factory) -> None:
    out = _graph(deps).invoke({"query": "usb hub", "user_id": "u1", "run_id": None})

    assert out["engines"] == ["amazon", "google_shopping"]
    assert len(out["products"]) == 2
    assert "usb hub" in out["answer"]

    session = session_factory()
    try:
        rows = SearchHistoryRepository(session).list_for_user("u1")
        assert len(rows) == 1
        assert rows[0].query == "usb hub"
        assert rows[0].result_count == 2
        assert rows[0].engines == "amazon,google_shopping"
    finally:
        session.close()


def test_parse_query_falls_back_to_heuristic_when_llm_is_none(deps: AgentDeps) -> None:
    out = _graph(deps).invoke({"query": "  red shoes  "})
    assert out["intent"] == "search"
    assert out["parsed"]["keywords"] == "red shoes"
    assert out["parsed"]["engines"] == available_engines()


def test_parse_query_falls_back_when_llm_raises(engines, session_factory) -> None:
    deps = AgentDeps(engines=engines, llm_factory=lambda: BoomLLM(), session_factory=session_factory)
    out = _graph(deps).invoke({"query": "green hat"})
    assert out["intent"] == "search"
    assert out["parsed"]["keywords"] == "green hat"


def test_parse_query_uses_llm_and_restricts_engines(engines, session_factory) -> None:
    parsed = ParsedQuery(keywords="wireless mouse", engines=["amazon"])
    llm = StructuredLLM(parsed=parsed)
    deps = AgentDeps(engines=engines, llm_factory=lambda: llm, session_factory=session_factory)

    out = _graph(deps).invoke({"query": "cheap wireless mouse on amazon"})
    assert out["intent"] == "search"
    assert out["parsed"]["keywords"] == "wireless mouse"
    assert out["engines"] == ["amazon"]
    assert len(out["products"]) == 1


def test_unknown_engine_in_parsed_output_is_ignored(engines, session_factory) -> None:
    parsed = ParsedQuery(keywords="mouse", engines=["does_not_exist"])
    deps = AgentDeps(engines=engines, llm_factory=lambda: StructuredLLM(parsed=parsed), session_factory=session_factory)

    out = _graph(deps).invoke({"query": "mouse"})
    assert out["engines"] == ["google_shopping", "amazon"]


def test_failing_engine_is_isolated(engines, session_factory) -> None:
    engines["amazon"] = FakeAdapter("amazon", fail=True)
    deps = AgentDeps(engines=engines, llm_factory=lambda: None, session_factory=session_factory)

    out = _graph(deps).invoke({"query": "usb hub"})
    assert out["results"]["amazon"] == []
    assert len(out["products"]) == 1
    assert out["products"][0]["engine"] == "google_shopping"
    assert out.get("error") is None


def test_all_engines_failing_sets_error(session_factory) -> None:
    failing: dict[str, SerpAPIEngineAdapter] = {"amazon": FakeAdapter("amazon", fail=True)}
    deps = AgentDeps(engines=failing, llm_factory=lambda: None, session_factory=session_factory)

    out = _graph(deps).invoke({"query": "usb hub"})
    assert out["products"] == []
    assert "amazon" in (out.get("error") or "")


def test_no_products_yields_deterministic_answer(session_factory) -> None:
    deps = AgentDeps(engines={}, llm_factory=lambda: None, session_factory=session_factory)
    out = _graph(deps).invoke({"query": "nothing"})
    assert out["answer"] == "No products found for 'nothing'."


def test_products_are_sorted_by_price(deps: AgentDeps) -> None:
    out = _graph(deps).invoke({"query": "usb hub"})
    prices = [p["price"] for p in out["products"]]
    assert prices == ["$9.99", "$19.99"]


def test_max_price_filter_excludes_expensive_items(engines, session_factory) -> None:
    parsed = ParsedQuery(keywords="usb hub", engines=["google_shopping", "amazon"], max_price=10.0)
    deps = AgentDeps(engines=engines, llm_factory=lambda: StructuredLLM(parsed=parsed), session_factory=session_factory)

    out = _graph(deps).invoke({"query": "usb hub under $10"})
    assert all(p["price"] == "$9.99" for p in out["products"])


def test_run_agent_marks_run_completed(deps: AgentDeps, session_factory) -> None:
    out = run_agent("usb hub", user_id="u1", deps=deps)
    assert out["run_id"] is not None

    from ecommerce_agent.repositories.agent_runs_repo import AgentRunRepository

    session = session_factory()
    try:
        run = AgentRunRepository(session).get(out["run_id"])
        assert run is not None
        assert run.status == "completed"
        assert run.final_answer == out["answer"]
    finally:
        session.close()


def test_run_agent_reuses_supplied_compiled_graph(deps: AgentDeps) -> None:
    graph = build_graph(deps)
    out = run_agent("usb hub", deps=deps, graph=graph)
    assert out["answer"]


def test_supervisor_sets_search_intent_by_default(deps: AgentDeps) -> None:
    out = _graph(deps).invoke({"query": "usb hub"})
    assert out["intent"] == "search"


def test_supervisor_routes_non_search_intent(engines, session_factory) -> None:
    """Chit-chat and intents map to their own worker; unknown falls back to search."""
    from ecommerce_agent.agent.nodes.supervisor import route_after_supervisor

    assert route_after_supervisor({"intent": "search"}) == "search"
    assert route_after_supervisor({"intent": "chit_chat"}) == "chit_chat"
    assert route_after_supervisor({"intent": "add_cart"}) == "cart"
    assert route_after_supervisor({"intent": "remove_cart"}) == "cart"
    assert route_after_supervisor({"intent": "show_cart"}) == "cart"
    assert route_after_supervisor({}) == "search"


def test_supervisor_selects_engines_like_old_plan_tools(engines, session_factory) -> None:
    parsed = ParsedQuery(keywords="mouse", engines=["amazon"])
    deps = AgentDeps(
        engines=engines, llm_factory=lambda: StructuredLLM(parsed=parsed), session_factory=session_factory
    )
    out = _graph(deps).invoke({"query": "mouse"})
    assert out["engines"] == ["amazon"]


def test_graph_contains_supervisor_and_worker_nodes(deps: AgentDeps) -> None:
    graph = build_graph(deps)
    node_names = set(graph.get_graph().nodes.keys())
    assert "supervisor" in node_names
    assert "search" in node_names
    assert "respond" in node_names
    assert "load_history" in node_names
    assert "persist" in node_names
    # deprecated parse_query/plan_tools are gone
    assert "parse_query" not in node_names
    assert "plan_tools" not in node_names


def test_chit_chat_routes_to_respond_without_search(session_factory) -> None:
    deps = AgentDeps(engines={}, llm_factory=lambda: None, session_factory=session_factory)
    out = _graph(deps).invoke({"query": "merhaba"})
    assert out["intent"] == "chit_chat"
    assert not out.get("products")  # search never ran, so no product list
    # answer is a chat reply, not a product listing
    assert "Hi!" in out["answer"]
