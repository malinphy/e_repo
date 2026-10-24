"""Shared LangGraph state schema (ShopState)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from langgraph.graph import MessagesState


class ShopState(MessagesState):
    """The central state passed across all LangGraph nodes and subgraphs.

    Identities & Tracking:
        user_id: Active user identifier (injected securely from auth/session, not LLM).
        thread_id: Chat thread / session identifier matching LangGraph checkpointer.
        chat_id: Specific turn / run identifier for the current user interaction.

    Workflow State:
        intent: Detected intent: 'search', 'qa', 'cart', 'checkout', 'chitchat'.
        search_query: Structured parameters for search (keywords, max_price, etc.).
        last_results: List of recently displayed products (enables 'add the 2nd one' references).
        cart: List of current cart items loaded from the database.
        pending_action: Human-in-the-loop pending action (e.g. checkout confirmation).
        error: Error message if any node failed gracefully.
    """

    user_id: str
    thread_id: str
    chat_id: Optional[str]
    intent: Optional[str]
    search_query: Optional[Dict[str, Any]]
    last_results: List[Dict[str, Any]]
    cart: List[Dict[str, Any]]
    pending_action: Optional[Dict[str, Any]]
    error: Optional[str]
