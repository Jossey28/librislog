# LibrisLog — Backend Implementation Plan

## Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12 | Runtime |
| uv | latest | Package manager, venv, script runner |
| FastAPI | latest | Web framework |
| SQLModel | latest | ORM (SQLAlchemy + Pydantic) |
| Pydantic v2 | (via SQLModel) | Data validation |
| Alembic | latest | DB migrations |
| httpx | latest | Async HTTP client for book API calls |
| uvicorn | latest | ASGI server |
| pytest | latest | Test runner |
| pytest-anyio | latest | Async test support |

---

## Project Setup

```
backend/
├── pyproject.toml
├── uv.lock
├── .python-version       # e.g. 3.12
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py         # Settings via pydantic-settings / env vars
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── books.py
│   │   └── import_.py
│   └── services/
│       ├── __init__.py
│       └── book_import.py
└── tests/
    ├── conftest.py
    ├── test_books.py
    └── test_import.py
```

### pyproject.toml (key sections)

```toml
[project]
name = "librislog-backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "sqlmodel",
    "alembic",
    "httpx",
    "uvicorn[standard]",
    "pydantic-settings",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-anyio", "httpx"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## app/config.py

Use `pydantic-settings` to read environment variables:

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/librislog.db"
    google_books_api_key: Optional[str] = None
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:80"]

settings = Settings()
```

---

## app/database.py

- Create SQLModel engine from `settings.database_url`
- `get_session()` dependency using `yield` for use in route handlers
- Separate `get_test_session()` fixture provided in `tests/conftest.py`

---

## app/main.py

- Instantiate `FastAPI` app with title, version
- Register CORS middleware using `settings.cors_origins`
- Include routers: `books.router`, `import_.router`
- `GET /api/health` — returns `{"status": "ok"}`
- Startup event: (optional) run `alembic upgrade head` or rely on entrypoint script

---

## app/routers/books.py

### Endpoints

#### `GET /api/books`
Query params:
- `status: Optional[ReadingStatus]` — filter by reading list
- `q: Optional[str]` — search title or author (case-insensitive LIKE)
- `sort: Literal["date_added", "rating"] = "date_added"`
- `order: Literal["asc", "desc"] = "desc"`

Returns: `list[BookRead]`

#### `POST /api/books`
Body: `BookCreate`
Returns: `BookRead` (201)

#### `GET /api/books/{id}`
Returns: `BookRead` or 404

#### `PATCH /api/books/{id}`
Body: `BookUpdate` (all fields optional)
Returns: `BookRead` or 404

#### `DELETE /api/books/{id}`
Returns: 204 or 404

---

## app/routers/import_.py

#### `GET /api/import/search`
Query params:
- `q: str` — title string or ISBN
- `type: Literal["title", "isbn"] = "title"`

Calls `book_import.search(q, type)`, returns `list[BookImportCandidate]` (max 10 results).

#### `POST /api/import`
Body: `BookImportRequest` (`BookImportCandidate` + optional `reading_status`)
Persists as a new `Book` row. Returns `BookRead` (201).
If `isbn` already exists in DB, returns 409 Conflict.

---

## app/services/book_import.py

### `async def search(query: str, search_type: str, *, http_client: httpx.AsyncClient) -> list[BookImportCandidate]`

1. Try Open Library:
   - ISBN: `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=data&format=json`
   - Title: `https://openlibrary.org/search.json?q={query}&limit=10`
   - Map response fields to `BookImportCandidate`
2. If results empty, try Google Books:
   - `https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}`
   - Map `volumeInfo` fields to `BookImportCandidate`
3. Return combined/deduped list (dedupe by ISBN where available)

### `def map_open_library(data: dict) -> BookImportCandidate`
### `def map_google_books(item: dict) -> BookImportCandidate`

Pure mapping functions — easy to unit test without HTTP.

---

## Tests

### tests/conftest.py

Shared fixtures (no test classes anywhere):

```python
@pytest.fixture(name="session")
def session_fixture():
    # Create in-memory SQLite engine
    # Create all tables via SQLModel.metadata.create_all
    # Yield session
    # Drop all after test

@pytest.fixture(name="client")
def client_fixture(session):
    # Override get_session dependency with test session
    # Yield TestClient(app)
```

### tests/test_books.py

Modular test functions covering:
- `test_create_book_returns_201`
- `test_create_book_missing_title_returns_422`
- `test_list_books_empty`
- `test_list_books_filter_by_status`
- `test_list_books_search_by_title`
- `test_list_books_sort_by_date_added`
- `test_list_books_sort_by_rating`
- `test_get_book_returns_book`
- `test_get_book_not_found_returns_404`
- `test_update_book_status`
- `test_update_book_rating`
- `test_update_book_partial`
- `test_delete_book`
- `test_delete_book_not_found_returns_404`

### tests/test_import.py

Test the import service with `monkeypatch` (no `unittest.mock`):

```python
def test_search_open_library_success(monkeypatch):
    # monkeypatch the httpx.AsyncClient.get to return fake Open Library response
    ...

def test_search_falls_back_to_google_books(monkeypatch):
    # monkeypatch Open Library to return empty, Google Books to return results
    ...

def test_import_creates_book(client, monkeypatch):
    # POST /api/import with a BookImportCandidate payload
    ...

def test_import_duplicate_isbn_returns_409(client, monkeypatch):
    ...

def test_map_open_library_fields():
    # Pure unit test, no HTTP, no monkeypatch needed
    ...

def test_map_google_books_fields():
    ...
```

---

## Running Locally

```bash
# Install deps
uv sync --all-extras

# Run migrations
uv run alembic upgrade head

# Start dev server
uv run uvicorn app.main:app --reload --port 8000

# Run tests
uv run pytest
```
