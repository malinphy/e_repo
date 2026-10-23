"""Chat thread repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.chat_threads import ChatThread


class ChatThreadRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, user_id: str, title: str | None = None) -> ChatThread:
        record = ChatThread(user_id=user_id, title=title)
        self._session.add(record)
        self._session.flush()
        return record

    def get(self, thread_id: int) -> ChatThread | None:
        return self._session.get(ChatThread, thread_id)

    def list_for_user(self, user_id: str, limit: int = 50) -> list[ChatThread]:
        stmt = (
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())