"""Shared pytest fixtures: in-memory DB, fake engines, fake LLM, API client."""
from __future__ import annotations

from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ecommerce_agent.agent.deps import AgentDeps
from ecommerce_agent.api.app import create_app
from ecommerce_agent.common.db.base import Base
from ecommerce_agent.tools.serpapi.base import SerpAPIEngineAdapter


class FakeAdapter(SerpAPIEngineAdapter):
    """Deterministic engine adapter for tests."""

    def __init__(self, engine: str, price: str = "$9.99", fail: bool = False) -> None:
        self.engine = engine
        self._price = price
        self._fail = fail

    def normalize(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Unused: this fake overrides the ``search`` template method."""
        return []

    def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        if self._fail:
            raise RuntimeError(f"{self.engine} is down")
        return [
            {
                "title": f"{self.engine} {query}",
                "price": self._price,
                "source": self.engine,
                "link": f"https://example.com/{self.engine}",
                "rating": 4.5,
                "reviews": 100,
            }
        ]


class FakeLLM:
    """Minimal chat model double recording the prompts it receives."""

    def __init__(self, content: str = "Best pick: example") -> None:
        self.content = content
        self.prompts: list[str] = []

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        self.prompts.append(str(input))

        class _Response:
            content = self.content

        return _Response()

    def with_structured_output(self, schema: Any, **kwargs: Any) -> "FakeLLM":
        self._schema = schema
        return self


@pytest.fixture()
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def engines() -> dict[str, FakeAdapter]:
    return {
        "google_shopping": FakeAdapter("google_shopping", price="$19.99"),
        "amazon": FakeAdapter("amazon", price="$9.99"),
    }


@pytest.fixture()
def deps(engines: dict[str, FakeAdapter], session_factory) -> AgentDeps:
    return AgentDeps(
        engines=engines,
        llm_factory=lambda: None,
        session_factory=session_factory,
    )


@pytest.fixture()
def client(deps: AgentDeps) -> Iterator[TestClient]:
    app = create_app(agent_deps=deps)
    with TestClient(app) as test_client:
        yield test_client
