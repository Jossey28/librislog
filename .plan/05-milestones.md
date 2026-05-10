# LibrisLog — Implementation Milestones

Each phase is a self-contained, shippable increment. Complete phases in order.
Mark tasks with `[x]` as they are done.

---

## Phase 1 — Backend Skeleton & CRUD

**Goal:** A working FastAPI app with SQLite, Alembic, full book CRUD, and a passing test suite.

### Tasks

- [x] Init `backend/` with `uv init`, add dependencies to `pyproject.toml`
- [x] Set up `app/config.py` (pydantic-settings, DATABASE_URL, CORS_ORIGINS)
- [x] Set up `app/database.py` (SQLModel engine, `get_session` dependency)
- [x] Define `ReadingStatus` enum and `Book` SQLModel in `app/models.py`
- [x] Define Pydantic schemas in `app/schemas.py` (`BookCreate`, `BookUpdate`, `BookRead`)
- [x] Configure Alembic (`alembic init`, update `env.py` to use SQLModel metadata)
- [x] Generate and apply initial migration (`alembic revision --autogenerate -m "create book table"`)
- [x] Implement `app/routers/books.py` (all 5 CRUD endpoints)
- [x] Wire up `app/main.py` (CORS, router, health endpoint)
- [x] Write `tests/conftest.py` (in-memory session fixture, TestClient fixture)
- [x] Write `tests/test_books.py` (all CRUD test functions, no classes)
- [x] Verify: `uv run pytest` passes

**Exit criteria:** All book CRUD endpoints work, all tests green. ✓

---

## Phase 2 — Book Import Service

**Goal:** Search Open Library and Google Books by title or ISBN; import results into DB.

### Tasks

- [x] Implement `app/services/book_import.py`:
  - [x] `search()` async function with Open Library primary call
  - [x] Google Books fallback when Open Library returns no results
  - [x] `map_open_library()` mapping function
  - [x] `map_google_books()` mapping function
- [x] Define `BookImportCandidate` and `BookImportRequest` schemas in `app/schemas.py`
- [x] Implement `app/routers/import_.py`:
  - [x] `GET /api/import/search` — calls service, returns candidates
  - [x] `POST /api/import` — persists candidate, 409 on duplicate ISBN
- [x] Register import router in `app/main.py`
- [x] Write `tests/test_import.py` using `monkeypatch` to fake HTTP responses:
  - [x] `test_search_open_library_success`
  - [x] `test_search_falls_back_to_google_books`
  - [x] `test_map_open_library_fields`
  - [x] `test_map_google_books_fields`
  - [x] `test_import_creates_book`
  - [x] `test_import_duplicate_isbn_returns_409`
- [x] Verify: `uv run pytest` passes

**Exit criteria:** Can search by title/ISBN, import a book, duplicates rejected. ✓

---

## Phase 3 — SvelteKit Scaffold & Three-List View

**Goal:** A working SvelteKit SPA that displays books in three status tabs, fetched from the backend.

### Tasks

- [x] Init `frontend/` with `npm create svelte@latest`
- [x] Install and configure Tailwind CSS + DaisyUI
- [x] Configure `svelte.config.js` for `adapter-static` (SPA mode, fallback `200.html`)
- [x] Configure Vite proxy (`/api` → `http://localhost:8000`) in `vite.config.ts`
- [x] Define TypeScript types in `src/lib/types.ts`
- [x] Implement `src/lib/api.ts` (all book + import API calls)
- [x] Build `+layout.svelte`:
  - [x] Desktop: fixed left sidebar with 3 status links + "Add Book" button
  - [x] Mobile: top header + bottom tab bar + FAB
- [x] Build `+page.svelte`:
  - [x] Active status tab driven by URL search param (`?status=`)
  - [x] Fetch and display books for active status
  - [x] Responsive card grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`)
- [x] Build `BookCard.svelte` (cover, title, author, status badge, star rating read-only)
- [x] Manual integration test: start backend + frontend dev servers, see books in each list

**Exit criteria:** Three-tab view works, books appear, layout is responsive on mobile and desktop. ✓

---

## Phase 4 — Book Detail, Edit & Add (Manual)

**Goal:** Users can open a book to see full details, edit all fields, delete it, and add books manually.

### Tasks

- [x] Build `StarRating.svelte` (read/write modes, DaisyUI rating)
- [x] Build `BookDrawer.svelte`:
  - [x] Slide-in drawer (desktop) / bottom sheet (mobile) via DaisyUI drawer
  - [x] Display all book fields
  - [x] Inline edit mode with save → `api.books.update()`
  - [x] Delete with confirm dialog → `api.books.delete()`
  - [x] Close updates the book list reactively
- [x] Build `AddBookModal.svelte` (manual entry tab only):
  - [x] Form with all fields, title required
  - [x] Submit → `api.books.create()`, close and refresh list
- [x] Connect "Add Book" button in layout to open `AddBookModal`
- [x] Connect `BookCard` click to open `BookDrawer`

**Exit criteria:** Full book lifecycle (create/read/update/delete) works through the UI. ✓

---

## Phase 5 — Import, Search, Sort & Filter

**Goal:** Import books from external APIs; search, sort and filter the book lists.

### Tasks

- [x] Build `ImportSearch.svelte`:
  - [x] Text input + title/ISBN toggle
  - [x] On search: call `api.import.search()`, show results with cover thumbnails
  - [x] "Add" per result: call `api.import.importBook()`, close modal, refresh list
  - [x] Loading and empty states
- [x] Add import tab to `AddBookModal.svelte`, embed `ImportSearch`
- [x] Build `SearchBar.svelte` (debounced, triggers `q` param refetch)
- [x] Add sort controls to `+page.svelte` (date added / rating, asc/desc toggle)
- [x] Wire search + sort state into `api.books.list()` call
- [x] Test full import flow end-to-end (manual: search a real title, import it)

**Exit criteria:** Books can be found via external APIs and imported; lists are searchable and sortable. ✓

---

## Phase 6 — Docker, Production Build & Polish

**Goal:** Everything runs in Docker Compose; the app is usable and looks polished.

### Tasks

- [x] Write `backend/entrypoint.sh` (alembic upgrade + uvicorn)
- [x] Write `backend/Dockerfile`
- [x] Write `frontend/nginx.conf` (`/api` proxy + SPA fallback)
- [x] Write `frontend/Dockerfile` (Node build stage → nginx stage)
- [x] Write `docker-compose.yml` (Traefik + backend + frontend, named volume)
- [x] Write `.env.example`
- [x] Verify: `docker compose up --build` starts cleanly, app is accessible at `http://localhost`
- [x] UI polish pass:
  - [x] Loading skeletons while fetching
  - [x] Empty state message per list tab
  - [x] Error toast on API failure (toast store + Toaster component)
  - [x] Cover image fallback placeholder
  - [x] Consistent spacing, colors, typography
- [x] Write a brief `README.md` covering setup, dev workflow, and Docker usage

**Exit criteria:** `docker compose up` gives a fully working, polished app at `http://localhost`. ✓
