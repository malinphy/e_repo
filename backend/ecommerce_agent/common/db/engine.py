"""SQLite engine + session factory (Singleton)."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _ensure_parent_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _enable_sqlite_fk(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine() -> Engine:
    """Return the singleton SQLAlchemy engine for the configured SQLite path."""
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _ensure_parent_dir(settings.sqlite_path)
        _engine = create_engine(
            f"sqlite:///{settings.sqlite_path}",
            future=True,
            echo=False,
        )
        event.listen(_engine, "connect", _enable_sqlite_fk)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def session_scope() -> Iterator[Session]:
    """Yield a session that auto-commits on success and rolls back on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_for_tests() -> None:
    """Drop the cached engine so tests can reconfigure the path."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
