"""Tests for the main coordinator graph (build_shop_graph)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import HumanMessage

from backend.app.agent.graph import build_shop_graph
from backend.app.schemas.product import Product


@pytest.mark.asyncio
async def test_main_graph_chitchat_flow():
    """Verify main graph routes greetings to chitchat and responds."""
    app = build_shop_graph()
    config = {"configurable": {"thread_id": "test_th_chitchat"}}

    state = {
        "messages": [HumanMessage(content="merhaba")],
        "user_id": "user_flow_1",
        "thread_id": "test_th_chitchat",
    }

    result = await app.ainvoke(state, config=config)

    assert result["intent"] == "chitchat"
    assert len(result["messages"]) >= 2
    # Verify assistant replied warmly
    last_reply = result["messages"][-1].content
    assert any(w in last_reply.lower() for w in ("merhaba", "hoş", "asistan"))


@pytest.mark.asyncio
async def test_main_graph_search_flow():
    """Verify main graph routes search queries through the search subgraph."""
    app = build_shop_graph()
    config = {"configurable": {"thread_id": "test_th_search"}}

    sample_product = Product(
        id="walmart_main_1",
        title="Sony Headphones WH-CH520",
        price=59.99,
        source="walmart",
        url="https://walmart.com/item/wh520",
        rating=4.6,
    )

    with patch("backend.app.agent.subgraphs.search.serp_fetch._fetch_single_engine", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [sample_product]

        state = {
            "messages": [HumanMessage(content="sony headphones ara")],
            "user_id": "user_flow_2",
            "thread_id": "test_th_search",
        }

        result = await app.ainvoke(state, config=config)

        assert result["intent"] == "search"
        assert len(result["last_results"]) >= 1
        assert "Sony Headphones" in result["last_results"][0]["title"]
