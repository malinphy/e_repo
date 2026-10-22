"""SearchHistory repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.search_history import SearchHistory


class SearchHistoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        query: str,
        engines: list[str],
        result_count: int,
        user_id: str | None = None,
    ) -> SearchHistory:
        record = SearchHistory(
            user_id=user_id,
            query=query,
            engines=",".join(engines),
            result_count=result_count,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def list_for_user(self, user_id: str, limit: int = 50) -> list[SearchHistory]:
        stmt = (
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())
