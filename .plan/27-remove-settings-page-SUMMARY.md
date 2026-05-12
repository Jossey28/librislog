# Feature Plan: Remove Settings Page and Create Standalone API Docs Page

## Summary
Remove the `/settings` page and restructure API documentation to be a standalone page accessible via a link in the user profile page's API Keys section.

## Key Changes
1. **Delete** `/settings` route completely
2. **Create** new `/api-docs` page (not in sidebar navigation)
3. **Update** profile page to include link to API docs in API Keys section
4. **Remove** Settings from sidebar/mobile navigation
5. **Update** i18n translations for English and German

## Files Changed
- **Create:** `frontend/src/routes/api-docs/+page.svelte`
- **Modify:** `frontend/src/routes/profile/+page.svelte`
- **Modify:** `frontend/src/routes/+layout.svelte`
- **Modify:** `frontend/src/lib/i18n/locales/en.json`
- **Modify:** `frontend/src/lib/i18n/locales/de.json`
- **Delete:** `frontend/src/routes/settings/+page.svelte`

## Testing
- **Backend:** No changes needed (API endpoints unchanged)
- **Backend Tests:** Already passing (only test API endpoints, not frontend)
- **Frontend:** Manual testing checklist provided
- **Playwright:** No e2e tests currently exist

## Complexity: Low ⚡
Straightforward refactoring with minimal risk. Language settings remain in profile page.

## Implementation Time: ~1 hour
- Development: 30-45 min
- Testing: 15-20 min

## User Impact: Minimal
- Settings had limited functionality (only API docs viewer)
- All functionality preserved, just relocated
- Better logical grouping (API docs with API Keys)

## Success Criteria
✅ Settings removed from navigation
✅ `/settings` route no longer exists
✅ `/api-docs` accessible and functional
✅ Profile page has working link to API docs
✅ All i18n strings display correctly
✅ No console errors or broken functionality

---

**See full implementation plan:** `27-remove-settings-page.md`
