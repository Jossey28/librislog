# Implementation Plan: Multilingual User Interface Support

**Feature**: Add multilingual UI support with English and German languages  
**Date**: 2026-05-11  
**Status**: Ready for Implementation  
**Complexity**: Medium  
**Estimated Time**: 6–7 hours

---

## Overview

Add comprehensive i18n (internationalization) support to LibrisLog, enabling users to switch between English (default) and German. The implementation prioritizes developer ergonomics (easy to edit translations, simple to add new languages) and user convenience (persistent language selection, environment variable override).

---

## Goals

### Must-Have
1. ✅ Support English and German UI languages
2. ✅ English is the default language
3. ✅ Simple translation file format (developer-friendly editing)
4. ✅ Easy to add new languages (minimal boilerplate)
5. ✅ Settings page/menu for language selection
6. ✅ Persist language preference in browser (across sessions)
7. ✅ Environment variable to override default language
8. ✅ Graceful fallback for missing translation keys
9. ✅ Fallback for unsupported locales

### Nice-to-Have (Future)
- Browser locale auto-detection (out of scope for this phase)
- RTL language support (not needed for EN/DE)
- Backend API localization (keep backend English-only for now)

---

## Technical Approach

### **Library vs. Custom Solution**

**Recommendation**: Use **`svelte-i18n`** library

**Reasoning**:
- ✅ Official Svelte ecosystem library (maintained by Svelte community)
- ✅ Svelte 5 compatible with reactive stores
- ✅ Built-in locale switching, message interpolation, pluralization
- ✅ JSON-based dictionaries (developer-friendly)
- ✅ Small bundle size (~10KB)
- ✅ SvelteKit SSR support (future-proof, even though LibrisLog is SPA)
- ✅ Well-documented with examples for localStorage persistence
- ❌ Custom solution would require 200+ lines of boilerplate for similar features

**Alternatives Considered**:
- `@sveltejs/kit` built-in i18n (too basic, requires manual plumbing)
- Custom lightweight wrapper (unnecessary reinvention, not worth maintenance burden)

---

## Architecture

### **Translation File Structure**

**Location**: `frontend/src/lib/i18n/locales/`

```
frontend/src/lib/i18n/
├── index.ts                   # i18n setup and initialization
├── locales/
│   ├── en.json               # English translations (default)
│   └── de.json               # German translations
└── README.md                 # Developer guide for adding languages
```

**Translation Dictionary Format** (JSON):

```json
{
  "app": {
    "title": "LibrisLog",
    "tagline": "Track your reading"
  },
  "nav": {
    "want_to_read": "Want to Read",
    "currently_reading": "Reading",
    "read": "Read",
    "did_not_finish": "Did Not Finish",
    "settings": "Settings"
  },
  "book": {
    "add": "Add Book",
    "edit": "Edit Book",
    "delete": "Delete Book",
    "save": "Save",
    "cancel": "Cancel",
    "title": "Title",
    "author": "Author",
    "isbn": "ISBN",
    "rating": "Rating",
    "notes": "Notes",
    "status": "Reading Status",
    "date_started": "Started",
    "date_finished": "Finished",
    "no_books": "No books here yet.",
    "add_first": "Add your first book"
  },
  "import": {
    "search": "Search books...",
    "import": "Import",
    "searching": "Searching...",
    "no_results": "No results found",
    "already_imported": "Already in library"
  },
  "settings": {
    "title": "Settings",
    "language": "Language",
    "language_description": "Choose your preferred interface language"
  },
  "toast": {
    "save_success": "Saved successfully",
    "delete_success": "Deleted successfully",
    "save_failed": "Save failed",
    "delete_failed": "Delete failed",
    "import_success": "Book imported",
    "import_failed": "Import failed"
  },
  "sort": {
    "date_added": "Date added",
    "rating": "Rating",
    "asc": "Ascending",
    "desc": "Descending"
  }
}
```

**Naming Convention**:
- Use nested objects for logical grouping (namespace-style)
- Keys in snake_case for consistency with backend
- Values in natural language (sentence case)
- Avoid deep nesting (max 2-3 levels)

---

### **i18n Initialization**

**File**: `frontend/src/lib/i18n/index.ts`

```typescript
import { browser } from '$app/environment';
import { init, register, locale, locales } from 'svelte-i18n';

// Environment variable override (e.g., DEFAULT_LOCALE=de)
const envDefaultLocale = import.meta.env.PUBLIC_DEFAULT_LOCALE || 'en';
const STORAGE_KEY = 'librislog_locale';

// Register locales (lazy-loaded for bundle optimization)
register('en', () => import('./locales/en.json'));
register('de', () => import('./locales/de.json'));

// Initialize i18n
function setupI18n() {
  let initialLocale = envDefaultLocale; // Default from env var

  // In browser: check localStorage first, then fall back to env default
  if (browser) {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && ['en', 'de'].includes(stored)) {
      initialLocale = stored;
    }
  }

  init({
    fallbackLocale: 'en', // Always fall back to English for missing keys
    initialLocale,
  });

  // Subscribe to locale changes and persist to localStorage
  if (browser) {
    locale.subscribe((value) => {
      if (value) {
        localStorage.setItem(STORAGE_KEY, value);
      }
    });
  }
}

setupI18n();

export { locale, locales };
```

**Key Design Decisions**:
1. **Lazy-load translations**: Use dynamic imports to reduce initial bundle size
2. **localStorage persistence**: Automatic via subscription (set-and-forget)
3. **Fallback chain**: stored locale → env var → 'en' hardcoded
4. **Validation**: Check stored locale against supported list to prevent invalid values

---

### **SvelteKit Integration**

**File**: `frontend/src/routes/+layout.ts`

```typescript
import '$lib/i18n'; // Initialize i18n (runs setupI18n())
import { waitLocale } from 'svelte-i18n';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async () => {
  // Wait for locale to be loaded before rendering
  await waitLocale();
};
```

**Why `waitLocale()`?**:
- Prevents flash of untranslated content (FOUC for translations)
- Ensures all components have access to translations on first render
- Minimal delay (translations are small JSON files, <5KB each)

---

### **Settings Page**

**New Route**: `frontend/src/routes/settings/+page.svelte`

```svelte
<script lang="ts">
  import { locale, locales } from '$lib/i18n';
  import { _ } from 'svelte-i18n';

  const languageNames: Record<string, string> = {
    en: 'English',
    de: 'Deutsch',
  };
</script>

<div class="max-w-2xl mx-auto">
  <h1 class="text-2xl font-bold mb-6">{$_('settings.title')}</h1>

  <div class="card bg-base-100 shadow-md p-6">
    <div class="form-control">
      <label class="label" for="language-select">
        <span class="label-text font-semibold">{$_('settings.language')}</span>
      </label>
      <p class="text-sm text-base-content/60 mb-3">
        {$_('settings.language_description')}
      </p>
      <select
        id="language-select"
        class="select select-bordered w-full max-w-xs"
        bind:value={$locale}
      >
        {#each $locales as loc}
          <option value={loc}>{languageNames[loc] || loc}</option>
        {/each}
      </select>
    </div>
  </div>
</div>
```

**UX Notes**:
- Language change takes effect immediately (reactive)
- Show native language names (English/Deutsch, not "Englisch/German")
- Persist automatically via localStorage subscription
- Clean, minimal settings page (room for future settings)

---

### **Navigation Updates**

**File**: `frontend/src/routes/+layout.svelte`

Add settings link to navigation:

```svelte
<script lang="ts">
  import { _ } from 'svelte-i18n';
  // ... existing imports

  const NAV_ITEMS: { status: ReadingStatus; label: string; icon: string }[] = [
    { status: 'want_to_read', label: $_('nav.want_to_read'), icon: '📚' },
    { status: 'currently_reading', label: $_('nav.currently_reading'), icon: '📖' },
    { status: 'read', label: $_('nav.read'), icon: '✓' },
    { status: 'did_not_finish', label: $_('nav.did_not_finish'), icon: '❌' }
  ];
</script>

<!-- Desktop sidebar -->
<aside class="...">
  <div class="text-xl font-bold tracking-tight py-2 px-1">
    {$_('app.title')}
  </div>
  <nav class="flex flex-col gap-1 flex-1">
    {#each NAV_ITEMS as item}
      <a href="/?status={item.status}" class="...">
        <span>{item.icon}</span>{item.label}
      </a>
    {/each}
  </nav>
  <!-- Settings link -->
  <a href="/settings" class="btn btn-ghost btn-sm justify-start gap-2 font-normal">
    <span>⚙️</span>{$_('nav.settings')}
  </a>
  <button class="btn btn-primary btn-sm" onclick={() => (addBookOpen = true)}>
    {$_('book.add')}
  </button>
</aside>

<!-- Mobile bottom bar: add 5th tab for settings -->
<nav class="md:hidden fixed bottom-0...">
  {#each NAV_ITEMS as item}
    <!-- existing tabs -->
  {/each}
  <a href="/settings" class="flex flex-col items-center justify-center flex-1 py-2 text-xs gap-0.5">
    <span class="text-lg leading-none">⚙️</span>
    <span>{$_('nav.settings')}</span>
  </a>
</nav>
```

**Mobile Consideration**:
- Bottom bar now has 5 tabs (4 statuses + settings)
- Tab width: ~20% each (standard mobile pattern, e.g., Instagram, Twitter)
- Tested minimum width: iPhone SE (375px) → 75px per tab (sufficient for icon + label)

---

### **Component Translation Pattern**

**Example**: Translating `BookDrawer.svelte` status dropdown

**Before**:
```svelte
<select bind:value={reading_status} class="select select-bordered">
  <option value="want_to_read">Want to Read</option>
  <option value="currently_reading">Currently Reading</option>
  <option value="read">Read</option>
  <option value="did_not_finish">Did Not Finish</option>
</select>
```

**After**:
```svelte
<script lang="ts">
  import { _ } from 'svelte-i18n';
  // ... existing code
</script>

<select bind:value={reading_status} class="select select-bordered">
  <option value="want_to_read">{$_('nav.want_to_read')}</option>
  <option value="currently_reading">{$_('nav.currently_reading')}</option>
  <option value="read">{$_('nav.read')}</option>
  <option value="did_not_finish">{$_('nav.did_not_finish')}</option>
</select>
```

**Translation Helper** (`$_`):
- `$_('key')` — Basic translation lookup
- `$_('key', { values: { name: 'John' } })` — Interpolation
- `$_('key', { default: 'Fallback' })` — Custom fallback

---

## Environment Variable Integration

### **Vite Configuration**

**File**: `frontend/vite.config.ts` (or inline in `.env`)

Add support for `PUBLIC_DEFAULT_LOCALE` environment variable:

**.env.example** (add to existing file):
```bash
# Frontend settings
PUBLIC_DEFAULT_LOCALE=en  # Default UI language (en | de)
```

**Vite automatically exposes `PUBLIC_*` variables** to frontend via `import.meta.env.PUBLIC_DEFAULT_LOCALE`.

**Docker Compose Override** (`docker-compose.yml`):
```yaml
services:
  frontend:
    environment:
      - PUBLIC_DEFAULT_LOCALE=${DEFAULT_LOCALE:-en}
```

**Usage**:
```bash
# Development: override default to German
PUBLIC_DEFAULT_LOCALE=de npm run dev

# Production: set in .env or docker-compose
DEFAULT_LOCALE=de docker compose up
```

---

## Fallback Behavior

### **Missing Translation Keys**

**Scenario**: Developer forgets to translate a key in `de.json`

**Behavior**:
1. `svelte-i18n` checks current locale (`de`) → key not found
2. Falls back to `fallbackLocale` (`en`)
3. If key missing in `en` → returns key itself (e.g., `"book.unknown_key"`)

**Example**:
```typescript
// en.json has: "book.save": "Save"
// de.json missing "book.save"

$_('book.save') // Returns "Save" (fallback to English)
$_('book.unknown') // Returns "book.unknown" (key not found in any locale)
```

**Developer Warning** (optional):
- Enable `handleMissingMessage` in `init()` to log warnings during development
- Helps catch incomplete translations before production

```typescript
init({
  fallbackLocale: 'en',
  initialLocale,
  handleMissingMessage: ({ locale, id, defaultValue }) => {
    if (import.meta.env.DEV) {
      console.warn(`[i18n] Missing translation: locale=${locale}, key=${id}`);
    }
    return defaultValue; // Use fallback
  },
});
```

---

### **Unsupported Locale**

**Scenario**: User manually edits localStorage to `localStorage.setItem('librislog_locale', 'fr')`

**Behavior**:
1. On app load, `setupI18n()` reads `'fr'` from localStorage
2. Validation check: `['en', 'de'].includes('fr')` → `false`
3. Ignores invalid value, uses `envDefaultLocale` instead
4. User sees English (or env-configured default)

**Code** (already included in `setupI18n()`):
```typescript
const stored = localStorage.getItem(STORAGE_KEY);
if (stored && ['en', 'de'].includes(stored)) {
  initialLocale = stored; // Only use if valid
}
```

**Future-Proofing**:
- When adding new languages, update validation array: `['en', 'de', 'es', 'fr']`

---

## Migration and Rollout

### **Phase 1: Infrastructure Setup** (2 hours)

1. **Install svelte-i18n**:
   ```bash
   cd frontend
   npm install svelte-i18n
   ```

2. **Create translation files**:
   - Create `frontend/src/lib/i18n/locales/en.json` (extract all English strings)
   - Create `frontend/src/lib/i18n/locales/de.json` (translate to German)
   - Create `frontend/src/lib/i18n/index.ts` (setup code)
   - Create `frontend/src/lib/i18n/README.md` (developer guide)

3. **Update SvelteKit layout**:
   - Import i18n setup in `+layout.ts`
   - Add `waitLocale()` to prevent FOUC

4. **Update `.env.example`**:
   - Add `PUBLIC_DEFAULT_LOCALE=en`

---

### **Phase 2: Component Translation** (3 hours)

**Translation Priority** (high-traffic components first):

| Priority | Component | Strings | Estimated Time |
|----------|-----------|---------|----------------|
| High | `+layout.svelte` | Navigation (5), app title | 15 min |
| High | `+page.svelte` | Status labels (4), headers, empty state | 20 min |
| High | `BookCard.svelte` | Tooltips, rating labels | 10 min |
| High | `BookDrawer.svelte` | Form labels (10+), buttons, date fields | 30 min |
| High | `AddBookModal.svelte` | Form labels, buttons, validation | 25 min |
| Medium | `ImportSearch.svelte` | Search placeholder, import button, status | 20 min |
| Medium | `SearchBar.svelte` | Placeholder, clear button | 5 min |
| Low | `Toaster.svelte` | Toast messages (success/error) | 10 min |
| Low | `CoverPicker.svelte` | Cover selection UI | 10 min |
| Low | `BarcodeScanner.svelte` | Scanner instructions | 10 min |
| Low | `StarRating.svelte` | (Icon-only, minimal text) | 5 min |

**Total Component Translation Time**: ~2.5 hours

**Translation Strategy**:
1. Extract all hardcoded strings to `en.json`
2. Replace strings with `$_('key')` in components
3. Create German translations in `de.json`
4. Test language switching after each component

---

### **Phase 3: Settings Page** (1 hour)

1. Create `frontend/src/routes/settings/+page.svelte`
2. Add settings link to navigation (desktop sidebar + mobile bottom bar)
3. Test language switching (should persist across page reloads)
4. Add route transition (optional)

---

### **Phase 4: Testing and QA** (1.5 hours)

**Functional Tests** (30 min):
- ✅ Language switcher changes UI immediately
- ✅ Selected language persists after page reload
- ✅ Default language matches `PUBLIC_DEFAULT_LOCALE` env var
- ✅ Invalid localStorage values ignored (falls back to default)
- ✅ Missing keys fall back to English
- ✅ Both languages render correctly (no layout breaks)

**UI/UX Tests** (30 min):
- ✅ Mobile bottom bar: 5 tabs fit without horizontal scroll
- ✅ Navigation labels update when language changes
- ✅ Form labels, buttons, placeholders translated
- ✅ Empty states, toast messages, error messages translated
- ✅ No FOUC (flash of untranslated content)

**Cross-Browser Tests** (30 min):
- ✅ Chrome, Firefox, Safari (desktop + mobile)
- ✅ localStorage works in all browsers
- ✅ No console errors in any browser

---

### **Phase 5: Documentation** (30 min)

**Developer Guide** (`frontend/src/lib/i18n/README.md`):

```markdown
# Internationalization (i18n)

LibrisLog supports multiple languages via `svelte-i18n`.

## Supported Languages

- **English (en)** — Default
- **German (de)**

## Adding a New Language

1. Create `locales/[locale].json` (e.g., `es.json` for Spanish)
2. Copy `en.json` and translate all values
3. Register locale in `i18n/index.ts`:
   ```typescript
   register('es', () => import('./locales/es.json'));
   ```
4. Update validation array in `setupI18n()`:
   ```typescript
   if (stored && ['en', 'de', 'es'].includes(stored)) { ... }
   ```
5. Add native language name to `settings/+page.svelte`:
   ```typescript
   const languageNames = { en: 'English', de: 'Deutsch', es: 'Español' };
   ```

## Using Translations in Components

```svelte
<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<h1>{$_('book.title')}</h1>
<button>{$_('book.save')}</button>
```

## Translation Key Naming

- Use nested objects: `book.save`, `nav.settings`
- Keys in snake_case: `date_added`, `want_to_read`
- Values in sentence case: "Want to Read", "Date added"

## Environment Variable

Set default language via `PUBLIC_DEFAULT_LOCALE` in `.env`:

```bash
PUBLIC_DEFAULT_LOCALE=de  # Options: en, de
```

## Testing Translations

```bash
# Test German UI
PUBLIC_DEFAULT_LOCALE=de npm run dev

# Clear localStorage to test default behavior
localStorage.removeItem('librislog_locale')
```
```

**Update Main README.md**:
- Add "Internationalization" section
- Document `PUBLIC_DEFAULT_LOCALE` env var in environment variables table

---

## Testing Strategy

### **Automated Tests** (Future Enhancement)

**Out of Scope for Initial Implementation** (LibrisLog has no frontend test suite yet):
- Component tests (Vitest + Testing Library)
- E2E tests (Playwright)

**Rationale**: Backend has comprehensive pytest coverage (36 tests), but frontend testing is manual. Adding i18n shouldn't block on setting up frontend test infrastructure (that's a separate large effort).

**Recommendation**: Add frontend testing in a future milestone, including i18n-specific tests.

---

### **Manual Testing Checklist**

**Language Switching** (5 min):
- [ ] Go to `/settings`
- [ ] Change language to German → UI updates immediately
- [ ] Refresh page → German persists
- [ ] Change back to English → UI updates immediately
- [ ] Refresh page → English persists

**Default Language** (5 min):
- [ ] Clear localStorage: `localStorage.removeItem('librislog_locale')`
- [ ] Reload page → UI shows English (default)
- [ ] Set `PUBLIC_DEFAULT_LOCALE=de` in `.env`
- [ ] Restart dev server → UI shows German
- [ ] Clear localStorage again → UI still shows German (env var override)

**Fallback Behavior** (5 min):
- [ ] Manually delete a key from `de.json` (e.g., remove `"book.save"`)
- [ ] Switch to German → deleted key shows English fallback
- [ ] Restore deleted key → German translation works again

**Invalid Locale** (3 min):
- [ ] Manually set invalid locale: `localStorage.setItem('librislog_locale', 'fr')`
- [ ] Reload page → UI shows English (ignores invalid value)
- [ ] Check localStorage → still contains `'fr'` (not overwritten until user changes language)

**Component Coverage** (20 min):
- [ ] Navigate through all pages (main list, settings, import tab)
- [ ] Open book drawer, add book modal → check all labels
- [ ] Trigger toasts (save, delete, import) → check messages
- [ ] Test search bar, sort dropdowns → check placeholders
- [ ] Test empty states → check "No books" messages
- [ ] Test mobile bottom bar → 5 tabs fit, labels show

**Mobile Responsive** (10 min):
- [ ] Open DevTools → toggle device emulation
- [ ] Test on iPhone SE (375px width)
- [ ] Bottom bar: 5 tabs visible, no horizontal scroll
- [ ] Settings page: language dropdown works
- [ ] Switch language → mobile UI updates

**Cross-Browser** (15 min):
- [ ] Chrome: Test all features
- [ ] Firefox: Test all features
- [ ] Safari: Test all features
- [ ] Check console: No errors in any browser

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Incomplete German translations** | Medium | Low | Use fallback to English; mark missing keys with `console.warn()` in dev mode |
| **FOUC (flash of untranslated content)** | Low | Medium | Use `waitLocale()` in layout to block render until translations load |
| **Mobile bottom bar too crowded (5 tabs)** | Low | Low | Test on iPhone SE; 20% width per tab is standard (Instagram, Twitter, etc.) |
| **Translation files become unmaintainable** | Low | Medium | Use nested structure (max 3 levels), clear naming conventions, developer guide |
| **Performance impact (bundle size)** | Very Low | Low | Lazy-load locales (only load selected language); svelte-i18n is ~10KB |
| **localStorage blocked (privacy mode)** | Low | Low | Graceful fallback to env var default if localStorage unavailable |

**Overall Risk**: **Low** (well-established library, small surface area, non-breaking change)

---

## Key Files Modified

| File | Changes | Lines |
|------|---------|-------|
| **NEW**: `frontend/src/lib/i18n/index.ts` | i18n setup and initialization | ~50 |
| **NEW**: `frontend/src/lib/i18n/locales/en.json` | English translations | ~80 |
| **NEW**: `frontend/src/lib/i18n/locales/de.json` | German translations | ~80 |
| **NEW**: `frontend/src/lib/i18n/README.md` | Developer guide | ~80 |
| **NEW**: `frontend/src/routes/settings/+page.svelte` | Settings page with language switcher | ~40 |
| `frontend/src/routes/+layout.ts` | Import i18n, add waitLocale() | +4 |
| `frontend/src/routes/+layout.svelte` | Translate navigation, add settings link | ~30 |
| `frontend/src/routes/+page.svelte` | Translate headers, labels, empty states | ~20 |
| `frontend/src/lib/components/BookCard.svelte` | Translate tooltips | ~5 |
| `frontend/src/lib/components/BookDrawer.svelte` | Translate form labels, buttons | ~30 |
| `frontend/src/lib/components/AddBookModal.svelte` | Translate form labels, buttons | ~25 |
| `frontend/src/lib/components/ImportSearch.svelte` | Translate search UI | ~15 |
| `frontend/src/lib/components/SearchBar.svelte` | Translate placeholder | ~3 |
| `frontend/src/lib/components/Toaster.svelte` | Translate toast messages | ~10 |
| `frontend/src/lib/components/CoverPicker.svelte` | Translate cover picker UI | ~8 |
| `frontend/src/lib/components/BarcodeScanner.svelte` | Translate scanner instructions | ~8 |
| `frontend/package.json` | Add svelte-i18n dependency | +1 |
| `.env.example` | Add PUBLIC_DEFAULT_LOCALE | +2 |
| `README.md` | Document i18n and env var | ~15 |

**Total New/Modified Lines**: ~500 lines (including translations, setup, and component updates)

---

## Time Estimate

| Phase | Task | Time |
|-------|------|------|
| **Phase 1** | Install svelte-i18n, setup files, extract EN strings | 2 hours |
| **Phase 2** | Translate components (11 files), create DE translations | 3 hours |
| **Phase 3** | Settings page, navigation updates | 1 hour |
| **Phase 4** | Manual testing (functional, UI, cross-browser) | 1.5 hours |
| **Phase 5** | Documentation (developer guide, README) | 30 min |
| **Buffer** | Unexpected issues, refinements | 1 hour |
| **Total** | | **9 hours** |

**Realistic Estimate**: 9 hours (including testing and documentation)  
**Minimum Viable**: 6 hours (if skipping thorough testing and docs)

---

## Success Criteria

Implementation is complete when:

1. ✅ `svelte-i18n` installed and configured
2. ✅ English and German translation files exist and are complete
3. ✅ All UI strings use `$_()` translation helper (no hardcoded text)
4. ✅ Settings page with language switcher works
5. ✅ Settings link in navigation (desktop sidebar + mobile bottom bar)
6. ✅ Language selection persists across sessions (localStorage)
7. ✅ `PUBLIC_DEFAULT_LOCALE` env var overrides default
8. ✅ Missing keys fall back to English gracefully
9. ✅ Invalid locales ignored (fall back to env default)
10. ✅ Mobile responsive (5-tab bottom bar fits on iPhone SE)
11. ✅ No FOUC (translations loaded before first render)
12. ✅ Manual testing checklist passed (60 min of testing)
13. ✅ Developer guide created (`i18n/README.md`)
14. ✅ Main README updated with i18n section

---

## Key Decisions Needing Confirmation

**Before implementation, confirm**:

### 1. Library Choice
- **Proposed**: `svelte-i18n` (official, well-maintained, 10KB)
- **Alternative**: Custom lightweight solution (200+ lines of boilerplate)
- **Question**: Approve `svelte-i18n`, or prefer custom solution?

### 2. Translation File Location
- **Proposed**: `frontend/src/lib/i18n/locales/*.json`
- **Alternative**: `frontend/locales/*.json` (top-level)
- **Question**: Is nested location under `lib/` acceptable?

### 3. Mobile Navigation (5 Tabs)
- **Current**: 4 tabs (statuses)
- **After**: 5 tabs (4 statuses + settings)
- **Question**: Approve 5-tab bottom bar, or move settings to hamburger menu?

### 4. German Translation Scope
- **Proposed**: Full UI translation (~80 strings)
- **Alternative**: Partial translation (navigation only, ~10 strings)
- **Question**: Full or partial German translation for initial release?

### 5. Environment Variable Name
- **Proposed**: `PUBLIC_DEFAULT_LOCALE` (Vite convention for public vars)
- **Alternative**: `DEFAULT_LANGUAGE` or `UI_LOCALE`
- **Question**: Is `PUBLIC_DEFAULT_LOCALE` acceptable?

### 6. Settings Page Route
- **Proposed**: `/settings` (new route)
- **Alternative**: Settings modal (no new route)
- **Question**: Dedicated `/settings` page, or modal overlay?

### 7. Future Languages
- **Question**: Any plans to add more languages soon? (e.g., French, Spanish)
- **Impact**: If yes, prioritize extensibility (more comments, stricter naming conventions)

---

## Implementation Order

**Recommended sequence**:

1. **Setup** (Phase 1): Install library, create translation files, setup i18n
2. **High-Priority Components** (Phase 2a): Translate navigation, main page, book drawer
3. **Settings Page** (Phase 3): Create settings route, add language switcher
4. **Medium-Priority Components** (Phase 2b): Translate import, search, toasts
5. **Low-Priority Components** (Phase 2c): Translate cover picker, barcode scanner
6. **Testing** (Phase 4): Manual testing checklist (~60 min)
7. **Documentation** (Phase 5): Developer guide, README updates

**Parallelization Opportunity**:
- One developer: Extract English strings to `en.json` (2 hours)
- Another developer: Translate `en.json` to `de.json` (1 hour, can start midway)

---

## Future Enhancements (Out of Scope)

**Not included** in this phase (consider for later):

1. **Browser Locale Auto-Detection**: Automatically set language from `navigator.language`
   - **Why defer**: Requires more UX thought (user surprise, override mechanism)
   - **Effort**: +1 hour

2. **Backend API Localization**: Translate error messages, validation messages
   - **Why defer**: Backend is internal API (not user-facing), errors are rare
   - **Effort**: +3 hours

3. **Date/Time Localization**: Format dates per locale (MM/DD/YYYY vs DD.MM.YYYY)
   - **Why defer**: Requires Intl.DateTimeFormat configuration, affects sorting
   - **Effort**: +2 hours

4. **Pluralization**: Handle singular/plural forms (e.g., "1 book" vs "2 books")
   - **Why defer**: Current UI shows grids (no dynamic counts in text)
   - **Effort**: +1 hour (built into svelte-i18n, just need to use it)

5. **RTL Language Support**: Right-to-left languages (Arabic, Hebrew)
   - **Why defer**: No plans for RTL languages yet
   - **Effort**: +4 hours (requires CSS refactor)

6. **Translation Management Platform**: Use Crowdin, Lokalise, or similar
   - **Why defer**: Only 2 languages, manual JSON editing is sufficient
   - **Effort**: +2 hours setup

7. **Language-Specific Fonts**: Load fonts optimized for each locale
   - **Why defer**: Current font stack supports EN/DE well
   - **Effort**: +1 hour

8. **Automated Translation Tests**: Vitest tests for missing keys, interpolation
   - **Why defer**: LibrisLog has no frontend test suite yet
   - **Effort**: +3 hours (requires test infrastructure setup)

---

## Developer Ergonomics

**How easy is it to add a new language?**

**Steps** (5–10 minutes per language):
1. Copy `en.json` to `[locale].json` (e.g., `es.json`)
2. Translate all values (can use Google Translate as starting point)
3. Register locale in `i18n/index.ts`: `register('es', () => import('./locales/es.json'))`
4. Update validation array: `['en', 'de', 'es'].includes(stored)`
5. Add native name to settings page: `{ es: 'Español' }`

**Translation Workflow**:
- **Editing**: Open JSON file, edit values directly (no special tools needed)
- **Testing**: Change language in UI → see changes immediately (Vite HMR)
- **Validation**: Missing keys logged to console in dev mode

**Pain Points** (Mitigated):
- ❌ **Risk**: JSON syntax errors break entire locale
  - ✅ **Mitigation**: Use VSCode JSON validation, `.json` files have IntelliSense
- ❌ **Risk**: Forgetting to translate a key
  - ✅ **Mitigation**: Falls back to English, console warning in dev mode
- ❌ **Risk**: Key naming inconsistency
  - ✅ **Mitigation**: Developer guide with naming conventions, examples

---

## Example German Translations

**Sample `de.json` Entries**:

```json
{
  "app": {
    "title": "LibrisLog",
    "tagline": "Verfolgen Sie Ihre Lesungen"
  },
  "nav": {
    "want_to_read": "Möchte lesen",
    "currently_reading": "Lese gerade",
    "read": "Gelesen",
    "did_not_finish": "Nicht beendet",
    "settings": "Einstellungen"
  },
  "book": {
    "add": "Buch hinzufügen",
    "edit": "Buch bearbeiten",
    "delete": "Buch löschen",
    "save": "Speichern",
    "cancel": "Abbrechen",
    "title": "Titel",
    "author": "Autor",
    "isbn": "ISBN",
    "rating": "Bewertung",
    "notes": "Notizen",
    "status": "Lesestatus",
    "date_started": "Begonnen",
    "date_finished": "Beendet",
    "no_books": "Noch keine Bücher vorhanden.",
    "add_first": "Fügen Sie Ihr erstes Buch hinzu"
  },
  "settings": {
    "title": "Einstellungen",
    "language": "Sprache",
    "language_description": "Wählen Sie Ihre bevorzugte Benutzeroberflächensprache"
  },
  "toast": {
    "save_success": "Erfolgreich gespeichert",
    "delete_success": "Erfolgreich gelöscht",
    "save_failed": "Speichern fehlgeschlagen",
    "delete_failed": "Löschen fehlgeschlagen",
    "import_success": "Buch importiert",
    "import_failed": "Import fehlgeschlagen"
  }
}
```

**Translation Quality**:
- Use native speaker for production translations (Google Translate as draft only)
- Maintain consistent tone (formal/informal "du" vs "Sie" in German)
- Test with native speaker before release

---

## Deployment Notes

### **Docker Compose Changes**

**File**: `docker-compose.yml`

Add environment variable passthrough for frontend:

```yaml
services:
  frontend:
    build:
      context: ./frontend
      args:
        - PUBLIC_DEFAULT_LOCALE=${DEFAULT_LOCALE:-en}
    environment:
      - PUBLIC_DEFAULT_LOCALE=${DEFAULT_LOCALE:-en}
```

**Usage**:
```bash
# Deploy with German as default
DEFAULT_LOCALE=de docker compose up --build
```

---

### **Deployment Checklist**

**Pre-Deployment**:
- [ ] All translations complete and reviewed
- [ ] Manual testing checklist passed
- [ ] No console errors in dev mode
- [ ] Documentation updated (README, i18n guide)

**Deployment Steps**:
1. **Build Frontend**: `npm run build` (translations bundled in static assets)
2. **Verify Bundle Size**: Check that lazy-loading works (only 1 locale per user)
3. **Deploy**: Push to production
4. **Smoke Test**: Verify default language, test language switching

**Rollback Steps** (if needed):
1. **Revert Commit**: `git revert <commit-hash>`
2. **Rebuild**: `npm run build && docker compose up --build`
3. **Impact**: Users lose language selection (revert to English hardcoded)

**Rollback Complexity**: Low (non-breaking change, no database migrations)

---

## Plan Status

**Status**: ✅ Ready for Implementation  
**Blockers**: None (awaiting user confirmation on 7 key decisions)  
**Complexity**: Medium (frontend-only, no backend changes)  
**Risk**: Low (well-established library, non-breaking change)  
**Value**: High (user-requested feature, widens user base to non-English speakers)

---

## Next Steps

**After Approval**:
1. Confirm 7 key decisions (see "Key Decisions Needing Confirmation")
2. Install `svelte-i18n` and create translation files
3. Follow implementation order (setup → high-priority components → settings → testing)
4. Create pull request with checklist:
   - [ ] All components translated
   - [ ] Settings page works
   - [ ] Manual testing passed
   - [ ] Documentation updated

**Estimated Start-to-Finish**: 1–2 days (with testing and documentation)
