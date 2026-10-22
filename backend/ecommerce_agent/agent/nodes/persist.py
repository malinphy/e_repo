"""persist node: record the run, search history, and chat messages."""
from __future__ import annotations

import logging
from typing import Any

from ...repositories.agent_runs_repo import AgentRunRepository
from ...repositories.chat_message_repo import ChatMessageRepository
from ...repositories.chat_thread_repo import ChatThreadRepository
from ...repositories.engine_results_repo import EngineResultsRepository
from ...repositories.search_history_repo import SearchHistoryRepository
from ..deps import AgentDeps
from ..state import AgentState

logger = logging.getLogger(__name__)


def make_persist_node(deps: AgentDeps):
    def persist(state: AgentState) -> dict[str, Any]:
        session = deps.session_factory()
        try:
            run_id = state.get("run_id")
            error = state.get("error")
            answer = state.get("answer", "")
            thread_id = state.get("thread_id")
            user_id = state.get("user_id")
            query = state.get("query", "")

            if run_id is not None:
                runs = AgentRunRepository(session)
                if error:
                    runs.fail(run_id, error)
                else:
                    runs.complete(run_id, answer)

                EngineResultsRepository(session).replace_for_run(
                    run_id,
                    state.get("results") or {},
                    state.get("engine_errors") or {},
                )

            history = SearchHistoryRepository(session)
            history.add(
                query=query,
                engines=state.get("engines") or [],
                result_count=len(state.get("products") or []),
                user_id=user_id,
            )

            # Persist chat messages if a thread is associated.
            if thread_id is not None:
                threads = ChatThreadRepository(session)
                if threads.get(thread_id) is not None:
                    messages = ChatMessageRepository(session)
                    messages.add(thread_id, "user", query, run_id=run_id)
                    if answer:
                        messages.add(thread_id, "assistant", answer, run_id=run_id)

            session.commit()
        except Exception as exc:  # noqa: BLE001 - persistence must not break the response
            session.rollback()
            logger.exception("failed to persist agent run: %s", exc)
        finally:
            session.close()
        return {}

    return persist
