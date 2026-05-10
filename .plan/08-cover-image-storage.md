# LibrisLog — Local Cover Image Storage

## Goal

At import time, download the cover image from the external URL and persist it on
disk.  Store the local path in the database instead of the original URL.

**Benefits:**
- No external requests when the UI loads a book list — images are served by the
  backend directly, dramatically reducing load time.
- Works offline after the initial import.
- Eliminates broken-image risk from third-party URLs expiring or changing.

---

## Storage Location

All persistent backend data lives under `/app/data/` in the container, which is
bind-mounted from `./data/` on the host.  Covers follow the same
convention:

| Context | Path |
|---------|------|
| Container | `/app/data/covers/` |
| Host (bind-mount) | `./data/covers/` |
| Development (uvicorn from `backend/`) | `./data/covers/` |

The path is configurable via `COVERS_DIR` env var so it can be overridden in
tests without touching the filesystem.

---

## Serving

Traefik already routes `PathPrefix('/api')` → backend with priority 10.  Mount
FastAPI `StaticFiles` at `/api/covers` so no Traefik changes are needed:

```
GET /api/covers/{filename}  →  Traefik  →  backend StaticFiles  →  file on disk
```

The `cover_url` stored in the database becomes `/api/covers/{filename}`.  The
frontend and SvelteKit dev proxy (`/api → localhost:8000`) both handle this path
without any changes.

---

## Filename Strategy

Use the **SHA-256 hash of the external URL** (first 32 hex characters) as the
filename stem, plus the extension inferred from the HTTP `Content-Type` response
header (`.jpg` for `image/jpeg`, `.png` for `image/png`, etc.; default `.jpg`).

Example: `a3f8c1d2e9b04567.jpg`

Rationale:
- **Natural deduplication** — two books with the same cover URL map to the same
  file; the download is skipped if the file already exists.
- **Deterministic** — easy to reason about and test.
- **No coupling to ISBN** — works for books without an ISBN.

---

## New File: `app/services/cover_storage.py`

```python
async def download_cover(
    url: str,
    covers_dir: Path,
    client: httpx.AsyncClient,
) -> str | None:
    """
    Download the image at `url` into `covers_dir`.

    Returns the local serving path  ("/api/covers/{filename}")  on success,
    or None if the download fails (caller should keep the original URL).

    Skips the download if the file already exists on disk (deduplication).
    """
```

Internal steps:
1. Compute `filename = sha256(url)[:32] + ext_from_content_type()`
2. If `covers_dir / filename` already exists → return local path immediately
3. `GET url` with a 15 s timeout
4. Verify `Content-Type` starts with `image/` and `Content-Length` (if present)
   is > `_MIN_COVER_BYTES` (5 000 bytes); otherwise return None
5. Write the response body to a temp file in `covers_dir` then `os.replace()`
   into the final path (atomic write — no half-written files on crash)
6. Return `"/api/covers/{filename}"`

Error handling: any `httpx.HTTPError`, non-image content-type, or OS error logs
a warning and returns None. The caller stores the original external URL as
fallback so the book is still importable.

---

## Changes to Existing Files

### `app/config.py`

Add one field:

```python
covers_dir: str = "./data/covers"
```

### `app/main.py`

1. Create `covers_dir` at startup using a FastAPI **lifespan** context manager
   (replaces the current bare `app = FastAPI(...)` instantiation):

```python
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.covers_dir).mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title="LibrisLog API", lifespan=lifespan)
app.mount("/api/covers", StaticFiles(directory=settings.covers_dir), name="covers")
```

Note: `StaticFiles` must be mounted **after** `app` is created but **before**
`include_router` calls (or after — order doesn't affect routing, but consistency
is good).

### `app/routers/import_.py`

Convert `import_book` from `def` to `async def`; add cover download step between
building the `Book` object and the DB commit:

```python
@router.post("", response_model=BookRead, status_code=201)
async def import_book(body: BookImportRequest, session: Session = Depends(get_session)):
    ...
    cover_url = c.cover_url
    if cover_url:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            local_path = await cover_storage.download_cover(
                cover_url,
                Path(settings.covers_dir),
                http_client,
            )
            if local_path:
                cover_url = local_path  # replace external URL with local path

    book = Book(..., cover_url=cover_url, ...)
    ...
```

Import `cover_storage` from `app.services`.

### `docker-compose.yml`

No changes needed.  The covers directory (`/app/data/covers/`) falls inside the
existing bind-mount (`./data:/app/data`).

### `.env.example`

Add documentation line:

```
# COVERS_DIR=/app/data/covers   # default; override for custom storage paths
```

### `.gitignore` (backend)

Add `data/covers/` so downloaded images are not committed during development.

---

## What Changes in the Database

No schema or migration needed.  `Book.cover_url` is already a nullable `VARCHAR`
column.  The value simply changes from an external URL like
`https://covers.openlibrary.org/b/id/11481354-L.jpg` to a local path like
`/api/covers/a3f8c1d2e9b04567.jpg`.

Existing books in the database (imported before this feature) keep their external
URLs and continue to display normally — they just don't benefit from local
caching until re-imported.

---

## Test Strategy

All tests use monkeypatching / fake HTTP clients — no real network calls or
filesystem writes (except tests that explicitly use `tmp_path`).

### Unit tests for `cover_storage.py`  (`tests/test_cover_storage.py`)

| Test | What it checks |
|------|---------------|
| `test_download_cover_success_jpeg` | Happy path: 200 + `image/jpeg` → file written, returns `/api/covers/{hash}.jpg` |
| `test_download_cover_success_png` | Content-Type `image/png` → extension `.png` used |
| `test_download_cover_skips_if_file_exists` | File already on disk → no HTTP request made, path returned immediately |
| `test_download_cover_returns_none_on_404` | 404 response → returns None, no file written |
| `test_download_cover_returns_none_on_non_image_content_type` | `text/html` response → returns None |
| `test_download_cover_returns_none_on_too_small_body` | Response body < 5 000 bytes → returns None |
| `test_download_cover_returns_none_on_http_error` | `httpx.ConnectError` → returns None |
| `test_download_cover_atomic_write` | Verifies the final file exists and temp file does not remain on disk |
| `test_download_cover_deduplication` | Same URL called twice → HTTP GET called only once |

All tests that write files use pytest's `tmp_path` fixture for an isolated
temporary directory.

### Integration tests for `POST /api/import`  (`tests/test_import.py`)

| Test | What it checks |
|------|---------------|
| `test_import_book_cover_downloaded` | `download_cover` monkeypatched to return a local path → saved `cover_url` is the local path |
| `test_import_book_cover_fallback_on_download_failure` | `download_cover` monkeypatched to return None → saved `cover_url` is the original external URL |
| `test_import_book_no_cover_url` | Candidate with `cover_url=None` → `download_cover` never called, `cover_url` remains None |

These extend the existing `test_import.py` test functions (no classes).

### Static file serving test

| Test | What it checks |
|------|---------------|
| `test_covers_static_endpoint_serves_file` | Write a dummy `.jpg` to `covers_dir`, `GET /api/covers/{filename}` → 200 with `image/jpeg` |
| `test_covers_static_endpoint_404_for_missing_file` | `GET /api/covers/nonexistent.jpg` → 404 |

These go in a new `tests/test_covers.py` file and use `tmp_path` + a custom
`TestClient` that points `covers_dir` to the temp directory.

---

## Files Touched

| File | Change |
|------|--------|
| `backend/app/config.py` | Add `covers_dir` setting |
| `backend/app/main.py` | Add lifespan (creates covers dir), mount StaticFiles at `/api/covers` |
| `backend/app/services/cover_storage.py` | **New** — `download_cover()` |
| `backend/app/routers/import_.py` | Make `import_book` async; call `download_cover` |
| `backend/tests/test_cover_storage.py` | **New** — unit tests for `cover_storage.py` |
| `backend/tests/test_covers.py` | **New** — static file serving tests |
| `backend/tests/test_import.py` | Add 3 integration tests for cover download in import flow |
| `.env.example` | Document `COVERS_DIR` |
| `.gitignore` (or `backend/.gitignore`) | Ignore `data/covers/` |

---

## Out of Scope

- Migrating existing books to download their covers retroactively (can be a
  separate script or admin endpoint later).
- Deleting orphaned cover files when a book is deleted.
- Image resizing / format normalisation (store whatever the source returns).
- CDN or object-storage backends (S3, etc.).
