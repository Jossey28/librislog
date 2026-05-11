# Plan: Mark Already-Imported Books in Import Search Results

## Overview

Add visual indicators to the Import Book tab's search results to show which books have already been imported into the local collection. This prevents duplicate imports (for books without ISBN) and provides better user awareness.

**Goal**: When a user searches for books in the Import tab, books that already exist in the local database should be visually marked (e.g., with a badge like "Already imported").

## Current State Analysis

### Backend
- **Import endpoint**: `/api/import` (POST) — checks ISBN duplicates and returns 409
- **Books endpoint**: `/api/books` (GET) — returns all books with filtering by status, search query, sort
- **Duplicate checking**: Only by ISBN (line 79-86 in `import_.py`), not by title/author combination
- Books without ISBN can be imported multiple times (as tested in `test_import_book_without_isbn_allows_duplicates`)

### Frontend
- **ImportSearch.svelte**: Displays search results from Open Library and Google Books
- **Search flow**:
  1. User enters query → `api.import.searchStream()` → SSE stream
  2. Results populate `results` array (`BookImportCandidate[]`)
  3. Each result shows: cover, title, author, source, year, "Add" button
- **No current duplicate detection** in the UI
- **Data available**: Local books are accessible via `api.books.list()`, but not currently checked against search results

### Data Flow

```
Search Results (BookImportCandidate)   Local Collection (Book)
├─ title                               ├─ id
├─ author                              ├─ title  
├─ isbn                                ├─ author
├─ publisher                           ├─ isbn
├─ published_year                      ├─ reading_status
└─ source                              └─ ... other fields
```

**Matching strategy needed**:
- **Primary**: ISBN (when available)
- **Secondary**: Normalized title + author (for books without ISBN)

## Problem Statement

Users searching for books to import cannot tell which books are already in their collection. This leads to:
1. Confusion when the backend rejects ISBN duplicates (409 error)
2. Accidental duplicate entries for books without ISBNs
3. Wasted time searching for books already imported
4. Poor user experience

## Requirements

### Functional
1. ✅ **Visual indicator** on search result cards showing "Already imported" status
2. ✅ **Disable "Add" button** for already-imported books
3. ✅ **Match by ISBN** (primary, exact match)
4. ✅ **Match by title + author** (secondary, normalized comparison for books without ISBN)
5. ✅ **Real-time checking** as search results stream in
6. ✅ **Performance**: No blocking UI during check (async, non-blocking)

### Non-Functional
- **Accuracy**: False positives are worse than false negatives (better to allow potential duplicate than block valid import)
- **Performance**: Matching should complete within 100ms for typical collections (< 1000 books)
- **UX**: Indicator should be visually clear but not intrusive

## Implementation Plan

### Phase 1: Backend — Add Check Endpoint (Optional Enhancement)

**Decision**: Start with **frontend-only** implementation (no backend changes needed).

**Rationale**:
- Frontend already has access to all books via `api.books.list()`
- Matching logic is simple and can run client-side
- Avoids backend complexity and deployment dependencies
- Can be enhanced later with backend endpoint if performance issues arise

**Future enhancement (Phase 2 — out of scope for initial implementation)**:
```python
# backend/app/routers/import_.py
@router.post("/check", response_model=List[str])
async def check_imported(
    candidates: List[BookImportCandidate],
    session: Session = Depends(get_session),
) -> List[str]:
    """Return ISBNs or title+author keys that already exist in the database."""
    imported_keys = []
    for c in candidates:
        if c.isbn:
            exists = session.exec(select(Book).where(Book.isbn == c.isbn)).first()
            if exists:
                imported_keys.append(c.isbn)
        else:
            # Fallback: check by normalized title + author
            normalized_title = c.title.strip().lower()
            normalized_author = (c.author or "").strip().lower()
            exists = session.exec(
                select(Book)
                .where(func.lower(Book.title) == normalized_title)
                .where(func.lower(Book.author) == normalized_author)
            ).first()
            if exists:
                imported_keys.append(f"{normalized_title}|{normalized_author}")
    return imported_keys
```

### Phase 2: Frontend — Client-Side Matching

#### Step 1: Fetch Local Books on Component Mount

**File**: `frontend/src/lib/components/ImportSearch.svelte`

**Changes**:
1. Add state to store local books:
```typescript
let localBooks = $state<Book[]>([]);
```

2. Add effect to fetch local books on mount:
```typescript
import { onMount } from 'svelte';

onMount(async () => {
    try {
        localBooks = await api.books.list();
    } catch (e) {
        console.error('Failed to fetch local books for duplicate check:', e);
        // Non-critical — continue without duplicate checking
    }
});
```

**Why `onMount`**: Ensures books are fetched once when the component loads, before any search is performed.

#### Step 2: Create Matching Function

**File**: `frontend/src/lib/components/ImportSearch.svelte`

**Add helper functions** (after the existing `candidateKey` function):

```typescript
function normalizeForMatch(value: string | null | undefined): string {
    return (value ?? '').trim().toLowerCase();
}

function isAlreadyImported(candidate: BookImportCandidate): boolean {
    // Primary match: ISBN
    if (candidate.isbn) {
        const normalizedIsbn = normalizeIsbn(candidate.isbn);
        return localBooks.some(book => 
            book.isbn && normalizeIsbn(book.isbn) === normalizedIsbn
        );
    }

    // Secondary match: title + author (for books without ISBN)
    // Require both title and author to avoid false positives
    if (!candidate.title || !candidate.author) {
        return false; // Cannot reliably match without both fields
    }

    const candidateTitle = normalizeForMatch(candidate.title);
    const candidateAuthor = normalizeForMatch(candidate.author);

    return localBooks.some(book => {
        const bookTitle = normalizeForMatch(book.title);
        const bookAuthor = normalizeForMatch(book.author);
        return bookTitle === candidateTitle && bookAuthor === candidateAuthor;
    });
}
```

**Matching strategy**:
- **ISBN match**: Exact match after removing dashes/spaces (most reliable)
- **Title + Author match**: Exact match after normalization (case-insensitive, trimmed)
- **Requires both fields**: Avoids false positives from common titles
- **No fuzzy matching**: Reduces complexity and false positives

#### Step 3: Update UI to Show Indicator

**File**: `frontend/src/lib/components/ImportSearch.svelte`

**Modify the result list item template** (lines 194-218):

```svelte
<ul class="flex flex-col gap-2 max-h-80 overflow-y-auto">
    {#each results as candidate}
        {@const key = candidate.isbn ?? candidate.title}
        {@const alreadyImported = isAlreadyImported(candidate)}
        <li class="flex gap-3 items-start p-2 rounded-lg border border-base-200 {alreadyImported ? 'bg-base-200/30' : ''}">
            {#if candidate.cover_url}
                <img src={candidate.cover_url} alt="Cover" class="w-10 rounded flex-shrink-0 object-cover" />
            {:else}
                <div class="w-10 h-14 bg-base-200 rounded flex-shrink-0"></div>
            {/if}
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <p class="font-medium text-sm line-clamp-2">{candidate.title}</p>
                    {#if alreadyImported}
                        <span class="badge badge-sm badge-outline badge-info">Already imported</span>
                    {/if}
                </div>
                {#if candidate.author}
                    <p class="text-xs text-base-content/60">{candidate.author}</p>
                {/if}
                <p class="text-xs text-base-content/40">{candidate.source}{candidate.published_year ? ` · ${candidate.published_year}` : ''}</p>
            </div>
            <div class="flex flex-col gap-1">
                <button
                    class="btn btn-xs btn-primary"
                    disabled={importing === key || alreadyImported}
                    onclick={() => importBook(candidate, 'want_to_read')}
                    title={alreadyImported ? 'This book is already in your collection' : 'Add to Want to Read'}
                >
                    {#if alreadyImported}
                        <span class="text-base-content/50">✓ Imported</span>
                    {:else}
                        {importing === key ? '…' : 'Add'}
                    {/if}
                </button>
            </div>
        </li>
    {/each}
</ul>
```

**UI changes**:
1. **Background tint**: `bg-base-200/30` for already-imported items (subtle visual cue)
2. **Badge**: "Already imported" badge next to title (DaisyUI `badge` component)
3. **Disabled button**: Button shows "✓ Imported" and is disabled
4. **Tooltip**: `title` attribute explains why button is disabled

#### Step 4: Update Local Books After Import

**File**: `frontend/src/lib/components/ImportSearch.svelte`

**Modify `importBook()` function** to update `localBooks` after successful import:

```typescript
async function importBook(candidate: BookImportCandidate, status: ReadingStatus) {
    const key = candidate.isbn ?? candidate.title;
    importing = key;
    try {
        const book = await api.import.importBook(candidate, status);
        // Update local books cache to reflect new import
        localBooks = [...localBooks, book];
        onImport?.(book);
    } catch (e: unknown) {
        toasts.add(e instanceof Error ? e.message : 'Import failed', 'error');
    } finally {
        importing = null;
    }
}
```

**Why**: Ensures newly imported books are immediately reflected in the duplicate check without requiring a component remount.

### Phase 3: Handle Edge Cases

#### Edge Case 1: User Deletes Book in Another Tab

**Problem**: `localBooks` becomes stale if user deletes a book in the main book list while the Import tab is open.

**Solution (Future Enhancement)**: 
- Implement event emitter or store to sync state across components
- For now: **Accept limitation** — user can close/reopen Import modal to refresh

**Mitigation**: 
- Add comment in code documenting this limitation
- Can be addressed in future with Svelte stores or cross-tab sync (out of scope)

#### Edge Case 2: Books with Same Title but Different Authors

**Current behavior**: ✅ Handled correctly — matching requires **both** title and author to match.

**Example**:
- Local book: "Foundation" by Isaac Asimov
- Search result: "Foundation" by Mike Vick
- Result: NOT marked as duplicate ✅

#### Edge Case 3: Books with ISBN vs. Books without ISBN

**Scenario**: 
- Local book: "Dune" (no ISBN)
- Search result: "Dune" by Frank Herbert (ISBN: 9780441013593)

**Current behavior**: 
- Search result will match by title+author → marked as duplicate
- Backend allows import (no ISBN conflict) → 409 error won't occur
- User tries to import → **succeeds** because ISBN is different

**Issue**: This creates a duplicate entry in the database.

**Solution**: **Accept as working-as-intended** — the backend allows this, and the duplicate check should reflect backend behavior. If backend allows ISBN books as duplicates of non-ISBN books, UI should not block it.

**Alternative (Stricter Matching)**:
- Enhance backend to check title+author when ISBN is present but no matching ISBN book exists
- Out of scope for this phase

#### Edge Case 4: Partial Matches (Typos, Different Editions)

**Problem**: 
- Local book: "The Lord of the Rings: The Fellowship of the Ring"
- Search result: "Fellowship of the Ring"
- User may expect these to match

**Solution**: **Do not implement fuzzy matching** in initial version.

**Rationale**:
- False positives are worse than false negatives
- User can manually check if unsure
- Fuzzy matching adds significant complexity (Levenshtein distance, thresholds, etc.)
- Can be added as future enhancement if user feedback indicates need

#### Edge Case 5: Large Collections (Performance)

**Scenario**: User has 5000+ books, matching takes too long.

**Measurement**: 
- Benchmark: 5000 books × 10 search results = 50,000 string comparisons
- Estimated time: ~10ms on modern hardware (JavaScript string operations are fast)

**Mitigation**:
- Frontend matching is fast enough for typical use cases (< 2000 books)
- If performance issues arise, implement backend endpoint (Phase 1 alternative)
- Consider caching normalized values in a Set for O(1) lookup

**Optimization (if needed)**:
```typescript
// Build lookup sets on mount for O(1) matching
let isbnSet = $state<Set<string>>(new Set());
let titleAuthorSet = $state<Set<string>>(new Set());

onMount(async () => {
    localBooks = await api.books.list();
    isbnSet = new Set(
        localBooks
            .filter(b => b.isbn)
            .map(b => normalizeIsbn(b.isbn!))
    );
    titleAuthorSet = new Set(
        localBooks
            .filter(b => b.author)
            .map(b => `${normalizeForMatch(b.title)}|${normalizeForMatch(b.author)}`)
    );
});

function isAlreadyImported(candidate: BookImportCandidate): boolean {
    if (candidate.isbn && isbnSet.has(normalizeIsbn(candidate.isbn))) {
        return true;
    }
    if (candidate.author) {
        const key = `${normalizeForMatch(candidate.title)}|${normalizeForMatch(candidate.author)}`;
        return titleAuthorSet.has(key);
    }
    return false;
}
```

**Decision**: Implement optimized version from the start (negligible complexity increase, future-proof).

## Testing Plan

### Backend Tests

**File**: `backend/tests/test_import.py`

**No new backend tests needed** for Phase 1 (frontend-only implementation).

**If Phase 2 backend endpoint is implemented**, add:

```python
def test_check_imported_by_isbn(client: TestClient):
    """POST /api/import/check should return ISBNs of already-imported books."""
    # Create book with ISBN
    client.post("/api/books", json={"title": "Dune", "isbn": "9780441013593"})
    
    # Check candidates
    payload = [
        {"title": "Dune", "isbn": "9780441013593", "source": "open_library"},
        {"title": "Foundation", "isbn": "9780553293357", "source": "google_books"},
    ]
    resp = client.post("/api/import/check", json=payload)
    assert resp.status_code == 200
    assert resp.json() == ["9780441013593"]


def test_check_imported_by_title_author(client: TestClient):
    """POST /api/import/check should match by title+author for books without ISBN."""
    client.post("/api/books", json={"title": "Unknown Book", "author": "John Doe"})
    
    payload = [
        {"title": "Unknown Book", "author": "John Doe", "source": "open_library"},
        {"title": "Unknown Book", "author": "Jane Smith", "source": "open_library"},
    ]
    resp = client.post("/api/import/check", json=payload)
    assert resp.status_code == 200
    assert resp.json() == ["unknown book|john doe"]


def test_check_imported_normalizes_isbn(client: TestClient):
    """ISBN matching should ignore dashes and spaces."""
    client.post("/api/books", json={"title": "Test", "isbn": "978-0-441-01359-3"})
    
    payload = [{"title": "Test", "isbn": "9780441013593", "source": "open_library"}]
    resp = client.post("/api/import/check", json=payload)
    assert resp.json() == ["9780441013593"]
```

### Frontend Tests

#### Manual Testing Checklist

Since no frontend test infrastructure exists, perform manual testing:

1. **✅ Test: Books with ISBN are matched**
   - Add a book manually with ISBN (e.g., "9780441013593")
   - Open Import tab
   - Search for the same ISBN
   - **Expected**: Result shows "Already imported" badge, button disabled

2. **✅ Test: Books without ISBN are matched by title+author**
   - Add a book manually without ISBN (title: "Unknown", author: "Test Author")
   - Open Import tab
   - Search for a similar book with matching title and author
   - **Expected**: Result shows "Already imported" badge

3. **✅ Test: Books with same title but different authors are NOT matched**
   - Add "Foundation" by "Isaac Asimov"
   - Search for "Foundation" by "Mike Vick" (different author)
   - **Expected**: Result does NOT show "Already imported" badge

4. **✅ Test: Books with partial title matches are NOT matched**
   - Add "The Lord of the Rings"
   - Search for "Lord of the Rings" (no "The")
   - **Expected**: Result does NOT show "Already imported" badge (exact match only)

5. **✅ Test: Newly imported books are immediately marked**
   - Open Import tab
   - Search for "Dune"
   - Click "Add" on a result
   - Search for "Dune" again (or scroll to see the same result)
   - **Expected**: Just-imported book now shows "Already imported" badge

6. **✅ Test: Disabled button has tooltip**
   - Find an already-imported book in search results
   - Hover over the disabled button
   - **Expected**: Tooltip appears saying "This book is already in your collection"

7. **✅ Test: Performance with large collection**
   - (Optional, if feasible) Add 100+ books to the collection
   - Perform search in Import tab
   - **Expected**: Results appear without noticeable lag (< 200ms)

8. **✅ Test: ISBN normalization**
   - Add book with ISBN "978-0-441-01359-3" (with dashes)
   - Search for ISBN "9780441013593" (without dashes)
   - **Expected**: Result is matched correctly

9. **✅ Test: Case-insensitive matching**
   - Add book "dune" by "frank herbert" (lowercase)
   - Search for "Dune" by "Frank Herbert" (title case)
   - **Expected**: Result is matched correctly

10. **✅ Test: Empty results**
    - Search for a nonsense query that returns no results
    - **Expected**: No errors, empty state message displayed

#### Integration Tests (Future — Using Playwright)

**File**: `frontend/tests/import-duplicate-detection.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Import Duplicate Detection', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        // Add a book first
        await page.click('text=+ Add Book');
        await page.fill('input[name="title"]', 'Dune');
        await page.fill('input[name="author"]', 'Frank Herbert');
        await page.fill('input[name="isbn"]', '9780441013593');
        await page.click('button:has-text("Add Book")');
        await page.waitForSelector('text=Dune');
    });

    test('should mark already-imported books in search results', async ({ page }) => {
        // Open Import tab
        await page.click('text=Import Book');
        
        // Search for the same book
        await page.fill('input[placeholder*="Search"]', 'Dune');
        await page.selectOption('select', 'isbn');
        await page.click('button:has-text("Search")');
        
        // Wait for results
        await page.waitForSelector('text=Already imported');
        
        // Verify badge is present
        const badge = page.locator('text=Already imported');
        await expect(badge).toBeVisible();
        
        // Verify button is disabled
        const addButton = page.locator('button:has-text("✓ Imported")');
        await expect(addButton).toBeDisabled();
    });

    test('should allow importing books not in collection', async ({ page }) => {
        await page.click('text=Import Book');
        await page.fill('input[placeholder*="Search"]', 'Foundation');
        await page.click('button:has-text("Search")');
        
        // Wait for results (assuming Foundation is NOT in collection)
        await page.waitForSelector('button:has-text("Add")');
        
        // Verify no "Already imported" badge
        const badge = page.locator('text=Already imported');
        await expect(badge).not.toBeVisible();
        
        // Verify button is enabled
        const addButton = page.locator('button:has-text("Add")').first();
        await expect(addButton).toBeEnabled();
    });

    test('should update indicator after import', async ({ page }) => {
        await page.click('text=Import Book');
        await page.fill('input[placeholder*="Search"]', 'Foundation');
        await page.click('button:has-text("Search")');
        
        // Import the first result
        await page.locator('button:has-text("Add")').first().click();
        await page.waitForTimeout(500); // Wait for import to complete
        
        // Search again
        await page.fill('input[placeholder*="Search"]', '');
        await page.fill('input[placeholder*="Search"]', 'Foundation');
        await page.click('button:has-text("Search")');
        
        // Now it should be marked as imported
        await expect(page.locator('text=Already imported').first()).toBeVisible();
    });
});
```

## Implementation Steps

### Step 1: Add Local Books State and Fetch Logic
**File**: `frontend/src/lib/components/ImportSearch.svelte`
**Estimated time**: 15 minutes

1. Import `onMount` and `Book` type
2. Add `localBooks`, `isbnSet`, `titleAuthorSet` state variables
3. Add `onMount` effect to fetch books and build lookup sets

### Step 2: Add Matching Functions
**File**: `frontend/src/lib/components/ImportSearch.svelte`
**Estimated time**: 20 minutes

1. Add `normalizeForMatch()` helper
2. Add `isAlreadyImported()` function using Set lookups

### Step 3: Update UI Template
**File**: `frontend/src/lib/components/ImportSearch.svelte`
**Estimated time**: 25 minutes

1. Add `{@const alreadyImported = isAlreadyImported(candidate)}`
2. Add background tint styling
3. Add "Already imported" badge
4. Modify button to show "✓ Imported" when disabled
5. Add `title` tooltip
6. Add `disabled={... || alreadyImported}`

### Step 4: Update `importBook()` to Sync State
**File**: `frontend/src/lib/components/ImportSearch.svelte`
**Estimated time**: 10 minutes

1. After successful import, add book to `localBooks`
2. Update `isbnSet` and `titleAuthorSet` if applicable

### Step 5: Manual Testing
**Estimated time**: 45 minutes

Run through all manual test cases documented above.

### Step 6: Documentation
**Estimated time**: 15 minutes

Add inline comments explaining:
- Matching strategy
- Performance optimization with Sets
- Known limitations (cross-tab sync)

## Success Criteria

1. ✅ Books with matching ISBNs show "Already imported" badge
2. ✅ Books with matching title+author (no ISBN) show "Already imported" badge
3. ✅ "Add" button is disabled for already-imported books
4. ✅ Button shows "✓ Imported" text when disabled
5. ✅ Hover tooltip explains why button is disabled
6. ✅ Newly imported books are immediately reflected in duplicate check
7. ✅ Exact match only (no false positives from partial matches)
8. ✅ Case-insensitive matching works correctly
9. ✅ ISBN normalization (dashes/spaces) works correctly
10. ✅ Performance is acceptable for collections up to 2000 books

## Edge Cases Summary

| Scenario | Behavior | Status |
|----------|----------|--------|
| Book with ISBN already exists | Marked as imported ✓ | ✅ Handled |
| Book without ISBN, matching title+author | Marked as imported ✓ | ✅ Handled |
| Same title, different authors | NOT marked (correct) | ✅ Handled |
| Partial title match | NOT marked (exact only) | ✅ By design |
| User deletes book in another tab | Stale until component remount | ⚠️ Known limitation |
| Large collection (2000+ books) | Optimized with Set lookups | ✅ Handled |
| ISBN with dashes vs. without | Normalized before comparison | ✅ Handled |
| Case variations | Normalized to lowercase | ✅ Handled |

## Future Enhancements

1. **Backend endpoint for duplicate checking** (if performance issues arise)
2. **Cross-component state sync** (Svelte stores or event emitter)
3. **Fuzzy matching** (Levenshtein distance for typos, configurable threshold)
4. **Show duplicate book details** (clicking badge could show the existing book)
5. **Alternative match levels**: "Exact match", "Possible match", "New book"
6. **ISBN-10 vs ISBN-13 matching** (convert ISBN-10 to ISBN-13 for comparison)
7. **Multi-language title matching** (e.g., "The Hobbit" vs. "El Hobbit")

## Dependencies

**No new dependencies required.**

Uses existing:
- Svelte 5 runes (`$state`, `onMount`)
- DaisyUI badge component (already in use)
- Existing API client (`api.books.list()`)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| False positives (blocking valid imports) | Low | High | Use exact matching only, require both title+author |
| False negatives (missing duplicates) | Medium | Low | Acceptable — user can manually check |
| Performance with large collections | Low | Medium | Use Set lookups (O(1) instead of O(n)) |
| Stale state (cross-tab edits) | Medium | Low | Document limitation, can be enhanced later |
| ISBN-10 vs ISBN-13 mismatch | Low | Low | Normalize both to 13 digits if needed (future) |

## Rollback Plan

If issues arise:
1. Remove duplicate checking logic (keep UI unchanged)
2. Remove `onMount` effect and `localBooks` state
3. Remove `{@const alreadyImported}` and related UI changes
4. Restore original button behavior

**Rollback complexity**: Low — all changes are localized to one component.

## Implementation Estimate

- **Step 1-4 (Code)**: 1.5 hours
- **Step 5 (Testing)**: 45 minutes
- **Step 6 (Documentation)**: 15 minutes
- **Total**: ~2.5 hours

## Documentation Updates

After implementation:
- Add entry to `.plan/05-milestones.md` (if tracking features)
- Update `README.md` with note about duplicate detection in Import tab
- Add inline code comments explaining matching logic

## Conclusion

This implementation provides reliable duplicate detection using a **client-side, exact-match strategy** with **optimized Set-based lookups**. The approach balances accuracy (no false positives), performance (O(1) lookups), and simplicity (no backend changes required). Future enhancements can address fuzzy matching and cross-tab synchronization if user feedback indicates need.
