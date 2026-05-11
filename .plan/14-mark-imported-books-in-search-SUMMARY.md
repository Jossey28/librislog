# Summary: Mark Already-Imported Books in Import Search Results

## Quick Overview

Add visual indicators to the Import Book tab showing which books are already in the local collection, preventing confusion and accidental duplicates.

## What's Being Built

**Feature**: Visual "Already imported" badge + disabled "Add" button for books that exist in the local collection.

**User Experience**:
- Search for books → Results show "Already imported" badge for existing books
- Button shows "✓ Imported" and is disabled for duplicates
- Hover tooltip explains why button is disabled
- Newly imported books are immediately marked

## Implementation Approach

### **Client-Side Matching** (No Backend Changes)

1. **Fetch local books** on component mount via `api.books.list()`
2. **Build lookup Sets** for O(1) matching performance:
   - `isbnSet`: Normalized ISBNs
   - `titleAuthorSet`: Normalized "title|author" keys
3. **Match search results** against local collection:
   - Primary: ISBN (exact, normalized)
   - Secondary: Title + Author (exact, case-insensitive, both required)
4. **Update UI** to show badge and disable button
5. **Sync state** after successful import

### Matching Strategy

```typescript
// Primary: ISBN match (most reliable)
if (candidate.isbn && isbnSet.has(normalizeIsbn(candidate.isbn))) {
    return true;
}

// Secondary: Title + Author match (for books without ISBN)
if (candidate.author) {
    const key = `${normalize(candidate.title)}|${normalize(candidate.author)}`;
    return titleAuthorSet.has(key);
}
```

**Design Decision**: **Exact matches only** — no fuzzy matching to avoid false positives.

## Key Files Modified

| File | Changes |
|------|---------|
| `frontend/src/lib/components/ImportSearch.svelte` | • Add `localBooks`, `isbnSet`, `titleAuthorSet` state<br>• Add `onMount` to fetch books<br>• Add `isAlreadyImported()` matching function<br>• Update UI template with badge + disabled button<br>• Update `importBook()` to sync state |

**Lines of code**: ~80 new lines (including comments)

## Testing Strategy

**Manual testing checklist** (10 test cases):
1. ✅ Books with ISBN are matched
2. ✅ Books without ISBN matched by title+author
3. ✅ Same title, different authors → NOT matched
4. ✅ Partial title matches → NOT matched
5. ✅ Newly imported books immediately marked
6. ✅ Disabled button has tooltip
7. ✅ Performance with large collection
8. ✅ ISBN normalization (with/without dashes)
9. ✅ Case-insensitive matching
10. ✅ Empty results (no errors)

**Future**: Playwright integration tests (when test infrastructure is added)

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Book with ISBN exists | ✅ Marked as imported |
| No ISBN, title+author match | ✅ Marked as imported |
| Same title, different author | ✅ NOT marked (correct) |
| Partial/fuzzy match | ✅ NOT marked (exact only) |
| User deletes book in another tab | ⚠️ Stale until remount (known limitation) |
| Large collection (2000+ books) | ✅ Set-based O(1) lookups (fast) |

## Performance

- **Complexity**: O(1) lookups using JavaScript Sets
- **Estimated time**: < 10ms for 2000 books × 10 results
- **Optimization**: Pre-compute normalized Sets on mount, not on every search

## Success Criteria

1. ✅ "Already imported" badge visible on matching books
2. ✅ "Add" button disabled with "✓ Imported" text
3. ✅ Tooltip explains disabled state
4. ✅ Exact match only (no false positives)
5. ✅ Case-insensitive + ISBN normalization working
6. ✅ Newly imported books immediately reflected
7. ✅ Performance acceptable for typical collections

## Implementation Time

- **Code changes**: 1.5 hours
- **Manual testing**: 45 minutes
- **Documentation**: 15 minutes
- **Total**: ~2.5 hours

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| False positives (blocking valid imports) | Exact matching only, require both title+author |
| False negatives (missing duplicates) | Acceptable — better than false positives |
| Performance issues | Use Set-based O(1) lookups |
| Stale state (cross-tab) | Document limitation, enhance later if needed |

## Future Enhancements

1. Backend endpoint for duplicate checking (if performance issues)
2. Cross-component state sync (Svelte stores)
3. Fuzzy matching (Levenshtein distance, configurable)
4. Show existing book details on badge click
5. ISBN-10 ↔ ISBN-13 conversion for better matching

## Dependencies

**None** — uses existing:
- Svelte 5 runes (`$state`, `onMount`)
- DaisyUI badge component
- Existing `api.books.list()` endpoint

## Rollback

**Simple rollback** (all changes in one component):
1. Remove `localBooks` state and `onMount` effect
2. Remove `isAlreadyImported()` function
3. Remove `{@const alreadyImported}` and UI changes
4. Restore original button behavior

**Rollback time**: < 10 minutes

---

**Status**: Ready for implementation
**Complexity**: Low
**Risk**: Low
**Value**: High (improves UX, prevents confusion)
