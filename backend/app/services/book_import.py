"""
Book import service.

Search priority:
  1. Open Library  (no API key required)
  2. Google Books  (optional API key, used as fallback)

Both return a list of BookImportCandidate objects normalised to the same schema.
"""

import logging
from typing import Optional

import httpx

from app.schemas import BookImportCandidate

logger = logging.getLogger(__name__)

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
    logger.debug("search() called — query=%r search_type=%r has_api_key=%s",
                 query, search_type, bool(api_key))

    own_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10.0)

    try:
        results = await _search_open_library(query, search_type, client)
        logger.info("Open Library returned %d result(s) for %r", len(results), query)

        if not results:
            logger.info("No Open Library results — falling back to Google Books")
            results = await _search_google_books(query, search_type, api_key, client)
            logger.info("Google Books returned %d result(s) for %r", len(results), query)

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

    logger.debug("Open Library request — url=%s params=%s", OPEN_LIBRARY_SEARCH_URL, params)

    try:
        resp = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        logger.debug("Open Library response — status=%d body_size=%d bytes",
                     resp.status_code, len(resp.content))
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("Open Library HTTP error: %s %s", exc.response.status_code, exc.response.text[:200])
        return []
    except httpx.HTTPError as exc:
        logger.warning("Open Library request failed: %s", exc)
        return []

    docs = resp.json().get("docs", [])
    logger.debug("Open Library docs in response: %d", len(docs))
    candidates = [map_open_library(doc) for doc in docs if doc.get("title")]
    for c in candidates:
        logger.debug("  OL candidate: title=%r isbn=%r", c.title, c.isbn)
    return candidates


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

    logger.debug("Google Books request — url=%s params=%s",
                 GOOGLE_BOOKS_SEARCH_URL,
                 {k: v for k, v in params.items() if k != "key"})

    try:
        resp = await client.get(GOOGLE_BOOKS_SEARCH_URL, params=params)
        logger.debug("Google Books response — status=%d body_size=%d bytes",
                     resp.status_code, len(resp.content))
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("Google Books HTTP error: %s — body: %s",
                       exc.response.status_code, exc.response.text[:500])
        return []
    except httpx.HTTPError as exc:
        logger.warning("Google Books request failed: %s", exc)
        return []

    body = resp.json()
    items = body.get("items") or []
    logger.debug("Google Books items in response: %d (totalItems=%s)",
                 len(items), body.get("totalItems", "n/a"))

    if not items and "error" in body:
        logger.warning("Google Books API error payload: %s", body["error"])

    candidates = [map_google_books(item) for item in items
                  if item.get("volumeInfo", {}).get("title")]
    for c in candidates:
        logger.debug("  GB candidate: title=%r isbn=%r", c.title, c.isbn)
    return candidates


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
