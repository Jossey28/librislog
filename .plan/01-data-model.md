# LibrisLog — Data Model

## Reading Status Enum

```python
class ReadingStatus(str, Enum):
    want_to_read     = "want_to_read"
    currently_reading = "currently_reading"
    read             = "read"
```

---

## SQLModel Table: `Book`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `int` | PK, auto-increment | Internal ID |
| `title` | `str` | NOT NULL | Book title |
| `author` | `str` | nullable | Author name(s) |
| `isbn` | `str` | nullable, unique | ISBN-10 or ISBN-13 |
| `cover_url` | `str` | nullable | URL to cover image |
| `publisher` | `str` | nullable | Publisher name |
| `published_year` | `int` | nullable | Year of publication |
| `page_count` | `int` | nullable | Number of pages |
| `genre` | `str` | nullable | Comma-separated genre tags |
| `notes` | `str` | nullable | User's personal notes |
| `rating` | `int` | nullable, 1–5 | User's personal rating |
| `reading_status` | `ReadingStatus` | NOT NULL, default `want_to_read` | Current list |
| `date_added` | `datetime` | NOT NULL, default `utcnow` | When the book was added |
| `date_started` | `date` | nullable | When reading started |
| `date_finished` | `date` | nullable | When reading finished |

```python
# app/models.py (sketch)
class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = Field(default=None, unique=True)
    cover_url: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    page_count: Optional[int] = None
    genre: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    reading_status: ReadingStatus = ReadingStatus.want_to_read
    date_added: datetime = Field(default_factory=datetime.utcnow)
    date_started: Optional[date] = None
    date_finished: Optional[date] = None
```

---

## Pydantic Schemas (API layer)

### `BookCreate` — POST /api/books
All fields except `title` are optional. `reading_status` defaults to `want_to_read`.

### `BookUpdate` — PATCH /api/books/{id}
All fields optional. Only provided fields are updated.

### `BookRead` — response schema
All fields including `id` and `date_added`. Used in list and detail responses.

### `BookImportCandidate` — response of GET /api/import/search
Represents a result from the external book API, not yet saved locally.

```python
class BookImportCandidate(BaseModel):
    title: str
    author: Optional[str]
    isbn: Optional[str]
    cover_url: Optional[str]
    publisher: Optional[str]
    published_year: Optional[int]
    page_count: Optional[int]
    genre: Optional[str]
    source: str  # "open_library" | "google_books"
```

### `BookImportRequest` — POST /api/import
Accepts a `BookImportCandidate` and an optional initial `reading_status`, then persists it.

---

## Database Migrations (Alembic)

- `alembic init alembic` sets up the migrations folder.
- `alembic/env.py` imports `SQLModel.metadata` from `app.models` so Alembic can autogenerate.
- Each schema change produces a versioned script in `alembic/versions/`.
- `alembic upgrade head` is run at container startup (entrypoint script).

### Initial migration
Creates the `book` table with all columns listed above.

---

## Indexes

| Index | Column(s) | Reason |
|-------|-----------|--------|
| (implicit) | `id` | Primary key |
| unique | `isbn` | Prevent duplicate imports |
| recommended | `reading_status` | Fast list-by-status queries |
| recommended | `date_added` | Sort by date added |
