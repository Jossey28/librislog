# Implementation Plan: Improved Date Handling and Sorting

## Overview

This plan addresses three interconnected improvements to date handling and book sorting:

1. **Date finished conflict check**: When transitioning to "read" or "did not finish" status, check if `date_finished` is already set and prompt user (similar to existing `date_started` conflict handling)
2. **Full timestamp storage**: Use timestamps (not just dates) for `date_added`, `date_started`, and `date_finished` internally, while displaying dates in UI, to enable precise chronological sorting
3. **Restore sort controls**: Bring back user-selectable sort options (date-based vs. name-based, asc vs. desc) in the frontend UI

---

## Problem Statement

### Current State

**Date Handling Issues:**
- `date_finished` is automatically set when transitioning to "read" or "did not finish" status without checking if it's already set (unlike `date_started` which has conflict detection)
- `date_started` and `date_finished` are stored as DATE types (no time component), meaning books added/finished on the same day have indeterminate sort order
- `date_added` is already a DATETIME with timezone, but the others are not

**Sorting Issues:**
- Smart sorting exists and works correctly (status-specific sorting)
- Manual sort controls were removed from the UI at some point
- Users cannot easily toggle between different sort orders (e.g., A-Z by title, oldest first, etc.)

### Desired State

1. **Consistent conflict handling** for both `date_started` and `date_finished` 
2. **Precise chronological sorting** using full timestamps
3. **Flexible sorting UI** with user-selectable options

---

## Technical Context

### Current Implementation

**Backend (Python/FastAPI):**
- `date_added`: `datetime` with UTC timezone (correct)
- `date_started`: `date` (date only, no time)
- `date_finished`: `date` (date only, no time)
- Smart sorting exists in `list_books()` using `STATUS_DEFAULT_SORT_COLUMN` mapping
- `transition_status` endpoint has conflict check for `date_started` only

**Frontend (Svelte):**
- TypeScript types define dates as strings (ISO format)
- `DateStartedConflictDialog.svelte` handles date_started conflicts
- Current UI uses `smart_sort: true` by default with no manual sort controls visible
- Date inputs use HTML5 `<input type="date">` (date only, no time picker)

### Related Files

**Backend:**
- `backend/app/models.py` - Book model with date fields
- `backend/app/schemas.py` - Pydantic schemas for API
- `backend/app/routers/books.py` - API endpoints with sorting logic
- `backend/alembic/versions/` - Database migrations

**Frontend:**
- `frontend/src/lib/types.ts` - TypeScript type definitions
- `frontend/src/routes/+page.svelte` - Main book list view
- `frontend/src/lib/components/BookDrawer.svelte` - Edit dialog with date inputs
- `frontend/src/lib/components/DateStartedConflictDialog.svelte` - Existing conflict dialog
- `frontend/src/lib/api.ts` - API client
- `frontend/src/lib/i18n/locales/en.json` - Translation strings

---

## Implementation Phases

### Phase 1: Backend — Timestamp Storage Migration

**Goal:** Convert `date_started` and `date_finished` from DATE to DATETIME (with timezone) in the database.

#### 1.1 Create Alembic Migration

**File:** `backend/alembic/versions/XXXX_convert_dates_to_timestamps.py`

**Changes:**
```python
"""Convert date_started and date_finished to datetime with timezone

Revision ID: XXXX
Revises: 8b0d7f6c9f31
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

revision = 'XXXX'
down_revision = '8b0d7f6c9f31'
branch_labels = None
depends_on = None

def upgrade():
    # SQLite doesn't have ALTER COLUMN TYPE, so we need to:
    # 1. Create new columns with DATETIME type
    # 2. Copy data (appending midnight UTC time)
    # 3. Drop old columns
    # 4. Rename new columns
    
    # Add new temporary columns
    op.add_column('book', sa.Column('date_started_new', sa.DateTime(timezone=True), nullable=True))
    op.add_column('book', sa.Column('date_finished_new', sa.DateTime(timezone=True), nullable=True))
    
    # Migrate data: DATE → DATETIME (append ' 00:00:00+00' for UTC midnight)
    # Use SQLite datetime() function to convert
    op.execute("""
        UPDATE book 
        SET date_started_new = datetime(date_started || ' 00:00:00')
        WHERE date_started IS NOT NULL
    """)
    op.execute("""
        UPDATE book 
        SET date_finished_new = datetime(date_finished || ' 00:00:00')
        WHERE date_finished IS NOT NULL
    """)
    
    # Drop old columns
    with op.batch_alter_table('book') as batch_op:
        batch_op.drop_index('ix_book_date_started')
        batch_op.drop_index('ix_book_date_finished')
        batch_op.drop_column('date_started')
        batch_op.drop_column('date_finished')
    
    # Rename new columns to original names
    with op.batch_alter_table('book') as batch_op:
        batch_op.alter_column('date_started_new', new_column_name='date_started')
        batch_op.alter_column('date_finished_new', new_column_name='date_finished')
        
        # Recreate indexes
        batch_op.create_index('ix_book_date_started', ['date_started'])
        batch_op.create_index('ix_book_date_finished', ['date_finished'])

def downgrade():
    # Reverse: DATETIME → DATE (truncate time component)
    op.add_column('book', sa.Column('date_started_old', sa.Date, nullable=True))
    op.add_column('book', sa.Column('date_finished_old', sa.Date, nullable=True))
    
    op.execute("""
        UPDATE book 
        SET date_started_old = date(date_started)
        WHERE date_started IS NOT NULL
    """)
    op.execute("""
        UPDATE book 
        SET date_finished_old = date(date_finished)
        WHERE date_finished IS NOT NULL
    """)
    
    with op.batch_alter_table('book') as batch_op:
        batch_op.drop_index('ix_book_date_started')
        batch_op.drop_index('ix_book_date_finished')
        batch_op.drop_column('date_started')
        batch_op.drop_column('date_finished')
        batch_op.alter_column('date_started_old', new_column_name='date_started')
        batch_op.alter_column('date_finished_old', new_column_name='date_finished')
        batch_op.create_index('ix_book_date_started', ['date_started'])
        batch_op.create_index('ix_book_date_finished', ['date_finished'])
```

**Why this approach:**
- SQLite doesn't support direct `ALTER COLUMN TYPE`
- Batch operations are necessary for SQLite
- Existing dates are preserved, with midnight UTC as the time component (reasonable default)
- Downgrade is possible (though time component is lost)

#### 1.2 Update Backend Model

**File:** `backend/app/models.py`

**Changes:**
```python
from datetime import date, datetime, timezone  # date import becomes less relevant

class Book(SQLModel, table=True):
    # ... existing fields ...
    date_added: datetime = Field(default_factory=_utcnow, index=True)
    date_started: Optional[datetime] = Field(default=None, index=True)  # Changed from date
    date_finished: Optional[datetime] = Field(default=None, index=True)  # Changed from date
```

**Impact:**
- All date fields are now `datetime` with timezone info
- Existing `_utcnow()` helper function can be reused
- Python code will use `datetime.now(timezone.utc)` instead of `date.today()`

#### 1.3 Update Backend Schemas

**File:** `backend/app/schemas.py`

**Changes:**
```python
from datetime import date, datetime  # Keep date for API backwards compat

class BookCreate(SQLModel):
    # ... existing fields ...
    date_started: Optional[datetime] = None  # Changed from date
    date_finished: Optional[datetime] = None  # Changed from date

class BookUpdate(SQLModel):
    # ... existing fields ...
    date_started: Optional[datetime] = None  # Changed from date
    date_finished: Optional[datetime] = None  # Changed from date

class BookRead(SQLModel):
    # ... existing fields ...
    date_added: datetime
    date_started: Optional[datetime]  # Changed from date
    date_finished: Optional[datetime]  # Changed from date

class StatusTransitionRequest(SQLModel):
    new_status: ReadingStatus
    force_date_started: Optional[datetime] = None  # Changed from date

class DateConflict(SQLModel):
    field: str
    existing_date: datetime  # Changed from date
    suggested_date: datetime  # Changed from date
```

**API Compatibility:**
- The API will now return full ISO 8601 timestamps (e.g., `"2026-05-11T14:30:00Z"`)
- Frontend already expects strings, so no breaking change for existing clients
- Clients can send either date-only strings (`"2026-05-11"`) or full timestamps
- FastAPI/Pydantic will parse both formats automatically

---

### Phase 2: Backend — Date Finished Conflict Detection

**Goal:** Add conflict detection for `date_finished` similar to existing `date_started` logic.

#### 2.1 Extend Status Transition Logic

**File:** `backend/app/routers/books.py`

**Function:** `transition_status()`

**Changes:**
```python
@router.post("/{book_id}/transition-status", response_model=StatusTransitionResponse)
def transition_status(
    book_id: int,
    transition: StatusTransitionRequest,
    session: Session = Depends(get_session),
) -> StatusTransitionResponse:
    logger.debug(
        "transition_status — id=%s new_status=%s force_date_started=%r force_date_finished=%r",
        book_id,
        transition.new_status,
        transition.force_date_started,
        transition.force_date_finished,
    )
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    conflict: DateConflict | None = None
    update_data: dict = {"reading_status": transition.new_status}
    now = _utcnow()  # Use datetime.now(timezone.utc) instead of date.today()

    # EXISTING: Check date_started conflict when transitioning to currently_reading
    if (
        transition.new_status == ReadingStatus.currently_reading
        and transition.new_status != book.reading_status
        and book.date_started is not None
    ):
        if transition.force_date_started is None:
            conflict = DateConflict(
                field="date_started",
                existing_date=book.date_started,
                suggested_date=now,
            )
            return StatusTransitionResponse(book=BookRead.model_validate(book), date_conflict=conflict)
        update_data["date_started"] = transition.force_date_started

    # NEW: Check date_finished conflict when transitioning to read or did_not_finish
    if (
        transition.new_status in (ReadingStatus.read, ReadingStatus.did_not_finish)
        and transition.new_status != book.reading_status
        and book.date_finished is not None
    ):
        if transition.force_date_finished is None:
            conflict = DateConflict(
                field="date_finished",
                existing_date=book.date_finished,
                suggested_date=now,
            )
            return StatusTransitionResponse(book=BookRead.model_validate(book), date_conflict=conflict)
        update_data["date_finished"] = transition.force_date_finished

    # Apply automatic date population if no conflict
    _apply_status_transition_dates(book, transition.new_status, update_data)
    book.sqlmodel_update(update_data)
    session.add(book)
    session.commit()
    session.refresh(book)
    return StatusTransitionResponse(book=BookRead.model_validate(book), date_conflict=None)
```

**Helper Function Update:**
```python
def _apply_status_transition_dates(
    book: Book,
    target_status: ReadingStatus,
    update_data: dict,
) -> None:
    """Automatically set date_started or date_finished if null during status transition."""
    if target_status == book.reading_status:
        return

    now = _utcnow()

    # Auto-set date_started when transitioning to currently_reading
    if target_status == ReadingStatus.currently_reading and book.date_started is None:
        if update_data.get("date_started") is None:
            update_data["date_started"] = now

    # Auto-set date_finished when transitioning to read or did_not_finish
    if target_status in (ReadingStatus.read, ReadingStatus.did_not_finish):
        if update_data.get("date_finished") is None:
            update_data["date_finished"] = now
```

#### 2.2 Update Status Transition Request Schema

**File:** `backend/app/schemas.py`

**Changes:**
```python
class StatusTransitionRequest(SQLModel):
    new_status: ReadingStatus
    force_date_started: Optional[datetime] = None
    force_date_finished: Optional[datetime] = None  # NEW
```

**Backward Compatibility:**
- `force_date_finished` is optional with default `None`
- Existing API calls without this field will continue to work

#### 2.3 Update Status Transition Response Schema

**File:** `backend/app/schemas.py`

**Changes:**
```python
class DateConflict(SQLModel):
    field: str  # "date_started" | "date_finished"
    existing_date: datetime
    suggested_date: datetime
```

**Note:** `field` discriminator allows the frontend to distinguish which date is in conflict.

---

### Phase 3: Frontend — Date Finished Conflict Dialog

**Goal:** Extend existing conflict dialog to handle `date_finished` conflicts.

#### 3.1 Rename and Generalize Existing Conflict Dialog Component

**Current File:** `frontend/src/lib/components/DateStartedConflictDialog.svelte`  
**New File:** `frontend/src/lib/components/DateConflictDialog.svelte`

**Changes:**
```svelte
<script lang="ts">
	import { _ } from '$lib/i18n';

	let {
		open = false,
		field,  // NEW: "date_started" | "date_finished"
		existingDate,
		suggestedDate,
		onKeep,
		onUseSuggested,
		onCancel
	}: {
		open?: boolean;
		field: 'date_started' | 'date_finished';  // NEW
		existingDate: string;
		suggestedDate: string;
		onKeep?: () => void;
		onUseSuggested?: () => void;
		onCancel?: () => void;
	} = $props();

	// Compute i18n keys based on field
	const titleKey = $derived(field === 'date_started' ? 'dateConflict.titleStarted' : 'dateConflict.titleFinished');
	const messageKey = $derived(field === 'date_started' ? 'dateConflict.messageStarted' : 'dateConflict.messageFinished');
</script>

{#if open}
	<div class="modal modal-open">
		<div class="modal-box max-w-md">
			<h3 class="text-lg font-bold">{$_(titleKey)}</h3>
			<p class="text-sm text-base-content/70 mt-2">
				{$_(messageKey, { values: { oldDate: existingDate, newDate: suggestedDate } })}
			</p>
			<div class="modal-action">
				<button type="button" class="btn btn-ghost btn-sm" onclick={onCancel}>{$_('common.cancel')}</button>
				<button type="button" class="btn btn-outline btn-sm" onclick={onKeep}
					>{$_('dateConflict.keepOld', { values: { oldDate: existingDate } })}</button
				>
				<button type="button" class="btn btn-primary btn-sm" onclick={onUseSuggested}
					>{$_('dateConflict.useNew', { values: { newDate: suggestedDate } })}</button
				>
			</div>
		</div>
		<div class="modal-backdrop" role="button" tabindex="-1"></div>
	</div>
{/if}
```

**Why rename:**
- Makes the component reusable for both conflict types
- Reduces code duplication
- Clearer naming

#### 3.2 Update BookDrawer to Handle Both Conflict Types

**File:** `frontend/src/lib/components/BookDrawer.svelte`

**Changes:**
```typescript
// Update imports
import DateConflictDialog from './DateConflictDialog.svelte';  // Renamed

// Update state variables
let dateConflictOpen = $state(false);
let dateConflictField = $state<'date_started' | 'date_finished'>('date_started');  // NEW
let conflictExistingDate = $state('');
let conflictSuggestedDate = $state('');
let pendingStatus = $state<ReadingStatus | null>(null);
let pendingPayload = $state<Partial<Book> | null>(null);

// Update applyPendingTransition function
async function applyPendingTransition(forceDate: string | null) {
	if (!book || !pendingStatus) return;

	const payload: any = {
		new_status: pendingStatus
	};

	// Add force parameter based on conflict field
	if (dateConflictField === 'date_started') {
		payload.force_date_started = forceDate;
	} else {
		payload.force_date_finished = forceDate;
	}

	const transition = await api.books.transitionStatus(book.id, payload);

	if (transition.date_conflict) {
		// Update conflict state with new conflict data
		dateConflictField = transition.date_conflict.field as 'date_started' | 'date_finished';
		conflictExistingDate = transition.date_conflict.existing_date;
		conflictSuggestedDate = transition.date_conflict.suggested_date;
		dateConflictOpen = true;
		return;
	}

	// Conflict resolved or no conflict
	let updated = transition.book;
	if (pendingPayload && Object.keys(pendingPayload).length > 0) {
		updated = await api.books.update(book.id, pendingPayload);
	}

	book = updated;
	onSave?.(updated);
	open = false;
	dateConflictOpen = false;
	pendingStatus = null;
	pendingPayload = null;
}

// Update save function to check for date_finished conflicts
async function save() {
	if (!book) return;
	saving = true;
	try {
		const statusChanged = reading_status !== book.reading_status;
		const dateStartedChanged =
			normalizeDate(date_started) !== (book.date_started ?? null);
		const dateFinishedChanged =
			normalizeDate(date_finished) !== (book.date_finished ?? null);

		if (statusChanged) {
			pendingStatus = reading_status;
			pendingPayload = buildNonStatusPayload(dateStartedChanged || dateFinishedChanged);

			const transition = await api.books.transitionStatus(book.id, {
				new_status: reading_status
			});

			if (transition.date_conflict) {
				// Set conflict field type
				dateConflictField = transition.date_conflict.field as 'date_started' | 'date_finished';
				conflictExistingDate = transition.date_conflict.existing_date;
				conflictSuggestedDate = transition.date_conflict.suggested_date;
				dateConflictOpen = true;
				return;
			}

			let updated = transition.book;
			if (pendingPayload && Object.keys(pendingPayload).length > 0) {
				updated = await api.books.update(book.id, pendingPayload);
			}
			book = updated;
			onSave?.(updated);
			open = false;
			pendingStatus = null;
			pendingPayload = null;
			return;
		}

		// No status change, normal update
		const updated = await api.books.update(book.id, {
			...buildNonStatusPayload(true),
			reading_status
		});
		book = updated;
		onSave?.(updated);
		open = false;
	} catch (e: unknown) {
		toasts.add(
			e instanceof Error
				? e.message
				: $_('common.actionFailed', { values: { action: $_('common.save') } }),
			'error'
		);
	} finally {
		saving = false;
	}
}

// Update the dialog component usage
<DateConflictDialog
	open={dateConflictOpen}
	field={dateConflictField}
	existingDate={conflictExistingDate}
	suggestedDate={conflictSuggestedDate}
	onCancel={() => {
		dateConflictOpen = false;
		pendingStatus = null;
		pendingPayload = null;
	}}
	onKeep={() => {
		dateConflictOpen = false;
		void applyPendingTransition(conflictExistingDate);
	}}
	onUseSuggested={() => {
		dateConflictOpen = false;
		void applyPendingTransition(conflictSuggestedDate);
	}}
/>
```

#### 3.3 Update i18n Strings

**File:** `frontend/src/lib/i18n/locales/en.json`

**Changes:**
```json
{
  "dateConflict": {
    "titleStarted": "Start date already set",
    "titleFinished": "Finish date already set",
    "messageStarted": "This book's start date is already set to {oldDate}. Do you want to keep it or set {newDate} as the new start date?",
    "messageFinished": "This book's finish date is already set to {oldDate}. Do you want to keep it or set {newDate} as the new finish date?",
    "keepOld": "Keep {oldDate}",
    "useNew": "Use {newDate}"
  }
}
```

**Note:** Similar updates needed for `de.json` (German locale).

#### 3.4 Update Frontend Types

**File:** `frontend/src/lib/types.ts`

**Changes:**
```typescript
export interface DateConflict {
	field: 'date_started' | 'date_finished';  // Extend to include date_finished
	existing_date: string;
	suggested_date: string;
}

export interface StatusTransitionRequest {
	new_status: ReadingStatus;
	force_date_started?: string | null;
	force_date_finished?: string | null;  // NEW
}
```

#### 3.5 Update API Client

**File:** `frontend/src/lib/api.ts`

**Changes:**
No changes needed — the API client already sends and receives generic JSON payloads. The new `force_date_finished` field will be passed through automatically.

---

### Phase 4: Frontend — Restore Sort Controls

**Goal:** Add user-selectable sorting options back to the UI.

#### 4.1 Update Type Definitions

**File:** `frontend/src/lib/types.ts`

**Changes:**
```typescript
export type SortField = 'date_added' | 'date_started' | 'date_finished' | 'rating' | 'title';  // Add 'title'
export type SortOrder = 'asc' | 'desc';
```

**Note:** Backend doesn't currently support title sorting, so this will need backend changes (see 4.3).

#### 4.2 Add Sort Controls to Main Page

**File:** `frontend/src/routes/+page.svelte`

**Changes:**
```svelte
<script lang="ts">
	// ... existing imports ...
	import type { SortField, SortOrder } from '$lib/types';

	// ... existing state ...
	let smartSort = $state(true);  // Toggle between smart and manual sort
	let sortField = $state<SortField>('date_added');
	let sortOrder = $state<SortOrder>('desc');

	async function fetchBooks(background = false) {
		if (background) {
			syncing = true;
		} else {
			loading = true;
		}
		try {
			books = await api.books.list({
				status: activeStatus,
				q: searchQuery || undefined,
				smart_sort: smartSort,
				sort: smartSort ? undefined : sortField,  // Only send sort if not using smart sort
				order: smartSort ? undefined : sortOrder
			});
		} catch (e: unknown) {
			toasts.add(e instanceof Error ? e.message : $_('import.searchFailed'), 'error');
		} finally {
			if (background) {
				syncing = false;
			} else {
				loading = false;
			}
		}
	}

	$effect(() => {
		// Re-fetch whenever any filter changes
		void activeStatus;
		void searchQuery;
		void smartSort;
		void sortField;
		void sortOrder;
		fetchBooks();
	});

	// ... rest of component ...
</script>

<!-- Add sort controls to the header row -->
<div class="flex flex-col sm:flex-row sm:items-center gap-3">
	<h1 class="text-xl font-bold">{$_(STATUS_LABEL_KEYS[activeStatus])}</h1>
	{#if syncing}
		<span class="text-xs text-base-content/60 inline-flex items-center gap-1">
			<span class="loading loading-spinner loading-xs"></span>
			{$_('common.syncing')}
		</span>
	{/if}
	
	<!-- NEW: Sort controls -->
	<div class="flex items-center gap-2">
		<label class="label cursor-pointer gap-2">
			<input type="checkbox" class="toggle toggle-sm" bind:checked={smartSort} />
			<span class="label-text text-xs">{$_('sort.smartSort')}</span>
		</label>

		{#if !smartSort}
			<select class="select select-bordered select-xs" bind:value={sortField}>
				<option value="date_added">{$_('sort.dateAdded')}</option>
				<option value="date_started">{$_('sort.dateStarted')}</option>
				<option value="date_finished">{$_('sort.dateFinished')}</option>
				<option value="title">{$_('sort.title')}</option>
				<option value="rating">{$_('sort.rating')}</option>
			</select>

			<button
				class="btn btn-ghost btn-xs btn-square"
				onclick={() => (sortOrder = sortOrder === 'asc' ? 'desc' : 'asc')}
				title={$_(`sort.${sortOrder}`)}
			>
				{#if sortOrder === 'desc'}
					↓
				{:else}
					↑
				{/if}
			</button>
		{/if}
	</div>

	<div class="flex items-center gap-2 flex-1">
		<SearchBar
			bind:value={searchQuery}
			placeholder={$_('common.searchBooks')}
			onSearch={(q) => (searchQuery = q)}
		/>
	</div>
	<button class="btn btn-primary btn-sm hidden sm:flex" onclick={() => (addBookOpen = true)}>
		+ {$_('app.addBook')}
	</button>
</div>
```

**Design rationale:**
- Smart sort toggle: defaults to ON, uses status-specific sorting
- Manual sort: user can choose any field and direction
- Compact controls that don't clutter the UI
- Icons (↓↑) for sort order to save space

#### 4.3 Add Title Sorting to Backend

**File:** `backend/app/routers/books.py`

**Function:** `list_books()`

**Changes:**
```python
@router.get("", response_model=List[BookRead])
def list_books(
    status: Optional[ReadingStatus] = Query(default=None),
    q: Optional[str] = Query(default=None),
    sort: Literal["date_added", "date_started", "date_finished", "rating", "title"] = Query(  # Add "title"
        default="date_added"
    ),
    order: Literal["asc", "desc"] = Query(default="desc"),
    smart_sort: bool = Query(default=True),
    session: Session = Depends(get_session),
) -> List[Book]:
    # ... existing code ...

    if smart_sort and status is not None:
        sort_col = STATUS_DEFAULT_SORT_COLUMN[status]
        sort_order = "desc"
    elif sort == "rating":
        sort_col = Book.rating
        sort_order = order
    elif sort == "date_started":
        sort_col = Book.date_started
        sort_order = order
    elif sort == "date_finished":
        sort_col = Book.date_finished
        sort_order = order
    elif sort == "title":  # NEW
        sort_col = Book.title
        sort_order = order
    else:
        sort_col = Book.date_added
        sort_order = order

    sort_expression = sort_col.desc() if sort_order == "desc" else sort_col.asc()
    
    # Only use nullslast for date/rating columns (not title)
    if sort_col in (Book.date_started, Book.date_finished, Book.rating):
        sort_expression = sort_expression.nullslast()

    statement = statement.order_by(sort_expression)
    # ... existing code ...
```

**Rationale:**
- Title sorting is case-insensitive (SQLite default collation is NOCASE for TEXT columns)
- No `nullslast()` needed for title (all books have titles due to required field)

#### 4.4 Add i18n Strings for Sort Controls

**File:** `frontend/src/lib/i18n/locales/en.json`

**Changes:**
```json
{
  "sort": {
    "smartSort": "Auto",
    "dateAdded": "Date Added",
    "dateStarted": "Date Started",
    "dateFinished": "Date Finished",
    "title": "Title",
    "rating": "Rating",
    "asc": "Ascending",
    "desc": "Descending"
  }
}
```

---

### Phase 5: Frontend — Display Timestamps as Dates

**Goal:** Show only the date portion in the UI while preserving timestamp precision in the background.

#### 5.1 Create Date Formatting Utility

**File:** `frontend/src/lib/utils/dateFormat.ts` (new file)

**Content:**
```typescript
/**
 * Format a datetime string (ISO 8601) to a localized date string.
 * 
 * @param datetime - ISO datetime string (e.g., "2026-05-11T14:30:00Z")
 * @param locale - Locale code (default: 'en-US')
 * @returns Formatted date string (e.g., "May 11, 2026" or "11.05.2026")
 */
export function formatDate(datetime: string | null, locale: string = 'en-US'): string {
	if (!datetime) return '';
	const date = new Date(datetime);
	return new Intl.DateTimeFormat(locale, {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	}).format(date);
}

/**
 * Convert an ISO datetime string to a date-only string for input[type="date"].
 * 
 * @param datetime - ISO datetime string
 * @returns Date string in YYYY-MM-DD format
 */
export function toDateInputValue(datetime: string | null): string {
	if (!datetime) return '';
	return datetime.split('T')[0];  // Extract date part before 'T'
}

/**
 * Convert a date input value (YYYY-MM-DD) to a full ISO datetime at midnight UTC.
 * 
 * @param dateString - Date string in YYYY-MM-DD format
 * @returns ISO datetime string with time set to midnight UTC
 */
export function fromDateInputValue(dateString: string): string {
	if (!dateString) return '';
	return `${dateString}T00:00:00Z`;
}
```

#### 5.2 Update BookDrawer Date Inputs

**File:** `frontend/src/lib/components/BookDrawer.svelte`

**Changes:**
```svelte
<script lang="ts">
	import { toDateInputValue, fromDateInputValue } from '$lib/utils/dateFormat';
	
	// ... existing code ...

	// Update effect to handle datetime → date conversion
	$effect(() => {
		if (book) {
			title = book.title;
			author = book.author ?? '';
			notes = book.notes ?? '';
			rating = book.rating;
			reading_status = book.reading_status;
			date_started = toDateInputValue(book.date_started);  // Convert to date-only
			date_finished = toDateInputValue(book.date_finished);  // Convert to date-only
			cover_url = book.cover_url ?? null;
			confirmDelete = false;
			dateConflictOpen = false;
			pendingStatus = null;
			pendingPayload = null;
		}
	});

	function buildNonStatusPayload(includeDates: boolean): Partial<Book> {
		const payload: Partial<Book> = {
			title,
			author: author || null,
			notes: notes || null,
			rating,
			cover_url: cover_url || null
		};

		if (includeDates) {
			// Convert date-only inputs back to full timestamps
			payload.date_started = date_started ? fromDateInputValue(date_started) : null;
			payload.date_finished = date_finished ? fromDateInputValue(date_finished) : null;
		}

		return payload;
	}

	// ... rest of component (no other changes needed)
</script>
```

**Why this works:**
- `<input type="date">` expects YYYY-MM-DD format, which is what `toDateInputValue` produces
- When user selects a date, it's converted to a full timestamp at midnight UTC via `fromDateInputValue`
- Backend receives full timestamps and stores them with time precision
- UI displays date-only, keeping the interface simple

#### 5.3 Update BookCard Date Display (if needed)

**File:** `frontend/src/lib/components/BookCard.svelte`

**Check if dates are displayed:** If the card shows dates, use `formatDate()` helper:
```svelte
<script lang="ts">
	import { formatDate } from '$lib/utils/dateFormat';
	// ... existing code ...
</script>

<!-- Example usage -->
{#if book.date_finished}
	<p class="text-xs text-base-content/60">{formatDate(book.date_finished)}</p>
{/if}
```

---

### Phase 6: Testing

**Goal:** Ensure all changes work correctly and don't introduce regressions.

#### 6.1 Backend Tests

**File:** `backend/tests/test_books.py`

**New Test Cases:**

```python
# ── Timestamp storage tests ──

def test_create_book_with_timestamp_dates(client: TestClient, monkeypatch):
    """Test that date_started and date_finished accept full timestamps."""
    from datetime import datetime, timezone
    
    now = datetime(2026, 5, 11, 14, 30, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.routers.books._utcnow", lambda: now)
    
    payload = {
        "title": "Test Book",
        "reading_status": "currently_reading",
        "date_started": now.isoformat(),
        "date_finished": None
    }
    resp = client.post("/api/books", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["date_started"] == now.isoformat()


def test_update_book_preserves_timestamp_precision(client: TestClient, monkeypatch):
    """Test that updating books preserves the time component of dates."""
    from datetime import datetime, timezone
    
    start_time = datetime(2026, 5, 10, 9, 15, 0, tzinfo=timezone.utc)
    finish_time = datetime(2026, 5, 11, 16, 45, 0, tzinfo=timezone.utc)
    
    book = _create_book(client, title="Book", reading_status="currently_reading")
    
    # Update with specific timestamps
    resp = client.patch(f"/api/books/{book['id']}", json={
        "date_started": start_time.isoformat(),
        "date_finished": finish_time.isoformat()
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_started"] == start_time.isoformat()
    assert data["date_finished"] == finish_time.isoformat()


def test_list_books_sorts_by_timestamp_not_date(client: TestClient):
    """Test that books with same date but different times sort correctly."""
    from datetime import datetime, timezone
    
    # Create books on the same day but different times
    book1 = _create_book(
        client,
        title="Morning Book",
        reading_status="read",
        date_finished=datetime(2026, 5, 11, 8, 0, 0, tzinfo=timezone.utc).isoformat()
    )
    book2 = _create_book(
        client,
        title="Evening Book",
        reading_status="read",
        date_finished=datetime(2026, 5, 11, 20, 0, 0, tzinfo=timezone.utc).isoformat()
    )
    
    resp = client.get("/api/books?status=read&smart_sort=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["title"] == "Evening Book"  # Most recent (evening) first
    assert data[1]["title"] == "Morning Book"


# ── Date finished conflict tests ──

def test_transition_to_read_with_existing_date_finished_returns_conflict(client: TestClient):
    """Test that transitioning to 'read' with existing date_finished prompts a conflict."""
    from datetime import datetime, timezone
    
    old_date = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    book = _create_book(
        client,
        title="Test Book",
        reading_status="currently_reading",
        date_finished=old_date.isoformat()  # Already has a finish date
    )
    
    resp = client.post(f"/api/books/{book['id']}/transition-status", json={
        "new_status": "read"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_conflict"] is not None
    assert data["date_conflict"]["field"] == "date_finished"
    assert data["date_conflict"]["existing_date"] == old_date.isoformat()


def test_transition_to_read_with_force_date_finished(client: TestClient):
    """Test that force_date_finished overrides existing date_finished."""
    from datetime import datetime, timezone
    
    old_date = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    new_date = datetime(2026, 5, 11, 18, 0, 0, tzinfo=timezone.utc)
    
    book = _create_book(
        client,
        title="Test Book",
        reading_status="currently_reading",
        date_finished=old_date.isoformat()
    )
    
    resp = client.post(f"/api/books/{book['id']}/transition-status", json={
        "new_status": "read",
        "force_date_finished": new_date.isoformat()
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_conflict"] is None
    assert data["book"]["reading_status"] == "read"
    assert data["book"]["date_finished"] == new_date.isoformat()


def test_transition_to_did_not_finish_with_existing_date_finished(client: TestClient):
    """Test date_finished conflict when transitioning to 'did_not_finish'."""
    from datetime import datetime, timezone
    
    old_date = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
    book = _create_book(
        client,
        title="Test Book",
        reading_status="currently_reading",
        date_finished=old_date.isoformat()
    )
    
    resp = client.post(f"/api/books/{book['id']}/transition-status", json={
        "new_status": "did_not_finish"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_conflict"] is not None
    assert data["date_conflict"]["field"] == "date_finished"


def test_transition_sets_date_finished_if_null(client: TestClient, monkeypatch):
    """Test that date_finished is auto-set if null when transitioning to 'read'."""
    from datetime import datetime, timezone
    
    now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.routers.books._utcnow", lambda: now)
    
    book = _create_book(
        client,
        title="Test Book",
        reading_status="currently_reading",
        date_finished=None
    )
    
    resp = client.post(f"/api/books/{book['id']}/transition-status", json={
        "new_status": "read"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_conflict"] is None
    assert data["book"]["date_finished"] == now.isoformat()


# ── Title sorting tests ──

def test_list_books_sort_by_title_asc(client: TestClient):
    """Test sorting by title in ascending order."""
    _create_book(client, title="Zebra")
    _create_book(client, title="Aardvark")
    _create_book(client, title="Meerkat")
    
    resp = client.get("/api/books?sort=title&order=asc&smart_sort=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["title"] == "Aardvark"
    assert data[1]["title"] == "Meerkat"
    assert data[2]["title"] == "Zebra"


def test_list_books_sort_by_title_desc(client: TestClient):
    """Test sorting by title in descending order."""
    _create_book(client, title="Aardvark")
    _create_book(client, title="Zebra")
    
    resp = client.get("/api/books?sort=title&order=desc&smart_sort=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["title"] == "Zebra"
    assert data[1]["title"] == "Aardvark"
```

**Test Execution:**
```bash
cd backend
pytest tests/test_books.py -v
```

#### 6.2 Frontend Manual Testing Checklist

**Conflict Dialog Tests:**
- [ ] Create a book with "currently_reading" status and set `date_started` manually
- [ ] Change status away and back to "currently_reading" → conflict dialog should appear
- [ ] Test "Keep old date" option → date_started unchanged
- [ ] Test "Use new date" option → date_started updated to today
- [ ] Create a book with "read" status and set `date_finished` manually
- [ ] Change status to "currently_reading" then back to "read" → conflict dialog should appear for date_finished
- [ ] Test both conflict resolution options for date_finished

**Sort Controls Tests:**
- [ ] Smart sort toggle ON → books sort correctly per status (want_to_read by date_added, etc.)
- [ ] Smart sort toggle OFF → manual sort controls appear
- [ ] Sort by Title A-Z → books alphabetically ordered
- [ ] Sort by Title Z-A → books reverse alphabetically ordered
- [ ] Sort by Date Added (oldest first) → works correctly
- [ ] Sort by Rating (lowest first) → works correctly
- [ ] Switch between sort options → list updates immediately

**Timestamp Precision Tests:**
- [ ] Create two books on the same day at different times (use browser dev tools to manually set timestamps in API request)
- [ ] Verify they sort in correct chronological order (not just by date)
- [ ] Check that date inputs still show date-only values (not time)

#### 6.3 Migration Testing

**Test Migration Locally:**
```bash
cd backend
# Backup database
cp data/librislog.db data/librislog.db.backup

# Run migration
alembic upgrade head

# Verify schema
sqlite3 data/librislog.db ".schema book"

# Check existing data was migrated correctly
sqlite3 data/librislog.db "SELECT id, title, date_started, date_finished FROM book LIMIT 5;"

# Rollback test
alembic downgrade -1
```

**Verify Migration Safety:**
- [ ] Existing date data is preserved
- [ ] Indexes are recreated correctly
- [ ] No data loss during migration
- [ ] Downgrade works correctly

---

## Risk Assessment & Mitigation

### High Priority Risks

**Risk 1: Data loss during migration**
- **Impact:** Existing `date_started` and `date_finished` values could be lost
- **Mitigation:**
  - Test migration thoroughly on a copy of production database
  - Create backup before running migration
  - Migration script uses INSERT/UPDATE (not DROP) to preserve data
  - Implement rollback plan (downgrade migration)

**Risk 2: API breaking changes**
- **Impact:** Existing API clients (if any) might break when receiving timestamps instead of dates
- **Mitigation:**
  - FastAPI/Pydantic accepts both date-only strings and full timestamps
  - Frontend already handles strings, so no breaking change
  - Consider API versioning if external clients exist

**Risk 3: Timezone confusion**
- **Impact:** Users in different timezones might see unexpected dates
- **Mitigation:**
  - All timestamps stored in UTC
  - Frontend displays local date (browser handles conversion)
  - Date inputs set time to midnight UTC (consistent behavior)

### Medium Priority Risks

**Risk 4: Sort control UX complexity**
- **Impact:** Too many options might confuse users
- **Mitigation:**
  - Default to smart sort (simple, automatic)
  - Manual controls are opt-in (toggle)
  - Clear labels and icons

**Risk 5: Conflict dialog fatigue**
- **Impact:** Users might find repeated conflict dialogs annoying
- **Mitigation:**
  - Dialogs only appear when truly necessary (existing date + status transition)
  - "Keep old date" is always an option (non-destructive)
  - Clear messaging explains why dialog appeared

### Low Priority Risks

**Risk 6: Performance degradation with timestamp sorting**
- **Impact:** Sorting by datetime might be slower than date
- **Mitigation:**
  - Indexes already exist on date columns
  - SQLite handles datetime sorting efficiently
  - No expected performance impact for typical dataset sizes (<10k books)

---

## Rollout Plan

### Development Phase

1. **Backend changes:**
   - Create and test migration locally
   - Update models, schemas, and routers
   - Run pytest suite
   - Manual API testing with curl/Postman

2. **Frontend changes:**
   - Update types and API client
   - Refactor DateStartedConflictDialog → DateConflictDialog
   - Update BookDrawer logic
   - Add sort controls to main page
   - Create date formatting utilities

3. **Integration testing:**
   - Test full flow: create book → transition status → check conflict dialogs
   - Test all sort options with real data
   - Verify timestamp precision in UI and DB

### Staging Deployment

1. Backup staging database
2. Deploy backend with migration
3. Verify migration success (check DB schema and data)
4. Deploy frontend
5. Smoke test all features
6. Performance testing (if needed)

### Production Deployment

1. **Pre-deployment:**
   - Schedule maintenance window (migration will lock table briefly)
   - Create database backup
   - Prepare rollback procedure

2. **Deployment:**
   - Run migration (should take <5 seconds for typical DB size)
   - Deploy backend
   - Deploy frontend
   - Run health checks

3. **Post-deployment:**
   - Monitor logs for errors
   - Verify sort behavior on production data
   - Check that conflict dialogs work correctly
   - Collect user feedback

### Rollback Procedure

If issues occur:
1. Revert frontend to previous version
2. Revert backend to previous version
3. Run migration downgrade: `alembic downgrade -1`
4. Restore database from backup if needed

---

## Success Metrics

### Functional Success

- [ ] All existing date_started and date_finished values preserved after migration
- [ ] No Python/TypeScript type errors
- [ ] All tests pass (backend + frontend)
- [ ] Conflict dialogs appear when expected (both date_started and date_finished)
- [ ] Sort controls work for all options
- [ ] Timestamp precision is maintained in database

### User Experience Success

- [ ] No user complaints about missing/incorrect dates
- [ ] Conflict dialogs are understandable and easy to use
- [ ] Sort controls are intuitive
- [ ] No performance regressions (page load times <2s)

### Technical Success

- [ ] No errors in server logs related to date handling
- [ ] Database migration completes in <30 seconds
- [ ] API response times unchanged (<200ms for list endpoint)

---

## Future Enhancements

**Not in Scope for This Plan:**

1. **Reading history tracking:** Separate table to track multiple reading sessions per book (re-reading support)
2. **Manual time input:** Allow users to set specific times (not just dates) in the UI
3. **Relative date sorting:** "Books finished this week/month" filters
4. **Export with full timestamps:** CSV/JSON exports with time precision
5. **Audit log:** Track when dates were changed and by whom

---

## Estimated Effort

| Phase | Backend | Frontend | Testing | Total |
|-------|---------|----------|---------|-------|
| Phase 1: Timestamp Migration | 3-4h | - | 1h | 4-5h |
| Phase 2: Date Finished Conflict | 2-3h | - | 1h | 3-4h |
| Phase 3: Frontend Conflict Dialog | - | 2-3h | 1h | 3-4h |
| Phase 4: Sort Controls | 1h | 2-3h | 1h | 4-5h |
| Phase 5: Date Display Utils | - | 1-2h | 30m | 1.5-2.5h |
| Phase 6: Integration Testing | - | - | 2-3h | 2-3h |
| **Total** | **6-8h** | **5-8h** | **6.5-7.5h** | **17.5-23.5h** |

**Estimated time:** ~3-4 working days (assuming 6-8 hours of focused work per day).

---

## Appendices

### Appendix A: Database Schema Changes

**Before:**
```sql
CREATE TABLE book (
    id INTEGER PRIMARY KEY,
    title VARCHAR NOT NULL,
    -- ... other fields ...
    date_added DATETIME NOT NULL,  -- Already has timezone
    date_started DATE,              -- Date only (no time)
    date_finished DATE,             -- Date only (no time)
    -- ... indexes ...
);
```

**After:**
```sql
CREATE TABLE book (
    id INTEGER PRIMARY KEY,
    title VARCHAR NOT NULL,
    -- ... other fields ...
    date_added DATETIME NOT NULL,      -- Unchanged
    date_started DATETIME,             -- Changed to DATETIME
    date_finished DATETIME,            -- Changed to DATETIME
    -- ... indexes ...
);
```

### Appendix B: API Request/Response Examples

**Create Book (Before and After):**
```json
// Request (backwards compatible — both work)
{
  "title": "Dune",
  "reading_status": "currently_reading",
  "date_started": "2026-05-11"  // Date-only (old format, still works)
}

// OR

{
  "title": "Dune",
  "reading_status": "currently_reading",
  "date_started": "2026-05-11T14:30:00Z"  // Full timestamp (new format)
}

// Response (after migration)
{
  "id": 1,
  "title": "Dune",
  "date_added": "2026-05-11T14:30:00Z",
  "date_started": "2026-05-11T14:30:00Z",  // Always returns full timestamp
  "date_finished": null,
  // ... other fields ...
}
```

**Status Transition with Conflict (New Feature):**
```json
// Request
POST /api/books/1/transition-status
{
  "new_status": "read"
}

// Response (conflict detected)
{
  "book": { /* current book state */ },
  "date_conflict": {
    "field": "date_finished",
    "existing_date": "2026-05-01T12:00:00Z",
    "suggested_date": "2026-05-11T15:45:00Z"
  }
}

// Follow-up request (user chose to keep old date)
POST /api/books/1/transition-status
{
  "new_status": "read",
  "force_date_finished": "2026-05-01T12:00:00Z"
}

// Response (no conflict, transition complete)
{
  "book": { /* updated book state with reading_status=read */ },
  "date_conflict": null
}
```

---

## Approval & Next Steps

**This plan is ready for review.**

**Decision points:**
1. ✅ Approve plan and proceed with implementation
2. ⏸️ Request changes or clarifications
3. ❌ Decline and maintain current behavior

**After approval:**
1. Start with Phase 1 (backend migration) — foundational change
2. Phases can be implemented and tested incrementally
3. Each phase can be deployed independently (except Phase 3 depends on Phase 2)

---

**End of Plan**
