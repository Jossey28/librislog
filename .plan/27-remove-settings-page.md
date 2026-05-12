# Implementation Plan: Remove Settings Page and Create Standalone API Docs Page

## 1. Overview

This plan restructures the API documentation by:
- Removing the `/settings` page entirely
- Creating a new standalone `/api-docs` page (not linked in navigation)
- Adding a link to the API docs in the user profile page's API Keys section
- Cleaning up navigation and i18n strings

## 2. Current State Analysis

### Existing Settings Page (`/settings`)
- Located at: `frontend/src/routes/settings/+page.svelte`
- Contains:
  - API docs viewer with Swagger UI / ReDoc toggle
  - iframe embedding `/api/docs` or `/api/redoc`
  - Loading state and view switcher

### Navigation
- Settings appears in sidebar (`+layout.svelte`):
  - Desktop sidebar navigation
  - Mobile bottom tab bar
  - NAV_ITEMS array at line 106-116

### Profile Page (`/profile`)
- Located at: `frontend/src/routes/profile/+page.svelte`
- Contains multiple sections:
  - Profile update (firstname, lastname, password)
  - Language settings
  - **API Keys management** (lines 193-223) ← Target location for API docs link
  - OIDC account linking (if enabled)

### Backend API Endpoints
- `/api/docs` - Swagger UI (custom styled)
- `/api/redoc` - ReDoc (custom styled)
- Both defined in `backend/app/main.py` (lines 134-154)
- No changes needed to backend

### i18n Strings
**English (`en.json`):**
- `app.settings` (line 6)
- `settings.*` section (lines 124-133)

**German (`de.json`):**
- `app.settings` (line 6)
- `settings.*` section (lines 124-133)

## 3. Implementation Steps

### Phase 1: Create New API Docs Page

**File: `frontend/src/routes/api-docs/+page.svelte`**

Create a new standalone page by adapting the existing settings page content:

```svelte
<script lang="ts">
	import { _ } from '$lib/i18n';

	type DocsView = 'swagger' | 'redoc';
	let docsView = $state<DocsView>('swagger');
	let docsLoading = $state(true);

	const docsUrl = $derived(docsView === 'swagger' ? '/api/docs' : '/api/redoc');

	function onDocsViewChange(event: Event) {
		docsView = (event.currentTarget as HTMLSelectElement).value as DocsView;
		docsLoading = true;
	}
</script>

<div class="max-w-5xl mx-auto flex flex-col gap-6">
	<div>
		<h1 class="text-2xl font-bold">{$_('apiDocs.title')}</h1>
		<p class="text-sm text-base-content/70 mt-1">{$_('apiDocs.subtitle')}</p>
	</div>

	<div class="card bg-base-100 shadow-sm border border-base-200">
		<div class="card-body gap-3">
			<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
				<div>
					<h2 class="text-lg font-semibold">{$_('apiDocs.title')}</h2>
					<p class="text-xs text-base-content/60 mt-1">{$_('apiDocs.subtitle')}</p>
				</div>
				<div class="flex items-center gap-2">
					<span class="text-xs text-base-content/60">{$_('apiDocs.viewLabel')}</span>
					<select class="select select-bordered select-sm" value={docsView} onchange={onDocsViewChange}>
						<option value="swagger">Swagger UI</option>
						<option value="redoc">ReDoc</option>
					</select>
				</div>
			</div>

			<div class="relative rounded-lg border border-base-200 overflow-hidden bg-base-200 min-h-[28rem]">
				{#if docsLoading}
					<div class="absolute inset-0 z-10 grid place-items-center bg-base-200/80">
						<span class="loading loading-spinner loading-md" aria-label={$_('apiDocs.loading')}></span>
					</div>
				{/if}
				<iframe
					src={docsUrl}
					title={$_('apiDocs.frameTitle')}
					class="w-full h-[70vh] min-h-[28rem] bg-base-100"
					onload={() => {
						docsLoading = false;
					}}
				></iframe>
			</div>

			<a href={docsUrl} target="_blank" rel="noreferrer" class="link link-primary text-xs self-start">
				{$_('apiDocs.openNewTab')}
			</a>
		</div>
	</div>
</div>
```

**Rationale:**
- Reuses proven UI from settings page
- Self-contained, no dependencies on removed settings page
- Not linked in navigation (standalone/unlisted)

---

### Phase 2: Update Profile Page with API Docs Link

**File: `frontend/src/routes/profile/+page.svelte`**

**Changes:**
1. Add a link to `/api-docs` in the API Keys section
2. Insert after the API Keys management card, before OIDC section

**Location:** After line 223 (closing `</div>` of API Keys card), add:

```svelte
	<div class="card bg-base-100 border border-base-200 shadow-sm">
		<div class="card-body gap-3">
			<h2 class="text-lg font-semibold">{$_('apiDocs.title')}</h2>
			<p class="text-sm text-base-content/70">{$_('apiDocs.profileHelp')}</p>
			<a href="/api-docs" class="btn btn-outline btn-sm self-start">
				{$_('apiDocs.viewDocs')}
			</a>
		</div>
	</div>
```

**Alternative (more compact):** Add link directly in API Keys section

Insert after line 222 (closing `</ul>` of keys list):

```svelte
			<div class="divider"></div>
			<div class="flex items-center justify-between">
				<p class="text-xs text-base-content/70">{$_('apiDocs.profileHelp')}</p>
				<a href="/api-docs" class="btn btn-link btn-xs">
					{$_('apiDocs.viewDocs')} →
				</a>
			</div>
```

**Recommendation:** Use the compact alternative to keep API Keys and API Docs logically grouped.

---

### Phase 3: Remove Settings from Navigation

**File: `frontend/src/routes/+layout.svelte`**

**Changes:**

1. **Remove settings from NAV_ITEMS** (lines 106-116)

**Before:**
```typescript
const NAV_ITEMS = $derived.by(() => {
	const items = [
		{ href: '/dashboard', labelKey: 'nav.dashboard', icon: '🏠' },
		{ href: '/library', labelKey: 'nav.library', icon: '📚' },
		{ href: '/settings', labelKey: 'app.settings', icon: '⚙️' }
	];
	if ($currentUser?.role === 'admin') {
		items.push({ href: '/admin', labelKey: 'admin.title', icon: '🛠️' });
	}
	return items;
});
```

**After:**
```typescript
const NAV_ITEMS = $derived.by(() => {
	const items = [
		{ href: '/dashboard', labelKey: 'nav.dashboard', icon: '🏠' },
		{ href: '/library', labelKey: 'nav.library', icon: '📚' }
	];
	if ($currentUser?.role === 'admin') {
		items.push({ href: '/admin', labelKey: 'admin.title', icon: '🛠️' });
	}
	return items;
});
```

2. **Remove settings page title handling** (lines 129-131)

**Before:**
```typescript
if ($page.url.pathname.startsWith('/settings')) {
	return `${$_('app.title')} - ${$_('settings.title')}`;
}
```

**After:**
Delete these lines entirely.

3. **Add api-docs page title handling** (after line 128)

**Insert:**
```typescript
if ($page.url.pathname.startsWith('/api-docs')) {
	return `${$_('app.title')} - ${$_('apiDocs.title')}`;
}
```

---

### Phase 4: Delete Settings Page

**Action:**
```bash
rm -rf /home/raffael/git/librislog/frontend/src/routes/settings
```

This removes:
- `frontend/src/routes/settings/+page.svelte`

---

### Phase 5: Update i18n Translations

#### English Translations

**File: `frontend/src/lib/i18n/locales/en.json`**

**Changes:**

1. **Remove** `app.settings` (line 6)
   - Delete: `"settings": "Settings",`

2. **Replace** `settings` section (lines 124-133) with `apiDocs` section:

**Before:**
```json
"settings": {
  "title": "Settings",
  "languageTitle": "Language",
  "apiDocsTitle": "API Documentation",
  "apiDocsHelp": "Explore and test backend endpoints directly from the app.",
  "apiDocsViewLabel": "View",
  "apiDocsLoading": "Loading API documentation",
  "apiDocsFrameTitle": "API documentation",
  "apiDocsOpenNewTab": "Open API docs in a new tab"
},
```

**After:**
```json
"apiDocs": {
  "title": "API Documentation",
  "subtitle": "Explore and test backend endpoints.",
  "viewLabel": "View",
  "loading": "Loading API documentation",
  "frameTitle": "API documentation",
  "openNewTab": "Open API docs in a new tab",
  "profileHelp": "Use API keys to integrate with external tools.",
  "viewDocs": "View API Documentation"
},
```

#### German Translations

**File: `frontend/src/lib/i18n/locales/de.json`**

**Changes:**

1. **Remove** `app.settings` (line 6)
   - Delete: `"settings": "Einstellungen",`

2. **Replace** `settings` section (lines 124-133) with `apiDocs` section:

**Before:**
```json
"settings": {
  "title": "Einstellungen",
  "languageTitle": "Sprache",
  "apiDocsTitle": "API-Dokumentation",
  "apiDocsHelp": "Erkunde und teste Backend-Endpunkte direkt in der App.",
  "apiDocsViewLabel": "Ansicht",
  "apiDocsLoading": "API-Dokumentation wird geladen",
  "apiDocsFrameTitle": "API-Dokumentation",
  "apiDocsOpenNewTab": "API-Dokumentation in neuem Tab öffnen"
},
```

**After:**
```json
"apiDocs": {
  "title": "API-Dokumentation",
  "subtitle": "Erkunde und teste Backend-Endpunkte.",
  "viewLabel": "Ansicht",
  "loading": "API-Dokumentation wird geladen",
  "frameTitle": "API-Dokumentation",
  "openNewTab": "API-Dokumentation in neuem Tab öffnen",
  "profileHelp": "Nutze API-Schlüssel zur Integration mit externen Tools.",
  "viewDocs": "API-Dokumentation anzeigen"
},
```

---

### Phase 6: Testing

#### Backend Tests

**File: `backend/tests/test_docs.py`**

Review and ensure this test doesn't reference a `/settings` frontend route (it likely only tests API endpoints):

```python
# Expected: Tests for /api/docs and /api/redoc endpoints
# No changes should be needed
```

**Action:** Read the file and verify no changes needed.

#### Frontend Unit Tests

No existing tests found for settings or navigation in:
- `frontend/src/lib/validation.test.ts`
- `frontend/src/lib/errors.test.ts`

**Action:** No test updates required.

#### Manual Testing Checklist

1. **Navigation:**
   - ✅ Settings no longer appears in desktop sidebar
   - ✅ Settings no longer appears in mobile bottom nav
   - ✅ Dashboard, Library, and Admin (if admin) links work

2. **Profile Page:**
   - ✅ API Keys section displays correctly
   - ✅ Link to "View API Documentation" appears
   - ✅ Link navigates to `/api-docs`

3. **API Docs Page:**
   - ✅ Page loads at `/api-docs`
   - ✅ Page title shows "LibrisLog - API Documentation"
   - ✅ Swagger UI / ReDoc toggle works
   - ✅ iframe loads correctly
   - ✅ "Open in new tab" link works

4. **Direct Navigation:**
   - ✅ `/settings` shows 404 or redirects appropriately
   - ✅ `/api-docs` is accessible when logged in
   - ✅ `/api-docs` redirects to login when not authenticated

5. **Localization:**
   - ✅ All strings display in English
   - ✅ Switch to German and verify all strings display correctly

---

## 4. Migration Considerations

### User Impact
- **Low impact:** Settings page had minimal functionality
- Users who bookmarked `/settings` will need to find API docs via profile page
- API docs remain fully accessible, just relocated

### Backwards Compatibility
- No API changes
- No database schema changes
- No breaking changes to existing functionality

### Rollback Plan
If issues arise:
1. Restore `frontend/src/routes/settings/+page.svelte` from git
2. Re-add settings to NAV_ITEMS
3. Revert i18n changes
4. Remove `/api-docs` route if created

---

## 5. File Checklist

### Files to Create
- ✅ `frontend/src/routes/api-docs/+page.svelte`

### Files to Modify
- ✅ `frontend/src/routes/profile/+page.svelte` (add API docs link)
- ✅ `frontend/src/routes/+layout.svelte` (remove settings from nav, add api-docs page title)
- ✅ `frontend/src/lib/i18n/locales/en.json` (replace settings with apiDocs)
- ✅ `frontend/src/lib/i18n/locales/de.json` (replace settings with apiDocs)

### Files to Delete
- ✅ `frontend/src/routes/settings/+page.svelte`

### Files to Review (No Changes Expected)
- ⚠️ `backend/tests/test_docs.py` (verify no frontend route references)
- ⚠️ `backend/app/main.py` (no changes needed, but verify API endpoints intact)

---

## 6. Implementation Order

**Recommended sequence to minimize breakage:**

1. **Create new API docs page** → ensures replacement is ready
2. **Update i18n files** → translation strings available before use
3. **Update profile page** → add link to API docs
4. **Update layout navigation** → remove settings, add api-docs title
5. **Delete settings page** → final cleanup
6. **Manual testing** → verify all functionality

---

## 7. Estimated Effort

- **Development:** 30-45 minutes
- **Testing:** 15-20 minutes
- **Total:** ~1 hour

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Broken i18n references | High | Test both EN and DE locales thoroughly |
| Users can't find API docs | Medium | Clear link in profile page, intuitive location |
| Direct `/settings` links fail | Low | Expected behavior, no mitigation needed |
| API docs page not accessible | High | Test authentication and routing |

---

## 9. Success Criteria

- ✅ Settings page removed from navigation
- ✅ `/settings` route deleted
- ✅ `/api-docs` page accessible and functional
- ✅ Profile page contains working link to API docs
- ✅ All i18n strings display correctly in EN and DE
- ✅ No console errors or broken links
- ✅ Backend tests pass
- ✅ Manual testing checklist complete

---

## 10. Notes

- Language settings remain in profile page (not affected by this change)
- API docs backend endpoints (`/api/docs`, `/api/redoc`) unchanged
- This change simplifies navigation and makes profile page the central hub for API-related features
- Future consideration: Add API docs link to admin page if needed
