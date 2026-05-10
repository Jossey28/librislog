from typing import List, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import Book
from app.schemas import BookImportCandidate, BookImportRequest, BookRead
from app.services import book_import

router = APIRouter(prefix="/api/import", tags=["import"])


@router.get("/search", response_model=List[BookImportCandidate])
async def search_books(
    q: str = Query(min_length=1, description="Title string or ISBN"),
    type: Literal["title", "isbn"] = Query(default="title"),
) -> List[BookImportCandidate]:
    """Search external APIs for books by title or ISBN."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await book_import.search(
            q,
            type,
            api_key=settings.google_books_api_key,
            http_client=client,
        )
    return results


@router.post("", response_model=BookRead, status_code=201)
def import_book(
    body: BookImportRequest,
    session: Session = Depends(get_session),
) -> Book:
    """Persist an import candidate into the local database."""
    c = body.candidate

    # Reject duplicates by ISBN when an ISBN is present
    if c.isbn:
        existing = session.exec(select(Book).where(Book.isbn == c.isbn)).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"A book with ISBN {c.isbn} already exists (id={existing.id}).",
            )

    book = Book(
        title=c.title,
        author=c.author,
        isbn=c.isbn,
        cover_url=c.cover_url,
        publisher=c.publisher,
        published_year=c.published_year,
        page_count=c.page_count,
        genre=c.genre,
        reading_status=body.reading_status,
    )
    session.add(book)
    session.commit()
    session.refresh(book)
    return book
