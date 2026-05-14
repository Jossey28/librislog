# Date Conflict Transition & Progress Prompt

## Summary

Three features were implemented and bugs fixed in this changeset:

1. **Date conflict on "currently_reading" transition** — When a finished book is moved back to "currently_reading", a dialog handles the inconsistent dates.
2. **Bugfix: pendingPayload overwriting transition-set dates** — Two locations where the PATCH after status transition could overwrite dates that the transition API just set.
3. **100% Progress Prompt** — When a book gets `date_finished` set (manually or via status transition), the user is asked if they want to create a 100% reading progress entry.
4. **Reading progress diagram virtual-entry fix** — The virtual `progress=0` entry now only uses `date_started` when it's older than the first log entry.

---

## User Perspective

### 1. Date Conflict Dialog on "currently_reading" Transition

**Before**: Transitioning a finished book (with `date_finished`) back to "currently_reading" would silently auto-set `date_started = today`, potentially overwriting a meaningful start date or creating inconsistent dates (start > finish). If `date_started` was already set, the user saw only the "Start date already set" dialog; resolving it could clear the finish date even when dates were consistent.

**After**: Two new conflict scenarios are handled:

- **Case A — Book was read, has `date_finished`, but NO `date_started`**: Transitioning to "currently_reading" shows a **"Book was already finished"** dialog with two options:
  - **(1) "Keep finish date"** — Keeps `date_finished` as-is, does NOT auto-set `date_started` (sets it to `None`).
  - **(2) "Clear & start today"** — Removes `date_finished`, sets `date_started = today`.

- **Case B — Book has BOTH dates, user resolves "Start date already set" by picking a new start date**: If the chosen start date is AFTER the existing finish date, a **chained** "Book was already finished" dialog follows. Options:
  - **(1) "Keep finish date"** — Clears `date_started` (to `None`), keeps `date_finished`.
  - **(2) "Clear & start today"** — Sets `date_started = today`, clears `date_finished`.

Visual: Buttons in the dialog have superscript footnote markers (`¹`, `²`); explanatory text below a separator describes each option.

### 2. Bugfix: Dates Now Persist Correctly

**Before**: When saving a book with a status change, the transition API correctly set `date_finished` (e.g., `today` for "read"), but the subsequent PATCH with the form's `pendingPayload` would overwrite it with the original stale form value (often `null`), effectively undoing the transition's date changes. Similarly, keeping an existing `date_started` in the conflict dialog would still clear `date_finished` unconditionally.

**After**: Both `date_started` and `date_finished` are stripped from `pendingPayload` before the PATCH call, preventing stale form values from overwriting transition-set dates. The "Keep existing start date" option no longer clears `date_finished` when dates are consistent.

### 3. 100% Progress Prompt

**When**: After saving a book where `date_finished` was newly set (was `null`, now has a value) AND the book has a `page_count`.

**What**: A dialog appears: **"Set Reading Progress?"** with the message _"Set the reading progress for 'Book Title' to 100%?"_ and two buttons:
  - **"Skip"** — Closes without action.
  - **"Set to 100%"** — Creates a reading progress entry at `page = page_count` via `POST /api/books/{id}/progress`, then closes.

**Triggered by**:
- Manually setting `date_finished` in the drawer and saving (no status change).
- Changing status to "Read" or "Did Not Finish" (backend auto-sets `date_finished = today`).
- Resolving a date conflict that results in `date_finished` being set (via `applyPendingTransition`).

### 4. Reading Progress Diagram Fix

**Before**: The chart always used `book.date_started` (falling back to `book.date_added`) for the virtual `progress=0` entry. If `date_started` was set to a date AFTER the first reading log entry, the line would start in the future and backtrack — visually incorrect.

**After**: The virtual entry uses `date_started` ONLY if it is strictly older than the oldest reading log entry. Otherwise it falls back to `book.date_added` (creation date), ensuring the chart line always progresses forward in time.

---

## Technical Changes

### Backend — `backend/app/routers/books.py`

| Change | Lines |
|--------|-------|
| `_apply_status_transition_dates` accepts `skip_auto_date_started: bool` param; when `True`, uses `setdefault("date_started", None)` to actively clear start date instead of auto-setting it | 54, 60-63 |
| Inner `started_after_finished` conflict detection inside the `date_started` conflict block (lines 472-481): when `force_date_started > book.date_finished`, returns chained `started_after_finished` conflict | 472-481 |
| New `started_after_finished` conflict block for Case A (lines 497-510): book has `date_finished` but no `date_started`, transitioning to `currently_reading` | 497-510 |
| New auto-clear block (lines 512-527): when transitioning to `currently_reading` with `force_date_started` that is AFTER the existing finish date, clears `date_finished`. Has `force_date_started > book.date_finished` guard so consistent dates are not cleared. | 512-519 |
| `clear_date_started` handling (lines 521-526): when `clear_date_started=True`, sets `update_data["date_started"] = None` | 521-526 |
| Passes `transition.skip_auto_date_started` to `_apply_status_transition_dates` in the main transition call | 528 |

### Backend — `backend/app/schemas.py`

| Change | Lines |
|--------|-------|
| Added `skip_auto_date_started: bool = False` to `StatusTransitionRequest` | 200 |
| Added `clear_date_started: bool = False` to `StatusTransitionRequest` | 201 |

### Backend — `backend/tests/test_books.py`

6 new tests (all passing, 179 total):

| Test | Scenario |
|------|----------|
| `test_transition_status_conflict_when_started_after_finished` | Book with `date_finished`, no `date_started` → "currently_reading" returns `started_after_finished` conflict |
| `test_transition_status_option_a_clear_finished_and_start` | Case A resolved with `force_date_started` → clears `date_finished`, sets `date_started` |
| `test_transition_status_option_b_skip_auto_date_started` | Case B resolved with `skip_auto_date_started=True` → keeps `date_finished`, `date_started=None` |
| `test_transition_status_chained_detects_started_after_finished` | Book with both dates → date_started conflict → resolve → started_after_finished conflict |
| `test_transition_status_chained_option_a_clear_finished` | Chained resolved with `force_date_started + skip_auto_date_started` → clears `date_finished` |
| `test_transition_status_chained_option_b_keep_finished` | Chained resolved with `skip_auto_date_started` → clears `date_started`, keeps `date_finished` |

### Frontend — `frontend/src/lib/types.ts`

| Change | Lines |
|--------|-------|
| `DateConflict.field` union extended: `'date_started' \| 'date_finished' \| 'started_after_finished'` | 50 |
| `StatusTransitionRequest` gains `skip_auto_date_started?: boolean` and `clear_date_started?: boolean` | 47-48 |

### Frontend — `frontend/src/lib/components/BookDrawer.svelte`

| Change | Lines |
|--------|-------|
| `conflictField` type widened to include `'started_after_finished'` | 26 |
| `pendingProgressBook` state variable for progress prompt dialog | 31 |
| `applyPendingTransition` captures `dateFinishedWasNull`, passes `skipAutoDateStarted`/`clearDateStarted` to API | 91-136 |
| `applyPendingTransition` strips `date_started`/`date_finished` from `pendingPayload` before PATCH and conditionally shows progress prompt | 116-130 |
| `save()` captures `dateFinishedWasNull`, strips dates from `pendingPayload` in status-changed PATCH path, checks for progress prompt after both save paths | 148, 172-174, 177-182, 195-197 |
| Dialog `onKeep`/`onUseSuggested` handlers branch on `'started_after_finished'` with different params (uses `skipAutoDateStarted`/`clearDateStarted` instead of `forceDateStarted`/`forceDateFinished`) | 352-373 |
| Progress prompt dialog inline template with Skip/Set to 100% buttons, calls `api.books.progress.create` on confirm | 376-425 |

### Frontend — `frontend/src/lib/components/DateConflictDialog.svelte`

| Change | Lines |
|--------|-------|
| `field` prop type widened to `'date_started' \| 'date_finished' \| 'started_after_finished'` | 14 |
| `typeKey` derived for three-way variant selection | 22-25 |
| `i18nValues` derived with different variable names for `startedAfterFinished` vs others | 27-30 |
| `keepKey`/`useNewKey` derived for dynamic i18n key selection per variant | 32-37 |
| Button labels use `i18nValues` for dynamic rendering | 45-53 |
| Superscript footnotes (`¹`, `²`) on buttons when `startedAfterFinished` | 51, 56 |
| Footer section (below `border-t` separator) with description text for each option | 58-63 |

### Frontend — `frontend/src/lib/components/BookDetailDialog.svelte`

| Change | Lines |
|--------|-------|
| Chart virtual-entry logic: compares `date_started` with oldest log entry date; only uses `date_started` if it's strictly older | 169-171 |

### Frontend — i18n

**`en.json`** — Added keys:
- `dateConflict.startedAfterFinished.*` (title, message, keepFinished, clearAndStart, keepDesc, clearDesc)
- `book.progressPromptTitle`, `book.progressPromptMessage`, `book.progressPromptSet`, `book.progressPromptSkip`

**`de.json`** — German translations for all above keys.

### Other — `.gitignore`

Added `cookies.txt` to gitignore.

---

## Bugs Fixed

1. **`pendingPayload` overwrite** (regression from the status transition flow): The PATCH call after `transitionStatus` in both `save()` and `applyPendingTransition()` would send stale form dates, overwriting the just-set transition dates. Fix: destructure out `date_started` and `date_finished` before PATCH.

2. **`date_finished` unconditionally cleared** (regression from auto-clear block): When keeping a consistent existing `date_started` during `date_started` conflict resolution, the auto-clear block would still fire (because `force_date_started` was set) and clear `date_finished`. Fix: added `force_date_started > book.date_finished` guard.

3. **Date comparison always returns "changed"** (minor): `fromDateInputValue(toDateInputValue(book.date_started))` produces `"2026-05-09T00:00:00.000Z"` while the API returns `"2026-05-09T00:00:00Z"` — the `.000` millisecond part makes `!==` always true, causing `includeDates` in `buildNonStatusPayload` to always be true. Not directly fixed (dates are now stripped anyway).
