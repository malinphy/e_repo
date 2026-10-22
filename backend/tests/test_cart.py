"""Tests for the cart node: add/remove/show via the supervisor-routed graph."""
from __future__ import annotations

from ecommerce_agent.agent.deps import AgentDeps
from ecommerce_agent.agent.graph import build_graph
from ecommerce_agent.agent.nodes.cart import _resolve_reference
from ecommerce_agent.agent.runner import run_agent
from ecommerce_agent.repositories.cart_repo import CartRepository
from ecommerce_agent.schemas.query import ParsedQuery
from tests.conftest import FakeAdapter


def _graph(deps: AgentDeps):
    return build_graph(deps)


def test_resolve_reference_by_position() -> None:
    items = [
        {"title": "Nike Air", "link": "a"},
        {"title": "Adidas Samba", "link": "b"},
        {"title": "Puma Suede", "link": "c"},
    ]
    assert [p["title"] for p in _resolve_reference("1st", items)] == ["Nike Air"]
    assert [p["title"] for p in _resolve_reference("2.si", items)] == ["Adidas Samba"]
    assert [p["title"] for p in _resolve_reference("3", items)] == ["Puma Suede"]
    assert _resolve_reference("99", items) == []


def test_resolve_reference_by_title_substring() -> None:
    items = [
        {"title": "Nike Air Force", "link": "a"},
        {"title": "Adidas Samba", "link": "b"},
    ]
    assert [p["title"] for p in _resolve_reference("nike", items)] == ["Nike Air Force"]
    assert _resolve_reference("asics", items) == []


def test_resolve_reference_all() -> None:
    items = [{"title": "Nike Air", "link": "a"}, {"title": "Adidas", "link": "b"}]
    assert len(_resolve_reference("all", items)) == 2
    # no reference auto-picks the first
    assert [p["title"] for p in _resolve_reference(None, items)] == ["Nike Air"]
    assert [p["title"] for p in _resolve_reference("", items)] == ["Nike Air"]


def test_cart_show_empty(engines, session_factory) -> None:
    deps = AgentDeps(engines=engines, llm_factory=lambda: None, session_factory=session_factory)
    parsed = ParsedQuery(keywords="", engines=[], intent="show_cart")
    llm = _Structured(parsed)
    deps = AgentDeps(engines=engines, llm_factory=lambda: llm, session_factory=session_factory)
    out = _graph(deps).invoke({"query": "sepetimde ne var", "user_id": "u1"})
    assert "empty" in out["answer"].lower()


def test_cart_add_show_remove_flow(engines, session_factory) -> None:
    deps = AgentDeps(engines=engines, llm_factory=lambda: None, session_factory=session_factory)

    # 1. search to populate last-run products (run_agent persists the run)
    run_agent("nike ayakkabi", user_id="u1", deps=deps)

    # 2. add the 1st result
    add_deps = AgentDeps(
        engines=engines,
        llm_factory=lambda: _Structured(ParsedQuery(keywords="", engines=[], intent="add_cart", item_reference="1")),
        session_factory=session_factory,
    )
    out = run_agent("ekle", user_id="u1", deps=add_deps)
    assert "Added" in out["answer"]

    # 3. show cart -> one item
    show_deps = AgentDeps(
        engines=engines,
        llm_factory=lambda: _Structured(ParsedQuery(keywords="", engines=[], intent="show_cart")),
        session_factory=session_factory,
    )
    out = run_agent("sepeti göster", user_id="u1", deps=show_deps)
    session = session_factory()
    try:
        items = CartRepository(session).list_items("u1")
        assert len(items) == 1
        assert items[0].quantity == 1
    finally:
        session.close()


class _Structured:
    def __init__(self, parsed: ParsedQuery) -> None:
        self._parsed = parsed

    def with_structured_output(self, schema):
        return _Runner(self._parsed)

    def invoke(self, input, **kwargs):
        class _R:
            content = "ok"
        return _R()


class _Runner:
    def __init__(self, parsed: ParsedQuery) -> None:
        self._parsed = parsed

    def invoke(self, input, **kwargs):
        return self._parsed