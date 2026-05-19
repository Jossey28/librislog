# Implementation Plan: Add Subtitle and Blurb Fields to Books

## Overview

Add two new optional text fields to the Book model:
- **`subtitle`**: Short secondary title (string, optional)
- **`blurb`**: Book description/summary (text, optional, can be long)

Both fields should be fully integrated into all parts of the application:
- Database schema and migrations
- Backend API (create, read, update)
- Import/export (CSV and JSON)
- Search functionality
- Frontend display (detail view with truncation/expansion for blurb)
- Frontend forms (add book, edit book)
- i18n translations

## Requirements

### Display Rules
1. **Detail View**: Show subtitle and blurb only if they are set (non-null and non-empty)
2. **Blurb Truncation**: In detail view, truncate long blurb text and provide "read more" link to expand
3. **Search**: Subtitle and blurb should be searchable via the existing book search query parameter

### Technical Constraints
- Subtitle: short text field (string)
- Blurb: long text field (text/string, no length limit at DB level)
- Both nullable/optional
- Follow existing patterns for optional string fields like `notes`, `publisher`, `author`

---

## 1. Database Changes

### 1.1 Add Columns to `book` Table

**File**: New Alembic migration in `backend/alembic/versions/`

**Migration name**: `add_subtitle_and_blurb_to_book`

**Operations**:
```python
def upgrade() -> None:
    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.add_column(sa.Column("subtitle", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("blurb", sa.Text(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.drop_column("blurb")
        batch_op.drop_column("subtitle")
```

**Notes**:
- Use `sa.String()` for `subtitle` (no length limit, similar to `author`, `publisher`)
- Use `sa.Text()` for `blurb` (long text content)
- Both nullable
- No indexes needed (unless search performance demands it later)

---

## 2. Backend Model Changes

### 2.1 Update `Book` Model

**File**: `backend/app/models.py`

Add two fields to the `Book` class (around line 39-64):

```python
class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    subtitle: Optional[str] = None  # NEW
    author: Optional[str] = Field(default=None, index=True)
    isbn: Optional[str] = Field(default=None, unique=True)
    cover_url: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    page_count: Optional[int] = None
    language: Optional[str] = Field(default=None, max_length=2)
    notes: Optional[str] = None
    blurb: Optional[str] = None  # NEW
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    # ... rest of fields
```

**Rationale**: Place `subtitle` after `title` (semantic grouping), place `blurb` after `notes` (both are longer text content).

---

## 3. Backend Schema Changes

### 3.1 Update Pydantic Schemas

**File**: `backend/app/schemas.py`

Add `subtitle` and `blurb` to:

#### `BookCreate` (lines 28-42)
```python
class BookCreate(SQLModel):
    title: str
    subtitle: Optional[str] = None  # NEW
    author: Optional[str] = None
    isbn: Optional[str] = None
    cover_url: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    page_count: Optional[int] = None
    language: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    blurb: Optional[str] = None  # NEW
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    reading_status: ReadingStatus = ReadingStatus.want_to_read
    date_started: Optional[datetime] = None
    date_finished: Optional[datetime] = None
```

#### `BookUpdate` (lines 45-59)
```python
class BookUpdate(SQLModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None  # NEW
    author: Optional[str] = None
    isbn: Optional[str] = None
    cover_url: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    page_count: Optional[int] = None
    language: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    blurb: Optional[str] = None  # NEW
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    reading_status: Optional[ReadingStatus] = None
    date_started: Optional[datetime] = None
    date_finished: Optional[datetime] = None
```

#### `BookImportCandidate` (lines 62-73)
```python
class BookImportCandidate(SQLModel):
    title: str
    subtitle: Optional[str] = None  # NEW
    author: Optional[str] = None
    isbn: Optional[str] = None
    cover_url: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    page_count: Optional[int] = None
    language: Optional[str] = None
    tags: Optional[str] = None
    blurb: Optional[str] = None  # NEW
    source: str  # "open_library" | "google_books"
```

#### `BookRead` (lines 82-98)
```python
class BookRead(SQLModel):
    id: int
    title: str
    subtitle: Optional[str]  # NEW
    author: Optional[str]
    isbn: Optional[str]
    cover_url: Optional[str]
    publisher: Optional[str]
    published_year: Optional[int]
    page_count: Optional[int]
    language: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str]
    blurb: Optional[str]  # NEW
    rating: Optional[int]
    reading_status: ReadingStatus
    date_added: datetime
    date_started: Optional[datetime]
    date_finished: Optional[datetime]
```

**Notes**:
- Keep field ordering consistent: `subtitle` after `title`, `blurb` after `notes`
- All instances are `Optional[str] = None`

---

## 4. API Changes

### 4.1 Update Book Search

**File**: `backend/app/routers/books.py`

#### Modify `list_books()` function (lines 128-194)

Update the search query logic (around lines 153-165) to include `subtitle` and `blurb`:

```python
if q:
    pattern = f"%{q}%"
    matching_tag_book_ids = select(BookTag.book_id).join(Tag, Tag.id == BookTag.tag_id).where(
        Tag.user_id == current_user.id,
        Tag.name.ilike(pattern),
    )
    statement = statement.where(
        or_(
            Book.title.ilike(pattern),  # type: ignore[union-attr]
            Book.subtitle.ilike(pattern),  # NEW
            Book.author.ilike(pattern),
            Book.blurb.ilike(pattern),  # NEW
            Book.id.in_(matching_tag_book_ids),
        )
    )
```

**Rationale**: Users should be able to search by subtitle or blurb content. This follows the existing pattern for searching title/author/tags.

### 4.2 No Changes Needed for Other Endpoints

The following endpoints already handle all fields generically via schemas:
- `POST /api/books` (create_book)
- `PATCH /api/books/{book_id}` (update_book)
- `GET /api/books/{book_id}` (get_book)

These will automatically support `subtitle` and `blurb` once the schemas are updated.

---

## 5. Import/Export Changes

### 5.1 Update Import Field Definitions

**File**: `backend/app/services/data_import.py`

#### Add to `BOOK_IMPORT_FIELDS` (lines 18-33)
```python
BOOK_IMPORT_FIELDS = [
    "title",
    "subtitle",  # NEW
    "author",
    "isbn",
    "publisher",
    "published_year",
    "page_count",
    "language",
    "tags",
    "notes",
    "blurb",  # NEW
    "rating",
    "reading_status",
    "date_started",
    "date_finished",
    "cover_url",
]
```

#### Add to `_ALIASES` mapping (lines 35-67)
```python
_ALIASES: dict[str, str] = {
    "title": "title",
    "book title": "title",
    "name": "title",
    "subtitle": "subtitle",  # NEW
    "book subtitle": "subtitle",  # NEW
    "author": "author",
    # ... existing mappings ...
    "notes": "notes",
    "blurb": "blurb",  # NEW
    "description": "blurb",  # NEW
    "summary": "blurb",  # NEW
    "synopsis": "blurb",  # NEW
    "rating": "rating",
    # ... rest of mappings
}
```

**Rationale**: Common CSV export formats use "description", "summary", or "synopsis" for blurb-like fields.

#### Update `execute_import()` (lines 393-516)

Add `subtitle` and `blurb` handling in the book creation block (around line 451):

```python
book = Book(
    title=title,
    subtitle=None if row_data.get("subtitle") in (None, "") else str(row_data.get("subtitle")),  # NEW
    author=None if row_data.get("author") in (None, "") else str(row_data.get("author")),
    isbn=None if row_data.get("isbn") in (None, "") else str(row_data.get("isbn")),
    cover_url=cover_url,
    publisher=None if row_data.get("publisher") in (None, "") else str(row_data.get("publisher")),
    published_year=_parse_int(row_data.get("published_year"), "published_year"),
    page_count=page_count,
    language=language,
    notes=None if row_data.get("notes") in (None, "") else str(row_data.get("notes")),
    blurb=None if row_data.get("blurb") in (None, "") else str(row_data.get("blurb")),  # NEW
    rating=rating,
    reading_status=reading_status,
    date_started=date_started,
    date_finished=date_finished,
    user_id=user.id,
)
```

**Notes**: No special validation needed—both are optional strings. Follow the existing pattern for `notes`, `author`, etc.

### 5.2 Update Export Field Definitions

**File**: `backend/app/services/data_export.py`

#### Update `BOOK_CSV_FIELDS` (lines 16-32)
```python
BOOK_CSV_FIELDS = [
    "title",
    "subtitle",  # NEW
    "author",
    "isbn",
    "publisher",
    "published_year",
    "page_count",
    "language",
    "tags",
    "notes",
    "blurb",  # NEW
    "rating",
    "reading_status",
    "date_added",
    "date_started",
    "date_finished",
    "cover_url",
]
```

#### Update `_book_to_dict()` (lines 44-61)
```python
def _book_to_dict(session: Session, book: Book) -> dict:
    return {
        "title": book.title,
        "subtitle": book.subtitle,  # NEW
        "author": book.author,
        "isbn": book.isbn,
        "publisher": book.publisher,
        "published_year": book.published_year,
        "page_count": book.page_count,
        "language": book.language,
        "tags": tags_text_for_book(session, book.id) if book.id else None,
        "notes": book.notes,
        "blurb": book.blurb,  # NEW
        "rating": book.rating,
        "reading_status": book.reading_status.value,
        "date_added": _serialize_datetime(book.date_added),
        "date_started": _serialize_datetime(book.date_started),
        "date_finished": _serialize_datetime(book.date_finished),
        "cover_url": book.cover_url,
    }
```

**Notes**: Both fields will be included in CSV/JSON exports automatically.

---

## 6. Frontend Type Changes

### 6.1 Update TypeScript Types

**File**: `frontend/src/lib/types.ts`

#### Update `Book` interface (lines 3-20)
```typescript
export interface Book {
	id: number;
	title: string;
	subtitle: string | null;  // NEW
	author: string | null;
	isbn: string | null;
	cover_url: string | null;
	publisher: string | null;
	published_year: number | null;
	page_count: number | null;
	language: string | null;
	tags: string | null;
	notes: string | null;
	blurb: string | null;  // NEW
	rating: number | null;
	reading_status: ReadingStatus;
	date_added: string;
	date_started: string | null;
	date_finished: string | null;
}
```

#### Update `BookImportCandidate` interface (lines 22-33)
```typescript
export interface BookImportCandidate {
	title: string;
	subtitle: string | null;  // NEW
	author: string | null;
	isbn: string | null;
	cover_url: string | null;
	publisher: string | null;
	published_year: number | null;
	page_count: number | null;
	language: string | null;
	tags: string | null;
	blurb: string | null;  // NEW
	source: string;
}
```

---

## 7. Frontend Component Changes

### 7.1 Update Book Detail Dialog

**File**: `frontend/src/lib/components/BookDetailDialog.svelte`

#### Add Subtitle Display (after line 250, before author section)

```svelte
<div class="p-4 flex-1 flex flex-col gap-4">
	<!-- Cover image (existing) -->
	
	<!-- NEW: Subtitle section -->
	{#if book.subtitle}
		<div class="text-sm text-base-content/70 italic -mt-2">
			{book.subtitle}
		</div>
	{/if}

	<!-- Author and status (existing line 269-272) -->
	<div class="flex items-center justify-between gap-2">
		<div class="text-sm text-base-content/70">{book.author ?? '-'}</div>
		<span class="badge badge-sm {STATUS_BADGE[book.reading_status]}">{$_(STATUS_LABEL_KEYS[book.reading_status])}</span>
	</div>
```

#### Add Blurb in a Separate "About" Section (below ALL metadata, around line 470)

The blurb should appear below all metadata fields (after notes, publisher, dates, etc.) in its own clearly separated "About" section, NOT in the middle of the metadata list.

```svelte
<!-- After all metadata sections (after notes, dates, publisher - around line 465) -->

<!-- NEW: About section with blurb -->
{#if book.blurb}
	<div class="divider my-2"></div>
	<h3 class="text-sm font-semibold mb-2">{$_('book.about')}</h3>
	
	{@const MAX_BLURB_LENGTH = 300}
	{@const isTruncated = book.blurb.length > MAX_BLURB_LENGTH}
	{@const displayBlurb = blurbExpanded || !isTruncated 
		? book.blurb 
		: book.blurb.slice(0, MAX_BLURB_LENGTH) + '...'}
	
	<div class="text-sm whitespace-pre-wrap break-words rounded border border-base-200 p-3">
		{displayBlurb}
		{#if isTruncated}
			<button 
				type="button" 
				class="link link-primary text-xs ml-2"
				onclick={() => blurbExpanded = !blurbExpanded}
			>
				{blurbExpanded ? $_('common.readLess') : $_('common.readMore')}
			</button>
		{/if}
	</div>
{/if}
```

Add state variable at the top of the script section (around line 26):

```svelte
let blurbExpanded = $state(false);
```

**Notes**:
- Only show subtitle/blurb if they exist
- Truncate blurb at 300 characters
- Add toggle to expand/collapse long blurb
- Follow existing pattern for conditional rendering (see `notes` section)

### 7.2 Update Add Book Modal

**File**: `frontend/src/lib/components/AddBookModal.svelte`

#### Add State Variables (around line 27-38)

```svelte
// Manual form state
let title = $state('');
let subtitle = $state('');  // NEW
let author = $state('');
let isbn = $state('');
let publisher = $state('');
let published_year = $state('');
let page_count = $state('');
let language = $state('');
let tags = $state('');
let notes = $state('');
let blurb = $state('');  // NEW
let rating = $state('');
let status = $state<ReadingStatus>('want_to_read');
let cover_url = $state<string | null>(null);
```

#### Update `reset()` Function (around line 41-55)

```svelte
function reset() {
	title = '';
	subtitle = '';  // NEW
	author = '';
	isbn = '';
	publisher = '';
	published_year = '';
	page_count = '';
	language = '';
	tags = '';
	notes = '';
	blurb = '';  // NEW
	rating = '';
	status = defaultStatus;
	cover_url = null;
	activeTab = 'manual';
}
```

#### Update `submitManual()` Function (around line 57-89)

```svelte
async function submitManual() {
	if (!title.trim()) return;
	submitting = true;
	try {
		const book = await api.books.create({
			title: title.trim(),
			subtitle: subtitle || null,  // NEW
			author: author || null,
			isbn: isbn || null,
			publisher: publisher || null,
			published_year: published_year ? parseInt(published_year) : null,
			page_count: page_count ? parseInt(page_count) : null,
			language: language || null,
			tags: tags || null,
			notes: notes || null,
			blurb: blurb || null,  // NEW
			rating: rating ? parseInt(rating) : null,
			reading_status: status,
			cover_url: cover_url || null
		});
		onAdded?.(book);
		open = false;
		reset();
	} catch (e: unknown) {
		// ... error handling
	}
}
```

#### Add Form Fields (after title field, around line 126)

```svelte
<label class="form-control">
	<span class="label label-text">{$_('book.title')} <span class="text-error">*</span></span>
	<input class="input input-bordered input-sm" bind:value={title} required />
</label>

<!-- NEW: Subtitle field -->
<label class="form-control">
	<span class="label label-text">{$_('book.subtitle')}</span>
	<input class="input input-bordered input-sm" bind:value={subtitle} />
</label>

<div class="grid grid-cols-2 gap-2">
	<!-- existing author, isbn, etc. -->
</div>
```

Add blurb field after notes (around line 173):

```svelte
<label class="form-control">
	<span class="label label-text">{$_('book.notes')}</span>
	<textarea class="textarea textarea-bordered text-sm" rows="2" bind:value={notes}></textarea>
</label>

<!-- NEW: Blurb field -->
<label class="form-control">
	<span class="label label-text">{$_('book.blurb')}</span>
	<textarea class="textarea textarea-bordered text-sm" rows="3" bind:value={blurb}></textarea>
</label>
```

**Notes**:
- Subtitle: single-line input below title
- Blurb: multi-line textarea (3 rows) below notes
- Both optional (no required marker)

### 7.3 Update Book Card (Optional Enhancement)

**File**: `frontend/src/lib/components/BookCard.svelte`

**Decision**: Do NOT show subtitle/blurb on card view—cards are compact and already have title/author/status/progress. Subtitle and blurb are detail-level information.

**No changes needed** to BookCard.svelte.

---

## 8. i18n Translation Keys

### 8.1 English Translations

**File**: `frontend/src/lib/i18n/locales/en.json`

Add to the `book` section (around line 94-120):

```json
"book": {
  "title": "Title",
  "subtitle": "Subtitle",
  "author": "Author",
  "status": "Status",
  "isbn": "ISBN",
  "publisher": "Publisher",
  "year": "Year",
  "pages": "Pages",
  "language": "Language",
  "tags": "Tags",
  "notes": "Notes",
  "blurb": "Description",
  "about": "About",
  // ... existing keys
}
```

Add to `common` section (around line 65-93):

```json
"common": {
  "search": "Search",
  "save": "Save",
  "edit": "Edit",
  "cancel": "Cancel",
  "readMore": "Read more",
  "readLess": "Read less",
  // ... existing keys
}
```

### 8.2 German Translations

**File**: `frontend/src/lib/i18n/locales/de.json`

Add corresponding German translations:

```json
"book": {
  "title": "Titel",
  "subtitle": "Untertitel",
  "author": "Autor",
  "blurb": "Beschreibung",
  "about": "Über das Buch",
  // ... existing keys
}
```

```json
"common": {
  "readMore": "Mehr lesen",
  "readLess": "Weniger lesen",
  // ... existing keys
}
```

**Notes**: 
- "blurb" translates to "Description" (EN) / "Beschreibung" (DE)
- "subtitle" is straightforward: "Subtitle" (EN) / "Untertitel" (DE)

---

## 9. Testing Updates

### 9.1 Backend Tests

**Files to Update**:
- `backend/tests/test_books.py`
- `backend/tests/test_import.py`
- `backend/tests/test_export.py`

#### `test_books.py`

Add `subtitle` and `blurb` to test book creation:

```python
def test_create_book_with_subtitle_and_blurb(client: TestClient):
    payload = {
        "title": "Test Book",
        "subtitle": "A Comprehensive Guide",
        "blurb": "This is a detailed description of the book content.",
        "reading_status": "want_to_read"
    }
    resp = client.post("/api/books", json=payload)
    assert resp.status_code == 201
    book = resp.json()
    assert book["subtitle"] == "A Comprehensive Guide"
    assert book["blurb"] == "This is a detailed description of the book content."
```

Test search includes subtitle and blurb:

```python
def test_search_finds_subtitle(client: TestClient):
    # Create book with subtitle
    client.post("/api/books", json={
        "title": "Main Title",
        "subtitle": "Unique Subtitle",
        "reading_status": "want_to_read"
    })
    # Search by subtitle
    resp = client.get("/api/books?q=Unique")
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert books[0]["subtitle"] == "Unique Subtitle"

def test_search_finds_blurb(client: TestClient):
    # Create book with blurb
    client.post("/api/books", json={
        "title": "Book Title",
        "blurb": "A story about dragons and magic",
        "reading_status": "want_to_read"
    })
    # Search by blurb content
    resp = client.get("/api/books?q=dragons")
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert "dragons" in books[0]["blurb"].lower()
```

#### `test_import.py`

Add tests for importing books with subtitle/blurb:

```python
def test_import_with_subtitle_and_blurb(client: TestClient, csv_with_subtitle_blurb):
    # Upload CSV with subtitle and blurb columns
    resp = client.post("/api/data/import/parse", files={"file": csv_with_subtitle_blurb})
    file_id = resp.json()["file_id"]
    
    mapping = {
        "title": "title",
        "subtitle": "subtitle",
        "blurb": "description"  # test alias mapping
    }
    
    # Execute import
    resp = client.post("/api/data/import/run", json={
        "file_id": file_id,
        "mapping": mapping,
        "import_mode": "rollback_all"
    })
    # ... assertions
```

#### `test_export.py`

Verify CSV/JSON exports include subtitle and blurb:

```python
def test_export_includes_subtitle_and_blurb(client: TestClient):
    # Create book with subtitle and blurb
    client.post("/api/books", json={
        "title": "Export Test",
        "subtitle": "Test Subtitle",
        "blurb": "Test blurb content",
        "reading_status": "read"
    })
    
    # Export as CSV
    resp = client.post("/api/data/export", json={
        "datasets": ["books"],
        "format": "csv"
    })
    
    # Parse and verify
    # ... check CSV contains subtitle and blurb columns
```

### 9.2 Frontend Tests (Manual Testing Checklist)

**Test Cases**:

1. **Add Book Modal**
   - [ ] Subtitle and blurb fields are visible
   - [ ] Can create book with subtitle only
   - [ ] Can create book with blurb only
   - [ ] Can create book with both
   - [ ] Can create book with neither (both optional)

2. **Book Detail Dialog**
   - [ ] Subtitle appears below title (if set)
   - [ ] Subtitle does not appear if empty
   - [ ] Blurb appears in dedicated section (if set)
   - [ ] Blurb does not appear if empty
   - [ ] Long blurb is truncated at 300 chars
   - [ ] "Read more" button appears for long blurbs
   - [ ] "Read less" button appears after expansion
   - [ ] Clicking toggle expands/collapses blurb

3. **Search**
   - [ ] Search by subtitle content returns correct books
   - [ ] Search by blurb content returns correct books
   - [ ] Search by title still works

4. **Import**
   - [ ] CSV with "subtitle" column imports correctly
   - [ ] CSV with "description"/"summary"/"synopsis" maps to blurb
   - [ ] Books without subtitle/blurb import correctly
   - [ ] Validation accepts subtitle and blurb fields

5. **Export**
   - [ ] CSV export includes subtitle and blurb columns
   - [ ] JSON export includes subtitle and blurb fields
   - [ ] Empty subtitle/blurb export as null/empty

6. **Edit Book**
   - [ ] Can add subtitle to existing book
   - [ ] Can add blurb to existing book
   - [ ] Can update subtitle
   - [ ] Can update blurb
   - [ ] Can clear subtitle (set to empty)
   - [ ] Can clear blurb (set to empty)

---

## 10. Implementation Order

Implement in the following sequence to maintain a working system at each step:

### Phase 1: Backend Foundation
1. **Create database migration** (`add_subtitle_and_blurb_to_book.py`)
   - Add columns to book table
   - Run migration: `alembic upgrade head`
   - Test: verify columns exist in SQLite DB

2. **Update backend models** (`models.py`)
   - Add `subtitle` and `blurb` to `Book` model

3. **Update backend schemas** (`schemas.py`)
   - Add fields to `BookCreate`, `BookUpdate`, `BookImportCandidate`, `BookRead`

4. **Test API endpoints**
   - Create book with subtitle/blurb
   - Update book with subtitle/blurb
   - Verify API responses include new fields

### Phase 2: Search & API
5. **Update search functionality** (`routers/books.py`)
   - Add `Book.subtitle` and `Book.blurb` to search query
   - Test: search by subtitle/blurb content

### Phase 3: Import/Export
6. **Update import service** (`services/data_import.py`)
   - Add to `BOOK_IMPORT_FIELDS`
   - Add aliases to `_ALIASES`
   - Update `execute_import()` to handle new fields
   - Test: import CSV with subtitle/blurb

7. **Update export service** (`services/data_export.py`)
   - Add to `BOOK_CSV_FIELDS`
   - Update `_book_to_dict()`
   - Test: export includes subtitle/blurb

### Phase 4: Frontend Types & Components
8. **Update TypeScript types** (`types.ts`)
   - Add `subtitle` and `blurb` to `Book` and `BookImportCandidate`

9. **Update AddBookModal** (`AddBookModal.svelte`)
   - Add state variables
   - Add form fields (subtitle input, blurb textarea)
   - Update submit function
   - Test: create books with new fields

10. **Update BookDetailDialog** (`BookDetailDialog.svelte`)
    - Add subtitle display section
    - Add blurb section with truncation logic
    - Add "read more/less" toggle
    - Test: view books with subtitle/blurb

### Phase 5: i18n & Testing
11. **Add translation keys**
    - English (`en.json`)
    - German (`de.json`)
    - Test: verify translations display correctly

12. **Write backend tests**
    - `test_books.py`: CRUD with subtitle/blurb, search
    - `test_import.py`: import with subtitle/blurb
    - `test_export.py`: export with subtitle/blurb
    - Run: `pytest backend/tests/`

13. **Manual frontend testing**
    - Use checklist from section 9.2
    - Test all user flows

### Phase 6: Documentation & Cleanup
14. **Update any relevant documentation**
    - API docs (if separate from code)
    - User guide (if exists)

15. **Code review & polish**
    - Check code style consistency
    - Verify error handling
    - Ensure no console errors

---

## 11. Edge Cases & Considerations

### Data Validation
- **No length limits**: Both fields are unrestricted text (follow `notes` pattern)
- **Empty strings vs null**: Treat empty strings as null (follow existing convention in `data_import.py`)
- **Special characters**: No special handling needed (SQLite handles UTF-8)

### Search Performance
- **Initial implementation**: No indexes on subtitle/blurb (LIKE query on text fields)
- **If performance issues arise**: Consider full-text search (SQLite FTS5) in future
- **Current scope**: Use simple `ILIKE` pattern matching (existing approach)

### UI/UX
- **Blurb truncation length**: 300 characters (configurable via constant)
- **Subtitle placement**: Directly below title in header area, italicized, subtle styling
- **Blurb placement**: Separate "About" section below ALL metadata, with section divider and heading — NOT interleaved with metadata fields
- **Mobile responsiveness**: Ensure blurb textarea and display work on mobile

### Migration Safety
- **Backward compatibility**: Both fields nullable—existing data unaffected
- **Rollback**: Migration includes downgrade to remove columns
- **Data loss**: No existing data affected (new columns only)

### Import/Export Compatibility
- **Legacy exports**: Old exports without subtitle/blurb will import fine (fields optional)
- **Field mapping**: Support common aliases (description, summary, synopsis → blurb)
- **Round-trip**: Export → Import should preserve subtitle and blurb exactly

---

## 12. Success Criteria

Implementation is complete when:

- ✅ Database has `subtitle` and `blurb` columns
- ✅ API accepts and returns subtitle/blurb for all book operations
- ✅ Search finds books by subtitle and blurb content
- ✅ Import handles CSV/JSON with subtitle/blurb (including aliases)
- ✅ Export includes subtitle/blurb in CSV/JSON
- ✅ Add Book Modal has subtitle input and blurb textarea
- ✅ Book Detail Dialog displays subtitle and blurb (with truncation)
- ✅ "Read more/less" toggle works for long blurbs
- ✅ Translation keys exist for EN and DE
- ✅ All backend tests pass
- ✅ Manual frontend testing checklist complete
- ✅ No regression in existing features

---

## 13. Estimated Effort

- **Backend (DB, models, schemas, API, import/export)**: 2-3 hours
- **Frontend (types, components, forms)**: 2-3 hours
- **Testing (backend tests + manual QA)**: 1-2 hours
- **i18n & documentation**: 0.5-1 hour

**Total**: 5.5-9 hours

---

## 14. Future Enhancements (Out of Scope)

- Full-text search indexing (FTS5) for subtitle/blurb
- Markdown/rich text formatting for blurb
- Character count indicator in blurb textarea
- Automatically fetch subtitle/blurb from external APIs (Google Books, OpenLibrary)
- Display blurb on hover in library grid view
- Separate "description" vs "synopsis" fields

---

## Appendix: Key File Summary

| File | Changes |
|------|---------|
| `backend/alembic/versions/XXXX_add_subtitle_and_blurb_to_book.py` | New migration |
| `backend/app/models.py` | Add `subtitle`, `blurb` to `Book` |
| `backend/app/schemas.py` | Add to `BookCreate`, `BookUpdate`, `BookImportCandidate`, `BookRead` |
| `backend/app/routers/books.py` | Update search to include subtitle/blurb |
| `backend/app/services/data_import.py` | Add to import fields, aliases, execution |
| `backend/app/services/data_export.py` | Add to export fields and dict mapping |
| `backend/tests/test_books.py` | Add tests for CRUD and search |
| `backend/tests/test_import.py` | Add import tests |
| `backend/tests/test_export.py` | Add export tests |
| `frontend/src/lib/types.ts` | Add to `Book`, `BookImportCandidate` |
| `frontend/src/lib/components/AddBookModal.svelte` | Add form fields, state, submit logic |
| `frontend/src/lib/components/BookDetailDialog.svelte` | Add display sections with truncation |
| `frontend/src/lib/i18n/locales/en.json` | Add translation keys |
| `frontend/src/lib/i18n/locales/de.json` | Add translation keys |

**Total files modified**: ~14 files  
**New files created**: 1 (migration)
