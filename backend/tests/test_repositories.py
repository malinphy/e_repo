"""Tests for the SQLAlchemy repositories."""
from __future__ import annotations

from ecommerce_agent.repositories.agent_runs_repo import AgentRunRepository
from ecommerce_agent.repositories.search_history_repo import SearchHistoryRepository
from ecommerce_agent.repositories.user_preferences_repo import UserPreferencesRepository


def test_search_history_add_and_list(session_factory) -> None:
    session = session_factory()
    try:
        repo = SearchHistoryRepository(session)
        repo.add("usb hub", ["amazon", "ebay"], result_count=3, user_id="u1")
        repo.add("mouse", ["amazon"], result_count=1, user_id="u1")
        repo.add("other user query", ["amazon"], result_count=1, user_id="u2")
        session.commit()

        rows = repo.list_for_user("u1")
        assert len(rows) == 2
        assert {row.query for row in rows} == {"usb hub", "mouse"}
        assert rows[0].engines in {"amazon,ebay", "amazon"}
    finally:
        session.close()


def test_user_preferences_upsert_creates_then_updates(session_factory) -> None:
    session = session_factory()
    try:
        repo = UserPreferencesRepository(session)
        created = repo.upsert("u1", ["amazon"], max_price="100", currency="EUR")
        session.commit()
        assert created.preferred_engines == "amazon"
        assert created.currency == "EUR"

        updated = repo.upsert("u1", ["ebay", "walmart"], max_price="50", currency="USD")
        session.commit()
        assert updated.preferred_engines == "ebay,walmart"
        assert updated.max_price == "50"
        assert repo.get("u1").currency == "USD"  # type: ignore[union-attr]
    finally:
        session.close()


def test_agent_run_lifecycle(session_factory) -> None:
    session = session_factory()
    try:
        repo = AgentRunRepository(session)
        run = repo.create("usb hub", user_id="u1")
        session.commit()
        assert run.status == "pending"

        repo.complete(run.id, "here you go")
        session.commit()
        completed = repo.get(run.id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.final_answer == "here you go"

        failed = repo.create("broken")
        session.commit()
        repo.fail(failed.id, "boom")
        session.commit()
        assert repo.get(failed.id).status == "failed"  # type: ignore[union-attr]
        assert len(repo.list_recent()) == 2
    finally:
        session.close()


def test_agent_run_get_missing_returns_none(session_factory) -> None:
    session = session_factory()
    try:
        assert AgentRunRepository(session).get(12345) is None
    finally:
        session.close()
