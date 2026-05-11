# Implementation Plan: Status-Specific Sorting & Automatic Date Management

## Overview

This plan implements status-aware sorting for book lists and automatic date field management based on status transitions. Each reading status category will sort by its most relevant date field, and date fields will be automatically set when books transition between statuses.

## Problem Statement

Currently, all status views (want to read, reading, read, did not finish) sort by `date_added`, which doesn't reflect the most relevant chronology for each category. Additionally, `date_started` and `date_finished` are manually managed, leading to inconsistent data.

## Proposed Solution

### Sorting Logic (by status):
- **Want to read**: Sort by `date_added` (DESC) — most recently added books first
- **Reading**: Sort by `date_started` (DESC) — most recently started books first
- **Read**: Sort by `date_finished` (DESC) — most recently finished books first
- **Did not finish**: Sort by `date_started` (DESC) — when the attempt started

### Automatic Date Management:
1. **Transitioning to "reading"** (`currently_reading`):
   - If `date_started` is `null`: set it to current date automatically
   - If `date_started` is already set: show confirmation dialog with two options:
     - Keep existing date
     - Set new date (current date)

2. **Transitioning to "read"** or "did not finish"**:
   - Automatically set `date_finished` to current date if it's `null`

---

## Implementation Phases

### Phase 1: Backend — API Contract & Sorting Logic

#### 1.1 Update `list_books` endpoint sorting logic

**File:** `backend/app/routers/books.py`

**Changes:**
- Add new sort logic that selects the appropriate column based on the `status` query parameter
- Keep the existing `sort` query parameter for user-controlled sorting (e.g., rating)
- Implement a "smart sort" mode that applies status-specific sorting when no explicit sort is requested

**Pseudocode:**
```python
def list_books(..., smart_sort: bool = True):
    # If smart_sort and a status filter is active, use status-specific sorting
    if smart_sort and status is not None:
        if status == ReadingStatus.want_to_read:
            sort_col = Book.date_added
        elif status == ReadingStatus.currently_reading:
            sort_col = Book.date_started
        elif status == ReadingStatus.read:
            sort_col = Book.date_finished
        elif status == ReadingStatus.did_not_finish:
            sort_col = Book.date_started
        
        # Always DESC for smart sort, with NULL values last
        statement = statement.order_by(sort_col.desc().nullslast())
    else:
        # Use existing manual sort logic (date_added or rating)
        ...
```

**Edge Case Handling:**
- Books with `null` dates should appear at the end (use `.nullslast()`)
- Ensure backward compatibility: when `smart_sort=false`, use existing behavior

#### 1.2 Create Alembic migration for indexing

**File:** `backend/alembic/versions/XXXX_add_date_started_finished_indexes.py`

**Changes:**
- Add database indexes on `date_started` and `date_finished` columns for efficient sorting
- These columns already exist, but are not indexed

**Migration script:**
```python
def upgrade():
    op.create_index(op.f('ix_book_date_started'), 'book', ['date_started'], unique=False)
    op.create_index(op.f('ix_book_date_finished'), 'book', ['date_finished'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_book_date_finished'), table_name='book')
    op.drop_index(op.f('ix_book_date_started'), table_name='book')
```

---

### Phase 2: Backend — Automatic Date Field Management

#### 2.1 Add date auto-population logic in `update_book` endpoint

**File:** `backend/app/routers/books.py`

**Changes:**
- Add business logic to automatically set `date_started` and `date_finished` based on status transitions
- Only trigger auto-population when status changes (not on every update)
- Return metadata about date changes in the response for frontend dialog handling

**Pseudocode:**
```python
@router.patch("/{book_id}", response_model=BookUpdateResponse)
async def update_book(...):
    book = session.get(Book, book_id)
    old_status = book.reading_status
    update_data = book_in.model_dump(exclude_unset=True)
    new_status = update_data.get("reading_status", old_status)
    
    # Status transition logic
    if new_status != old_status:
        if new_status == ReadingStatus.currently_reading:
            if book.date_started is None:
                update_data["date_started"] = date.today()
        
        elif new_status in [ReadingStatus.read, ReadingStatus.did_not_finish]:
            if book.date_finished is None:
                update_data["date_finished"] = date.today()
    
    # Apply updates
    book.sqlmodel_update(update_data)
    session.commit()
    session.refresh(book)
    return book
```

#### 2.2 Add new API endpoint for status transition with date conflict check

**File:** `backend/app/routers/books.py`

**New endpoint:** `POST /api/books/{book_id}/transition-status`

**Request schema:**
```python
class StatusTransitionRequest(SQLModel):
    new_status: ReadingStatus
    force_date_started: Optional[date] = None  # Override date_started if set
```

**Response schema:**
```python
class StatusTransitionResponse(SQLModel):
    book: BookRead
    date_conflict: Optional[dict] = None  # {"field": "date_started", "existing": "2024-01-15"}
```

**Logic:**
- Check if transitioning to `currently_reading` and `date_started` already exists
- If conflict exists, return `date_conflict` metadata (don't auto-set)
- Frontend will prompt user and call again with `force_date_started`
- If no conflict or `force_date_started` is provided, apply transition

**Why a separate endpoint?**
- Cleaner separation between generic updates and status-specific business logic
- Makes conflict detection explicit
- Easier to test and reason about

---

### Phase 3: Frontend — Status-Aware Sorting UI

#### 3.1 Update sort field type and remove manual sort controls for status views

**File:** `frontend/src/lib/types.ts`

**Changes:**
```typescript
export type SortField = 'date_added' | 'rating' | 'date_started' | 'date_finished' | 'smart';
```

#### 3.2 Update `+page.svelte` to use smart sorting by default

**File:** `frontend/src/routes/+page.svelte`

**Changes:**
- Set `sort = 'smart'` by default (or omit sort parameter entirely)
- Backend will apply status-specific sorting automatically
- Remove sort dropdown from the UI when using smart sort (or make it optional/advanced)
- Keep the ability to switch to manual sorting if needed

**Pseudocode:**
```typescript
let sort = $state<SortField>('smart');  // Default to smart sorting
let order = $state<SortOrder>('desc');

async function fetchBooks(background = false) {
    books = await api.books.list({
        status: activeStatus,
        q: searchQuery || undefined,
        sort: sort === 'smart' ? undefined : sort,  // Omit for smart sort
        order
    });
}
```

**UI Changes:**
- Hide or collapse sort controls when in smart mode
- Add a toggle or advanced option to switch back to manual sorting

---

### Phase 4: Frontend — Date Conflict Dialog

#### 4.1 Create new Svelte component: `DateConflictDialog.svelte`

**File:** `frontend/src/lib/components/DateConflictDialog.svelte`

**Purpose:** Show a modal when user transitions a book to "reading" status and `date_started` is already set.

**Props:**
```typescript
{
    open: boolean;
    existingDate: string;  // ISO date string
    newDate: string;       // Current date as ISO string
    onConfirm: (useNewDate: boolean) => void;
    onCancel: () => void;
}
```

**UI:**
```
┌─────────────────────────────────────┐
│  📅 Date Already Set                │
│                                     │
│  This book has already been marked  │
│  as started on {existingDate}.      │
│                                     │
│  Do you want to:                    │
│  ○ Keep existing date ({existing})  │
│  ○ Set new date ({newDate})         │
│                                     │
│  [Cancel]  [Confirm]                │
└─────────────────────────────────────┘
```

#### 4.2 Update `BookDrawer.svelte` to integrate conflict dialog

**File:** `frontend/src/lib/components/BookDrawer.svelte`

**Changes:**
- Import and use `DateConflictDialog` component
- When user changes status to "reading", first call the new API endpoint
- If response includes `date_conflict`, show the dialog
- On dialog confirmation, call API again with `force_date_started`

**Pseudocode:**
```typescript
let dateConflictOpen = $state(false);
let conflictData = $state<any>(null);

async function save() {
    if (statusChanged && newStatus === 'currently_reading') {
        const response = await api.books.transitionStatus(book.id, {
            new_status: newStatus
        });
        
        if (response.date_conflict) {
            conflictData = response.date_conflict;
            dateConflictOpen = true;
            return;  // Wait for user choice
        }
    }
    
    // Normal save flow
    await api.books.update(book.id, ...);
}

function handleConflictConfirm(useNewDate: boolean) {
    const forcedDate = useNewDate ? new Date().toISOString().split('T')[0] : null;
    // Call API with forced date
    api.books.transitionStatus(book.id, {
        new_status: 'currently_reading',
        force_date_started: forcedDate
    });
    dateConflictOpen = false;
}
```

---

### Phase 5: Testing

#### 5.1 Backend Tests

**File:** `backend/tests/test_books.py`

**New test cases:**

1. **Test smart sorting by status:**
   - `test_list_books_smart_sort_want_to_read_by_date_added()`
   - `test_list_books_smart_sort_reading_by_date_started()`
   - `test_list_books_smart_sort_read_by_date_finished()`
   - `test_list_books_smart_sort_dnf_by_date_started()`
   - `test_list_books_smart_sort_null_dates_appear_last()`

2. **Test automatic date field population:**
   - `test_transition_to_reading_sets_date_started_if_null()`
   - `test_transition_to_reading_preserves_existing_date_started()`
   - `test_transition_to_read_sets_date_finished_if_null()`
   - `test_transition_to_dnf_sets_date_finished_if_null()`
   - `test_no_date_change_when_status_unchanged()`

3. **Test new transition endpoint:**
   - `test_transition_status_endpoint_success()`
   - `test_transition_status_returns_date_conflict()`
   - `test_transition_status_with_force_date_started()`

**Example test:**
```python
def test_list_books_smart_sort_reading_by_date_started(client: TestClient):
    _create_book(client, title="Started Yesterday", reading_status="currently_reading", date_started="2026-05-10")
    _create_book(client, title="Started Today", reading_status="currently_reading", date_started="2026-05-11")
    _create_book(client, title="No Start Date", reading_status="currently_reading", date_started=None)
    
    resp = client.get("/api/books?status=currently_reading")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["title"] == "Started Today"  # Most recent first
    assert data[1]["title"] == "Started Yesterday"
    assert data[2]["title"] == "No Start Date"  # Null last
```

#### 5.2 Frontend Tests (Optional — Manual Testing)

If Playwright or other frontend test framework is available:

**Test scenarios:**
1. Navigate to each status tab and verify books are sorted correctly
2. Transition a book to "reading" status (with null `date_started`) → verify no dialog, date auto-set
3. Transition a book to "reading" status (with existing `date_started`) → verify dialog appears
4. Select "keep existing" in dialog → verify old date preserved
5. Select "set new date" in dialog → verify date updated to today
6. Transition to "read" or "dnf" → verify `date_finished` auto-set

**Manual testing checklist:**
- [ ] Sort order is correct for each status category
- [ ] Books without dates appear at the end of lists
- [ ] Conflict dialog shows correct dates
- [ ] Dialog buttons work correctly
- [ ] Date fields update correctly after status transitions

---

## Data Migration & Backfill Considerations

### Existing Data

Books already in the database may have:
- `date_started = null` for books in "reading" status
- `date_finished = null` for books in "read" or "did not finish" status

### Migration Strategy

**Option 1: No backfill (recommended)**
- Let the system work with existing null dates
- Sorting will push these books to the end of lists
- Users can manually update dates if needed

**Option 2: Backfill with `date_added`**
- Run a one-time migration to set missing dates to `date_added` as a fallback
- More accurate than leaving null, but assumes the addition date is a reasonable proxy

**Recommendation:** Start with Option 1 for simplicity. Add backfill later if users report issues.

---

## Risk Assessment & Edge Cases

### Risks

1. **Breaking existing sort behavior:**
   - **Mitigation:** Keep manual sort controls available; smart sort is opt-in (or default but switchable)

2. **Date conflict dialog UX complexity:**
   - **Mitigation:** Make dialog very clear with radio buttons and explicit date labels

3. **Database performance with new indexes:**
   - **Impact:** Minimal; indexes improve query performance, slight increase in write overhead
   - **Mitigation:** Monitor query performance; indexes are on low-cardinality date fields (acceptable)

4. **Null date handling in sorting:**
   - **Mitigation:** Use `.nullslast()` in SQL to push null dates to the end

### Edge Cases

1. **User manually sets date_started, then transitions away and back to "reading":**
   - **Behavior:** Dialog will appear on second transition
   - **Why:** User's manual input is preserved, system asks again

2. **User transitions directly from "want to read" to "read" (skipping "reading"):**
   - **Behavior:** `date_finished` is set, but `date_started` remains null
   - **Why:** Valid scenario; user may have read offline or forgot to mark as reading

3. **User transitions from "reading" to "want to read" to "reading" again:**
   - **Behavior:** Dialog appears if `date_started` was set during first reading attempt
   - **Why:** Valid re-reading scenario

4. **Multiple rapid status changes (race condition):**
   - **Mitigation:** Backend should handle updates atomically within a transaction
   - **Current code:** Already uses SQLModel's transaction handling

---

## Rollout & Verification Steps

### Development
1. Implement Phase 1 (backend sorting) → test with curl/Postman
2. Implement Phase 2 (date management) → test with automated tests
3. Run Alembic migration in dev environment
4. Implement Phase 3 (frontend sorting) → verify in browser
5. Implement Phase 4 (conflict dialog) → manually test all scenarios

### Staging/Pre-Production
1. Deploy backend + migration
2. Verify existing books sort correctly
3. Test date conflict scenarios with real data
4. Get user feedback on UX

### Production
1. Run database migration (indexes)
2. Deploy backend
3. Deploy frontend
4. Monitor for errors or performance issues
5. Collect user feedback on new sorting behavior

### Verification Checklist
- [ ] Books in each status category sort by correct field
- [ ] Null dates appear at the end of lists
- [ ] Date conflict dialog appears when expected
- [ ] Date fields auto-populate correctly
- [ ] No performance regressions on list queries
- [ ] No breaking changes to existing API consumers (if any)

---

## API Contract Summary

### Changes to `GET /api/books`

**Before:**
```
GET /api/books?status=reading&sort=date_added&order=desc
```

**After (smart sort, default):**
```
GET /api/books?status=reading
→ Backend automatically sorts by date_started DESC
```

**After (manual sort, opt-in):**
```
GET /api/books?status=reading&sort=rating&order=asc
→ Backend sorts by rating ASC (existing behavior)
```

### New endpoint: `POST /api/books/{book_id}/transition-status`

**Request:**
```json
{
  "new_status": "currently_reading",
  "force_date_started": null  // or "2026-05-11"
}
```

**Response (no conflict):**
```json
{
  "book": { ...updated book object... },
  "date_conflict": null
}
```

**Response (conflict detected):**
```json
{
  "book": { ...current book object... },
  "date_conflict": {
    "field": "date_started",
    "existing_date": "2024-01-15"
  }
}
```

---

## Alternative Approaches Considered

### Alternative 1: Client-side sorting only
- **Pros:** No backend changes, faster to implement
- **Cons:** Inefficient for large datasets, doesn't scale, no proper pagination support
- **Verdict:** ❌ Not recommended for production

### Alternative 2: Always prompt for dates on status transition
- **Pros:** More explicit, gives user full control
- **Cons:** Adds friction to every transition, annoying for most cases
- **Verdict:** ❌ Too intrusive

### Alternative 3: Add separate "date resumed" field for re-reading
- **Pros:** Captures full reading history
- **Cons:** Significant data model change, complex UI, overkill for MVP
- **Verdict:** ⏳ Consider for future enhancement (reading history feature)

---

## Estimated Complexity

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 1: Backend sorting | 2-3 hours | Low |
| Phase 2: Date management logic | 3-4 hours | Medium |
| Phase 3: Frontend sorting | 1-2 hours | Low |
| Phase 4: Conflict dialog | 2-3 hours | Medium |
| Phase 5: Testing | 3-4 hours | Low |
| **Total** | **11-16 hours** | **Medium** |

**Total estimated time:** ~2 working days

---

## Next Steps

1. ✅ Review and approve this plan
2. ⏸️ Address any questions or concerns
3. ⏸️ Proceed with Phase 1 implementation

**After plan approval:**
- Start with Phase 1 (backend sorting) as it's the foundation
- Phases 1-2 can be implemented and tested independently of frontend
- Phases 3-4 depend on backend completion
- Phase 5 (testing) runs in parallel with each phase
