"""load_history node: load previous messages from a chat thread into state."""
from __future__ import annotations

from typing import Any

from ...repositories.chat_message_repo import ChatMessageRepository
from ...repositories.chat_thread_repo import ChatThreadRepository
from ..deps import AgentDeps
from ..state import AgentState

MAX_HISTORY_MESSAGES = 20


def make_load_history_node(deps: AgentDeps):
    def load_history(state: AgentState) -> dict[str, Any]:
        thread_id = state.get("thread_id")
        if thread_id is None:
            return {"message_history": []}

        session = deps.session_factory()
        try:
            thread = ChatThreadRepository(session).get(thread_id)
            if thread is None:
                return {"message_history": []}

            messages = ChatMessageRepository(session).list_for_thread(
                thread_id, limit=MAX_HISTORY_MESSAGES
            )
            history = [
                {"role": m.role, "content": m.content} for m in messages
            ]
            return {"message_history": history}
        finally:
            session.close()

    return load_history