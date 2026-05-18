from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import Book, ReadingProgress, ReadingStatus, UserSettings


def _create_book(client, **overrides):
    payload = {"title": "Book", **overrides}
    resp = client.post("/api/books", json=payload)
    assert resp.status_code == 201
    return resp.json()


def test_statistics_requires_auth(client):
    client.headers.pop("X-API-Key")
    resp = client.get("/api/statistics")
    assert resp.status_code == 401


def test_statistics_empty_library(client):
    resp = client.get("/api/statistics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["avg_books_per_month"] is None
    assert data["busiest_month"] is None
    assert data["avg_page_count"] is None
    assert data["most_popular_language"] is None
    assert data["status_distribution"] == {
        "want_to_read": 0,
        "currently_reading": 0,
        "read": 0,
        "did_not_finish": 0,
    }
    assert data["page_buckets"] == {
        "pages_to_read": 0,
        "pages_read": 0,
        "pages_wasted": 0,
    }
    assert data["pages_read_per_month"] == []
    assert data["books_finished_per_month"] == []
    assert data["books_finished_per_year"] == []
    assert data["favorite_author"] is None


def test_statistics_core_metrics_and_distributions(client):
    _create_book(
        client,
        title="Read Jan 1",
        author="Author A",
        cover_url="/api/covers/a1.jpg",
        page_count=100,
        language="EN",
        reading_status="read",
        date_finished="2026-01-10T10:00:00Z",
    )
    _create_book(
        client,
        title="Read Jan 2",
        author="Author A",
        cover_url="/api/covers/a2.jpg",
        page_count=200,
        language="EN",
        reading_status="read",
        date_finished="2026-01-15T10:00:00Z",
    )
    _create_book(
        client,
        title="Read Mar",
        author="Author B",
        page_count=300,
        language="DE",
        reading_status="read",
        date_finished="2026-03-01T10:00:00Z",
    )
    _create_book(client, title="Want", page_count=120, language="EN", reading_status="want_to_read")
    dnf = _create_book(client, title="DNF", author="Author A", language="FR", reading_status="did_not_finish")

    client.post(f"/api/books/{dnf['id']}/progress", json={"page": 40})
    client.post(f"/api/books/{dnf['id']}/progress", json={"page": 60})

    resp = client.get("/api/statistics")
    assert resp.status_code == 200
    data = resp.json()

    assert data["avg_books_per_month"] == 1.5
    assert data["busiest_month"] == "2026-01"
    assert data["busiest_month_count"] == 2
    assert data["avg_page_count"] == 180
    assert data["most_popular_language"] == "EN"
    assert data["most_popular_language_count"] == 3

    assert data["status_distribution"] == {
        "want_to_read": 1,
        "currently_reading": 0,
        "read": 3,
        "did_not_finish": 1,
    }
    assert data["page_buckets"] == {
        "pages_to_read": 120,
        "pages_read": 600,
        "pages_wasted": 60,
    }

    assert data["books_finished_per_month"] == [
        {"month": "2026-01", "count": 2},
        {"month": "2026-02", "count": 0},
        {"month": "2026-03", "count": 1},
    ]
    assert data["pages_read_per_month"] == [
        {"month": "2026-01", "pages": 300},
        {"month": "2026-02", "pages": 0},
        {"month": "2026-03", "pages": 300},
    ]
    assert data["books_finished_per_year"] == [{"year": 2026, "count": 3}]

    assert data["favorite_author"]["author"] == "Author A"
    assert data["favorite_author"]["book_count"] == 3
    assert "/api/covers/a1.jpg" in data["favorite_author"]["cover_urls"]
    assert "/api/covers/a2.jpg" in data["favorite_author"]["cover_urls"]


def test_statistics_timezone_month_bucketing(client, session: Session):
    settings = session.exec(select(UserSettings)).first()
    settings.timezone = "America/New_York"
    session.add(settings)
    session.commit()

    _create_book(
        client,
        title="Boundary",
        reading_status="read",
        page_count=222,
        date_finished="2026-05-01T03:00:00Z",
    )

    resp = client.get("/api/statistics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["books_finished_per_month"] == [{"month": "2026-04", "count": 1}]
    assert data["pages_read_per_month"] == [{"month": "2026-04", "pages": 222}]


def test_statistics_pages_wasted_ignores_non_dnf(client):
    read = _create_book(client, title="Read", reading_status="read")
    dnf = _create_book(client, title="DNF", reading_status="did_not_finish")
    client.post(f"/api/books/{read['id']}/progress", json={"page": 90})
    client.post(f"/api/books/{dnf['id']}/progress", json={"page": 33})

    resp = client.get("/api/statistics")
    assert resp.status_code == 200
    assert resp.json()["page_buckets"]["pages_wasted"] == 33


def test_statistics_invalid_timezone_falls_back_to_utc(client, session: Session):
    settings = session.exec(select(UserSettings)).first()
    settings.timezone = "Mars/OlympusMons"
    session.add(settings)
    session.commit()

    _create_book(
        client,
        title="UTC fallback",
        reading_status="read",
        page_count=111,
        date_finished="2026-05-01T00:30:00Z",
    )

    resp = client.get("/api/statistics")
    assert resp.status_code == 200
    assert resp.json()["books_finished_per_month"] == [{"month": "2026-05", "count": 1}]
