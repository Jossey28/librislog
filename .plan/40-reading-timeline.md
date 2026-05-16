# Reading Timeline — Vertical Timeline of Finished Books

## Problem / Overview

There is currently no page that visualises the user's reading history chronologically. The library page already supports filtering by "read" status and sorting by `date_finished`, but it presents books in a tabular card grid — not as a chronological narrative. A dedicated "Reading Timeline" page adds a new way to reflect on the reading journey: a vertical timeline showing finished books from newest to oldest, with date, cover, title, author, tags, and rating.

## Timeline Library Choice

### Candidates

| Library | Status | Notes |
|---------|--------|-------|
| **daisyUI Timeline** | ✅ Already installed (v5.5.19) | Pure CSS component; no JS runtime. Provides `timeline`, `timeline-start`, `timeline-middle`, `timeline-end`, `timeline-box`, `timeline-snap-icon`, `timeline-vertical`, `timeline-compact` classes. |
| **Flowbite-Svelte Timeline** | ❌ Not installed | Would require `flowbite-svelte` npm dependency. Svelte 5 runes-based component library. Opinionated markup; conflicts with existing daisyUI theming. |

### Decision: daisyUI Timeline

**Reasoning:**

1. **Zero new dependencies** — daisyUI is already a dependency (`"daisyui": "^5.5.19"` in `frontend/package.json`). Adding Flowbite-Svelte would pull in a second UI framework with its own Tailwind plugin, theme system, and potential class conflicts.
2. **Pure CSS** — daisyUI's timeline is CSS-only. No component import, no JS overhead. The markup is a simple `<ul class="timeline">` with `<li>` items. This fits perfectly: the page just needs to render a list of books in chronological order.
3. **Multiple layout options** — `timeline-vertical` (default), `timeline-snap-icon`, `timeline-compact`. We can start with `timeline-vertical timeline-snap-icon` for a clean look.
4. **Existing project pattern** — The entire codebase uses daisyUI for components. Staying within daisyUI is consistent.
5. **No dependency on Svelte component version** — daisyUI timeline works with plain Tailwind/daisyUI classes, so it's compatible with Svelte 5 without needing library wrappers.

## Design Mockup (Conceptual)

```
┌────────────────────────────────────┐
│  Timeline                          │
│                                    │
│  May 2026 ──┬── Book A             │
│            ││    Author Name        │
│  May 15    ●│    ★★★★☆  #tag1      │
│            ││    [cover]            │
│  ──────────││────────              │
│  May 14    ●│    Book B             │
│            ││    Author Name        │
│            ││    ★★★★★  #fiction   │
│            ││    [cover]            │
│  ──────────││────────              │
│  Apr 2026 ─┘├── Book C             │
│            │     Author Name        │
│  Apr 20    ●     ★★★☆☆             │
│            │     [cover]            │
└────────────────────────────────────┘
```

**Layout:**
- **Month/year markers** sit on the left side of the timeline line (e.g., "May 2026", "Apr 2026") and act as section headers
- **Each book** is a timeline entry between two month/year markers
- **Left side** of each book entry: exact finish day (e.g., "May 15")
- **Middle**: timeline dot node (primary-color SVG circle)
- **Right side** (`timeline-end` with `timeline-box`): book cover thumbnail, title, author, rating stars, tag badges

## Data Flow

```
[Browser]
   │
   ▼
GET /api/books?status=read&sort=date_finished&order=desc&smart_sort=false
   │
   ▼
[Backend: list_books endpoint]
   │  select * from book
   │  where reading_status = 'read'
   │  and user_id = current_user.id
   │  and date_finished is not null     ← backend-side filter
   │  order by date_finished desc
   │
   ▼
[Response] → List<BookRead> (already existing schema)
   │
   ▼
[Frontend: /timeline page]
    │  group books by month+year (e.g. "2026-05")
    │  render month/year markers as timeline section headers
    │  each book entry shows exact day (e.g. "May 15")
    ▼
[Browser render]
```

## Files to Create

### 1. `frontend/src/routes/timeline/+page.svelte`

A new SvelteKit route page. Follows the same pattern as `dashboard/+page.svelte` and `library/+page.svelte`:

- Uses `api.books.list({ status: 'read', sort: 'date_finished', order: 'desc', smart_sort: false })` to fetch books
- Groups books by month+year (extracted from `date_finished`, e.g. `"2026-05"`), sorted newest first
- Renders month/year section headers (e.g. "May 2026") as timeline markers with a filled dot
- Each book entry below its month/year header shows the exact day (e.g. "May 15")
- Renders a vertical daisyUI timeline inside a card
- Uses `formatDate` / `formatDateTime` from `$lib/date` and `getTimezone` from `$lib/stores/timezone`
- Each timeline entry shows:
  - **Left (`timeline-start`)**: finish date formatted according to the user's timezone (e.g., `May 2026` or `2026-05-16`)
  - **Middle (`timeline-middle`)**: a filled circle (using daisyUI `text-primary` SVG circle or a simple daisyUI icon)
  - **Right (`timeline-end timeline-box`)**: book cover thumbnail (if available), title, author, rating stars (or placeholder), tags (if any)
- Horizontal rule (`<hr>`) connects items
- Loading spinner while fetching
- Empty state: "No finished books yet" with link to library
- Error handling with toast
- Click on a timeline item opens `BookDetailDialog` (reuse existing component)
- "View all in library" link at top-right

### 2. `frontend/src/lib/i18n/locales/en.json` — add `timeline` section

New i18n keys (see below).

### 3. `frontend/src/lib/i18n/locales/de.json` — add `timeline` section

German translations (see below).

## Files to Modify

### 1. `frontend/src/routes/+layout.svelte`

**Three changes:**

a) Add `{ href: '/timeline', labelKey: 'nav.timeline', icon: '📖' }` to the `NAV_ITEMS` array after `/library`.

```typescript
const NAV_ITEMS = $derived.by(() => {
    const items = [
        { href: '/dashboard', labelKey: 'nav.dashboard', icon: '🏠' },
        { href: '/library', labelKey: 'nav.library', icon: '📚' },
        { href: '/timeline', labelKey: 'nav.timeline', icon: '📖' },
    ];
    // ...
});
```

b) Add a `pageTitle()` check for `/timeline`:

```typescript
if ($page.url.pathname.startsWith('/timeline')) {
    return `${$_('app.title')} - ${$_('nav.timeline')}`;
}
```

### 2. No backend changes needed

The existing `GET /api/books` endpoint already supports `status=read`, `sort=date_finished`, and `order=desc`. Additionally, `smart_sort=false` should be passed to avoid default-sort override. The backend already handles `date_finished` being null by using `.nullslast()`.

**However**, it would be good practice to add a client-side filter in the frontend (or a backend query refinement — see "Optional" below) to exclude books where `date_finished` is null even when status is "read" (data consistency safeguard). The existing `list_books` endpoint returns all books matching the status; a "read" book without `date_finished` would have a null sort value and appear last — but ideally shouldn't appear on the timeline at all.

**Optional backend improvement:** Add a `has_date_finished` query param to the `list_books` endpoint (or filter in the frontend JS). Recommendation: filter in the frontend after receiving data, since this is a presentation concern and the backend already properly sorts nulls last. The frontend can just skip books where `date_finished === null`.

## Step-by-Step Implementation Order

### Step 1: i18n keys (en.json + de.json)

Add the new timeline section to both locale files. This is independent and can be done first.

### Step 2: Create `frontend/src/routes/timeline/+page.svelte`

The core page. Implementation details:

```svelte
<script lang="ts">
    import { page } from '$app/stores';
    import { onMount } from 'svelte';
    import type { Book } from '$lib/types';
    import { api } from '$lib/api';
    import { _ } from '$lib/i18n';
    import { toasts } from '$lib/toasts';
    import { shouldShowActionToast } from '$lib/errors';
    import { formatDate } from '$lib/date';
    import { getTimezone } from '$lib/stores/timezone';
    import BookDetailDialog from '$lib/components/BookDetailDialog.svelte';
    import BookDrawer from '$lib/components/BookDrawer.svelte';

    let loading = $state(true);
    let books = $state<Book[]>([]);
    let selectedBook = $state<Book | null>(null);
    let detailOpen = $state(false);
    let drawerOpen = $state(false);
    let tz = $state('UTC');

    onMount(() => {
        tz = getTimezone();
        void loadTimeline();
    });

    async function loadTimeline() {
        loading = true;
        try {
            const allRead = await api.books.list({
                status: 'read',
                sort: 'date_finished',
                order: 'desc',
                smart_sort: false
            });
            // Filter out books without date_finished (data consistency)
            books = allRead.filter(b => b.date_finished !== null);
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : $_('common.actionFailed', { values: { action: 'load' } });
            if (shouldShowActionToast(msg)) {
                toasts.add(msg, 'error');
            }
            books = [];
        } finally {
            loading = false;
        }
    }

    // Group books by month+year (e.g. "2026-05")
    let grouped = $derived.by(() => {
        const map = new Map<string, Book[]>();
        for (const b of books) {
            if (!b.date_finished) continue;
            const key = b.date_finished.slice(0, 7);  // "2026-05"
            if (!map.has(key)) map.set(key, []);
            map.get(key)!.push(b);
        }
        // Sort month+year keys descending
        const sorted = [...map.entries()].sort(([a], [b]) => b.localeCompare(a));
        // Within each group, books are already sorted by date_finished desc from API
        return sorted;
    });

    function openDetailView(book: Book) {
        selectedBook = book;
        detailOpen = true;
        drawerOpen = false;
    }

    function openEditFromDetail(book: Book) {
        selectedBook = book;
        detailOpen = false;
        drawerOpen = true;
    }

    function handleSave(updated: Book) {
        if (updated.reading_status !== 'read' || !updated.date_finished) {
            // Book no longer belongs on timeline; reload
            void loadTimeline();
            return;
        }
        // Update in-place
        books = books.map(b => b.id === updated.id ? updated : b);
    }

    function handleDelete(id: number) {
        detailOpen = false;
        drawerOpen = false;
        books = books.filter(b => b.id !== id);
    }

    // Simple star rendering helper
    function stars(rating: number | null): string {
        if (rating === null || rating < 1) return '';
        return '★'.repeat(rating) + '☆'.repeat(5 - rating);
    }

    // Format a month+year section header (e.g., "May 2026")
    function formatMonthYear(iso: string): string {
        const d = new Date(iso);
        return d.toLocaleDateString(tz === 'UTC' ? 'en-US' : undefined, {
            month: 'short',
            year: 'numeric',
            timeZone: tz
        });
    }

    // Format a book entry date showing exact day (e.g., "May 15")
    function formatDay(iso: string): string {
        const d = new Date(iso);
        return d.toLocaleDateString(tz === 'UTC' ? 'en-US' : undefined, {
            month: 'short',
            day: 'numeric',
            timeZone: tz
        });
    }
</script>
```

Template outline:

```
<div class="flex flex-col gap-6">
  <!-- Header card -->
  <div class="hero ...">
    <h1>$_('timeline.title')</h1>
    <p>$_('timeline.subtitle')</p>
    <a href="/library?status=read">$_('timeline.viewInLibrary')</a>
  </div>

  <!-- Loading state -->
  {#if loading}
    <div class="..."><span class="loading loading-spinner ..."></span></div>

  <!-- Empty state -->
  {:else if books.length === 0}
    <p>$_('timeline.noReadBooks')</p>

  <!-- Timeline -->
  {:else}
    {#each grouped as [monthKey, monthBooks]}
      <ul class="timeline timeline-vertical timeline-snap-icon">
        <!-- Month/year section header -->
        <li>
          <hr />
          <div class="timeline-start text-base font-semibold">
            {formatMonthYear(monthBooks[0].date_finished!)}
          </div>
          <div class="timeline-middle">
            <svg class="text-primary h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <circle cx="10" cy="10" r="5" />
            </svg>
          </div>
          <div class="timeline-end timeline-box"></div>
          <hr />
        </li>

        <!-- Book entries for this month -->
        {#each monthBooks as book, i (book.id)}
          <li>
            {#if i < monthBooks.length - 1 || true}<hr />{/if}
            <div class="timeline-start text-xs sm:text-sm">
              {formatDay(book.date_finished!)}
            </div>
            <div class="timeline-middle">
              <svg class="text-primary h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                <circle cx="10" cy="10" r="5" />
              </svg>
            </div>
            <div class="timeline-end timeline-box cursor-pointer" onclick={() => openDetailView(book)}>
              <div class="flex gap-3 items-start">
                {#if book.cover_url}
                  <img src={book.cover_url} alt={book.title} class="w-10 h-14 object-cover rounded shrink-0" />
                {/if}
                <div class="min-w-0">
                  <p class="font-medium">{book.title}</p>
                  {#if book.author}
                    <p class="text-sm text-base-content/70">{book.author}</p>
                  {/if}
                  {#if book.rating}
                    <p class="text-warning text-sm">{stars(book.rating)}</p>
                  {/if}
                  {#if book.tags}
                    <div class="flex flex-wrap gap-1 mt-1">
                      {#each book.tags.split(',').filter(Boolean) as tag}
                        <span class="badge badge-xs badge-outline">{tag.trim()}</span>
                      {/each}
                    </div>
                  {/if}
                </div>
              </div>
            </div>
            {#if i < monthBooks.length - 1}<hr class="bg-primary" />{/if}
          </li>
        {/each}
      </ul>
    {/each}
  {/if}
</div>

<!-- Reuse existing detail/edit components -->
<BookDetailDialog bind:book={selectedBook} bind:open={detailOpen} onEdit={openEditFromDetail} onDelete={handleDelete} />
<BookDrawer bind:book={selectedBook} bind:open={drawerOpen} onSave={handleSave} />
```

### Step 3: Update `+layout.svelte`

Add the timeline nav item and page-title branch.

### Step 4: Verify

- Run frontend type-check: `npm run check` (in `frontend/`)
- Run frontend tests: `npm test`
- Build: `npm run build`
- Manual test: navigate to `/timeline`, verify books appear, click one to open detail

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No books with status "read" | Empty state message: "No finished books in your library yet." with link to `/library` |
| "Read" books with no `date_finished` | Filtered out client-side (data consistency). They will be at the end of the API response (nullslast) but filtered by the `books.filter(b => b.date_finished)` call. |
| Book status changes from "read" after being on timeline | After edit dialog saves (via `handleSave`), if `reading_status !== 'read'` or `date_finished === null`, the book is removed from the timeline by re-fetching. |
| Book is deleted | Removed from local list via `handleDelete`. Detail dialog handles this already. |
| Very long title/author | Use Tailwind truncation classes (`truncate`, `line-clamp-2`) inside `timeline-box`. |
| Many books in one month | Grouped naturally under the same month/year marker; books are sorted by exact date descending within each group. |
| Only one book in a month | Still shows the month/year marker as a section header, with the single book entry below it. |
| Many books (performance) | The API already paginates implicitly by returning all results. For very large libraries (>500 read books), a future optimisation could add pagination or limit. Not needed for initial implementation. |
| No cover image | Conditionally render `<img>` only when `cover_url` is truthy. Layout adapts via flex. |
| No tags | Only render tag badges when `book.tags` is non-null and non-empty. |
| No rating | Only render stars when `book.rating` is not null. |
| Timezone awareness | Use `getTimezone()` and `formatDate()` for date display, matching existing pattern in `BookDetailDialog.svelte` and `BookDrawer.svelte`. |
| Cross-year months (e.g., May 2026 and May 2025) | Correctly grouped as separate sections since keys use the full `YYYY-MM` prefix. |

## i18n Keys

### `en.json`

```json
"nav": {
    "timeline": "Timeline"
}
"timeline": {
    "title": "Reading Timeline",
    "subtitle": "A chronological view of books you've finished reading",
    "viewInLibrary": "View all in library",
    "noReadBooks": "No finished books in your library yet."
}
```

### `de.json`

```json
"nav": {
    "timeline": "Zeitleiste"
}
"timeline": {
    "title": "Lese-Zeitleiste",
    "subtitle": "Eine chronologische Ansicht der Bücher, die du gelesen hast",
    "viewInLibrary": "Alle in der Bibliothek anzeigen",
    "noReadBooks": "Noch keine gelesenen Bücher in deiner Bibliothek."
}
```

## Summary of Changes

| File | Action |
|------|--------|
| `frontend/src/routes/timeline/+page.svelte` | **Create** — new page with daisyUI timeline |
| `frontend/src/lib/i18n/locales/en.json` | **Modify** — add `nav.timeline` and `timeline.*` keys |
| `frontend/src/lib/i18n/locales/de.json` | **Modify** — add German translations |
| `frontend/src/routes/+layout.svelte` | **Modify** — add `/timeline` nav item and page-title branch |

No backend changes required. No new npm dependencies.
