# Implementation Plan: Input Suggestions for BookDrawer

## Goal

Add autocomplete dropdown suggestions for the **author**, **publisher**, and **tags** fields in the book edit dialog (`BookDrawer.svelte`). Suggestions are sourced from the current user's existing library data, keeping user data isolated.

---

## 1) Backend Changes

### 1.1 New Schema

File: `backend/app/schemas.py`

```python
class SuggestionList(SQLModel):
    suggestions: list[str]
```

### 1.2 New Endpoints

File: `backend/app/routers/books.py`

| Method | Path | Query Params | SQL |
|--------|------|-------------|-----|
| `GET` | `/api/books/suggestions/authors` | `q: str`, `limit: int (default 10, max 50)` | `SELECT DISTINCT author FROM book WHERE user_id=? AND author IS NOT NULL AND author ILIKE ? ORDER BY author LIMIT ?` |
| `GET` | `/api/books/suggestions/publishers` | `q: str`, `limit: int (default 10, max 50)` | `SELECT DISTINCT publisher FROM book WHERE user_id=? AND publisher IS NOT NULL AND publisher ILIKE ? ORDER BY publisher LIMIT ?` |
| `GET` | `/api/books/suggestions/tags` | `q: str`, `limit: int (default 10, max 50)` | `SELECT name FROM tag WHERE user_id=? AND name ILIKE ? ORDER BY name LIMIT ?` |

Key design:
- Substring match (`%q%`) via `ILIKE` for case-insensitive matching.
- User isolation via `require_user` dependency.
- Tag suggestions query the `Tag` table directly.
- Empty query (`q=""`) returns empty list (no query executed).

### 1.3 Tests

File: `backend/tests/test_books.py`

- `test_suggest_authors_returns_matching_authors`
- `test_suggest_authors_empty_query_returns_empty`
- `test_suggest_authors_no_match_returns_empty`
- `test_suggest_authors_deduplication`
- `test_suggest_publishers_returns_matching_publishers`
- `test_suggest_tags_returns_matching_tags`
- `test_suggest_user_isolation`

---

## 2) Frontend API Layer

File: `frontend/src/lib/api.ts`

Add `suggestions` sub-object under `books`:

```typescript
suggestions: {
  async authors(q: string, limit = 10): Promise<string[]> { ... },
  async publishers(q: string, limit = 10): Promise<string[]> { ... },
  async tags(q: string, limit = 10): Promise<string[]> { ... },
}
```

---

## 3) Frontend Component — `SuggestionInput.svelte`

New file: `frontend/src/lib/components/SuggestionInput.svelte`

A generic, reusable input-with-suggestions component.

### Props
- `value` (bindable) — current input value
- `label` — optional label text
- `placeholder` — placeholder text
- `disabled` — disables input
- `fetchSuggestions` — async function `(query: string) => Promise<string[]>`

### Interaction
- **Debounce**: 250ms on keystroke before calling API; clear suggestions immediately when input empties.
- **Keyboard**: ArrowDown/ArrowUp navigate suggestions, Enter selects highlighted, Escape closes dropdown.
- **Click**: `mousedown` on suggestion selects it (fires before blur).
- **Blur**: `setTimeout(200)` before closing dropdown to let click fire first.
- **Match highlighting**: Wrap matched portion in `<mark>` with accent styling.
- **Max suggestions**: 8-10 items from API, scrollable dropdown.

### Accessibility
- `role="combobox"` on container, `role="searchbox"` on input, `role="listbox"` on dropdown, `role="option"` with `aria-selected` on items.
- `aria-expanded`, `aria-autocomplete="list"`, `aria-controls`.

---

## 4) BookDrawer.svelte Updates

- Replace raw `<input>` for **author** and **publisher** with `<SuggestionInput>`.
- Wire `fetchSuggestions` to `api.books.suggestions.authors` / `api.books.suggestions.publishers`.
- Pass `fetchSuggestions={q => api.books.suggestions.tags(q)}` to `TagInput`.

---

## 5) TagInput.svelte Updates

- New prop: `fetchSuggestions: (query: string) => Promise<string[]>`.
- Add internal state: `suggestions`, `highlightedIndex`, `isOpen`, `isLoading`, `debounceTimer`.
- On input, debounce 250ms, call `fetchSuggestions`, show dropdown.
- Arrow keys navigate suggestions; Enter selects (adds tag to list, clears input); Escape closes.
- Match highlighting same as `SuggestionInput`.
- Dropdown positioned absolutely below the input area.

---

## 6) Data Flow

```
User types "fra" in Author field
  → SuggestionInput debounce 250ms
  → api.books.suggestions.authors("fra")
  → GET /api/books/suggestions/authors?q=fra&limit=10
  → Backend: SELECT DISTINCT author FROM book WHERE user_id=? AND author ILIKE '%fra%'
  → Response: { suggestions: ["Frank Herbert", "Franklin Bob"] }
  → Dropdown renders, user clicks or arrow+Enter to select
  → value = "Frank Herbert", dropdown closes
```

For tags, selection instead calls the existing `addCurrentTag` logic.

---

## 7) No Database Changes

The `author` and `publisher` columns exist on `Book`. The `Tag` table exists. No migrations needed.

---

## 8) Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Minor variants cause duplicate suggestions ("Herbert " vs "Herbert") | `DISTINCT` eliminates exact duplicates; normalization of input is deferred — not worth complexity for v1 |
| SQLite ILIKE compatibility | Already used in production (`list_books`), tested and known to work |
| High-frequency keystrokes cause many API calls | 250ms debounce eliminates rapid-fire calls |
| Dropdown positioning in scrollable drawer | Absolute positioning inside relative container with max-h + overflow-y-auto |
| Click on suggestion closes before click registers | `onmousedown` + setTimeout on blur |

---

## 9) Implementation Order

| Step | Description | Dependencies |
|------|-------------|-------------|
| 1 | Backend: `SuggestionList` schema + 3 endpoints | None |
| 2 | Backend: Tests for endpoints | Step 1 |
| 3 | Frontend: `api.books.suggestions.*` methods | Step 1 |
| 4 | Frontend: `SuggestionInput.svelte` component | None |
| 5 | Frontend: Update `BookDrawer.svelte` — author/publisher fields | Steps 3, 4 |
| 6 | Frontend: Update `TagInput.svelte` — suggestion dropdown | Step 3 |
| 7 | Manual verification / Playwright test update | All above |

Steps 4 can be done in parallel with Steps 1+2. Steps 5+6 depend on 3+4 but can be done in parallel.
