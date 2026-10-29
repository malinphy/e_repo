"""Pytest fixtures for unit and integration testing."""
from __future__ import annotations

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, engine as default_engine
import backend.app.models  # noqa: F401 - ensure models are registered


@pytest.fixture(scope="session", autouse=True)
def initialize_default_database():
    """Ensure SQLite tables exist in the default database before any test runs."""
    Base.metadata.create_all(bind=default_engine)
    yield


@pytest.fixture(scope="session")
def test_engine():
    """Create an in-memory SQLite engine for the test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine):
    """Provide a transactional database session for an individual test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
