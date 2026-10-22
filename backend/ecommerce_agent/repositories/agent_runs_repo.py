"""AgentRun repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.agent_runs import AgentRun


class AgentRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, query: str, user_id: str | None = None) -> AgentRun:
        record = AgentRun(user_id=user_id, query=query, status="pending")
        self._session.add(record)
        self._session.flush()
        return record

    def get(self, run_id: int) -> AgentRun | None:
        return self._session.get(AgentRun, run_id)

    def complete(self, run_id: int, final_answer: str) -> AgentRun | None:
        record = self._session.get(AgentRun, run_id)
        if record is None:
            return None
        record.final_answer = final_answer
        record.status = "completed"
        self._session.flush()
        return record

    def fail(self, run_id: int, error: str) -> AgentRun | None:
        record = self._session.get(AgentRun, run_id)
        if record is None:
            return None
        record.error = error
        record.status = "failed"
        self._session.flush()
        return record

    def list_recent(self, limit: int = 50) -> list[AgentRun]:
        stmt = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
        return list(self._session.scalars(stmt).all())
