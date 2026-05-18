from collections import Counter
from datetime import datetime
from statistics import mean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.auth import require_user
from app.database import get_session
from app.models import Book, ReadingProgress, ReadingStatus, User, UserSettings
from app.schemas import (
    FavoriteAuthor,
    LanguageDistribution,
    MonthlyBooks,
    MonthlyPages,
    PageBuckets,
    StatisticsResponse,
    StatusDistribution,
    YearlyBooks,
)

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


def _user_timezone(session: Session, user_id: int) -> ZoneInfo:
    settings = session.exec(select(UserSettings).where(UserSettings.user_id == user_id)).first()
    timezone_name = settings.timezone if settings and settings.timezone else "UTC"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _month_key(dt: datetime, tz: ZoneInfo) -> str:
    local = dt.astimezone(tz)
    return f"{local.year:04d}-{local.month:02d}"


def _month_range(start_key: str, end_key: str) -> list[str]:
    start_year, start_month = map(int, start_key.split("-"))
    end_year, end_month = map(int, end_key.split("-"))
    keys: list[str] = []
    year, month = start_year, start_month
    while (year < end_year) or (year == end_year and month <= end_month):
        keys.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return keys


@router.get("", response_model=StatisticsResponse)
def get_statistics(
    current_user: User = Depends(require_user),
    session: Session = Depends(get_session),
) -> StatisticsResponse:
    tz = _user_timezone(session, current_user.id)
    books = list(session.exec(select(Book).where(Book.user_id == current_user.id)).all())

    status_counts = Counter(book.reading_status for book in books)
    status_distribution = StatusDistribution(
        want_to_read=status_counts.get(ReadingStatus.want_to_read, 0),
        currently_reading=status_counts.get(ReadingStatus.currently_reading, 0),
        read=status_counts.get(ReadingStatus.read, 0),
        did_not_finish=status_counts.get(ReadingStatus.did_not_finish, 0),
    )

    page_values = [book.page_count for book in books if book.page_count is not None]
    avg_page_count = round(mean(page_values), 2) if page_values else None

    language_counts: Counter[str | None] = Counter(book.language for book in books)
    language_distribution = [
        LanguageDistribution(language=language, count=count)
        for language, count in sorted(
            language_counts.items(),
            key=lambda item: (-item[1], item[0] is None, item[0] or ""),
        )
    ]
    known_language_counts = [(code, count) for code, count in language_counts.items() if code]
    known_language_counts.sort(key=lambda item: (-item[1], item[0]))
    most_popular_language = known_language_counts[0][0] if known_language_counts else None
    most_popular_language_count = known_language_counts[0][1] if known_language_counts else None

    pages_to_read = sum(
        book.page_count or 0
        for book in books
        if book.reading_status == ReadingStatus.want_to_read and book.page_count is not None
    )
    pages_read = sum(
        book.page_count or 0
        for book in books
        if book.reading_status == ReadingStatus.read and book.page_count is not None
    )

    dnf_book_ids = [book.id for book in books if book.reading_status == ReadingStatus.did_not_finish and book.id is not None]
    pages_wasted = 0
    if dnf_book_ids:
        wasted_rows = session.exec(
            select(ReadingProgress.book_id, func.max(ReadingProgress.page))
            .where(
                ReadingProgress.user_id == current_user.id,
                ReadingProgress.book_id.in_(dnf_book_ids),
            )
            .group_by(ReadingProgress.book_id)
        ).all()
        pages_wasted = int(sum((max_page or 0) for _, max_page in wasted_rows))

    page_buckets = PageBuckets(
        pages_to_read=int(pages_to_read),
        pages_read=int(pages_read),
        pages_wasted=pages_wasted,
    )

    finished_books = [
        book
        for book in books
        if book.reading_status == ReadingStatus.read and book.date_finished is not None
    ]

    finished_books_per_month: Counter[str] = Counter()
    pages_read_per_month_counter: Counter[str] = Counter()
    for book in finished_books:
        month = _month_key(book.date_finished, tz)
        finished_books_per_month[month] += 1
        if book.page_count is not None:
            pages_read_per_month_counter[month] += int(book.page_count)

    if finished_books_per_month:
        avg_books_per_month = round(
            sum(finished_books_per_month.values()) / len(finished_books_per_month),
            2,
        )
        busiest_month, busiest_month_count = min(
            (
                (month, count)
                for month, count in finished_books_per_month.items()
            ),
            key=lambda item: (-item[1], item[0]),
        )
        month_keys = _month_range(min(finished_books_per_month), max(finished_books_per_month))
        books_finished_per_month = [
            MonthlyBooks(month=month, count=finished_books_per_month.get(month, 0)) for month in month_keys
        ]
    else:
        avg_books_per_month = None
        busiest_month = None
        busiest_month_count = None
        books_finished_per_month = []

    if pages_read_per_month_counter:
        month_keys = _month_range(min(pages_read_per_month_counter), max(pages_read_per_month_counter))
        pages_read_per_month = [
            MonthlyPages(month=month, pages=pages_read_per_month_counter.get(month, 0)) for month in month_keys
        ]
    else:
        pages_read_per_month = []

    if finished_books_per_month:
        yearly_counts: Counter[int] = Counter()
        for month_key, count in finished_books_per_month.items():
            yearly_counts[int(month_key.split("-")[0])] += count
        year_start = min(yearly_counts)
        year_end = max(yearly_counts)
        books_finished_per_year = [
            YearlyBooks(year=year, count=yearly_counts.get(year, 0))
            for year in range(year_start, year_end + 1)
        ]
    else:
        books_finished_per_year = []

    author_counts: Counter[str] = Counter()
    for book in books:
        if book.author and book.author.strip():
            author_counts[book.author.strip()] += 1

    favorite_author = None
    if author_counts:
        author_name, author_count = min(
            author_counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )
        author_cover_rows = session.exec(
            select(Book.cover_url)
            .where(
                Book.user_id == current_user.id,
                Book.author == author_name,
                Book.cover_url.is_not(None),
            )
            .distinct()
            .limit(20)
        ).all()
        cover_urls = [cover_url for cover_url in author_cover_rows if cover_url]
        favorite_author = FavoriteAuthor(
            author=author_name,
            book_count=author_count,
            cover_urls=cover_urls,
        )

    return StatisticsResponse(
        avg_books_per_month=avg_books_per_month,
        busiest_month=busiest_month,
        busiest_month_count=busiest_month_count,
        avg_page_count=avg_page_count,
        most_popular_language=most_popular_language,
        most_popular_language_count=most_popular_language_count,
        language_distribution=language_distribution,
        status_distribution=status_distribution,
        page_buckets=page_buckets,
        pages_read_per_month=pages_read_per_month,
        books_finished_per_month=books_finished_per_month,
        books_finished_per_year=books_finished_per_year,
        favorite_author=favorite_author,
    )
