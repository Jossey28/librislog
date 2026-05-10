# LibrisLog — Frontend Implementation Plan

## Tech Stack

| Tool | Purpose |
|------|---------|
| SvelteKit | App framework (SPA mode via adapter-static) |
| TypeScript | Type safety |
| Tailwind CSS | Utility-first styling |
| DaisyUI | Pre-built UI components |
| Vite | Dev server & bundler |

---

## Project Setup

```bash
npm create svelte@latest frontend
# Choose: Skeleton project, TypeScript, no extra integrations

cd frontend
npm install -D tailwindcss postcss autoprefixer daisyui
npx tailwindcss init -p
npm install
```

### svelte.config.js

```js
import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({ fallback: '200.html' })
  }
};
```

### tailwind.config.ts

```ts
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['light', 'dark'],  // enable theme toggling later if desired
  }
}
```

### vite.config.ts

Add a dev proxy so API calls to `/api` are forwarded to the FastAPI backend during development:

```ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

In production the nginx config handles this proxy (see `04-docker.md`).

---

## Directory Structure

```
frontend/src/
├── app.html
├── app.css               # Tailwind base imports
├── lib/
│   ├── api.ts            # Typed fetch wrapper for all backend calls
│   ├── types.ts          # TypeScript interfaces mirroring backend schemas
│   └── components/
│       ├── BookCard.svelte
│       ├── BookDrawer.svelte
│       ├── AddBookModal.svelte
│       ├── ImportSearch.svelte
│       ├── SearchBar.svelte
│       └── StarRating.svelte
└── routes/
    ├── +layout.svelte    # App shell: nav + slot
    └── +page.svelte      # Main view: tabs + book lists
```

---

## src/lib/types.ts

Mirror the backend Pydantic schemas as TypeScript interfaces:

```ts
export type ReadingStatus = 'want_to_read' | 'currently_reading' | 'read';

export interface Book {
  id: number;
  title: string;
  author: string | null;
  isbn: string | null;
  cover_url: string | null;
  publisher: string | null;
  published_year: number | null;
  page_count: number | null;
  genre: string | null;
  notes: string | null;
  rating: number | null;  // 1–5
  reading_status: ReadingStatus;
  date_added: string;      // ISO datetime
  date_started: string | null;
  date_finished: string | null;
}

export interface BookImportCandidate {
  title: string;
  author: string | null;
  isbn: string | null;
  cover_url: string | null;
  publisher: string | null;
  published_year: number | null;
  page_count: number | null;
  genre: string | null;
  source: string;
}

export type SortField = 'date_added' | 'rating';
export type SortOrder = 'asc' | 'desc';
```

---

## src/lib/api.ts

A thin typed wrapper around `fetch`. All requests go to `/api`.

```ts
export const api = {
  books: {
    list(params?: { status?: ReadingStatus; q?: string; sort?: SortField; order?: SortOrder }): Promise<Book[]>
    get(id: number): Promise<Book>
    create(data: Partial<Book>): Promise<Book>
    update(id: number, data: Partial<Book>): Promise<Book>
    delete(id: number): Promise<void>
  },
  import: {
    search(q: string, type: 'title' | 'isbn'): Promise<BookImportCandidate[]>
    importBook(candidate: BookImportCandidate, status?: ReadingStatus): Promise<Book>
  }
}
```

All functions throw on non-2xx responses with a structured error message.

---

## Routes

### `+layout.svelte`

App shell layout:

- **Desktop** (md+): Fixed left sidebar with app name + 3 nav links (Want to Read / Currently Reading / Read) + "Add Book" button.
- **Mobile**: Top header bar + bottom tab bar with the same 3 tabs + FAB (floating action button) for "Add Book".
- Contains `<slot />` for page content.
- Passes currently selected `status` tab as context or URL param.

### `+page.svelte`

- Reads active `status` from tab / URL search param.
- Fetches books via `api.books.list({ status, q, sort, order })`.
- Contains `<SearchBar>` and sort controls.
- Renders a responsive grid of `<BookCard>` components.
- Opens `<BookDrawer>` when a card is clicked.
- Opens `<AddBookModal>` when "Add Book" is triggered.

---

## Components

### `BookCard.svelte`

Props: `book: Book`

Displays:
- Cover image (with fallback placeholder if `cover_url` is null)
- Title, Author
- `<StarRating>` (read-only, shows current rating)
- DaisyUI `badge` for reading status
- Click opens `BookDrawer`

Responsive: fixed card width on desktop, full-width on mobile.

### `BookDrawer.svelte`

Props: `book: Book | null`, `open: boolean`

A DaisyUI `drawer` or `modal` (slides in from right on desktop, bottom sheet on mobile).

Displays full book details. Contains:
- Inline editable fields (title, author, notes, rating, dates, status)
- "Save" button → calls `api.books.update()`
- "Delete" button with confirmation → calls `api.books.delete()`
- Cover image (large)

### `AddBookModal.svelte`

A DaisyUI `modal`. Two tabs:

**Manual entry tab:**
- Form fields: title (required), author, isbn, publisher, year, page count, genre, notes, rating, status
- Submit → `api.books.create()`

**Import tab:**
- Contains `<ImportSearch>`

### `ImportSearch.svelte`

- Text input + toggle for title / ISBN search type
- On submit: calls `api.import.search()`
- Shows list of `BookImportCandidate` results with cover thumbnails
- "Add" button per result → calls `api.import.importBook()`, then closes modal

### `SearchBar.svelte`

Props: `value: string`, `onSearch: (q: string) => void`

Simple debounced search input. Triggers re-fetch of book list.

### `StarRating.svelte`

Props: `value: number | null`, `readonly?: boolean`, `onChange?: (rating: number) => void`

5-star display using DaisyUI `rating` component. Shows empty stars if no rating.

---

## Responsive Layout Strategy

| Breakpoint | Layout |
|-----------|--------|
| `< md` (mobile) | Single column cards, bottom tab nav, FAB for add |
| `md` (tablet) | 2-column card grid, bottom nav or sidebar |
| `lg+` (desktop) | 3-column card grid, fixed left sidebar |

DaisyUI + Tailwind responsive classes (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`) handle this declaratively.

---

## Running Locally

```bash
npm install
npm run dev   # starts at http://localhost:5173, proxies /api to localhost:8000
npm run build # production build to ./build/
```
