"""Tests for app.services.user_deletion module."""

from app.auth import get_password_hash
from app.models import Book, User, UserRole
from app.services.user_deletion import delete_user_reading_data


def test_delete_user_reading_data_cleans_local_covers(session, tmp_path):
    """Books with local cover URLs should have their cover files deleted."""
    user = User(
        firstname="Test",
        lastname="User",
        email="cover-test@example.com",
        role=UserRole.user,
        hashed_password=get_password_hash("password"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    cover_filename = "1__abc123.jpg"
    (tmp_path / cover_filename).write_bytes(b"cover-data")

    book = Book(
        user_id=user.id,
        title="Test Book",
        cover_url="/api/covers/" + cover_filename,
    )
    session.add(book)
    session.commit()

    counts = delete_user_reading_data(session, user.id, str(tmp_path))

    assert counts.books == 1
    assert not (tmp_path / cover_filename).exists()


def test_delete_user_reading_data_skips_external_covers(session, tmp_path):
    """Books with external cover URLs should skip cover file deletion."""
    user = User(
        firstname="Test",
        lastname="User",
        email="external-cover@example.com",
        role=UserRole.user,
        hashed_password=get_password_hash("password"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    book = Book(
        user_id=user.id,
        title="External Cover Book",
        cover_url="https://example.com/cover.jpg",
    )
    session.add(book)
    session.commit()

    counts = delete_user_reading_data(session, user.id, str(tmp_path))

    assert counts.books == 1
