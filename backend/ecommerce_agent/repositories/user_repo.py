"""User repository."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.users import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: str) -> User | None:
        return self._session.get(User, user_id)

    def upsert(
        self,
        user_id: str,
        location: str | None = None,
        gender: str | None = None,
        age: int | None = None,
    ) -> User:
        """Create the user if absent, otherwise update the given profile fields."""
        record = self._session.get(User, user_id)
        if record is None:
            record = User(
                user_id=user_id,
                location=location,
                gender=gender,
                age=age,
            )
            self._session.add(record)
        else:
            if location is not None:
                record.location = location
            if gender is not None:
                record.gender = gender
            if age is not None:
                record.age = age
        self._session.flush()
        return record