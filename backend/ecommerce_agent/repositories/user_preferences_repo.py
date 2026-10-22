"""UserPreferences repository."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.user_preferences import UserPreferences


class UserPreferencesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: str) -> UserPreferences | None:
        return self._session.get(UserPreferences, user_id)

    def upsert(
        self,
        user_id: str,
        preferred_engines: list[str],
        max_price: str | None = None,
        currency: str = "USD",
    ) -> UserPreferences:
        record = self._session.get(UserPreferences, user_id)
        if record is None:
            record = UserPreferences(
                user_id=user_id,
                preferred_engines=",".join(preferred_engines),
                max_price=max_price,
                currency=currency,
            )
            self._session.add(record)
        else:
            record.preferred_engines = ",".join(preferred_engines)
            record.max_price = max_price
            record.currency = currency
        self._session.flush()
        return record
