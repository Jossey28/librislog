# Summary: Improved Date Handling and Sorting

**Plan File:** `19-improved-date-handling-and-sorting.md`

## Overview

Comprehensive plan to improve date/timestamp handling, conflict detection, and sorting capabilities.

## Three Main Improvements

### 1. Date Finished Conflict Check ✨
**Current:** `date_finished` auto-set without checking existing value  
**Planned:** Conflict dialog (like `date_started`) when transitioning to "read" or "did not finish"

### 2. Full Timestamp Storage 🕐
**Current:** `date_started` and `date_finished` stored as DATE (no time component)  
**Planned:** Store as DATETIME with timezone for precise chronological sorting

**Why:** Books finished on same day have indeterminate sort order currently

### 3. Restore Sort Controls 🔄
**Current:** Smart sort only (status-specific, automatic)  
**Planned:** User-selectable sort options with toggle between smart and manual modes

**Options:** Title (A-Z), Date Added, Date Started, Date Finished, Rating (+ asc/desc)

---

## Implementation Phases

| Phase | Description | Effort |
|-------|-------------|--------|
| **Phase 1** | Backend timestamp migration (DB + models) | 4-5h |
| **Phase 2** | Backend date_finished conflict detection | 3-4h |
| **Phase 3** | Frontend conflict dialog (both date types) | 3-4h |
| **Phase 4** | Frontend sort controls UI + backend title sorting | 4-5h |
| **Phase 5** | Frontend date formatting utilities | 1.5-2.5h |
| **Phase 6** | Integration testing | 2-3h |
| **Total** | | **~3-4 days** |

---

## Key Technical Details

### Database Migration
- SQLite doesn't support `ALTER COLUMN TYPE` → use temp columns + batch operations
- Existing dates preserved with midnight UTC as time component
- Indexes recreated after column type change
- Rollback supported via downgrade migration

### Backend Changes
- `models.py`: `date_started`, `date_finished` → `datetime` (from `date`)
- `schemas.py`: Update all date fields to `datetime`
- `routers/books.py`: Add `force_date_finished` parameter, extend conflict logic
- New conflict check in `transition_status()` endpoint
- Add title sorting support in `list_books()` endpoint

### Frontend Changes
- Rename `DateStartedConflictDialog` → `DateConflictDialog` (reusable)
- Add `field` prop to distinguish date_started vs date_finished conflicts
- New date formatting utilities: `toDateInputValue()`, `fromDateInputValue()`, `formatDate()`
- Sort controls UI with smart/manual toggle
- i18n strings for new conflict messages and sort options

---

## API Contract Changes

### Status Transition Endpoint (Extended)
**Before:**
```json
{
  "new_status": "read",
  "force_date_started": "2026-05-11"
}
```

**After:**
```json
{
  "new_status": "read",
  "force_date_started": "2026-05-11T14:30:00Z",
  "force_date_finished": "2026-05-11T18:00:00Z"  // NEW
}
```

### List Books Endpoint (Extended)
**New Query Parameters:**
- `sort=title` (in addition to existing options)
- `smart_sort=true|false` (already exists, now exposed in UI)

### Date Format Changes
**Before:** `"2026-05-11"` (date-only string)  
**After:** `"2026-05-11T14:30:00Z"` (ISO 8601 timestamp)

**Backward Compatibility:** Backend accepts both formats via Pydantic parsing.

---

## Testing Strategy

### Backend Tests (pytest)
- Timestamp storage and precision
- Date finished conflict detection
- Force date parameters work correctly
- Title sorting (asc/desc)
- Migration safety (no data loss)

### Frontend Manual Testing
- Date conflict dialogs for both fields
- Sort controls (all options + toggle)
- Date inputs show date-only (not time)
- Timestamps preserved in background
- Migration verification (existing data intact)

---

## Risk Assessment

**High Priority:**
- ⚠️ Data loss during migration → **Mitigation:** Backup DB, test thoroughly, rollback plan
- ⚠️ API breaking changes → **Mitigation:** Backward compatibility via Pydantic

**Medium Priority:**
- ⚠️ Timezone confusion → **Mitigation:** All UTC storage, browser handles display
- ⚠️ UX complexity → **Mitigation:** Smart sort default, manual opt-in

**Low Priority:**
- ⚠️ Performance → **Mitigation:** Indexes exist, SQLite handles datetime efficiently

---

## Rollout Procedure

1. **Development:** Implement phases incrementally, test each independently
2. **Staging:** Deploy + verify migration + smoke test
3. **Production:**
   - Backup database
   - Run migration (quick, <30s)
   - Deploy backend + frontend
   - Monitor logs
   - Collect user feedback

**Rollback:** Revert code + `alembic downgrade -1` + restore backup if needed

---

## Success Criteria

✅ All existing dates preserved after migration  
✅ No type errors (Python/TypeScript)  
✅ All tests pass  
✅ Conflict dialogs appear when expected  
✅ Sort controls work for all options  
✅ Timestamp precision maintained  
✅ No performance regressions  
✅ User feedback positive  

---

## Out of Scope (Future Enhancements)

- Reading history tracking (multiple sessions per book)
- Manual time input in UI
- Relative date filters ("this week", "this month")
- Export with full timestamps
- Audit log for date changes

---

## Approval Decision

**Status:** Ready for review

**Options:**
1. ✅ **Approve** → Proceed with Phase 1 (backend migration)
2. ⏸️ **Request Changes** → Specify modifications needed
3. ❌ **Decline** → Maintain current behavior

**Next Step After Approval:**  
Start with Phase 1 (backend timestamp migration) as it's the foundation for all other changes.

---

**Full Plan:** `.plan/19-improved-date-handling-and-sorting.md` (55KB, ~1100 lines)
