"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from repops.api.dependencies import get_db
from repops.api.main import app
from repops.models import Base


# ---------------------------------------------------------------------------
# In-memory SQLite DB for fast unit tests
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def engine():
    """Create a SQLite in-memory engine for the test session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db_session(engine) -> Session:
    """Yield a fresh session for each test, rolled back after."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """FastAPI test client with DB session overridden to use test DB."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()
