# Dashboard Global Search Feature

## Overview

Implement a global search box on the dashboard that searches through all books regardless of their reading status. Search results should appear in a dropdown below the search box while typing, displaying key book information. Clicking a result should navigate to the appropriate library view with the book's detail dialog opened.

## Requirements

### Functional Requirements

1. **Search Box Placement**: Add search box to dashboard page, prominently placed
2. **Real-time Search**: Search executes as user types (debounced)
3. **Cross-Status Search**: Search across all reading statuses (want_to_read, currently_reading, read, did_not_finish)
4. **Search Fields**: Match against book title and author
5. **Result Display**: Show results in dropdown below search box with:
   - Book cover (or placeholder if unavailable)
   - Book title
   - Author (hide if not available)
   - Reading status badge (hide if somehow not available, though it's required)
6. **Result Navigation**: Clicking a result navigates to `/library?status={book.reading_status}` and opens the book detail dialog
7. **Empty States**: Handle no results gracefully
8. **Loading State**: Show loading indicator while searching

### Non-Functional Requirements

- Responsive design (mobile + desktop)
- Accessible keyboard navigation
- Consistent with existing UI/UX patterns
- Performant search with debouncing

## Current State Analysis

### Existing Components

- **SearchBar.svelte**: Reusable search input component with debouncing (300ms)
- **BookCard.svelte**: Displays book with cover, title, author, rating, status badge
- **api.books.list()**: Existing API that accepts `q` parameter for search

### Current API Capabilities

From `backend/app/routers/books.py`:
```python
@router.get("", response_model=List[BookRead])
def list_books(
    status: Optional[ReadingStatus] = Query(default=None),
    q: Optional[str] = Query(default=None),
    ...
):
    statement = select(Book).where(Book.user_id == current_user.id)
    
    if status is not None:
        statement = statement.where(Book.reading_status == status)
    
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            Book.title.ilike(pattern) | Book.author.ilike(pattern)
        )
```

**Key finding**: The existing `/api/books` endpoint already supports:
- Cross-status search (when `status` param is omitted)
- Title and author search (via `q` parameter)
- User-scoped filtering

**No backend changes needed!** We can use the existing API.

## Architecture

### Component Structure

```
dashboard/+page.svelte
  └── DashboardSearchBox.svelte (NEW)
      ├── SearchBar.svelte (reused)
      └── SearchResultsDropdown.svelte (NEW)
          └── SearchResultItem.svelte (NEW)
```

### Data Flow

1. User types in search box
2. SearchBar debounces input (300ms)
3. Call `api.books.list({ q: searchQuery })` (no status filter = search all)
4. Display results in dropdown
5. Click result → navigate to library with query params
6. Library page reads URL params → opens detail dialog

## Implementation Plan

### Phase 1: Backend Verification & Testing

**File**: `backend/tests/test_books.py`

**Changes**:
- Add test case for global search (search without status filter)
- Verify search returns books from multiple statuses
- Test empty query behavior
- Test no results scenario

**Test Cases**:
```python
def test_list_books_global_search_across_statuses(client: TestClient):
    """Verify q param searches across all statuses when status is not specified"""
    # Create books in different statuses
    _create_book(client, title="Python Guide", reading_status="want_to_read")
    _create_book(client, title="Python Tricks", reading_status="read")
    _create_book(client, title="Java Basics", reading_status="currently_reading")
    
    # Search without status filter
    resp = client.get("/api/books?q=Python")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = [b["title"] for b in data]
    assert "Python Guide" in titles
    assert "Python Tricks" in titles

def test_list_books_global_search_by_author(client: TestClient):
    """Verify search matches author field across all statuses"""
    _create_book(client, title="Book A", author="Jane Doe", reading_status="want_to_read")
    _create_book(client, title="Book B", author="Jane Smith", reading_status="read")
    _create_book(client, title="Book C", author="John Doe", reading_status="currently_reading")
    
    resp = client.get("/api/books?q=Jane")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

def test_list_books_global_search_no_results(client: TestClient):
    """Verify empty array returned when no matches"""
    _create_book(client, title="Existing Book")
    
    resp = client.get("/api/books?q=nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []
```

---

### Phase 2: Frontend Components

#### 2.1 Create SearchResultItem Component

**File**: `frontend/src/lib/components/SearchResultItem.svelte`

**Purpose**: Display individual search result with cover, title, author, status

**Props**:
- `book: Book`
- `onClick: (book: Book) => void`

**Features**:
- Compact horizontal layout
- Small cover thumbnail (48x72px or similar)
- Title (line-clamp-1)
- Author in muted text (hide if null)
- Status badge (same styling as BookCard)
- Hover effect
- Keyboard navigation support (role="option")

**HTML Structure**:
```svelte
<button
  role="option"
  class="flex items-center gap-3 w-full p-2 hover:bg-base-200 transition-colors cursor-pointer text-left"
  onclick={() => onClick(book)}
>
  <div class="w-12 h-18 flex-shrink-0 bg-base-300 rounded overflow-hidden">
    {#if book.cover_url}
      <img src={book.cover_url} alt="" class="w-full h-full object-cover" />
    {:else}
      <!-- Book icon placeholder -->
    {/if}
  </div>
  
  <div class="flex-1 min-w-0">
    <h3 class="text-sm font-medium truncate">{book.title}</h3>
    {#if book.author}
      <p class="text-xs text-base-content/60 truncate">{book.author}</p>
    {/if}
  </div>
  
  <span class="badge badge-xs {STATUS_BADGE[book.reading_status]} flex-shrink-0">
    {$_(STATUS_LABEL_KEYS[book.reading_status])}
  </span>
</button>
```

---

#### 2.2 Create SearchResultsDropdown Component

**File**: `frontend/src/lib/components/SearchResultsDropdown.svelte`

**Purpose**: Container for search results with loading/empty states

**Props**:
- `results: Book[]`
- `loading: boolean`
- `query: string`
- `onSelectBook: (book: Book) => void`

**Features**:
- Positioned absolutely below search input
- Max height with scroll
- Loading spinner state
- Empty state when query exists but no results
- Hidden when query is empty or results are empty and not loading

**HTML Structure**:
```svelte
{#if query && (loading || results.length > 0)}
  <div class="absolute top-full left-0 right-0 mt-2 bg-base-100 border border-base-300 rounded-lg shadow-lg max-h-96 overflow-y-auto z-50">
    {#if loading}
      <div class="p-8 text-center">
        <span class="loading loading-spinner loading-md"></span>
      </div>
    {:else if results.length === 0}
      <div class="p-8 text-center text-base-content/40">
        <p>{$_('dashboard.search.noResults')}</p>
      </div>
    {:else}
      <div role="listbox">
        {#each results as book (book.id)}
          <SearchResultItem {book} onClick={onSelectBook} />
        {/each}
      </div>
    {/if}
  </div>
{/if}
```

---

#### 2.3 Create DashboardSearchBox Component

**File**: `frontend/src/lib/components/DashboardSearchBox.svelte`

**Purpose**: Main search orchestrator - manages search state, API calls, navigation

**State**:
- `searchQuery: string` - bound to SearchBar
- `results: Book[]` - search results
- `loading: boolean` - API call in progress

**Methods**:
```typescript
async function handleSearch(query: string) {
  searchQuery = query;
  
  if (!query.trim()) {
    results = [];
    loading = false;
    return;
  }
  
  loading = true;
  try {
    results = await api.books.list({ q: query.trim() });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : $_('dashboard.search.failed');
    if (shouldShowActionToast(message)) {
      toasts.add(message, 'error');
    }
    results = [];
  } finally {
    loading = false;
  }
}

function handleSelectBook(book: Book) {
  // Navigate to library with status and book ID
  // Library will need to detect book ID in URL and open detail
  const url = `/library?status=${book.reading_status}&bookId=${book.id}`;
  goto(url);
  
  // Reset search
  searchQuery = '';
  results = [];
}
```

**HTML Structure**:
```svelte
<div class="relative w-full max-w-2xl">
  <SearchBar
    bind:value={searchQuery}
    placeholder={$_('dashboard.search.placeholder')}
    onSearch={handleSearch}
  />
  
  <SearchResultsDropdown
    {results}
    {loading}
    query={searchQuery}
    onSelectBook={handleSelectBook}
  />
</div>
```

---

#### 2.4 Integrate into Dashboard

**File**: `frontend/src/routes/dashboard/+page.svelte`

**Changes**:
1. Import `DashboardSearchBox`
2. Add search box below hero section, before stats cards

**Placement**:
```svelte
<div class="flex flex-col gap-6">
  <!-- Existing hero section -->
  <div class="hero rounded-2xl bg-base-100 shadow-sm border border-base-200">
    <!-- ... existing hero content ... -->
  </div>

  <!-- NEW: Global Search -->
  <div class="card bg-base-100 border border-base-200 shadow-sm">
    <div class="card-body">
      <h2 class="card-title mb-2">{$_('dashboard.search.title')}</h2>
      <DashboardSearchBox />
    </div>
  </div>

  <!-- Existing quote section -->
  {#if quoteEnabled}
    <!-- ... -->
  {/if}
  
  <!-- ... rest of dashboard ... -->
</div>
```

---

#### 2.5 Update Library Page for Deep Linking

**File**: `frontend/src/routes/library/+page.svelte`

**Changes**: Support `bookId` query parameter to auto-open book detail

**Implementation**:
```svelte
<script lang="ts">
  // ... existing code ...
  
  let bookIdFromUrl = $derived<number | null>(() => {
    const param = $page.url.searchParams.get('bookId');
    return param ? parseInt(param, 10) : null;
  });
  
  // Effect to auto-open book detail when bookId in URL
  $effect(() => {
    if (bookIdFromUrl && !loading && books.length > 0) {
      const book = books.find(b => b.id === bookIdFromUrl);
      if (book) {
        openDetailView(book);
        // Clean URL without refreshing
        const url = new URL(window.location.href);
        url.searchParams.delete('bookId');
        window.history.replaceState({}, '', url);
      }
    }
  });
</script>
```

**Note**: This enables navigation from dashboard search results to open the book detail dialog directly.

---

### Phase 3: Internationalization

**File**: `frontend/src/lib/i18n/locales/en.json`

**Add keys**:
```json
{
  "dashboard": {
    "search": {
      "title": "Search Your Library",
      "placeholder": "Search all books by title or author...",
      "noResults": "No books found",
      "failed": "Search failed"
    }
  }
}
```

**File**: `frontend/src/lib/i18n/locales/de.json` (and other languages)

**Add German translations**:
```json
{
  "dashboard": {
    "search": {
      "title": "Bibliothek durchsuchen",
      "placeholder": "Alle Bücher nach Titel oder Autor durchsuchen...",
      "noResults": "Keine Bücher gefunden",
      "failed": "Suche fehlgeschlagen"
    }
  }
}
```

---

### Phase 4: Styling & Responsiveness

**Considerations**:
- Search box should be full-width on mobile, max-width on desktop
- Results dropdown should respect viewport boundaries
- Consider click-outside-to-close behavior for dropdown
- Ensure proper z-index layering

**Responsive Design**:
```svelte
<div class="relative w-full">
  <!-- Search bar responsive sizing handled by parent card-body padding -->
</div>
```

---

### Phase 5: Testing

#### Backend Tests

**File**: `backend/tests/test_books.py`

Run:
```bash
pytest backend/tests/test_books.py::test_list_books_global_search_across_statuses -v
pytest backend/tests/test_books.py::test_list_books_global_search_by_author -v
pytest backend/tests/test_books.py::test_list_books_global_search_no_results -v
```

#### Frontend Manual Tests

**Test Cases**:

1. **Basic Search**
   - Type "python" → verify results appear
   - Verify debouncing (results don't fetch on every keystroke)
   - Verify books from different statuses appear

2. **Author Search**
   - Type author name → verify author matches work
   - Verify partial matches work (case-insensitive)

3. **Empty States**
   - Type nonsense query → verify "No books found" appears
   - Clear search box → verify dropdown disappears

4. **Loading State**
   - Slow network simulation → verify spinner shows
   - Verify loading doesn't block UI

5. **Navigation**
   - Click search result → verify navigation to correct library status tab
   - Verify book detail dialog opens automatically
   - Verify URL is cleaned after opening (bookId removed)

6. **Responsive**
   - Test on mobile viewport → verify dropdown doesn't overflow
   - Test on tablet/desktop → verify max-width constraint

7. **Accessibility**
   - Tab navigation through results
   - Enter key on result should navigate
   - Screen reader compatibility

8. **Edge Cases**
   - Book without author → verify layout doesn't break
   - Book without cover → verify placeholder shows
   - Very long title → verify truncation works
   - Many results (20+) → verify scroll works

#### Integration Tests (Optional Future Enhancement)

If Playwright tests are added later:

**File**: `tests/e2e/dashboard-search.spec.ts`

```typescript
test('dashboard search finds and navigates to book', async ({ page }) => {
  // Setup: Create books via API
  await createBook(page, { title: 'Test Python Book', reading_status: 'read' });
  
  // Navigate to dashboard
  await page.goto('/dashboard');
  
  // Type in search
  await page.fill('[placeholder*="Search all books"]', 'Python');
  
  // Wait for results
  await page.waitForSelector('role=option');
  
  // Click first result
  await page.click('role=option >> nth=0');
  
  // Verify navigation
  await expect(page).toHaveURL(/\/library\?status=read/);
  
  // Verify detail dialog opened
  await expect(page.locator('dialog[open]')).toBeVisible();
});
```

---

## Risk Analysis

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Slow search on large libraries (1000+ books) | Medium | - Backend already has user_id filtering<br>- Database index on user_id + title/author<br>- Frontend debouncing (300ms)<br>- Consider pagination if needed |
| Dropdown positioned incorrectly on edge cases | Low | - Use absolute positioning with proper parent container<br>- Test on various screen sizes |
| Navigation doesn't open detail dialog | Medium | - Implement URL param detection in library page<br>- Test thoroughly<br>- Fallback: Just navigate to tab (user can click again) |
| Search doesn't work if API endpoint changes | Low | - We're using existing stable endpoint<br>- API is already used by library page |
| i18n keys missing for some languages | Low | - Start with English and German<br>- Document keys for translators |

---

## Performance Considerations

### API Performance
- **Current**: `/api/books?q=query` fetches all matching books
- **Optimization (future)**: Add `limit` parameter to cap results at 50
- **Database**: Ensure index exists on `(user_id, title, author)`

### Frontend Performance
- **Debouncing**: 300ms prevents excessive API calls
- **Result Limit**: Display max 50 results (add scrolling if needed)
- **Image Loading**: Use lazy loading for cover images in results

---

## Implementation Order

1. ✅ **Phase 1**: Backend tests (verify existing API works as expected)
2. ✅ **Phase 2.1-2.2**: Build SearchResultItem and SearchResultsDropdown
3. ✅ **Phase 2.3**: Build DashboardSearchBox
4. ✅ **Phase 2.5**: Update Library page for deep linking
5. ✅ **Phase 2.4**: Integrate into Dashboard
6. ✅ **Phase 3**: Add i18n keys
7. ✅ **Phase 4**: Styling polish and responsive testing
8. ✅ **Phase 5**: Manual testing

---

## Definition of Done

- [ ] Backend tests pass for global search
- [ ] Search box appears on dashboard below hero
- [ ] Typing triggers debounced search
- [ ] Results show cover, title, author (if available), status badge
- [ ] Clicking result navigates to library and opens detail dialog
- [ ] Empty state shows "No books found"
- [ ] Loading state shows spinner
- [ ] Responsive on mobile and desktop
- [ ] All i18n keys added for English and German
- [ ] Manual test cases pass
- [ ] No console errors or warnings
- [ ] Code follows existing project conventions

---

## Future Enhancements (Out of Scope)

- Advanced filters (by status, rating, date range)
- Search result highlighting (matching text bold)
- Recent searches / search history
- Keyboard shortcuts (Cmd+K to focus search)
- Search by ISBN
- Fuzzy search / typo tolerance
- Search result pagination (if library grows very large)
- Analytics on popular searches

---

## Dependencies

### External Libraries
- None required (using existing Svelte, DaisyUI, svelte-i18n)

### Internal Dependencies
- `SearchBar.svelte` (already exists)
- `api.books.list()` (already exists)
- Status constants and labels (already exists in BookCard)

---

## File Summary

### Files to Create
1. `frontend/src/lib/components/SearchResultItem.svelte` - Individual result display
2. `frontend/src/lib/components/SearchResultsDropdown.svelte` - Results container
3. `frontend/src/lib/components/DashboardSearchBox.svelte` - Main search orchestrator

### Files to Modify
1. `frontend/src/routes/dashboard/+page.svelte` - Add search box
2. `frontend/src/routes/library/+page.svelte` - Support bookId URL param
3. `frontend/src/lib/i18n/locales/en.json` - Add search keys
4. `frontend/src/lib/i18n/locales/de.json` - Add German translations
5. `backend/tests/test_books.py` - Add global search tests

### Files to Review (No Changes)
- `frontend/src/lib/components/SearchBar.svelte` - Reused as-is
- `frontend/src/lib/components/BookCard.svelte` - Reference for styling
- `frontend/src/lib/api.ts` - Uses existing `books.list()` method
- `backend/app/routers/books.py` - No changes needed

---

## Open Questions

1. **Result Limit**: Should we cap results at 50? Or implement pagination?
   - **Recommendation**: Start with no cap, add limit later if performance degrades

2. **Click Outside Behavior**: Should dropdown close when clicking outside?
   - **Recommendation**: Yes, implement click-outside handler on dropdown

3. **Keyboard Shortcuts**: Should we add Cmd+K / Ctrl+K to focus search?
   - **Recommendation**: Out of scope for MVP, add as enhancement

4. **Search Scope**: Should we search notes/genre fields too?
   - **Recommendation**: No, keep it simple (title + author only)

---

## Acceptance Criteria

**User Story**: As a user, I want to quickly search my entire library from the dashboard so that I can find any book regardless of its reading status.

**Acceptance Criteria**:
1. ✅ Search box is visible on dashboard page
2. ✅ Typing in search box triggers debounced search (max 300ms delay)
3. ✅ Search returns books matching title OR author across all statuses
4. ✅ Results display in dropdown showing: cover, title, author, status
5. ✅ Books without author still display correctly (author section hidden)
6. ✅ Books without cover show placeholder icon
7. ✅ Clicking result navigates to library page on correct status tab
8. ✅ Book detail dialog opens automatically after navigation
9. ✅ Empty search shows no results
10. ✅ No matches shows "No books found" message
11. ✅ Loading state shows spinner
12. ✅ Responsive design works on mobile and desktop

---

## Notes

- This feature requires no backend changes - the API already supports cross-status search
- The implementation reuses existing components (SearchBar) and patterns (BookCard styling)
- Deep linking to library with bookId enables seamless navigation
- The architecture is extensible for future enhancements (filters, advanced search, etc.)
