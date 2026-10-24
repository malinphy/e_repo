"""State schema for Search Subgraph."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from ...state import ShopState


class SearchSubgraphState(ShopState):
    """Internal state for Search Subgraph execution."""

    raw_products: Optional[List[Dict[str, Any]]]
