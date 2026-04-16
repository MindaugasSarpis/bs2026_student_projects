"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from repops.db import SessionFactory


def get_db() -> Generator[Session, None, None]:
    """Yield a database session per request."""
    session: Session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
