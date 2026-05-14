# Date Validation in Book Edit Dialog

## Requirements

1. **Date finished max constraint**: `<input type="date">` for `date_finished` should not allow selecting future dates.
2. **Start ≤ finished validation**: On save, if both `date_started` and `date_finished` are set, validate that `date_started` is not greater than `date_finished`. Show toast and prevent save if invalid.

## Files to Change

| File | What |
|------|------|
| `frontend/src/lib/components/BookDrawer.svelte` | Add `max` to date inputs, add validation in `save()`, expand catch block |
| `backend/app/routers/books.py` | Add `_validate_dates()` helper, call in `create_book`, `update_book`, `transition_status` |
| `frontend/src/lib/i18n/locales/en.json` | 2 new error keys |
| `frontend/src/lib/i18n/locales/de.json` | 2 new error keys |

## Frontend Changes

### 1a. Add `max` to date inputs

```svelte
<script lang="ts">
  let today = $state(new Date().toISOString().slice(0, 10));
</script>

<input type="date" bind:value={date_finished} max={today} />
```

Both `date_started` and `date_finished` get `max={today}` to prevent future date selection.

### 1b. Add start≤finished check in `save()`

After `if (!book) return;`:

```typescript
const ds = date_started.trim();
const df = date_finished.trim();
if (ds && df && ds > df) {
  toasts.add($_('error.dateStartedAfterFinished'), 'error');
  saving = false;
  return;
}
```

Lexicographic comparison works because values are YYYY-MM-DD strings.

### 1c. Expand catch block

Add checks for `error.dateStartedAfterFinished` and `error.dateInFuture` alongside the existing `error.isbnAlreadyExists` check.

## Backend Changes

### 2a. Add `_validate_dates()` helper in `books.py`

```python
def _validate_dates(data: dict) -> None:
    now = datetime.now(timezone.utc)
    for field in ("date_started", "date_finished"):
        val = data.get(field)
        if val is not None and val > now:
            raise HTTPException(422, detail="error.dateInFuture")
    ds = data.get("date_started")
    df = data.get("date_finished")
    if ds is not None and df is not None and ds > df:
        raise HTTPException(422, detail="error.dateStartedAfterFinished")
```

### 2b. Call in handlers

Call `_validate_dates(book_data)` in `create_book` and `_validate_dates(update_data)` in `update_book` and `transition_status`.

## i18n Keys

```
error.dateInFuture:
  en: "Date cannot be in the future."
  de: "Datum darf nicht in der Zukunft liegen."

error.dateStartedAfterFinished:
  en: "Start date cannot be after finish date."
  de: "Startdatum darf nicht nach dem Enddatum liegen."
```

## Edge Cases

- Single date filled → no comparison
- Equal dates → allowed (strict `>` check)
- User types future date manually → backend catches it (defense-in-depth)
- Status transition path → validation runs before API call in `save()`
