# LibrisLog — Import Search Progress Indicator

## Goal

Show the user real-time progress while `ImportSearch` searches external APIs:
1. "Searching Open Library…"
2. "Found N results" — or "Nothing on Open Library, trying Google Books…"
3. "Found N results from Google Books" — or "No results found"

The progress messages come from the backend as the search actually runs, not from
a timer or a fake animation.

---

## Transport: Server-Sent Events (SSE)

### Why SSE

| Option | Verdict |
|--------|---------|
| SSE (`text/event-stream`) | **Chosen** — one-way server push, native `EventSource` browser API, zero extra dependencies on either side, simple line protocol |
| WebSockets | Overkill — bidirectional is not needed here |
| Polling | Requires server-side state store per request; more complex |
| Fake client-side steps | Doesn't reflect real backend behaviour; misleading if one source is slow or skipped |

FastAPI supports SSE via `StreamingResponse`. No extra package needed.

### SSE protocol recap

```
data: {"stage":"open_library","status":"searching"}\n\n
data: {"stage":"open_library","status":"done","count":0}\n\n
data: {"stage":"google_books","status":"searching"}\n\n
data: {"stage":"google_books","status":"done","count":5}\n\n
data: {"stage":"complete","results":[...]}\n\n
```

Each event is a JSON object on a single `data:` line, terminated by a blank line.
The final `complete` event carries the full result list so the frontend only needs
one stream, not a stream + a follow-up request.

---

## Event Schema

```
Stage name          status values         extra fields
──────────────────  ────────────────────  ────────────────────────────────────
open_library        searching             —
open_library        done                  count: int
google_books        searching             —
google_books        done                  count: int
google_books        skipped               reason: "no_api_key"
complete            —                     results: BookImportCandidate[]
error               —                     message: str
```

---

## Backend Changes

### 1. `app/services/book_import.py`

Add `search_with_progress()` — an `AsyncGenerator` that yields event dicts and
performs the same search logic as `search()`.  The existing `search()` function
is kept unchanged so that:
- All existing tests continue to work without modification.
- The non-streaming `GET /api/import/search` endpoint continues to work (useful
  for direct API consumers / curl).

```python
async def search_with_progress(
    query: str,
    search_type: str,
    *,
    api_key: str = "",
    http_client: Optional[httpx.AsyncClient] = None,
) -> AsyncGenerator[dict, None]:
    yield {"stage": "open_library", "status": "searching"}
    ol_results = await _search_open_library(...)
    yield {"stage": "open_library", "status": "done", "count": len(ol_results)}

    gb_results: list[BookImportCandidate] = []
    if not ol_results:
        if not api_key:
            yield {"stage": "google_books", "status": "skipped", "reason": "no_api_key"}
        else:
            yield {"stage": "google_books", "status": "searching"}
            gb_results = await _search_google_books(...)
            yield {"stage": "google_books", "status": "done", "count": len(gb_results)}

    results = ol_results or gb_results
    yield {"stage": "complete", "results": [r.model_dump() for r in results]}
```

### 2. `app/routers/import_.py`

New endpoint alongside the existing `/search`:

```python
GET /api/import/search/stream?q=…&type=…
```

Returns `StreamingResponse` with `media_type="text/event-stream"`.

Headers set on the response:
- `Cache-Control: no-cache` — required by SSE spec
- `X-Accel-Buffering: no` — tells nginx (inside the frontend container) and
  Traefik not to buffer the stream; without this, events are held until the
  connection closes

The generator serialises each event dict as `data: {json}\n\n`.

### 3. No schema changes

`BookImportCandidate` is already defined; the `complete` event uses
`.model_dump()` to serialise it. No new Pydantic models needed.

---

## Frontend Changes

### `src/lib/api.ts`

Add `api.import.searchStream(query, type)` that returns an `AsyncGenerator`
yielding typed progress events parsed from the SSE stream.

Uses `fetch()` + `ReadableStream` reader (not `EventSource`) because:
- `EventSource` doesn't support custom headers or POST, but more importantly it
  cannot be used with the Vite dev proxy `/api` in the same way `fetch` can.
- `fetch` + streaming gives full control and works identically in dev and prod.

### `src/lib/types.ts`

Add types for progress events:

```typescript
export type SearchStage =
  | { stage: 'open_library'; status: 'searching' }
  | { stage: 'open_library'; status: 'done'; count: number }
  | { stage: 'google_books'; status: 'searching' }
  | { stage: 'google_books'; status: 'done'; count: number }
  | { stage: 'google_books'; status: 'skipped'; reason: string }
  | { stage: 'complete'; results: BookImportCandidate[] }
  | { stage: 'error'; message: string };
```

### `src/lib/components/ImportSearch.svelte`

Replace the current `searching: boolean` state with a richer progress model:

```typescript
let stages = $state<SearchStage[]>([]);   // append-only log of events
let searching = $state(false);
let results = $state<BookImportCandidate[]>([]);
```

**Progress UI** — shown while `searching` is true and after, until results are
rendered:

A vertical step list (one row per received event) using DaisyUI `steps` or a
simple custom list:

```
◌ Searching Open Library…         ← spinner while status=searching
✓ Open Library — 0 results        ← check when done, count=0
◌ Searching Google Books…         ← spinner
✓ Google Books — 5 results        ← check, count=5
```

If `status=skipped`:
```
— Google Books skipped (no API key configured)
```

If `stage=error`:
```
✗ Search failed: <message>
```

Icons: unicode or DaisyUI badge colours (no extra icon library needed).
Progress area is hidden once results are rendered and searching is done.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/book_import.py` | Add `search_with_progress()` async generator |
| `backend/app/routers/import_.py` | Add `GET /api/import/search/stream` endpoint |
| `frontend/src/lib/types.ts` | Add `SearchStage` union type |
| `frontend/src/lib/api.ts` | Add `api.import.searchStream()` |
| `frontend/src/lib/components/ImportSearch.svelte` | Replace search logic + UI with SSE-based progress display |

---

## Test Strategy

### Backend

- Add `test_search_with_progress_open_library_success` — assert yielded events in order when OL returns results
- Add `test_search_with_progress_falls_back_to_google` — assert OL done (count=0) → GB searching → GB done → complete
- Add `test_search_with_progress_skips_google_without_key` — assert `google_books skipped` event when no API key
- Add `test_search_stream_endpoint` — hit `/api/import/search/stream` via TestClient, parse SSE lines, verify final `complete` event contains results

Existing `search()` tests remain unchanged.

### Frontend

Manual test only (no Jest/Vitest in this project):
- Open "Search & Import" tab, type a title, click Search
- Verify progress steps appear in sequence
- Verify results render after `complete` event

---

## Traefik / nginx notes

- The `X-Accel-Buffering: no` response header disables nginx buffering inside
  the frontend container (nginx only handles static files, so this header is only
  relevant if a future reverse-proxy nginx sits in front of the backend).
- Traefik v3 passes `text/event-stream` responses through without buffering by
  default when the response is chunked/streaming.
- The Vite dev proxy (`/api` → `localhost:8000`) forwards SSE correctly out of
  the box.

---

## Out of Scope

- Per-item progress within the Open Library or Google Books response parsing.
- Cancelling an in-flight search from the client.
- Persisting progress state across page navigations.
