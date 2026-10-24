"""Tests for Search Subgraph nodes and end-to-end execution."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import HumanMessage

from backend.app.agent.subgraphs.search.query_rewriter import query_rewriter_node
from backend.app.agent.subgraphs.search.normalize_rank import normalize_rank_node
from backend.app.agent.subgraphs.search.graph import build_search_subgraph
from backend.app.agent.subgraphs.search.state import SearchSubgraphState
from backend.app.schemas.product import Product


def test_query_rewriter_extracts_price_and_keywords():
    """Verify query rewriter extracts keywords and price limit from query text."""
    state: SearchSubgraphState = {
        "messages": [HumanMessage(content="find running shoes under 120")],
        "user_id": "u1",
        "thread_id": "t1",
        "chat_id": "c1",
        "intent": "search",
        "search_query": None,
        "last_results": [],
        "cart": [],
        "pending_action": None,
        "error": None,
        "raw_products": None,
    }

    result = query_rewriter_node(state)
    query_data = result["search_query"]

    assert query_data["max_price"] == 120.0
    assert "running shoes" in query_data["keywords"].lower()


def test_normalize_rank_deduplicates_and_filters_budget():
    """Verify deduplication and budget filtering in normalize_rank_node."""
    state: SearchSubgraphState = {
        "messages": [HumanMessage(content="shoes")],
        "user_id": "u1",
        "thread_id": "t1",
        "chat_id": "c1",
        "intent": "search",
        "search_query": {"keywords": "shoes", "max_price": 100.0},
        "last_results": [],
        "cart": [],
        "pending_action": None,
        "error": None,
        "raw_products": [
            {"id": "w1", "title": "Nike Revolution 6", "price": 65.0, "source": "walmart", "rating": 4.5, "url": "url1"},
            {"id": "w2", "title": "Nike Revolution 6", "price": 68.0, "source": "ebay", "rating": 4.0, "url": "url2"}, # Duplicate title
            {"id": "w3", "title": "Nike Air Zoom (Expensive)", "price": 180.0, "source": "amazon", "rating": 4.9, "url": "url3"}, # Over budget
            {"id": "w4", "title": "Adidas Ultraboost Light", "price": 95.0, "source": "google_shopping", "rating": 4.7, "url": "url4"},
        ],
    }

    result = normalize_rank_node(state)
    ranked = result["last_results"]

    # Over budget ($180) must be filtered out
    assert all(p["price"] <= 100.0 for p in ranked)
    # Duplicate Nike Revolution 6 must be deduplicated to 1 item
    assert len([p for p in ranked if "Revolution 6" in p["title"]]) == 1
    # Check that AIMessage was added
    assert len(result["messages"]) == 1


@pytest.mark.asyncio
async def test_search_subgraph_compiles_and_runs():
    """Verify Search Subgraph compiles and executes end-to-end with mocked SerpAPI."""
    subgraph = build_search_subgraph()

    sample_product = Product(
        id="walmart_sub_1",
        title="Logitech MX Master 3S",
        price=99.99,
        source="walmart",
        url="https://walmart.com/item/mx3",
        rating=4.9,
    )

    with patch("backend.app.agent.subgraphs.search.serp_fetch._fetch_single_engine", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [sample_product]

        initial_state: SearchSubgraphState = {
            "messages": [HumanMessage(content="logitech mx master")],
            "user_id": "u_test",
            "thread_id": "t_test",
            "chat_id": "c_test",
            "intent": "search",
            "search_query": {"keywords": "logitech mx master", "marketplaces": ["walmart"]},
            "last_results": [],
            "cart": [],
            "pending_action": None,
            "error": None,
            "raw_products": None,
        }

        final_state = await subgraph.ainvoke(initial_state)

        assert len(final_state["last_results"]) >= 1
        assert final_state["last_results"][0]["id"] == "walmart_sub_1"
        assert len(final_state["messages"]) >= 2  # HumanMessage + AIMessage
