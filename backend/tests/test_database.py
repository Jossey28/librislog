"""Tests for app.database module."""

from app.database import create_db_and_tables, get_session, _dispose_engine
from sqlmodel import Session


def test_create_db_and_tables():
    """Calling create_db_and_tables should not raise."""
    create_db_and_tables()


def test_get_session_yields_session():
    """get_session generator should yield a Session instance."""
    gen = get_session()
    session = next(gen)
    assert isinstance(session, Session)
    # Exhaust generator to close the session context
    try:
        next(gen)
    except StopIteration:
        pass


def test_dispose_engine():
    """Line 17: _dispose_engine should run without error."""
    _dispose_engine()
