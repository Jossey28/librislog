# LibrisLog — Dialog Close Behavior & State Persistence Fixes

**Status**: ✅ **COMPLETE** (2026-05-11)  
**Summary**: See `13-dialog-close-behavior-SUMMARY.md`

## Goal

Fix inconsistent dialog/modal behavior across the application:

1. **Prevent accidental closes**: Disable backdrop click-to-close for all modals/drawers
2. **Consistent state handling**: Preserve unsaved changes in edit drawer when reopening
3. **Auto-close on save**: Book edit drawer should close after successful save
4. **Preserve form state**: Add book modal should retain form values when switching between tabs

---

## Current Behavior Analysis

### BookDrawer (Edit Book Dialog)

**File**: `frontend/src/lib/components/BookDrawer.svelte`

Current issues:
- ✅ **Backdrop click closes drawer** — lines 90-96 have `onclick={() => (open = false)}`
- ✅ **Unsaved changes persist** — `$effect` repopulates fields from `book` prop, so changes vanish on reopen (lines 32-43)
- ✅ **Doesn't auto-close on save** — `save()` function (lines 45-65) doesn't set `open = false`

Current implementation:
```svelte
<!-- Backdrop -->
<div
    class="fixed inset-0 bg-black/40 z-40"
    role="button"
    tabindex="-1"
    onclick={() => (open = false)}  ← PROBLEM: backdrop closes
    onkeydown={(e) => e.key === 'Escape' && (open = false)}
></div>
```

```typescript
$effect(() => {
    if (book) {
        title = book.title;
        author = book.author ?? '';
        notes = book.notes ?? '';
        // ... resets all fields from book prop
    }
});
```

### AddBookModal (Create Book Dialog)

**File**: `frontend/src/lib/components/AddBookModal.svelte`

Current issues:
- ✅ **Backdrop click closes modal** — line 162 has backdrop close handler
- ✅ **Manual tab resets on reopen** — `reset()` is called when modal closes (line 85), clearing all fields
- ✅ **Import tab doesn't preserve state** — ImportSearch component has internal state that's lost when modal closes

Current implementation:
```svelte
<!-- Click-outside to close -->
<div 
    class="modal-backdrop" 
    role="button" 
    tabindex="-1" 
    onclick={() => { open = false; reset(); }}  ← PROBLEM: backdrop closes + resets
    onkeydown={() => {}}
></div>
```

```typescript
function reset() {
    title = '';
    author = '';
    isbn = '';
    // ... clears all fields
    activeTab = 'manual';
}
```

---

## Implementation Plan

### Phase 1: Disable Backdrop Click-to-Close

#### A) BookDrawer.svelte

**Change**: Remove `onclick` handler from backdrop, keep only explicit close button and Escape key.

```svelte
<!-- Backdrop -->
<div
    class="fixed inset-0 bg-black/40 z-40"
    role="button"
    tabindex="-1"
    onkeydown={(e) => e.key === 'Escape' && (open = false)}
></div>
```

**Note**: Backdrop still blocks clicks on content behind it but doesn't close the drawer.

#### B) AddBookModal.svelte

**Change**: Remove close logic from backdrop click handler.

```svelte
<!-- Click-outside backdrop (visual only, no close) -->
<div 
    class="modal-backdrop" 
    role="button" 
    tabindex="-1"
    onkeydown={(e) => e.key === 'Escape' && (open = false)}
></div>
```

**Keep explicit close handlers**:
- `✕` button at top-right (line 85)
- Escape key

---

### Phase 2: Auto-Close on Successful Save (BookDrawer)

**File**: `frontend/src/lib/components/BookDrawer.svelte`

**Change**: Set `open = false` after successful save in the `save()` function.

```typescript
async function save() {
    if (!book) return;
    saving = true;
    try {
        const updated = await api.books.update(book.id, {
            title,
            author: author || null,
            notes: notes || null,
            rating,
            reading_status,
            date_started: date_started || null,
            date_finished: date_finished || null,
            cover_url: cover_url || null
        });
        book = updated;
        onSave?.(updated);
        open = false;  // ← NEW: close drawer on successful save
    } catch (e: unknown) {
        toasts.add(e instanceof Error ? e.message : 'Save failed');
    } finally {
        saving = false;
    }
}
```

---

### Phase 3: Preserve Edit State When Reopening (BookDrawer)

**Current problem**: `$effect` always resets fields from `book` prop, even if user made unsaved changes and reopened the drawer.

**Two approaches**:

#### Approach A: Don't Preserve Unsaved Changes (Simpler)
Keep current behavior — drawer always shows latest saved state when reopened.

**Pros**:
- Simple, predictable
- No "stale edit" confusion
- Matches current manual tab behavior

**Cons**:
- User loses unsaved changes if they accidentally close

**Recommendation**: Use this approach — it's clearer UX and matches modal behavior.

#### Approach B: Preserve Unsaved Changes Until Explicit Cancel
Track `isDirty` flag and only reset on explicit "Cancel" or successful save.

**Implementation**:
```typescript
let isDirty = $state(false);

// Only reset when book changes AND not dirty
$effect(() => {
    if (book && !isDirty) {
        title = book.title;
        author = book.author ?? '';
        // ... populate fields
    }
});

function save() {
    // ... save logic
    isDirty = false;
    open = false;
}

function cancel() {
    isDirty = false;
    open = false;
}

// Mark dirty on any field change
// (could use $derived or watch individual fields)
```

**Cons**:
- More complex
- User might forget they have unsaved changes
- Need "Discard changes?" confirmation dialog

**Recommendation**: Only implement if user specifically requests this behavior.

---

### Phase 4: Preserve Manual Form State (AddBookModal)

**Current problem**: `reset()` is called on modal close, clearing manual tab fields.

**Change**: Only call `reset()` on explicit actions, not on backdrop/Escape close.

```typescript
// Remove reset() from general close handler
function handleClose() {
    open = false;
    // Do NOT call reset() here
}

function submitManual() {
    if (!title.trim()) return;
    submitting = true;
    try {
        const book = await api.books.create({
            title: title.trim(),
            author: author || null,
            // ... rest of fields
        });
        onAdded?.(book);
        open = false;
        reset();  // ← Only reset after successful submission
    } catch (e: unknown) {
        toasts.add(e instanceof Error ? e.message : 'Failed to add book', 'error');
    } finally {
        submitting = false;
    }
}
```

**Update template close buttons**:
```svelte
<!-- Top-right X button -->
<button class="btn btn-ghost btn-sm btn-circle" onclick={handleClose}>✕</button>

<!-- Backdrop (no close action) -->
<div 
    class="modal-backdrop"
    role="button"
    tabindex="-1"
    onkeydown={(e) => e.key === 'Escape' && handleClose()}
></div>
```

**Note**: Import tab state (ImportSearch component) is internal and will still reset when modal closes — acceptable since import is a one-shot action.

---

### Phase 5: Add Visual "Reset Form" Button (Optional Enhancement)

Since modal will preserve form state, add an explicit "Clear Form" button for manual tab:

```svelte
<div class="modal-action mt-2">
    <button type="button" class="btn btn-ghost btn-sm" onclick={reset}>
        Clear Form
    </button>
    <button type="submit" class="btn btn-primary btn-sm" disabled={submitting}>
        {submitting ? 'Adding…' : 'Add Book'}
    </button>
</div>
```

---

## Summary of Changes

| Component | Change | Reason |
|-----------|--------|--------|
| `BookDrawer.svelte` | Remove backdrop `onclick` close | Prevent accidental closes |
| `BookDrawer.svelte` | Add `open = false` after successful save | Auto-close after save |
| `BookDrawer.svelte` | Keep current reset-on-reopen behavior | Simpler, predictable UX |
| `AddBookModal.svelte` | Remove backdrop `onclick` close | Prevent accidental closes |
| `AddBookModal.svelte` | Only call `reset()` after successful submit | Preserve form state between opens |
| `AddBookModal.svelte` (optional) | Add "Clear Form" button | Explicit way to reset |

---

## Test Plan

### Manual Testing Checklist

#### BookDrawer (Edit Dialog)

1. **Backdrop click doesn't close**
   - Open a book in edit drawer
   - Click gray backdrop area
   - ✅ Drawer stays open

2. **Escape key closes drawer**
   - Open drawer
   - Press Escape
   - ✅ Drawer closes

3. **X button closes drawer**
   - Open drawer
   - Click X button
   - ✅ Drawer closes

4. **Auto-close on save**
   - Open drawer, make changes
   - Click Save
   - ✅ Drawer closes after successful save
   - ✅ Changes appear in book list

5. **State resets on reopen**
   - Open drawer, make changes
   - Close drawer (X or Escape) without saving
   - Reopen same book
   - ✅ Fields show saved values, not unsaved changes

#### AddBookModal (Create/Import Dialog)

6. **Backdrop click doesn't close**
   - Open add book modal
   - Click gray backdrop
   - ✅ Modal stays open

7. **Escape key closes modal**
   - Open modal
   - Press Escape
   - ✅ Modal closes

8. **X button closes modal**
   - Open modal
   - Click X
   - ✅ Modal closes

9. **Manual tab preserves form state**
   - Open modal, switch to Manual tab
   - Fill in title, author, etc.
   - Close modal (X or Escape)
   - Reopen modal
   - ✅ Manual tab still shows filled fields

10. **Import tab resets state (acceptable)**
    - Open modal, switch to Import tab
    - Run a search
    - Close modal
    - Reopen modal
    - ✅ Import tab is back to initial state (no search results)

11. **Manual submit clears form**
    - Fill in manual form
    - Click "Add Book"
    - ✅ Book added, modal closes
    - Reopen modal
    - ✅ Form is cleared

12. **Import submit clears form**
    - Search and import a book
    - ✅ Book added, modal closes
    - Reopen modal
    - ✅ Import tab is cleared

13. **Tab switching preserves state**
    - Fill in manual form
    - Switch to Import tab
    - Switch back to Manual tab
    - ✅ Manual form fields still filled

### Edge Cases

14. **Multiple books edited in sequence**
    - Edit book A, close without saving
    - Edit book B
    - ✅ Book B fields show book B data, not book A unsaved changes

15. **Network error doesn't close drawer**
    - Disconnect network
    - Edit book, click Save
    - ✅ Error toast appears
    - ✅ Drawer stays open
    - ✅ Changes preserved for retry

---

## Automated Testing (Optional - Frontend has no test suite yet)

Since the project currently has no frontend automated tests, these would require setting up Playwright or similar.

**If frontend tests are added later**, test cases should cover:

### Unit Tests (Svelte Testing Library)
- Modal `open` state doesn't change on backdrop click
- Drawer `open` state doesn't change on backdrop click
- Form state persists across open/close cycles
- `reset()` only called after successful submission

### Integration Tests (Playwright)
- Full user flow: open modal → fill form → close → reopen → verify fields
- Edit flow: open drawer → edit → save → verify drawer closed + list updated
- Import flow: search → import → verify modal closed + book added

---

## Files To Modify

1. `frontend/src/lib/components/BookDrawer.svelte`
   - Remove backdrop close handler
   - Add `open = false` in `save()` function
   - Keep current state reset behavior

2. `frontend/src/lib/components/AddBookModal.svelte`
   - Remove backdrop close handler
   - Move `reset()` call from close to submit success
   - (Optional) Add "Clear Form" button

---

## Risk Analysis

### Low Risk
- Removing backdrop close is straightforward
- Auto-close on save is one-line change
- No backend changes needed

### Medium Risk
- Form state persistence might confuse users who expect clean slate
- Need to communicate that closing != canceling
- Should consider adding "unsaved changes" indicator (future enhancement)

### Mitigation
- Clear visual affordances (X button prominent)
- Escape key still works as quick exit
- Form state helps users more than it confuses them
- Can add "Discard changes?" confirmation in future if needed

---

## Future Enhancements (Out of Scope)

1. **Dirty state indicator**
   - Show "●" or "Unsaved changes" badge when fields are modified
   - Add confirmation dialog: "Discard changes?" when closing with unsaved edits

2. **Auto-save drafts**
   - Persist form state to localStorage
   - Restore on page reload

3. **Undo/Redo**
   - Track edit history
   - Allow reverting changes before save

4. **Keyboard shortcuts**
   - Ctrl+S to save
   - Ctrl+Enter to submit

---

## Implementation Order

1. ✅ **Phase 1**: Disable backdrop clicks (BookDrawer + AddBookModal)
2. ✅ **Phase 2**: Auto-close on save (BookDrawer only)
3. ✅ **Phase 4**: Preserve manual form state (AddBookModal)
4. ⚠️ **Phase 3**: Keep current behavior (no code change needed)
5. 🔹 **Phase 5**: Optional "Clear Form" button (AddBookModal)

**Estimated time**: 30-45 minutes of implementation + 15 minutes testing

---

## Questions for Clarification

Before implementing, please confirm:

1. **Edit drawer state**: Should we keep current behavior (always reset to saved values on reopen)? Or preserve unsaved changes?
   - **Recommendation**: Keep current behavior (simpler)

2. **"Clear Form" button**: Do you want an explicit button to clear the manual form, or is resetting on successful submit enough?
   - **Recommendation**: Add the button — helps users start over mid-entry

3. **Escape key**: Should Escape still close dialogs, or only the X button?
   - **Recommendation**: Keep Escape — it's standard UX

---

## Acceptance Criteria

- ✅ Backdrop clicks do NOT close either modal or drawer
- ✅ X button closes both modal and drawer
- ✅ Escape key closes both modal and drawer
- ✅ Edit drawer auto-closes after successful save
- ✅ Manual form fields persist when closing and reopening modal
- ✅ Manual form clears only after successful book creation
- ✅ Import tab resets on reopen (acceptable behavior)
- ✅ No regressions in existing functionality

