"""Create all tables. Import models first so they register with Base.metadata."""
from __future__ import annotations

from .base import Base
from .engine import get_engine


def init_db() -> None:
    """Create all tables in the configured SQLite database."""
    # Import models so they are registered with Base.metadata before create_all.
    from ...models import search_history, user_preferences, agent_runs  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
