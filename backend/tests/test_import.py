"""
Tests for the book import service and import API endpoints.

HTTP calls are intercepted with monkeypatch — no real network requests are made.
All test functions are modular (no classes).
"""

import pytest
from fastapi.testclient import TestClient

from app.schemas import BookImportCandidate
from app.services import book_import


# ── Fake response data ─────────────────────────────────────────────────────────

OPEN_LIBRARY_DUNE_DOC = {
    "title": "Dune",
    "author_name": ["Frank Herbert"],
    "isbn": ["9780441013593", "0441013597"],
    "publisher": ["Ace Books", "Chilton Books"],
    "first_publish_year": 1965,
    "number_of_pages_median": 412,
    "subject": ["Science Fiction", "Ecology", "Fantasy"],
    "cover_i": 11481354,
}

GOOGLE_BOOKS_FOUNDATION_ITEM = {
    "volumeInfo": {
        "title": "Foundation",
        "authors": ["Isaac Asimov"],
        "industryIdentifiers": [
            {"type": "ISBN_13", "identifier": "9780553293357"},
            {"type": "ISBN_10", "identifier": "0553293354"},
        ],
        "publisher": "Bantam Books",
        "publishedDate": "1991",
        "pageCount": 255,
        "categories": ["Science Fiction"],
        "imageLinks": {"thumbnail": "http://books.google.com/thumbnail.jpg"},
    }
}


# ── map_open_library unit tests ────────────────────────────────────────────────

def test_map_open_library_fields():
    result = book_import.map_open_library(OPEN_LIBRARY_DUNE_DOC)
    assert result.title == "Dune"
    assert result.author == "Frank Herbert"
    assert result.isbn == "9780441013593"  # ISBN-13 preferred
    assert result.published_year == 1965
    assert result.page_count == 412
    assert result.publisher == "Ace Books"
    assert "Science Fiction" in result.genre
    assert result.cover_url == "https://covers.openlibrary.org/b/id/11481354-M.jpg"
    assert result.source == "open_library"


def test_map_open_library_missing_optional_fields():
    minimal = {"title": "Minimal Book"}
    result = book_import.map_open_library(minimal)
    assert result.title == "Minimal Book"
    assert result.author is None
    assert result.isbn is None
    assert result.cover_url is None
    assert result.publisher is None
    assert result.genre is None
    assert result.source == "open_library"


def test_map_open_library_genre_capped_at_three():
    doc = {"title": "X", "subject": ["A", "B", "C", "D", "E"]}
    result = book_import.map_open_library(doc)
    assert result.genre == "A, B, C"


# ── map_google_books unit tests ───────────────────────────────────────────────

def test_map_google_books_fields():
    result = book_import.map_google_books(GOOGLE_BOOKS_FOUNDATION_ITEM)
    assert result.title == "Foundation"
    assert result.author == "Isaac Asimov"
    assert result.isbn == "9780553293357"  # ISBN-13 preferred
    assert result.publisher == "Bantam Books"
    assert result.published_year == 1991
    assert result.page_count == 255
    assert result.genre == "Science Fiction"
    assert result.cover_url == "https://books.google.com/thumbnail.jpg"  # https upgraded
    assert result.source == "google_books"


def test_map_google_books_missing_optional_fields():
    minimal = {"volumeInfo": {"title": "Minimal"}}
    result = book_import.map_google_books(minimal)
    assert result.title == "Minimal"
    assert result.author is None
    assert result.isbn is None
    assert result.cover_url is None
    assert result.published_year is None
    assert result.source == "google_books"


def test_map_google_books_prefers_isbn13_over_isbn10():
    item = {
        "volumeInfo": {
            "title": "T",
            "industryIdentifiers": [
                {"type": "ISBN_10", "identifier": "0553293354"},
                {"type": "ISBN_13", "identifier": "9780553293357"},
            ],
        }
    }
    result = book_import.map_google_books(item)
    assert result.isbn == "9780553293357"


def test_map_google_books_published_year_partial_date():
    item = {"volumeInfo": {"title": "T", "publishedDate": "1991-06"}}
    result = book_import.map_google_books(item)
    assert result.published_year == 1991


# ── search() integration tests using monkeypatch ──────────────────────────────

@pytest.fixture()
def fake_ol_result() -> list[BookImportCandidate]:
    return [book_import.map_open_library(OPEN_LIBRARY_DUNE_DOC)]


@pytest.fixture()
def fake_gb_result() -> list[BookImportCandidate]:
    return [book_import.map_google_books(GOOGLE_BOOKS_FOUNDATION_ITEM)]


@pytest.mark.anyio
async def test_search_returns_open_library_results(monkeypatch, fake_ol_result):
    async def fake_ol(query, search_type, client):
        return fake_ol_result

    async def fake_gb(query, search_type, api_key, client):
        return []

    monkeypatch.setattr(book_import, "_search_open_library", fake_ol)
    monkeypatch.setattr(book_import, "_search_google_books", fake_gb)

    results = await book_import.search("dune", "title")
    assert len(results) == 1
    assert results[0].title == "Dune"
    assert results[0].source == "open_library"


@pytest.mark.anyio
async def test_search_falls_back_to_google_books_when_ol_empty(monkeypatch, fake_gb_result):
    async def fake_ol(query, search_type, client):
        return []

    async def fake_gb(query, search_type, api_key, client):
        return fake_gb_result

    monkeypatch.setattr(book_import, "_search_open_library", fake_ol)
    monkeypatch.setattr(book_import, "_search_google_books", fake_gb)

    # api_key must be non-empty — the real API requires a key and the guard
    # skips the fallback when none is configured.
    results = await book_import.search("foundation", "title", api_key="test-key")
    assert len(results) == 1
    assert results[0].source == "google_books"


@pytest.mark.anyio
async def test_search_returns_empty_when_both_fail(monkeypatch):
    async def fake_ol(query, search_type, client):
        return []

    async def fake_gb(query, search_type, api_key, client):
        return []

    monkeypatch.setattr(book_import, "_search_open_library", fake_ol)
    monkeypatch.setattr(book_import, "_search_google_books", fake_gb)

    results = await book_import.search("unknownxyz", "title")
    assert results == []


# ── Import API endpoint tests ─────────────────────────────────────────────────

def test_import_search_endpoint(client: TestClient, monkeypatch):
    async def fake_search(query, search_type, *, api_key, http_client):
        return [book_import.map_open_library(OPEN_LIBRARY_DUNE_DOC)]

    monkeypatch.setattr(book_import, "search", fake_search)

    resp = client.get("/api/import/search?q=dune&type=title")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Dune"
    assert data[0]["source"] == "open_library"


def test_import_search_requires_query(client: TestClient):
    resp = client.get("/api/import/search")
    assert resp.status_code == 422


def test_import_book_creates_entry(client: TestClient):
    payload = {
        "candidate": {
            "title": "Dune",
            "author": "Frank Herbert",
            "isbn": "9780441013593",
            "cover_url": "https://covers.openlibrary.org/b/id/11481354-M.jpg",
            "publisher": "Ace Books",
            "published_year": 1965,
            "page_count": 412,
            "genre": "Science Fiction",
            "source": "open_library",
        },
        "reading_status": "want_to_read",
    }
    resp = client.post("/api/import", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Dune"
    assert data["isbn"] == "9780441013593"
    assert data["reading_status"] == "want_to_read"
    assert data["id"] is not None


def test_import_book_duplicate_isbn_returns_409(client: TestClient):
    payload = {
        "candidate": {
            "title": "Dune",
            "isbn": "9780441013593",
            "source": "open_library",
        },
        "reading_status": "want_to_read",
    }
    client.post("/api/import", json=payload)
    resp = client.post("/api/import", json=payload)
    assert resp.status_code == 409


def test_import_book_without_isbn_allows_duplicates(client: TestClient):
    """Books without ISBN can be added multiple times (no unique constraint)."""
    payload = {
        "candidate": {
            "title": "Unknown Book",
            "source": "open_library",
        },
        "reading_status": "want_to_read",
    }
    r1 = client.post("/api/import", json=payload)
    r2 = client.post("/api/import", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201


def test_import_book_with_reading_status(client: TestClient):
    payload = {
        "candidate": {
            "title": "Foundation",
            "isbn": "9780553293357",
            "source": "google_books",
        },
        "reading_status": "read",
    }
    resp = client.post("/api/import", json=payload)
    assert resp.status_code == 201
    assert resp.json()["reading_status"] == "read"
