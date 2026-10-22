"""Chat message repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.chat_messages import ChatMessage


class ChatMessageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        thread_id: int,
        role: str,
        content: str,
        run_id: int | None = None,
    ) -> ChatMessage:
        record = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            run_id=run_id,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def list_for_thread(self, thread_id: int, limit: int = 100) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())