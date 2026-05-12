# LibrisLog — Book Detail View/Dialog — SUMMARY

**Status**: 📋 **PLANNED**  
**Date**: 2026-05-12

---

## Overview

Replace the current click-to-edit pattern with a dedicated read-only detail view for books. When users click a book card, they'll see a detail dialog showing all book information with separate "Edit" and "Delete" action buttons.

---

## Key Changes

### New Component
- **`BookDetailDialog.svelte`**: New read-only dialog displaying all book information
  - Shows cover, title, author, ISBN, publisher, year, pages, genre
  - Displays reading status with badge, star rating, dates, notes
  - "Edit" button opens the existing BookDrawer
  - "Delete" button (with confirmation) replaces the one in BookDrawer
  - No backdrop click-to-close (per plan #13)

### Modified Components
- **`library/+page.svelte`**: Update click handler to open detail dialog instead of edit drawer
  - Add `detailDialogOpen` state
  - Change `openDrawer` → `openDetailView`
  - Add `openEditFromDetail` handler
  
- **`BookDrawer.svelte`**: Remove delete functionality
  - Remove delete button, confirmation state, and handler
  - Remove `onDelete` prop
  - Keep as edit-only dialog

---

## User Flow

**Current**: Click book → Edit dialog  
**New**: Click book → Detail dialog → Click "Edit" → Edit dialog

```
BookCard click
    ↓
BookDetailDialog (read-only)
    ├─ Edit button → BookDrawer (edit mode)
    └─ Delete button → Confirm → Delete book
```

---

## Benefits

1. **Clear separation**: Viewing vs. editing are distinct actions
2. **Better UX**: Users can view book details without accidentally changing them
3. **More discoverable**: Delete action is visible in detail view
4. **Consistent patterns**: Follows common UI conventions (read → edit flow)

---

## Implementation Effort

**Estimated**: 4-7 hours
- Component creation: 2-3 hours
- Integration: 1-2 hours
- Testing & polish: 1-2 hours

---

## No Backend Changes

This is a **frontend-only** feature using existing API endpoints. No database migrations or backend code changes required.

---

## Testing Focus

- [ ] Detail dialog opens on book click
- [ ] All book fields display correctly
- [ ] Edit button opens edit drawer
- [ ] Delete button (with confirmation) works
- [ ] Dialog doesn't close on backdrop click
- [ ] Escape key closes dialog
- [ ] Responsive layout (mobile + desktop)
- [ ] No console errors

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Z-index conflicts between dialogs | Close detail before opening edit |
| State sync issues | Use same `selectedBook` for both |
| User confusion (UX change) | Keep consistent delete confirmation pattern |

---

## Related Plans

- **Plan #13**: Dialog close behavior (backdrop click disabled)
- **Plan #12**: Automatic list updates (refresh after delete)

---

**Full Details**: See `28-book-detail-view.md`
