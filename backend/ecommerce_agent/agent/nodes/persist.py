"""persist node: record the run and search history."""
from __future__ import annotations

import logging
from typing import Any

from ...repositories.agent_runs_repo import AgentRunRepository
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

            if run_id is not None:
                runs = AgentRunRepository(session)
                if error:
                    runs.fail(run_id, error)
                else:
                    runs.complete(run_id, answer)

            history = SearchHistoryRepository(session)
            history.add(
                query=state.get("query", ""),
                engines=state.get("engines") or [],
                result_count=len(state.get("products") or []),
                user_id=state.get("user_id"),
            )
            session.commit()
        except Exception as exc:  # noqa: BLE001 - persistence must not break the response
            session.rollback()
            logger.exception("failed to persist agent run: %s", exc)
        finally:
            session.close()
        return {}

    return persist
