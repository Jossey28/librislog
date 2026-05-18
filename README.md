# LibrisLog

A single-user book tracking webapp. Keep three reading lists (Want to Read, Currently Reading, Read), import books from Open Library or Google Books, and manage your collection.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLModel, SQLite, Alembic, Pydantic v2 |
| Frontend | SvelteKit (SPA), Tailwind CSS v4, DaisyUI v5 |
| Router | Traefik v3 |
| Package manager | `uv` (Python), `npm` (Node) |

---

## Quick Start (Docker)

```bash
cp .env.example .env          # adjust values if needed
docker compose up --build -d
```

Optional: inject the app version from git (shown in the sidebar and health endpoint):

```bash
export APP_VERSION=$(git describe --tags --always)
export GIT_SHA=$(git rev-parse HEAD)
docker compose up --build -d
```

Omitting the vars leaves the fallback `v0.0.0-dev` / `unknown`.

The app is available at **http://localhost:8080**.

---

## Development

### Prerequisites

- Python 3.14+
- Node.js 26+ (use [nvm](https://github.com/nvm-sh/nvm): `nvm use` inside `frontend/`)
- [uv](https://github.com/astral-sh/uv)

### Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API available at **http://localhost:8000**. Health check: `GET /api/health`.

### Frontend

```bash
cd frontend
nvm use          # pins to Node 26 via .nvmrc
npm install
npm run dev
```

Dev server at **http://localhost:5173** — proxies `/api` to `localhost:8000`.

---

## Testing

```bash
cd backend
uv run pytest
```

All 36 tests cover CRUD endpoints and the book import service.

---

## Book Import

Search is backed by **Open Library** (no API key required) with **Google Books** as a fallback. An optional `GOOGLE_BOOKS_API_KEY` in `.env` raises the Google Books quota.

---

## Environment Variables

See `.env.example` for all available variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/librislog.db` | SQLite database path |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `GOOGLE_BOOKS_API_KEY` | _(empty)_ | Optional Google Books API key |

---

## Project Structure

```
librislog/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── config.py        # pydantic-settings config
│   │   ├── models.py        # SQLModel Book model
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── database.py      # DB engine + session dependency
│   │   ├── routers/
│   │   │   ├── books.py     # CRUD endpoints
│   │   │   └── import_.py   # Import search + import endpoints
│   │   └── services/
│   │       └── book_import.py  # Open Library + Google Books
│   ├── alembic/             # DB migrations
│   ├── tests/               # pytest test suite
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts       # Typed fetch wrappers
│   │   │   ├── types.ts     # TypeScript interfaces
│   │   │   ├── toasts.ts    # Toast notification store
│   │   │   └── components/  # Svelte components
│   │   └── routes/          # SvelteKit pages
│   └── package.json
├── docker-compose.yml
└── .env.example
```
