# Date Conflict on "currently_reading" Transition — Implementation Summary

## Feature Overview

When a user transitions a book that was already finished (has `date_finished`) back to "currently_reading", the system now detects the date conflict and presents a dialog with two resolution options: (A) remove the finish date and start today, or (B) keep the finish date and skip setting a start date. Additionally, when a book's finish date is newly set and the book has a page count, a progress prompt dialog asks the user whether to set reading progress to 100%.

## User Perspective

- **Marking a finished book as "currently reading"**: The user changes a read/did-not-finish book to "currently reading". Instead of getting a 422 error toast, they see a conflict dialog: "This book was finished on [date]. What should we do?" with two buttons.
  - **"Keep finish date"**: The book becomes "currently reading" with no start date; the existing finish date is retained.
  - **"Clear & start today"**: The finish date is removed and today's date is set as the start date.
  - Each option has a footnote explanation describing exactly what will happen.

- **Chained conflicts**: If the book already has both `date_started` and `date_finished` set, the user first resolves the date_started conflict (keep existing or use suggested), and if they then trigger a `started_after_finished` conflict, they get the new dialog as a second step.

- **Progress prompt**: When a book was previously "currently reading" (no finish date) and the user sets it to "read" (acquiring a `date_finished`), if the book has a `page_count`, a modal asks: "Set reading progress for 'Title' to 100%?" — the user can skip or set it.

- **Reading progress chart fix**: The progress-over-time chart now properly handles the case where `date_started` is set to a date *after* the earliest progress entry — it uses the earliest entry date as the chart start point instead of the later `date_started`.

## Technical Changes

### Backend — `backend/app/routers/books.py`
- Added `skip_auto_date_started: bool = False` parameter to `_apply_status_transition_dates()` — when `True`, skips auto-setting `date_started` to `_utcnow()` and instead sets `date_started = None`.
- Three new conflict detection blocks in `transition_status()`:
  1. **started_after_finished (basic)**: When transitioning to "currently_reading" with `date_finished` set, `date_started` is `None`, and no `force_date_started`/`skip_auto_date_started` — returns a `DateConflict(field="started_after_finished")`.
  2. **started_after_finished (chained after force_date_started)**: When `force_date_started` is provided but exceeds `date_finished` — returns the same conflict.
  3. **started_after_finished (no force_date_started)**: When transitioning from a finished state with `date_finished` but no `date_started` — returns conflict.
- Auto-clear `date_finished`: When `force_date_started` is provided for "currently_reading" transition and it exceeds `date_finished`, the backend sets `date_finished = None` in `update_data`.
- `clear_date_started` handling: New block that sets `date_started = None` when `transition.clear_date_started` is `True`.
- All three conflict blocks now also call `_validate_dates()` and pass `skip_auto_date_started` through.

### Backend — `backend/app/schemas.py`
- Added `skip_auto_date_started: bool = False` to `StatusTransitionRequest`.
- Added `clear_date_started: bool = False` to `StatusTransitionRequest`.
- `DateConflict.field` union remains unchanged in schema (extended in frontend types only).

### Backend — `backend/tests/test_books.py`
- **`test_transition_status_conflict_when_started_after_finished`**: Verifies that transitioning a finished book (no date_started) to "currently_reading" returns `date_conflict.field == "started_after_finished"`.
- **`test_transition_status_option_a_clear_finished_and_start`**: Verifies that providing `force_date_started` clears `date_finished` and sets the new start date.
- **`test_transition_status_option_b_skip_auto_date_started`**: Verifies that `skip_auto_date_started: true` keeps `date_finished` and leaves `date_started` as `None`.
- **`test_transition_status_chained_detects_started_after_finished`**: Two-step test: first triggers `date_started` conflict, then resolves with `force_date_started` → second conflict `started_after_finished`.
- **`test_transition_status_chained_option_a_clear_finished`**: Resolves started_after_finished with `force_date_started + skip_auto_date_started` → clears `date_finished`.
- **`test_transition_status_chained_option_b_keep_finished`**: Resolves with `skip_auto_date_started: true` → clears `date_started`, keeps `date_finished`.

### Frontend — `frontend/src/lib/types.ts`
- Extended `DateConflict.field` union: `'date_started' | 'date_finished' | 'started_after_finished'`.
- Added `skip_auto_date_started?: boolean` and `clear_date_started?: boolean` to `StatusTransitionRequest`.

### Frontend — `frontend/src/lib/components/DateConflictDialog.svelte`
- Extended `field` prop type to include `'started_after_finished'`.
- Added `startedAfterFinished` as a third `typeKey` variant.
- Dynamic `i18nValues`, `keepKey`, `useNewKey` based on `typeKey`.
- The `startedAfterFinished` variant shows button labels:
  - **Keep button**: "Keep finish date" with footnote `¹`
  - **Use suggested button**: "Clear & start today" with footnote `²`
- Footnote explanations rendered below the action buttons when `typeKey === 'startedAfterFinished'`.

### Frontend — `frontend/src/lib/components/BookDrawer.svelte`
- `conflictField` type extended from `'date_started' | 'date_finished'` to include `'started_after_finished'`.
- Added `pendingProgressBook` state variable for the progress prompt modal.
- `applyPendingTransition()`: Now accepts `skipAutoDateStarted` and `clearDateStarted` params; passes them through to the API call. After a successful transition, if the book just acquired `date_finished` (was null before) and has `page_count`, sets `pendingProgressBook` instead of closing the drawer. Strips `date_started`/`date_finished` from `pendingPayload` before calling `api.books.update` (prevents overwriting backend-set dates).
- `save()`: Same `dateFinishedWasNull` tracking and progress prompt logic. Only applies to status-changing saves where the transition path was used. Strips dates from `pendingPayload`.
- Dialog `onKeep` handler: For `started_after_finished` conflict, calls `applyPendingTransition({ skipAutoDateStarted: true, clearDateStarted: true })` — keeps finish date, clears start date.
- Dialog `onUseSuggested` handler: For `started_after_finished` conflict, calls `applyPendingTransition({ forceDateStarted: conflictSuggestedDate, skipAutoDateStarted: true })` — removes finish date, sets start date to suggested (today).
- **Progress prompt modal**: New `{#if pendingProgressBook}` block renders a modal asking the user to set progress to 100%. Two buttons: "Skip" (closes drawer, calls `onSave`) and "Set to 100%" (calls `api.books.progress.create(pbook.id, pbook.page_count!)`, then closes drawer).

### Frontend — `frontend/src/lib/components/BookDetailDialog.svelte`
- SVG chart width increased from 300 to 380 for better readability.
- Chart point calculation now checks whether `book.date_started` is actually before the oldest progress entry (`uniqueDays[0]`). If `date_started` is **after** the oldest entry, the virtual start point uses `book.date_added` (or `null`) instead of `date_started`, preventing the chart line from starting to the right of actual data points.

### Frontend — `frontend/src/lib/i18n/locales/en.json`
New keys:
```
book.progressPromptTitle: "Set Reading Progress?"
book.progressPromptMessage: "Set the reading progress for \"{title}\" to 100%?"
book.progressPromptSet: "Set to 100%"
book.progressPromptSkip: "Skip"

dateConflict.startedAfterFinished.title: "Book was already finished"
dateConflict.startedAfterFinished.message: "This book was finished on {finishedDate}. What should we do?"
dateConflict.startedAfterFinished.keepFinished: "Keep finish date"
dateConflict.startedAfterFinished.clearAndStart: "Clear & start today"
dateConflict.startedAfterFinished.keepDesc: "Keeps the finish date ({finishedDate}) and does not set a start date."
dateConflict.startedAfterFinished.clearDesc: "Removes the finish date and sets today ({newStartDate}) as the start date."
```

### Frontend — `frontend/src/lib/i18n/locales/de.json`
Same keys translated to German.

### `.gitignore`
- Added `cookies.txt` to ignore list.

## Files Modified (10)

| File | Change Summary |
|------|---------------|
| `.gitignore` | Added `cookies.txt` |
| `backend/app/routers/books.py` | 3 conflict blocks, `skip_auto_date_started` param, `clear_date_started` handling, auto-clear `date_finished` |
| `backend/app/schemas.py` | 2 new fields on `StatusTransitionRequest` |
| `backend/tests/test_books.py` | 6 new tests for conflict detection and resolution options |
| `frontend/src/lib/types.ts` | Extended `DateConflict.field`, added request fields |
| `frontend/src/lib/components/DateConflictDialog.svelte` | Third dialog variant `startedAfterFinished` |
| `frontend/src/lib/components/BookDrawer.svelte` | Conflict resolution, progress prompt modal, date-stripping in payload |
| `frontend/src/lib/components/BookDetailDialog.svelte` | Wider SVG, smarter chart start point |
| `frontend/src/lib/i18n/locales/en.json` | 9 new English i18n keys |
| `frontend/src/lib/i18n/locales/de.json` | 9 new German i18n keys |

## Untracked File

| File | Content |
|------|---------|
| `.plan/37-date-conflict-transition.md` | Original implementation plan |
