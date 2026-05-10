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

- [ ] Implement `app/services/book_import.py`:
  - [ ] `search()` async function with Open Library primary call
  - [ ] Google Books fallback when Open Library returns no results
  - [ ] `map_open_library()` mapping function
  - [ ] `map_google_books()` mapping function
- [ ] Define `BookImportCandidate` and `BookImportRequest` schemas in `app/schemas.py`
- [ ] Implement `app/routers/import_.py`:
  - [ ] `GET /api/import/search` — calls service, returns candidates
  - [ ] `POST /api/import` — persists candidate, 409 on duplicate ISBN
- [ ] Register import router in `app/main.py`
- [ ] Write `tests/test_import.py` using `monkeypatch` to fake HTTP responses:
  - [ ] `test_search_open_library_success`
  - [ ] `test_search_falls_back_to_google_books`
  - [ ] `test_map_open_library_fields`
  - [ ] `test_map_google_books_fields`
  - [ ] `test_import_creates_book`
  - [ ] `test_import_duplicate_isbn_returns_409`
- [ ] Verify: `uv run pytest` passes

**Exit criteria:** Can search by title/ISBN, import a book, duplicates rejected.

---

## Phase 3 — SvelteKit Scaffold & Three-List View

**Goal:** A working SvelteKit SPA that displays books in three status tabs, fetched from the backend.

### Tasks

- [ ] Init `frontend/` with `npm create svelte@latest`
- [ ] Install and configure Tailwind CSS + DaisyUI
- [ ] Configure `svelte.config.js` for `adapter-static` (SPA mode, fallback `200.html`)
- [ ] Configure Vite proxy (`/api` → `http://localhost:8000`) in `vite.config.ts`
- [ ] Define TypeScript types in `src/lib/types.ts`
- [ ] Implement `src/lib/api.ts` (all book + import API calls)
- [ ] Build `+layout.svelte`:
  - [ ] Desktop: fixed left sidebar with 3 status links + "Add Book" button
  - [ ] Mobile: top header + bottom tab bar + FAB
- [ ] Build `+page.svelte`:
  - [ ] Active status tab driven by URL search param (`?status=`)
  - [ ] Fetch and display books for active status
  - [ ] Responsive card grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`)
- [ ] Build `BookCard.svelte` (cover, title, author, status badge, star rating read-only)
- [ ] Manual integration test: start backend + frontend dev servers, see books in each list

**Exit criteria:** Three-tab view works, books appear, layout is responsive on mobile and desktop.

---

## Phase 4 — Book Detail, Edit & Add (Manual)

**Goal:** Users can open a book to see full details, edit all fields, delete it, and add books manually.

### Tasks

- [ ] Build `StarRating.svelte` (read/write modes, DaisyUI rating)
- [ ] Build `BookDrawer.svelte`:
  - [ ] Slide-in drawer (desktop) / bottom sheet (mobile) via DaisyUI drawer
  - [ ] Display all book fields
  - [ ] Inline edit mode with save → `api.books.update()`
  - [ ] Delete with confirm dialog → `api.books.delete()`
  - [ ] Close updates the book list reactively
- [ ] Build `AddBookModal.svelte` (manual entry tab only):
  - [ ] Form with all fields, title required
  - [ ] Submit → `api.books.create()`, close and refresh list
- [ ] Connect "Add Book" button in layout to open `AddBookModal`
- [ ] Connect `BookCard` click to open `BookDrawer`

**Exit criteria:** Full book lifecycle (create/read/update/delete) works through the UI.

---

## Phase 5 — Import, Search, Sort & Filter

**Goal:** Import books from external APIs; search, sort and filter the book lists.

### Tasks

- [ ] Build `ImportSearch.svelte`:
  - [ ] Text input + title/ISBN toggle
  - [ ] On search: call `api.import.search()`, show results with cover thumbnails
  - [ ] "Add" per result: call `api.import.importBook()`, close modal, refresh list
  - [ ] Loading and empty states
- [ ] Add import tab to `AddBookModal.svelte`, embed `ImportSearch`
- [ ] Build `SearchBar.svelte` (debounced, triggers `q` param refetch)
- [ ] Add sort controls to `+page.svelte` (date added / rating, asc/desc toggle)
- [ ] Wire search + sort state into `api.books.list()` call
- [ ] Test full import flow end-to-end (manual: search a real title, import it)

**Exit criteria:** Books can be found via external APIs and imported; lists are searchable and sortable.

---

## Phase 6 — Docker, Production Build & Polish

**Goal:** Everything runs in Docker Compose; the app is usable and looks polished.

### Tasks

- [ ] Write `backend/entrypoint.sh` (alembic upgrade + uvicorn)
- [ ] Write `backend/Dockerfile`
- [ ] Write `frontend/nginx.conf` (`/api` proxy + SPA fallback)
- [ ] Write `frontend/Dockerfile` (Node build stage → nginx stage)
- [ ] Write `docker-compose.yml` (two services, named volume, internal network)
- [ ] Write `.env.example`
- [ ] Verify: `docker compose up --build` starts cleanly, app is accessible at `http://localhost`
- [ ] UI polish pass:
  - [ ] Loading skeletons while fetching
  - [ ] Empty state message per list tab
  - [ ] Error toast on API failure
  - [ ] Cover image fallback placeholder
  - [ ] Consistent spacing, colors, typography
- [ ] Write a brief `README.md` covering setup, dev workflow, and Docker usage

**Exit criteria:** `docker compose up` gives a fully working, polished app at `http://localhost`.
