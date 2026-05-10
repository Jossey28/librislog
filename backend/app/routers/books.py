from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import Book, ReadingStatus
from app.schemas import BookCreate, BookRead, BookUpdate

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("", response_model=List[BookRead])
def list_books(
    status: Optional[ReadingStatus] = Query(default=None),
    q: Optional[str] = Query(default=None),
    sort: Literal["date_added", "rating"] = Query(default="date_added"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    session: Session = Depends(get_session),
) -> List[Book]:
    statement = select(Book)

    if status is not None:
        statement = statement.where(Book.reading_status == status)

    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            Book.title.ilike(pattern) | Book.author.ilike(pattern)  # type: ignore[union-attr]
        )

    sort_col = Book.date_added if sort == "date_added" else Book.rating
    if order == "desc":
        statement = statement.order_by(sort_col.desc())  # type: ignore[union-attr]
    else:
        statement = statement.order_by(sort_col.asc())  # type: ignore[union-attr]

    return list(session.exec(statement).all())


@router.post("", response_model=BookRead, status_code=201)
def create_book(book_in: BookCreate, session: Session = Depends(get_session)) -> Book:
    book = Book.model_validate(book_in)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, session: Session = Depends(get_session)) -> Book:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.patch("/{book_id}", response_model=BookRead)
def update_book(
    book_id: int, book_in: BookUpdate, session: Session = Depends(get_session)
) -> Book:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    update_data = book_in.model_dump(exclude_unset=True)
    book.sqlmodel_update(update_data)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, session: Session = Depends(get_session)) -> None:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    session.delete(book)
    session.commit()
