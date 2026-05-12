# Dashboard Global Search - Implementation Plan Summary

## Feature Overview

Add a global search box to the dashboard that allows users to search through all books in their library regardless of reading status. Results appear in a dropdown below the search box while typing, showing book details (cover, title, author, status). Clicking a result navigates to the appropriate library view with the book detail dialog automatically opened.

## Key Decisions

### No Backend Changes Required ✅

The existing `/api/books?q=query` endpoint already supports:
- Cross-status search (when status parameter is omitted)
- Title and author search (via case-insensitive ILIKE)
- User-scoped filtering

### Component Architecture

```
DashboardSearchBox (new - orchestrator)
  ├── SearchBar (existing - reused)
  └── SearchResultsDropdown (new)
      └── SearchResultItem (new)
```

### Navigation Strategy

When user clicks a search result:
1. Navigate to `/library?status={book.reading_status}&bookId={book.id}`
2. Library page detects `bookId` in URL params
3. Auto-opens book detail dialog for that book
4. Cleans URL (removes bookId param) without page refresh

## Implementation Phases

| Phase | Component/File | Effort | Priority |
|-------|---------------|--------|----------|
| 1 | Backend tests (`test_books.py`) | Low | High |
| 2.1 | `SearchResultItem.svelte` | Low | High |
| 2.2 | `SearchResultsDropdown.svelte` | Low | High |
| 2.3 | `DashboardSearchBox.svelte` | Medium | High |
| 2.4 | Dashboard integration | Low | High |
| 2.5 | Library deep linking | Low | High |
| 3 | i18n keys (en, de) | Low | Medium |
| 4 | Styling & responsive | Low | Medium |
| 5 | Testing & polish | Medium | High |

## Files to Create (3)

1. **`frontend/src/lib/components/SearchResultItem.svelte`**
   - Displays single search result
   - Compact horizontal layout: cover thumbnail + title/author + status badge
   - Handles missing author/cover gracefully

2. **`frontend/src/lib/components/SearchResultsDropdown.svelte`**
   - Container for search results
   - Absolute positioning below search input
   - Loading, empty, and results states

3. **`frontend/src/lib/components/DashboardSearchBox.svelte`**
   - Main orchestrator component
   - Manages search state, API calls, navigation
   - Combines SearchBar + SearchResultsDropdown

## Files to Modify (5)

1. **`frontend/src/routes/dashboard/+page.svelte`**
   - Add `DashboardSearchBox` component below hero section

2. **`frontend/src/routes/library/+page.svelte`**
   - Add URL param detection for `bookId`
   - Auto-open detail dialog when bookId present
   - Clean URL after opening

3. **`backend/tests/test_books.py`**
   - Add test for cross-status search
   - Add test for author search
   - Add test for no results

4. **`frontend/src/lib/i18n/locales/en.json`**
   - Add `dashboard.search.title`
   - Add `dashboard.search.placeholder`
   - Add `dashboard.search.noResults`
   - Add `dashboard.search.failed`

5. **`frontend/src/lib/i18n/locales/de.json`**
   - Add German translations for above keys

## Technical Highlights

### Search Performance
- **Debouncing**: 300ms delay (handled by existing SearchBar)
- **Scope**: Title + author only (backend ILIKE query)
- **User Filtering**: Automatic via `current_user.id` in backend
- **Result Limit**: No limit initially; monitor performance

### UX Features
- Real-time search as user types
- Loading spinner during API call
- Empty state message when no results
- Keyboard navigation support
- Click-outside-to-close (optional)
- Responsive design (mobile + desktop)

### Accessibility
- Proper ARIA roles (`role="listbox"`, `role="option"`)
- Keyboard navigation
- Screen reader compatible
- Semantic HTML

## Testing Strategy

### Backend Tests
```bash
pytest backend/tests/test_books.py::test_list_books_global_search* -v
```

### Manual Testing Checklist
- [ ] Search finds books across all statuses
- [ ] Search matches both title and author
- [ ] Debouncing works (doesn't search on every keystroke)
- [ ] Results show correct cover/title/author/status
- [ ] Missing author doesn't break layout
- [ ] Missing cover shows placeholder
- [ ] Clicking result navigates correctly
- [ ] Book detail dialog auto-opens
- [ ] Empty query hides dropdown
- [ ] No results shows empty state
- [ ] Loading state shows spinner
- [ ] Responsive on mobile/tablet/desktop
- [ ] No console errors

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Slow search on large libraries | - Database indexed on user_id<br>- Frontend debouncing<br>- Consider pagination if needed |
| Dropdown positioning issues | - Absolute positioning with proper container<br>- Test on various screen sizes |
| Deep linking fails | - Fallback: just navigate to tab<br>- Thorough testing |

## Acceptance Criteria

✅ **Must Have**:
- Search box on dashboard
- Real-time debounced search
- Results show cover, title, author (if available), status
- Click result → navigate to library + auto-open detail
- Empty/loading states
- Responsive design

🚫 **Out of Scope** (Future Enhancements):
- Advanced filters (by rating, date, etc.)
- Search history
- Keyboard shortcuts (Cmd+K)
- Search highlighting
- ISBN search
- Fuzzy search

## Estimated Effort

- **Backend**: 30 minutes (tests only)
- **Frontend Components**: 2-3 hours
  - SearchResultItem: 30 min
  - SearchResultsDropdown: 45 min
  - DashboardSearchBox: 1 hour
  - Integration: 30 min
- **Deep Linking**: 30 minutes
- **i18n**: 15 minutes
- **Testing**: 1 hour
- **Total**: ~4-5 hours

## Next Steps

1. ✅ Review plan with stakeholder
2. ⏳ Implement Phase 1 (backend tests)
3. ⏳ Build frontend components (Phase 2)
4. ⏳ Add i18n keys
5. ⏳ Manual testing
6. ⏳ Polish and deploy

---

**Plan Status**: ✅ Ready for Review

**Created**: 2026-05-12  
**Plan File**: `.plan/29-dashboard-global-search.md`
