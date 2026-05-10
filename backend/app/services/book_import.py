"""
Book import service.

Search priority:
  1. Open Library  (no API key required)
  2. Google Books  (optional API key, used as fallback)

Both return a list of BookImportCandidate objects normalised to the same schema.
"""

from typing import Optional

import httpx

from app.schemas import BookImportCandidate

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

GOOGLE_BOOKS_SEARCH_URL = "https://www.googleapis.com/books/v1/volumes"


# ── Public API ────────────────────────────────────────────────────────────────

async def search(
    query: str,
    search_type: str,
    *,
    api_key: str = "",
    http_client: Optional[httpx.AsyncClient] = None,
) -> list[BookImportCandidate]:
    """Search Open Library first; fall back to Google Books if no results."""
    own_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10.0)

    try:
        results = await _search_open_library(query, search_type, client)
        if not results:
            results = await _search_google_books(query, search_type, api_key, client)
        return results
    finally:
        if own_client:
            await client.aclose()


# ── Open Library ──────────────────────────────────────────────────────────────

async def _search_open_library(
    query: str,
    search_type: str,
    client: httpx.AsyncClient,
) -> list[BookImportCandidate]:
    if search_type == "isbn":
        params = {
            "q": f"isbn:{query}",
            "fields": "title,author_name,isbn,publisher,first_publish_year,number_of_pages_median,subject,cover_i",
            "limit": 5,
        }
    else:
        params = {
            "q": query,
            "fields": "title,author_name,isbn,publisher,first_publish_year,number_of_pages_median,subject,cover_i",
            "limit": 10,
        }

    try:
        resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    docs = resp.json().get("docs", [])
    return [map_open_library(doc) for doc in docs if doc.get("title")]


def map_open_library(doc: dict) -> BookImportCandidate:
    """Map a single Open Library search doc to BookImportCandidate."""
    # Authors: list of strings
    authors = doc.get("author_name") or []
    author = ", ".join(authors) if authors else None

    # ISBN: first entry of the list, prefer ISBN-13 (length 13)
    isbns: list[str] = doc.get("isbn") or []
    isbn = _pick_isbn(isbns)

    # Cover image
    cover_id = doc.get("cover_i")
    cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id=cover_id) if cover_id else None

    # Publisher: first entry
    publishers: list[str] = doc.get("publisher") or []
    publisher = publishers[0] if publishers else None

    # Genres: first 3 subjects joined
    subjects: list[str] = doc.get("subject") or []
    genre = ", ".join(subjects[:3]) if subjects else None

    return BookImportCandidate(
        title=doc["title"],
        author=author,
        isbn=isbn,
        cover_url=cover_url,
        publisher=publisher,
        published_year=doc.get("first_publish_year"),
        page_count=doc.get("number_of_pages_median"),
        genre=genre,
        source="open_library",
    )


# ── Google Books ──────────────────────────────────────────────────────────────

async def _search_google_books(
    query: str,
    search_type: str,
    api_key: str,
    client: httpx.AsyncClient,
) -> list[BookImportCandidate]:
    if search_type == "isbn":
        q = f"isbn:{query}"
    else:
        q = query

    params: dict = {"q": q, "maxResults": 10}
    if api_key:
        params["key"] = api_key

    try:
        resp = await client.get(GOOGLE_BOOKS_SEARCH_URL, params=params)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    items = resp.json().get("items") or []
    return [map_google_books(item) for item in items if item.get("volumeInfo", {}).get("title")]


def map_google_books(item: dict) -> BookImportCandidate:
    """Map a single Google Books volume item to BookImportCandidate."""
    vi = item.get("volumeInfo", {})

    # Authors
    authors: list[str] = vi.get("authors") or []
    author = ", ".join(authors) if authors else None

    # ISBN: prefer ISBN_13
    identifiers: list[dict] = vi.get("industryIdentifiers") or []
    isbns_13 = [i["identifier"] for i in identifiers if i.get("type") == "ISBN_13"]
    isbns_10 = [i["identifier"] for i in identifiers if i.get("type") == "ISBN_10"]
    isbn = (isbns_13 or isbns_10 or [None])[0]

    # Cover image: use thumbnail, upgrade to https
    image_links: dict = vi.get("imageLinks") or {}
    cover_url = image_links.get("thumbnail")
    if cover_url:
        cover_url = cover_url.replace("http://", "https://")

    # Published year: publishedDate can be "YYYY", "YYYY-MM", or "YYYY-MM-DD"
    published_date: Optional[str] = vi.get("publishedDate")
    published_year: Optional[int] = None
    if published_date:
        try:
            published_year = int(published_date[:4])
        except (ValueError, IndexError):
            pass

    # Genres
    categories: list[str] = vi.get("categories") or []
    genre = ", ".join(categories[:3]) if categories else None

    return BookImportCandidate(
        title=vi["title"],
        author=author,
        isbn=isbn,
        cover_url=cover_url,
        publisher=vi.get("publisher"),
        published_year=published_year,
        page_count=vi.get("pageCount"),
        genre=genre,
        source="google_books",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pick_isbn(isbns: list[str]) -> Optional[str]:
    """Return the first ISBN-13 found, or the first ISBN-10, or None."""
    for isbn in isbns:
        clean = isbn.replace("-", "").replace(" ", "")
        if len(clean) == 13 and clean.isdigit():
            return clean
    for isbn in isbns:
        clean = isbn.replace("-", "").replace(" ", "")
        if len(clean) == 10 and clean[:9].isdigit():
            return clean
    return isbns[0] if isbns else None
