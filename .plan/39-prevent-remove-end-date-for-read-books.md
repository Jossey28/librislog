# Prevent removing `date_finished` for "read" books

## Problem

Users can accidentally clear the finish date (`date_finished`) of a "read" book in the edit dialog, leaving the book in an inconsistent state (finished reading but no end date).

## Requirements

- Saving a book with status "read" and an empty `date_finished` must be rejected with an error.
- Removing the finish date must still be allowed when simultaneously transitioning away from "read" (e.g., → "want_to_read").
- Validation on both frontend (instant feedback) and backend (enforcement).

## Validation Logic

```
User clears date_finished input
         │
         ▼
   ┌──────────────────────┐
   │ Frontend early check │
   │ status="read"        │
   │ status unchanged     │  ← rejects immediately (toast)
   │ df was previously set │
   └──────────────────────┘
         │ (passed)
         ▼
   ┌───────────────────┐
   │ PATCH /api/books  │  (status unchanged path)
   │ POST /transition  │  (status changed path)
   └───────────────────┘
         │
         ▼
   ┌────────────────────────────┐
   │ Backend check              │
   │ date_finished→null         │
   │ AND book.status="read"     │
   │ AND target.status="read"   │  ← HTTP 422
   └────────────────────────────┘
         │ (passed)
         ▼
   ┌────────────────────┐
   │ Saved successfully │
   └────────────────────┘
```

For transition away from "read" with cleared date: frontend sends `clear_date_finished: true`, backend clears the field.

## Files to Change

### 1. `backend/app/schemas.py`
- Add `clear_date_finished: bool = False` to `StatusTransitionRequest`

### 2. `backend/app/routers/books.py`
- New helper `_validate_date_finished_for_read(book, update_data, target_status)`
  - Returns early if `date_finished` not in payload, or value not null, or book's current `date_finished` is already null
  - Raises `HTTPException(422, "error.dateFinishedRequiredForRead")` if `book.reading_status == "read"` and `target_status == "read"`
- Call it in `update_book()` after `_validate_dates()`
- Handle `clear_date_finished` in `transition_status()` (mirrors existing `clear_date_started`)
- Call validation in `transition_status()` as well

### 3. `frontend/src/lib/components/BookDrawer.svelte`
- Early frontend guard in `save()` (before network call):
  ```javascript
  const dfCleared = !date_finished.trim();
  if (dfCleared && book.date_finished && reading_status === 'read' && !statusChanged) {
      toasts.add($_('error.dateFinishedRequiredForRead'), 'error');
      return;
  }
  ```
- Pass `clear_date_finished` in transition call when clearing date while changing away from "read"
- Catch new error key in the `catch` block

### 4. `frontend/src/lib/i18n/locales/en.json`
```json
"dateFinishedRequiredForRead": "A finished book must have an end date. Change the status if you want to remove the finish date."
```

### 5. `frontend/src/lib/i18n/locales/de.json`
```json
"dateFinishedRequiredForRead": "Ein gelesenes Buch muss ein Enddatum haben. Ändere den Status, wenn du das Enddatum entfernen möchtest."
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| "read" + clear `date_finished`, keep status | **Rejected** |
| "read" → "want_to_read" + clear `date_finished` | **Allowed**, date cleared |
| "read" → "currently_reading" + clear `date_finished` | **Allowed**, date cleared |
| "read" + edit other fields, don't touch `date_finished` | **Allowed** (field not in payload) |
| "read" with `date_finished=null` in DB (inconsistent) | **Allowed** (only rejects when actively removing a value) |
