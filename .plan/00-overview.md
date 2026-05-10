# LibrisLog — Project Overview

## Goal

A single-user book tracking webapp. Users can manage books across three reading-state lists,
add books manually or by importing from a title/ISBN lookup, and view rich metadata per book.
No authentication is required.

---

## Architecture

```
┌─────────────────────────┐        HTTP/JSON (REST)       ┌──────────────────────────┐
│   Frontend              │ ◄───────────────────────────► │   Backend                │
│   SvelteKit (SPA)       │                               │   FastAPI                │
│   Tailwind + DaisyUI    │                               │   SQLModel + SQLite      │
│   served by nginx       │                               │   Alembic migrations     │
└─────────────────────────┘                               └──────────────┬───────────┘
                                                                         │
                                                          ┌──────────────▼───────────┐
                                                          │   External Book APIs     │
                                                          │   1. Open Library        │
                                                          │   2. Google Books (fall) │
                                                          └──────────────────────────┘
```

The frontend and backend are fully decoupled. The backend exposes a pure JSON REST API.
The frontend is a static SPA that consumes it. Both run as separate Docker containers.

---

## Directory Structure

```
librislog/
├── backend/
│   ├── pyproject.toml          # uv-managed project + dependencies
│   ├── uv.lock
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, router registration
│   │   ├── database.py         # SQLModel engine + session dependency
│   │   ├── models.py           # SQLModel table models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── books.py        # CRUD + list/search/filter endpoints
│   │   │   └── import_.py      # Book lookup + import endpoint
│   │   └── services/
│   │       └── book_import.py  # Open Library → Google Books fallback logic
│   └── tests/
│       ├── conftest.py         # Shared fixtures (test DB, client, monkeypatch helpers)
│       ├── test_books.py       # Book CRUD endpoint tests
│       └── test_import.py      # Import service tests
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── svelte.config.js        # adapter-static (SPA mode)
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── app.html
│   │   ├── lib/
│   │   │   ├── api.ts          # Typed API client (fetch wrapper)
│   │   │   ├── types.ts        # TypeScript types mirroring backend schemas
│   │   │   └── components/
│   │   │       ├── BookCard.svelte
│   │   │       ├── BookDrawer.svelte
│   │   │       ├── AddBookModal.svelte
│   │   │       ├── ImportSearch.svelte
│   │   │       ├── SearchBar.svelte
│   │   │       └── StarRating.svelte
│   │   └── routes/
│   │       ├── +layout.svelte  # Nav shell (sidebar desktop / bottom-nav mobile)
│   │       └── +page.svelte    # Main page with 3-tab list view
│
├── docker-compose.yml
├── .env.example
└── .plan/
```

---

## Architectural Decision Records (ADRs)

### ADR-001: Separate frontend and backend containers
The frontend (SvelteKit, built to static files, served by nginx) and the backend (FastAPI via
uvicorn) run as independent Docker services. Communication is purely via REST JSON. This allows
swapping out the frontend without touching the backend, and vice versa.

### ADR-002: SvelteKit in SPA mode
`@sveltejs/adapter-static` with `fallback: '200.html'` is used so all routing happens
client-side. nginx serves the built static files and redirects unknown paths to `200.html`.

### ADR-003: SQLite as database
Sufficient for a single-user app. The DB file is stored in a named Docker volume so it
persists across container restarts. Alembic manages schema migrations.

### ADR-004: uv as Python package manager
`uv` is used for dependency management and virtual environment creation. The project is
defined in `pyproject.toml`. `uv run pytest` is the canonical test invocation.

### ADR-005: Book import fallback chain
Open Library API is tried first (no API key needed). If no match is found, Google Books API
is used as fallback. Both return a unified `BookImportResult` schema.

### ADR-006: No authentication
The app is designed for single-user, local/self-hosted use. Authentication can be added later
as a separate concern without changing the core API structure.

---

## REST API Contract (high level)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/books` | List all books; supports `?status=`, `?q=`, `?sort=` |
| `POST` | `/api/books` | Create a book manually |
| `GET` | `/api/books/{id}` | Get a single book |
| `PATCH` | `/api/books/{id}` | Update book fields (incl. status change) |
| `DELETE` | `/api/books/{id}` | Delete a book |
| `GET` | `/api/import/search?q={query}&type=title\|isbn` | Search external APIs, return candidates |
| `POST` | `/api/import` | Import a found candidate into the local DB |
| `GET` | `/api/health` | Health check |

All endpoints return JSON. Errors follow the RFC 7807 Problem Details format via FastAPI's
default `HTTPException` handler.
