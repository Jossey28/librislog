# LibrisLog — Book Detail View/Dialog

**Status**: 📋 **PLANNED**  
**Date**: 2026-05-12

## Goal

Replace the current click-to-edit pattern with a read-only detail view that separates viewing from editing:

1. **Clicking a book** opens a read-only **BookDetailDialog** showing all book information
2. **Detail dialog** includes an "Edit" button that opens the existing **BookDrawer** (edit dialog)
3. **Delete button** moves from edit dialog to detail view dialog
4. **Improved UX**: Clear separation between viewing and editing actions

---

## Current Behavior

### Current Flow

1. User clicks on a `BookCard` in the library view
2. `onClick` handler in `/routes/library/+page.svelte` (line 186) calls `openDrawer(book)`
3. This directly opens the `BookDrawer` component in edit mode
4. User can edit all fields and delete the book from this same drawer

### Current Implementation

**BookCard.svelte** (lines 23-25):
```svelte
<button
    class="card card-compact bg-base-100 shadow hover:shadow-md transition-shadow cursor-pointer w-full text-left"
    onclick={() => onClick(book)}
>
```

**library/+page.svelte** (lines 92-95):
```svelte
function openDrawer(book: Book) {
    selectedBook = book;
    drawerOpen = true;
}
```

**BookDrawer.svelte**:
- Full editing form with all fields (lines 228-320)
- Save button (line 297-299)
- Delete button with confirmation (lines 300-318)
- Can be closed via X button or Escape key (no backdrop close per plan 13)

---

## Requirements

### Functional Requirements

1. **New BookDetailDialog Component**:
   - Read-only display of all book information
   - Clean, organized layout showing:
     - Cover image (if available)
     - Title, author, ISBN
     - Publisher, published year, page count, genre
     - Reading status with visual badge
     - Star rating (read-only)
     - Date started, date finished
     - Notes
   - "Edit" button to open BookDrawer
   - "Delete" button (with confirmation) to delete the book
   - "Close" button (X) to dismiss the dialog
   - Escape key support

2. **Modified Click Flow**:
   - BookCard click → opens BookDetailDialog (new)
   - BookDetailDialog "Edit" button → opens BookDrawer (existing)
   - BookDrawer remains unchanged in functionality, but no longer directly opened from card click

3. **Delete Action Migration**:
   - Remove delete button from BookDrawer
   - Add delete button to BookDetailDialog
   - Maintain existing delete confirmation pattern
   - Keep same delete API call and callback chain

4. **Dialog Management**:
   - Support three dialog states: closed, detail view open, edit mode open
   - Proper dialog stacking when detail is open and user clicks "Edit"
   - Closing edit dialog should return to detail dialog (not close both)
   - Closing detail dialog should close everything

### Non-Functional Requirements

1. **Consistency**: Follow existing dialog patterns (same close behavior as plan #13)
2. **Accessibility**: Proper ARIA labels and keyboard navigation
3. **Responsive**: Work on mobile and desktop
4. **Styling**: Match existing DaisyUI theme and component patterns
5. **i18n**: Use translation keys for all user-facing text

---

## Technical Design

### Component Architecture

```
BookCard
    ↓ onClick
library/+page.svelte (openDetailView)
    ↓ opens
BookDetailDialog (NEW)
    ├─ "Edit" button → opens BookDrawer (existing)
    └─ "Delete" button → deletes book + closes dialog
```

### New Component: BookDetailDialog.svelte

**Location**: `frontend/src/lib/components/BookDetailDialog.svelte`

**Props**:
```typescript
let {
    book = $bindable(null),
    open = $bindable(false),
    onEdit,
    onDelete
}: {
    book?: Book | null;
    open?: boolean;
    onEdit?: (book: Book) => void;
    onDelete?: (id: number) => void;
} = $props();
```

**Key Features**:
- Modal overlay pattern (similar to existing dialogs)
- No backdrop click-to-close (per plan #13)
- Read-only display with formatted data
- Action buttons: Edit, Delete (with confirmation), Close
- Proper z-index layering for dialog stacking

**Layout Structure**:
```svelte
{#if open && book}
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black/40 z-40" 
         role="button" 
         tabindex="-1"
         onkeydown={(e) => e.key === 'Escape' && (open = false)}
    ></div>

    <!-- Dialog Panel -->
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="bg-base-100 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b">
                <h2 class="text-xl font-bold">{book.title}</h2>
                <button onclick={() => (open = false)}>✕</button>
            </div>

            <!-- Content (scrollable) -->
            <div class="flex-1 overflow-y-auto p-6">
                <!-- Cover + Metadata Grid -->
                <!-- Status Badge -->
                <!-- Rating (read-only) -->
                <!-- Dates -->
                <!-- Notes -->
            </div>

            <!-- Footer Actions -->
            <div class="flex gap-2 p-4 border-t">
                <button class="btn btn-primary" onclick={handleEdit}>
                    {$_('common.edit')}
                </button>
                <button class="btn btn-error btn-outline" onclick={handleDelete}>
                    {$_('common.delete')}
                </button>
                <button class="btn btn-ghost" onclick={() => (open = false)}>
                    {$_('common.close')}
                </button>
            </div>
        </div>
    </div>
{/if}
```

### Modified Component: library/+page.svelte

**Changes**:
1. Add new state for detail dialog:
```typescript
let detailDialogOpen = $state(false);
```

2. Rename/modify click handler:
```typescript
function openDetailView(book: Book) {
    selectedBook = book;
    detailDialogOpen = true;
}
```

3. Add handler for opening edit from detail:
```typescript
function openEditFromDetail(book: Book) {
    // Detail dialog stays open (or closes, depending on UX preference)
    detailDialogOpen = false; // Close detail first
    drawerOpen = true;        // Open edit drawer
}
```

4. Update BookCard usage (line 186):
```svelte
<BookCard {book} onClick={openDetailView} />
```

5. Add new dialog component before BookDrawer:
```svelte
<BookDetailDialog
    bind:book={selectedBook}
    bind:open={detailDialogOpen}
    onEdit={openEditFromDetail}
    onDelete={handleDelete}
/>

<BookDrawer
    bind:book={selectedBook}
    bind:open={drawerOpen}
    onSave={handleSave}
    onDelete={handleDelete}  <!-- Remove this line later -->
/>
```

### Modified Component: BookDrawer.svelte

**Changes**:
1. Remove delete button UI (lines 300-318)
2. Remove delete-related state:
```typescript
// DELETE THESE:
let deleting = $state(false);
let confirmDelete = $state(false);

// DELETE THIS FUNCTION:
async function deleteBook() { ... }
```

3. Simplify footer to only have Save button:
```svelte
<div class="flex gap-2 mt-auto pt-2">
    <button type="submit" class="btn btn-primary btn-sm flex-1" disabled={saving}>
        {saving ? $_('common.saving') : $_('common.save')}
    </button>
</div>
```

4. Update props (remove onDelete callback since it's now in detail dialog):
```typescript
let {
    book = $bindable(null),
    open = $bindable(false),
    onSave
}: {
    book?: Book | null;
    open?: boolean;
    onSave?: (book: Book) => void;
} = $props();
```

---

## Implementation Steps

### Step 1: Create BookDetailDialog Component

**File**: `frontend/src/lib/components/BookDetailDialog.svelte`

1. Create new Svelte component file
2. Define props interface with $bindable patterns
3. Implement modal overlay structure:
   - Backdrop (no click-to-close)
   - Centered dialog panel with max-width
   - Header with title and close button
   - Scrollable content area
   - Footer with action buttons

4. Build content layout:
   - Two-column layout for larger screens
   - Left: Cover image (if available) with placeholder fallback
   - Right: Metadata grid
   - Full-width sections below for notes

5. Display all book fields (read-only):
   - Title (header)
   - Author
   - ISBN (with monospace font)
   - Publisher, published year
   - Page count, genre
   - Reading status (with colored badge matching BookCard)
   - Star rating (using existing StarRating component with readonly=true)
   - Date started (formatted, hide if null)
   - Date finished (formatted, hide if null)
   - Notes (textarea-like display, hide if empty)

6. Implement action handlers:
   ```typescript
   function handleEdit() {
       if (!book) return;
       onEdit?.(book);
   }

   let confirmingDelete = $state(false);
   let deleting = $state(false);

   async function handleDelete() {
       if (!book || !confirmingDelete) {
           confirmingDelete = true;
           return;
       }
       
       deleting = true;
       try {
           await api.books.delete(book.id);
           onDelete?.(book.id);
           open = false;
       } catch (e: unknown) {
           toasts.add(
               e instanceof Error ? e.message : $_('common.actionFailed', { values: { action: $_('common.delete') } }),
               'error'
           );
       } finally {
           deleting = false;
           confirmingDelete = false;
       }
   }
   ```

7. Add i18n translation keys (if needed):
   - Most keys already exist: `common.edit`, `common.delete`, `common.close`, `common.confirm`, etc.
   - Verify all book field labels exist: `book.title`, `book.author`, `book.isbn`, etc.

### Step 2: Update library/+page.svelte

**File**: `frontend/src/routes/library/+page.svelte`

1. Add import for new component:
```typescript
import BookDetailDialog from '$lib/components/BookDetailDialog.svelte';
```

2. Add state variable:
```typescript
let detailDialogOpen = $state(false);
```

3. Modify `openDrawer` to `openDetailView`:
```typescript
function openDetailView(book: Book) {
    selectedBook = book;
    detailDialogOpen = true;
}
```

4. Add new handler for edit-from-detail:
```typescript
function openEditFromDetail(book: Book) {
    detailDialogOpen = false;
    drawerOpen = true;
}
```

5. Update BookCard onClick (line 186):
```svelte
<BookCard {book} onClick={openDetailView} />
```

6. Add BookDetailDialog before BookDrawer (around line 192):
```svelte
<BookDetailDialog
    bind:book={selectedBook}
    bind:open={detailDialogOpen}
    onEdit={openEditFromDetail}
    onDelete={handleDelete}
/>

<BookDrawer
    bind:book={selectedBook}
    bind:open={drawerOpen}
    onSave={handleSave}
/>
```

### Step 3: Simplify BookDrawer Component

**File**: `frontend/src/lib/components/BookDrawer.svelte`

1. Remove delete-related state variables (lines ~24-25):
```typescript
// DELETE:
let deleting = $state(false);
let confirmDelete = $state(false);
```

2. Remove `deleteBook()` function (lines ~179-196)

3. Remove delete confirmation reset in $effect (line ~61):
```typescript
// DELETE:
confirmDelete = false;
```

4. Update props to remove `onDelete` callback (lines 11-21):
```typescript
let {
    book = $bindable(null),
    open = $bindable(false),
    onSave
}: {
    book?: Book | null;
    open?: boolean;
    onSave?: (book: Book) => void;
} = $props();
```

5. Simplify action buttons (lines 296-319):
```svelte
<div class="flex gap-2 mt-auto pt-2">
    <button type="submit" class="btn btn-primary btn-sm flex-1" disabled={saving}>
        {saving ? $_('common.saving') : $_('common.save')}
    </button>
</div>
```

### Step 4: Handle Dialog Stacking Edge Cases

**Considerations**:
1. Should detail dialog stay open when user clicks "Edit"?
   - **Decision**: Close detail dialog, open edit drawer (cleaner UX)
   - Alternative: Keep detail open with lower z-index (more complex)

2. Should edit drawer return to detail on save?
   - **Decision**: Close edit drawer after save (current behavior maintained)
   - Detail dialog is already closed, so this is natural

3. What if user opens edit, closes without saving?
   - **Decision**: Return to closed state (detail was closed when edit opened)

4. Escape key behavior:
   - Detail open: Close detail
   - Edit open: Close edit
   - Both behaviors already implemented per plan #13

### Step 5: Styling and Polish

1. **Cover Display**:
   - Use aspect-ratio for consistent sizing
   - Add subtle border or shadow
   - Fallback icon for books without cover (reuse from BookCard)

2. **Metadata Grid**:
   - Use DaisyUI's form-control pattern for consistent spacing
   - Label + value pairs with proper typography hierarchy
   - Grey out null/empty values or hide them entirely

3. **Status Badge**:
   - Reuse exact badge styling from BookCard (lines 15-20):
   ```typescript
   const STATUS_BADGE: Record<string, string> = {
       want_to_read: 'badge-info',
       currently_reading: 'badge-warning',
       read: 'badge-success',
       did_not_finish: 'badge-error'
   };
   ```

4. **Action Buttons**:
   - Primary: Edit button (most common action)
   - Error outline: Delete button (destructive but secondary)
   - Ghost: Close button (least prominent)
   - Delete confirmation: Show confirm/cancel buttons similar to BookDrawer pattern

5. **Responsive Design**:
   - Mobile: Single column, cover above metadata
   - Tablet+: Two columns, cover left, metadata right
   - Use Tailwind responsive classes: `md:grid-cols-2`, `md:flex-row`, etc.

---

## Data Flow

### Opening Detail View
```
User clicks BookCard
    ↓
library/+page.svelte::openDetailView(book)
    ↓
selectedBook = book
detailDialogOpen = true
    ↓
BookDetailDialog renders with book data
```

### Opening Edit from Detail
```
User clicks "Edit" in BookDetailDialog
    ↓
BookDetailDialog::handleEdit()
    ↓
onEdit?.(book) callback
    ↓
library/+page.svelte::openEditFromDetail()
    ↓
detailDialogOpen = false
drawerOpen = true
    ↓
BookDrawer opens for editing
```

### Saving Changes
```
User clicks "Save" in BookDrawer
    ↓
BookDrawer::save()
    ↓
API call: api.books.update(...)
    ↓
onSave?.(updated) callback
    ↓
library/+page.svelte::handleSave(updated)
    ↓
Updates books array
drawerOpen = false (from save function)
    ↓
User returns to library view
```

### Deleting Book
```
User clicks "Delete" in BookDetailDialog
    ↓
BookDetailDialog::handleDelete() - first click
    ↓
confirmingDelete = true
Button text changes to "Confirm"
    ↓
User clicks "Confirm"
    ↓
BookDetailDialog::handleDelete() - second click
    ↓
API call: api.books.delete(book.id)
    ↓
onDelete?.(book.id) callback
    ↓
library/+page.svelte::handleDelete(id)
    ↓
Removes book from books array
Triggers background refresh
detailDialogOpen = false (from handleDelete)
    ↓
User returns to library view
```

---

## Testing Strategy

### Manual Testing Checklist

#### Unit/Component Level

**BookDetailDialog.svelte**:
- [ ] Opens when `open` prop is true
- [ ] Displays all book fields correctly
- [ ] Handles books with missing/null fields gracefully
- [ ] Closes via X button
- [ ] Closes via Escape key
- [ ] Does NOT close via backdrop click
- [ ] Edit button calls `onEdit` callback
- [ ] Delete button shows confirmation on first click
- [ ] Delete button calls API and `onDelete` on second click
- [ ] Shows loading state during delete operation
- [ ] Shows error toast if delete fails
- [ ] Displays cover image if available
- [ ] Shows placeholder icon if no cover
- [ ] Status badge matches BookCard styling
- [ ] Star rating displays correctly (read-only)
- [ ] Formatted dates display correctly
- [ ] Notes section hidden if empty
- [ ] Responsive layout works on mobile and desktop

**library/+page.svelte**:
- [ ] Clicking BookCard opens detail dialog (not edit drawer)
- [ ] `selectedBook` is set correctly
- [ ] `detailDialogOpen` state toggles correctly

**BookDrawer.svelte**:
- [ ] Delete button is removed from UI
- [ ] Delete-related state variables removed
- [ ] `deleteBook()` function removed
- [ ] Props no longer include `onDelete`
- [ ] Save functionality still works correctly
- [ ] No regressions in edit functionality

#### Integration Testing

**Detail → Edit Flow**:
- [ ] Open book detail dialog
- [ ] Click "Edit" button
- [ ] Edit dialog opens
- [ ] Detail dialog closes
- [ ] Edit form is populated with book data
- [ ] Make changes and save
- [ ] Edit dialog closes
- [ ] Book list updates with changes

**Detail → Delete Flow**:
- [ ] Open book detail dialog
- [ ] Click "Delete" button
- [ ] Button changes to "Confirm"
- [ ] Click "Confirm"
- [ ] Book is deleted from backend
- [ ] Book removed from list
- [ ] Detail dialog closes
- [ ] Background refresh triggered
- [ ] No errors in console

**Cancel/Close Scenarios**:
- [ ] Open detail → close → book list unchanged
- [ ] Open detail → open edit → close edit → return to book list (not detail)
- [ ] Open detail → delete → cancel → detail stays open

**Error Handling**:
- [ ] Delete fails → error toast shown
- [ ] Delete fails → dialog stays open
- [ ] Delete fails → confirm state resets

### Playwright E2E Tests

**Note**: The project uses Vitest but has no Playwright setup yet. E2E tests should be added when Playwright is configured.

**Test File**: `tests/e2e/book-detail-dialog.spec.ts` (future)

**Test Cases**:
```typescript
test.describe('Book Detail Dialog', () => {
    test('should open detail dialog when clicking a book card', async ({ page }) => {
        // Navigate to library
        // Click on a book card
        // Verify detail dialog appears
        // Verify book data is displayed correctly
    });

    test('should open edit dialog from detail view', async ({ page }) => {
        // Open detail dialog
        // Click "Edit" button
        // Verify edit drawer opens
        // Verify detail dialog closes
    });

    test('should delete book from detail dialog', async ({ page }) => {
        // Open detail dialog
        // Click "Delete" button
        // Verify confirmation state
        // Click "Confirm"
        // Verify book is removed from list
        // Verify dialog closes
    });

    test('should not close on backdrop click', async ({ page }) => {
        // Open detail dialog
        // Click on backdrop area
        // Verify dialog remains open
    });

    test('should close on escape key', async ({ page }) => {
        // Open detail dialog
        // Press Escape key
        // Verify dialog closes
    });
});
```

### Backend Tests

**No backend changes required** — this is a frontend-only feature using existing API endpoints.

Existing tests remain valid:
- `backend/tests/test_books.py` (no changes needed)

---

## Migration Notes

### Breaking Changes

**None** — This is a purely additive change that enhances the existing UI without breaking any APIs or changing data models.

### Backward Compatibility

- All existing API calls remain unchanged
- BookDrawer can still be used independently (e.g., from AddBookModal)
- No changes to backend required
- No database migrations needed

### Rollback Plan

If issues arise:
1. Revert changes to `library/+page.svelte` (restore `openDrawer` handler)
2. Revert changes to BookCard `onClick` prop
3. Delete `BookDetailDialog.svelte` file
4. Restore delete button in `BookDrawer.svelte`
5. Restore `onDelete` prop in BookDrawer

Git revert is straightforward since all changes are contained to frontend components.

---

## i18n Translation Keys

### Required Keys (verify existence)

Most keys already exist in the application. Verify these are present:

```json
{
  "common": {
    "edit": "Edit",
    "delete": "Delete",
    "close": "Close",
    "confirm": "Confirm",
    "cancel": "Cancel",
    "saving": "Saving...",
    "deleting": "Deleting...",
    "rating": "Rating"
  },
  "book": {
    "title": "Title",
    "author": "Author",
    "isbn": "ISBN",
    "publisher": "Publisher",
    "year": "Publication Year",
    "pages": "Pages",
    "genre": "Genre",
    "status": "Status",
    "dateStarted": "Date Started",
    "dateFinished": "Date Finished",
    "notes": "Notes",
    "coverOf": "Cover of {title}"
  },
  "status": {
    "want_to_read": "Want to Read",
    "currently_reading": "Currently Reading",
    "read": "Read",
    "did_not_finish": "Did Not Finish"
  }
}
```

### New Keys (if needed)

If any new labels are introduced, add to translation files:
- `frontend/src/lib/i18n/locales/en.json`
- `frontend/src/lib/i18n/locales/de.json` (if applicable)

---

## Success Criteria

### User Experience
- [ ] Clicking a book opens a read-only detail view (not edit mode)
- [ ] Detail view shows all book information in an organized layout
- [ ] "Edit" button in detail view opens the edit dialog
- [ ] Delete action is accessible from detail view
- [ ] Dialog behavior is consistent with other dialogs (no accidental closes)
- [ ] Smooth transition between detail and edit views

### Code Quality
- [ ] New component follows existing patterns (DaisyUI, Svelte 5 runes)
- [ ] Proper TypeScript types throughout
- [ ] No console errors or warnings
- [ ] Code is DRY (reuses existing components like StarRating)
- [ ] Comments explain non-obvious logic
- [ ] i18n used for all user-facing text

### Performance
- [ ] No unnecessary re-renders
- [ ] Dialog opens/closes smoothly
- [ ] No lag when switching between detail and edit

### Accessibility
- [ ] Keyboard navigation works correctly
- [ ] Focus management is proper
- [ ] ARIA labels are present
- [ ] Screen reader friendly
- [ ] Color contrast meets WCAG standards

---

## Risks and Mitigations

### Risk 1: Dialog Stacking Z-Index Issues

**Risk**: Detail dialog and edit drawer may have z-index conflicts when transitioning.

**Mitigation**: 
- Close detail dialog before opening edit drawer (chosen approach)
- Use consistent z-index values across all dialogs
- Test on multiple browsers

### Risk 2: State Sync Issues

**Risk**: `selectedBook` may get out of sync when switching between dialogs.

**Mitigation**:
- Use same `selectedBook` reference for both dialogs
- Clear state properly in handlers
- Test edge cases (rapid clicking, keyboard navigation)

### Risk 3: Inconsistent Delete Behavior

**Risk**: Moving delete action may confuse users familiar with current UI.

**Mitigation**:
- Keep same confirmation pattern
- Visual consistency in button styling
- This is a UX improvement, but document in changelog

### Risk 4: Translation Keys Missing

**Risk**: Some translation keys may not exist, causing missing labels.

**Mitigation**:
- Verify all required keys before implementation
- Test with different locales (if multi-language support is active)
- Add missing keys to all locale files

---

## Future Enhancements

### Phase 2 (Not in Scope)

1. **Quick Actions in Detail View**:
   - Change status dropdown directly in detail view
   - Update rating without opening edit dialog
   - "Quick note" field for faster updates

2. **Enhanced Detail Layout**:
   - Tabbed interface: Overview, Reading Activity, Notes
   - Related books section (same author, genre)
   - Reading statistics (time spent, pages per day)

3. **Shareable Book Links**:
   - Direct URL to open detail dialog: `/library?book=123`
   - Deep linking support
   - Share book details with other users

4. **Print/Export Options**:
   - Print book details
   - Export to PDF
   - Copy formatted summary to clipboard

---

## References

- **Related Plans**:
  - Plan #13: Dialog close behavior (backdrop click disabled)
  - Plan #12: Automatic list updates (refresh after delete)
  
- **Existing Components**:
  - `BookCard.svelte`: Book display in grid
  - `BookDrawer.svelte`: Edit dialog (will be modified)
  - `StarRating.svelte`: Reusable rating display
  - `AddBookModal.svelte`: Example of modal pattern

- **API Endpoints**:
  - `api.books.delete(id)`: Delete book
  - `api.books.update(id, data)`: Update book
  - `api.books.list(...)`: Refresh list after changes

- **Styling Reference**:
  - DaisyUI modal: https://daisyui.com/components/modal/
  - DaisyUI badges: https://daisyui.com/components/badge/
  - Tailwind responsive: https://tailwindcss.com/docs/responsive-design

---

## Implementation Checklist

- [ ] Create `BookDetailDialog.svelte` component
- [ ] Implement read-only layout with all book fields
- [ ] Add Edit button with callback
- [ ] Add Delete button with confirmation pattern
- [ ] Handle close actions (X button, Escape key)
- [ ] Update `library/+page.svelte` to use detail dialog
- [ ] Add `detailDialogOpen` state
- [ ] Modify `openDrawer` to `openDetailView`
- [ ] Add `openEditFromDetail` handler
- [ ] Update BookCard `onClick` prop
- [ ] Simplify BookDrawer by removing delete functionality
- [ ] Remove delete button UI from BookDrawer
- [ ] Remove delete-related state and functions
- [ ] Update BookDrawer props (remove onDelete)
- [ ] Test detail dialog opening/closing
- [ ] Test edit flow from detail
- [ ] Test delete flow from detail
- [ ] Test responsive layout
- [ ] Test keyboard navigation
- [ ] Verify all translations are present
- [ ] Test error handling (delete failure)
- [ ] Verify no console errors
- [ ] Test on multiple browsers
- [ ] Manual QA checklist completion
- [ ] Update documentation if needed

---

## Estimated Effort

- **Component Creation**: 2-3 hours
- **Integration & Updates**: 1-2 hours
- **Testing & Polish**: 1-2 hours
- **Total**: 4-7 hours

---

## Notes

- This change improves the user experience by creating a clear distinction between viewing and editing
- The delete action is more discoverable in the detail view
- Follows common UX patterns (view → edit, not direct edit)
- Maintains consistency with plan #13 (no accidental closes)
- No backend changes required
- Easy to roll back if needed
