# Plan: Automatic List View Updates on Book Add/Delete

## Overview

Implement automatic, real-time updates to the book list view when books are added or deleted, ensuring the UI stays synchronized with backend state without requiring manual refreshes.

**Goal**: When a user adds or deletes a book, the list view should immediately reflect these changes across all reading status tabs.

## Current State Analysis

### Frontend (Svelte 5)
- **File**: `frontend/src/routes/+page.svelte`
- Uses Svelte 5 runes (`$state`, `$derived`, `$effect`)
- Already has reactive state management for `books` array
- Has `handleAdded()` and `handleDelete()` functions that update local state
- Uses `$effect()` to re-fetch when filters change (status, search, sort)

### Current Behavior
✅ **Already working for same-tab operations**:
- When adding a book via `AddBookModal`, `handleAdded()` adds it to the local `books` array
- When deleting via `BookDrawer`, `handleDelete()` filters it from the local `books` array
- Updates are immediate and don't require re-fetching

### Identified Issues
1. **Cross-tab synchronization**: Changes in one browser tab don't reflect in others
2. **Status filter edge case**: When adding a book with a different status than the active tab, it correctly doesn't show (working as intended)
3. **No optimistic updates on save**: When updating a book's status in the drawer, it moves the book between lists, but only via the `handleSave()` callback

## Problem Statement

The current implementation already provides automatic updates within a single page/tab context. However:
- Multi-tab scenarios are not handled (if user has multiple browser tabs open)
- No real-time collaboration (multiple users viewing the same data)
- Updates rely on local state manipulation, which could diverge from backend truth

## Implementation Plan

### Phase 1: Enhanced Local Reactivity (Already Mostly Complete)

**Status**: ✅ Current implementation already handles this well

The existing code already implements proper local reactivity:
```typescript
function handleAdded(book: Book) {
    if (book.reading_status === activeStatus) {
        books = [book, ...books];
    }
    addBookOpen = false;
}

function handleDelete(id: number) {
    books = books.filter((b) => b.id !== id);
}
```

**Potential Enhancement**: Add status change detection in `handleSave()`
- Currently, when a book's status changes, it stays in the list until a refresh
- Should remove it from the list if its status no longer matches `activeStatus`

### Phase 2: Implement Smart Re-fetching After Mutations

**Approach**: Trigger a re-fetch after successful add/delete operations to ensure backend state synchronization.

#### Changes to `+page.svelte`

1. **Enhance `handleAdded()`**:
```typescript
function handleAdded(book: Book) {
    // Optimistic update for immediate feedback
    if (book.reading_status === activeStatus) {
        books = [book, ...books];
    }
    addBookOpen = false;
    // Re-fetch to ensure backend sync (handles sort order, etc.)
    fetchBooks();
}
```

2. **Enhance `handleDelete()`**:
```typescript
function handleDelete(id: number) {
    // Optimistic update
    books = books.filter((b) => b.id !== id);
    // Re-fetch to ensure backend sync
    fetchBooks();
}
```

3. **Enhance `handleSave()`**:
```typescript
function handleSave(updated: Book) {
    // If status changed and no longer matches activeStatus, remove from list
    if (updated.reading_status !== activeStatus) {
        books = books.filter((b) => b.id !== updated.id);
    } else {
        // Update in place
        books = books.map((b) => (b.id === updated.id ? updated : b));
    }
    // Re-fetch to ensure backend sync and correct sort order
    fetchBooks();
}
```

**Rationale**:
- Optimistic updates provide immediate UI feedback (good UX)
- Re-fetching ensures consistency with backend (correctness)
- Handles edge cases like sort order changes after rating updates

### Phase 3: Add Loading States and Debouncing

**Problem**: Multiple rapid operations could trigger many re-fetches

**Solution**: Add mutation tracking and debounce re-fetch calls

#### Implementation

1. **Add mutation state tracking**:
```typescript
let mutating = $state(false);
```

2. **Debounce fetchBooks** (optional, for rapid operations):
```typescript
import { debounce } from '$lib/utils'; // utility function to implement

const debouncedFetch = debounce(fetchBooks, 300);
```

3. **Update handlers to use debounced fetch**:
```typescript
function handleDelete(id: number) {
    books = books.filter((b) => b.id !== id);
    debouncedFetch();
}
```

**Note**: This phase is optional and should be implemented if performance issues are observed.

### Phase 4 (Future): WebSocket/SSE for Multi-Tab Sync

**Not included in current scope**, but documented for future enhancement:

- Implement Server-Sent Events (SSE) or WebSocket connection
- Backend broadcasts book mutations to all connected clients
- Frontend subscribes to events and updates local state
- Requires backend changes to FastAPI (add SSE endpoint)

**Estimated effort**: Medium (2-3 days)
**Priority**: Low (nice-to-have for multi-user scenarios)

## Testing Plan

### Backend Tests (pytest)

**File**: `backend/tests/test_books.py`

The existing test suite already covers the API endpoints comprehensively. No backend changes are required for Phase 1-3, so no new backend tests are needed.

**If Phase 4 is implemented**, add tests for:
- SSE endpoint connectivity
- Event broadcasting on create/update/delete
- Event payload validation

### Frontend Tests

**Current State**: No frontend test suite exists (no Vitest/Jest configuration in `package.json`)

**Recommendation**: Add frontend testing infrastructure

#### Setup Required

1. **Install test dependencies**:
```bash
cd frontend
npm install -D vitest @testing-library/svelte @testing-library/jest-dom
```

2. **Create `vitest.config.ts`**:
```typescript
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
```

3. **Add test script to `package.json`**:
```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui"
  }
}
```

#### Test Cases to Implement

**File**: `frontend/src/routes/+page.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import Page from './+page.svelte';
import { api } from '$lib/api';

// Mock the API
vi.mock('$lib/api', () => ({
  api: {
    books: {
      list: vi.fn(),
      create: vi.fn(),
      delete: vi.fn(),
      update: vi.fn(),
    }
  }
}));

describe('Book List Auto-Update', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should add new book to list when added with matching status', async () => {
    // Arrange
    const mockBooks = [
      { id: 1, title: 'Existing Book', reading_status: 'want_to_read' }
    ];
    vi.mocked(api.books.list).mockResolvedValue(mockBooks);

    const newBook = {
      id: 2,
      title: 'New Book',
      reading_status: 'want_to_read'
    };
    vi.mocked(api.books.create).mockResolvedValue(newBook);

    // Act
    const { component } = render(Page);
    await waitFor(() => expect(screen.getByText('Existing Book')).toBeInTheDocument());

    // Simulate adding a book
    // (This would involve opening modal and submitting, simplified here)
    // component.$set({ addBookOpen: true });
    // ... trigger handleAdded with newBook

    // Assert
    await waitFor(() => {
      expect(screen.getByText('New Book')).toBeInTheDocument();
    });
  });

  it('should remove book from list when deleted', async () => {
    // Arrange
    const mockBooks = [
      { id: 1, title: 'Book to Delete', reading_status: 'want_to_read' },
      { id: 2, title: 'Book to Keep', reading_status: 'want_to_read' }
    ];
    vi.mocked(api.books.list).mockResolvedValue(mockBooks);
    vi.mocked(api.books.delete).mockResolvedValue(undefined);

    // Act
    render(Page);
    await waitFor(() => expect(screen.getByText('Book to Delete')).toBeInTheDocument());

    // Simulate delete
    // component.handleDelete(1);

    // Assert
    await waitFor(() => {
      expect(screen.queryByText('Book to Delete')).not.toBeInTheDocument();
      expect(screen.getByText('Book to Keep')).toBeInTheDocument();
    });
  });

  it('should remove book from list when status changes to different category', async () => {
    // Arrange
    const mockBooks = [
      { id: 1, title: 'Want to Read Book', reading_status: 'want_to_read' }
    ];
    vi.mocked(api.books.list).mockResolvedValue(mockBooks);

    const updatedBook = {
      id: 1,
      title: 'Want to Read Book',
      reading_status: 'currently_reading'
    };
    vi.mocked(api.books.update).mockResolvedValue(updatedBook);

    // Act
    render(Page);
    await waitFor(() => expect(screen.getByText('Want to Read Book')).toBeInTheDocument());

    // Simulate status change via handleSave
    // component.handleSave(updatedBook);

    // Assert
    await waitFor(() => {
      expect(screen.queryByText('Want to Read Book')).not.toBeInTheDocument();
    });
  });

  it('should re-fetch books after add operation', async () => {
    // Arrange
    vi.mocked(api.books.list).mockResolvedValue([]);
    const newBook = { id: 1, title: 'New Book', reading_status: 'want_to_read' };
    vi.mocked(api.books.create).mockResolvedValue(newBook);

    // Act
    const { component } = render(Page);

    // Trigger handleAdded
    // component.handleAdded(newBook);

    // Assert
    await waitFor(() => {
      // Expect api.books.list to be called at least twice:
      // once on mount, once after handleAdded
      expect(api.books.list).toHaveBeenCalledTimes(2);
    });
  });

  it('should re-fetch books after delete operation', async () => {
    // Arrange
    const mockBooks = [{ id: 1, title: 'Book', reading_status: 'want_to_read' }];
    vi.mocked(api.books.list).mockResolvedValue(mockBooks);

    // Act
    const { component } = render(Page);
    await waitFor(() => expect(api.books.list).toHaveBeenCalledTimes(1));

    // Trigger handleDelete
    // component.handleDelete(1);

    // Assert
    await waitFor(() => {
      expect(api.books.list).toHaveBeenCalledTimes(2);
    });
  });

  it('should not add book to list when status does not match active tab', async () => {
    // Arrange
    vi.mocked(api.books.list).mockResolvedValue([]);

    const newBook = {
      id: 1,
      title: 'Different Status Book',
      reading_status: 'read' // Active status is 'want_to_read'
    };

    // Act
    render(Page);

    // Trigger handleAdded with mismatched status
    // component.handleAdded(newBook);

    // Assert
    expect(screen.queryByText('Different Status Book')).not.toBeInTheDocument();
  });
});
```

**Note**: The above tests are **conceptual** because:
1. Svelte 5 with runes is very new, and testing library support may be limited
2. Testing component methods directly may require different approaches in Svelte 5
3. May need to use `component.$$.ctx` or similar internal access (not recommended in production)

**Alternative Testing Strategy**:
- Focus on **integration tests** using Playwright or Cypress
- Test the full user flow: open modal → add book → verify it appears in list
- More robust and doesn't depend on component internals

### Integration Tests (Playwright)

**Recommended approach** for testing the automatic update behavior.

**File**: `frontend/tests/book-list-updates.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Book List Auto-Updates', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should show newly added book in the list', async ({ page }) => {
    // Arrange: Navigate to "Want to Read" tab
    await page.click('text=Want to Read');

    // Act: Add a new book
    await page.click('text=+ Add Book');
    await page.fill('input[placeholder="Title"]', 'Test Book');
    await page.click('button:has-text("Add Book")');

    // Assert: Book appears in the list
    await expect(page.locator('text=Test Book')).toBeVisible();
  });

  test('should remove deleted book from the list', async ({ page }) => {
    // Arrange: Add a book first
    await page.click('text=+ Add Book');
    await page.fill('input[placeholder="Title"]', 'Book to Delete');
    await page.click('button:has-text("Add Book")');
    await expect(page.locator('text=Book to Delete')).toBeVisible();

    // Act: Open book drawer and delete
    await page.click('text=Book to Delete');
    await page.click('button:has-text("Delete")');
    await page.click('button:has-text("Confirm?")');

    // Assert: Book is removed from list
    await expect(page.locator('text=Book to Delete')).not.toBeVisible();
  });

  test('should remove book when status changes to different category', async ({ page }) => {
    // Arrange: Add book to "Want to Read"
    await page.click('text=+ Add Book');
    await page.fill('input[placeholder="Title"]', 'Status Change Book');
    await page.selectOption('select', 'want_to_read');
    await page.click('button:has-text("Add Book")');
    await expect(page.locator('text=Status Change Book')).toBeVisible();

    // Act: Change status to "Currently Reading"
    await page.click('text=Status Change Book');
    await page.selectOption('select[name="status"]', 'currently_reading');
    await page.click('button:has-text("Save")');

    // Assert: Book is removed from "Want to Read" list
    await expect(page.locator('text=Status Change Book')).not.toBeVisible();

    // Verify it appears in "Currently Reading" tab
    await page.click('text=Currently Reading');
    await expect(page.locator('text=Status Change Book')).toBeVisible();
  });

  test('should maintain sort order after adding book', async ({ page }) => {
    // Arrange: Add multiple books with different dates
    const books = ['Book A', 'Book B', 'Book C'];
    for (const title of books) {
      await page.click('text=+ Add Book');
      await page.fill('input[placeholder="Title"]', title);
      await page.click('button:has-text("Add Book")');
      await page.waitForTimeout(100); // Ensure different timestamps
    }

    // Act: Verify sort order (newest first by default)
    const bookElements = await page.locator('.book-card').allTextContents();

    // Assert: Books are in reverse order (C, B, A)
    expect(bookElements).toContain('Book C');
    expect(bookElements.indexOf('Book C')).toBeLessThan(bookElements.indexOf('Book B'));
    expect(bookElements.indexOf('Book B')).toBeLessThan(bookElements.indexOf('Book A'));
  });
});
```

## Implementation Steps

### Step 1: Enhance `handleSave()` for Status Changes
**File**: `frontend/src/routes/+page.svelte`

**Change**:
```typescript
function handleSave(updated: Book) {
    // Remove from list if status no longer matches
    if (updated.reading_status !== activeStatus) {
        books = books.filter((b) => b.id !== updated.id);
    } else {
        books = books.map((b) => (b.id === updated.id ? updated : b));
    }
    // Re-fetch to sync with backend (handles sort order, etc.)
    fetchBooks();
}
```

**Why**: Ensures books disappear from the current list when moved to a different reading status.

### Step 2: Add Re-fetch to `handleAdded()` and `handleDelete()`
**File**: `frontend/src/routes/+page.svelte`

**Changes**:
```typescript
function handleAdded(book: Book) {
    if (book.reading_status === activeStatus) {
        books = [book, ...books];
    }
    addBookOpen = false;
    fetchBooks(); // Ensure backend sync
}

function handleDelete(id: number) {
    books = books.filter((b) => b.id !== id);
    fetchBooks(); // Ensure backend sync
}
```

**Why**: 
- Provides optimistic updates (immediate UI feedback)
- Follows up with authoritative backend data (correctness)
- Handles edge cases like sort order after rating changes

### Step 3: Test Manual Verification (No Test Suite Yet)

Since there's no frontend test suite, perform manual testing:

1. **Add Book Test**:
   - Open "Want to Read" tab
   - Click "+ Add Book"
   - Fill in title and submit
   - Verify book appears in the list immediately
   - Refresh page and verify book is still there

2. **Delete Book Test**:
   - Click on a book to open drawer
   - Click "Delete" → "Confirm?"
   - Verify book disappears from list immediately
   - Refresh page and verify book is gone

3. **Status Change Test**:
   - Open a book in "Want to Read"
   - Change status to "Currently Reading"
   - Click "Save"
   - Verify book disappears from "Want to Read" list
   - Navigate to "Currently Reading" tab
   - Verify book appears there

4. **Sort Order Test**:
   - Add multiple books
   - Add one with a 5-star rating
   - Switch sort to "Rating" descending
   - Verify 5-star book appears first

### Step 4 (Optional): Set Up Frontend Test Infrastructure

**If time permits**, add testing infrastructure:

1. Install Playwright:
```bash
cd frontend
npm install -D @playwright/test
npx playwright install
```

2. Create `playwright.config.ts`:
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:5173',
  },
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: true,
  },
});
```

3. Add test script to `package.json`:
```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

4. Implement integration tests from the test plan above

## Edge Cases and Considerations

### 1. Race Conditions
**Scenario**: User rapidly adds/deletes books before re-fetch completes

**Mitigation**: 
- Optimistic updates prevent UI blocking
- Re-fetch uses latest backend state
- Svelte's reactivity ensures UI updates correctly

### 2. Network Failures
**Scenario**: Re-fetch fails due to network issues

**Current behavior**: 
- Optimistic update succeeds (UI looks correct)
- Re-fetch silently fails
- User sees stale data

**Potential improvement**: 
- Add error handling to `fetchBooks()`
- Show toast notification on failure
- Retry logic with exponential backoff

### 3. Concurrent Multi-User Edits
**Scenario**: Two users edit the same book simultaneously

**Current behavior**: 
- Last write wins (backend behavior)
- No conflict detection
- No multi-tab sync

**Future improvement**: 
- Implement Phase 4 (WebSocket/SSE)
- Add optimistic locking or version numbers

### 4. Performance with Large Lists
**Scenario**: User has 1000+ books

**Current behavior**: 
- Re-fetching entire list on every mutation
- Could be slow

**Mitigation**: 
- Backend pagination (not yet implemented)
- Virtual scrolling (e.g., `svelte-virtual`)
- Debounced re-fetch (Phase 3)

### 5. Filter State Preservation
**Scenario**: User has search query active, adds book that doesn't match

**Current behavior**: 
- `handleAdded()` adds book to local array
- Re-fetch applies search filter
- Book might not appear in list

**Expected behavior**: ✅ Working correctly
- Search filter should be respected
- Book only appears if it matches current filters

## Success Criteria

1. ✅ Adding a book shows it in the list immediately (if status matches)
2. ✅ Deleting a book removes it from the list immediately
3. ✅ Changing a book's status removes it from the current list
4. ✅ List maintains correct sort order after mutations
5. ✅ Search/filter state is preserved after mutations
6. ✅ No manual refresh required
7. ✅ Backend state is the source of truth (re-fetch ensures sync)

## Implementation Estimate

- **Step 1-2**: 30 minutes (code changes)
- **Step 3**: 30 minutes (manual testing)
- **Step 4** (optional): 2-3 hours (test infrastructure setup)
- **Total**: 1 hour (without test infrastructure), 4 hours (with tests)

## Dependencies

- No new dependencies required for Phase 1-3
- Optional: Playwright (for integration tests)

## Rollback Plan

If issues arise:
1. Remove `fetchBooks()` calls from handlers
2. Revert to pure optimistic updates
3. Users will need to refresh manually for backend sync

The changes are minimal and low-risk, so rollback is straightforward.

## Future Enhancements

1. **Real-time multi-tab sync** (WebSocket/SSE)
2. **Optimistic locking** (prevent concurrent edit conflicts)
3. **Pagination** (for large book collections)
4. **Infinite scroll** (better UX for large lists)
5. **Undo/redo** (for accidental deletes)
6. **Bulk operations** (add/delete multiple books)

## Documentation Updates

After implementation, update:
- **README.md**: Add note about automatic list updates
- **ARCHITECTURE.md** (if exists): Document reactivity strategy
- **User Guide** (if exists): No manual refresh needed

## Conclusion

The current implementation already handles automatic list updates well for single-tab usage through Svelte 5's reactive state management. The proposed enhancements (adding re-fetch calls after mutations) will ensure backend synchronization and handle edge cases like sort order changes, making the system more robust without adding significant complexity.
