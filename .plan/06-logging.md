# LibrisLog — Backend Logging Plan

## Goal

Add structured, configurable debug logging to the FastAPI backend so that issues
like the Google Books fallback can be diagnosed at runtime without redeploying.

---

## Design Decisions

### Standard library `logging`, not a third-party package

Python's built-in `logging` module is the right choice:
- FastAPI and uvicorn already emit their own records through it, so a single
  configuration point controls everything.
- No new dependency; no extra Docker layer weight.
- `logger = logging.getLogger(__name__)` gives per-module namespacing for free
  (e.g. `app.services.book_import`, `app.routers.import_`).

### Single `LOG_LEVEL` env var

A new `log_level` field in `app/config.py` (pydantic-settings reads `LOG_LEVEL`
from `.env`).  Default: `"INFO"`.  Accepted values: `DEBUG`, `INFO`, `WARNING`,
`ERROR`, `CRITICAL`.

### Centralised setup in `app/logging_config.py`

A `configure_logging(level: str)` function called once from `app/main.py` on
module load.  It:
- Sets the root `app` logger to the requested level.
- Applies a consistent format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Leaves uvicorn's own loggers untouched (they configure themselves).

---

## Scope — What Gets Logged

### `app.services.book_import` (highest value — this is where Google Books lives)

| Level   | Event |
|---------|-------|
| DEBUG   | Outgoing request URL + params for every HTTP call |
| DEBUG   | Raw response status code and body size |
| DEBUG   | Number of results returned by each source |
| INFO    | "Open Library returned N results" |
| INFO    | "Falling back to Google Books" |
| WARNING | HTTP error from Open Library (currently silent `return []`) |
| WARNING | HTTP error from Google Books (currently silent `return []`) |
| DEBUG   | Each mapped candidate (title, isbn, source) |

### `app.routers.import_`

| Level | Event |
|-------|-------|
| DEBUG | Incoming search query + type |
| INFO  | "Imported book: {title} (isbn={isbn})" |
| WARNING | Duplicate ISBN rejected (409) |

### `app.routers.books`

| Level | Event |
|-------|-------|
| DEBUG | Each CRUD operation with its key parameters |

### `app.main`

| Level | Event |
|-------|-------|
| INFO  | "Logging configured at level {level}" emitted on startup |

---

## Files Changed

| File | Change |
|------|--------|
| `app/config.py` | Add `log_level: str = "INFO"` field |
| `app/logging_config.py` | **New** — `configure_logging()` |
| `app/main.py` | Call `configure_logging(settings.log_level)` at module load |
| `app/services/book_import.py` | Add `logger` + debug/info/warning calls |
| `app/routers/import_.py` | Add `logger` + debug/info/warning calls |
| `app/routers/books.py` | Add `logger` + debug calls |
| `.env.example` | Document `LOG_LEVEL=INFO` |
| `.env` | Add `LOG_LEVEL=DEBUG` (local dev default) |

---

## `.env` Usage

```dotenv
# Logging
LOG_LEVEL=DEBUG   # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

In Docker production (`docker-compose.yml`) the default remains `INFO` unless
overridden in `.env`.

---

## Out of Scope

- Structured JSON logging (would require `python-json-logger`; can be added later).
- Log rotation / file output (uvicorn handles that at the process level).
- Per-request trace IDs (overkill for a single-user app).
- Frontend logging (separate concern).
