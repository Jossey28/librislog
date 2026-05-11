# Summary: Multilingual User Interface Support

## Quick Overview

Add comprehensive i18n (internationalization) support to LibrisLog with English (default) and German languages. Users can switch languages via a new settings page, with preferences persisting across sessions and an environment variable override for deployment flexibility.

---

## What's Being Built

**Feature**: Multilingual UI support with English and German

**User Benefits**:
- Choose preferred language (English or German)
- Language preference saved automatically (persists across sessions)
- Seamless language switching (immediate UI update)
- New settings page for language configuration

**User Flow**:
1. User opens app → sees English UI (default)
2. User navigates to Settings page (new tab in navigation)
3. User selects "Deutsch" from language dropdown
4. UI immediately switches to German
5. User closes app and reopens → German persists (localStorage)

---

## Technical Approach

### **Library Choice**

**Using `svelte-i18n`** (official Svelte ecosystem library):
- ✅ 10KB bundle size, lazy-loaded translations
- ✅ Built-in fallback, interpolation, pluralization
- ✅ Svelte 5 compatible with reactive stores
- ✅ Well-documented, actively maintained

**Alternative Considered**: Custom solution (rejected due to 200+ lines of boilerplate)

---

### **Translation Structure**

**Location**: `frontend/src/lib/i18n/locales/`

```
i18n/
├── index.ts           # Setup and initialization
├── locales/
│   ├── en.json       # English (default, ~80 keys)
│   └── de.json       # German (~80 keys)
└── README.md         # Developer guide
```

**Translation Format** (nested JSON):
```json
{
  "nav": {
    "want_to_read": "Want to Read",
    "currently_reading": "Reading",
    "read": "Read",
    "settings": "Settings"
  },
  "book": {
    "add": "Add Book",
    "save": "Save",
    "title": "Title",
    "author": "Author"
  }
}
```

---

### **Persistence Strategy**

**localStorage** (automatic via reactive subscription):
1. User selects language → `locale.set('de')`
2. `locale` store subscription fires → `localStorage.setItem('librislog_locale', 'de')`
3. Next session: Read from localStorage → `initialLocale = 'de'`

**Fallback Chain**:
1. Check localStorage (e.g., `'de'`)
2. If invalid/missing → Check `PUBLIC_DEFAULT_LOCALE` env var
3. If not set → Default to `'en'`

**Validation**: Only accept `'en'` or `'de'` from localStorage (reject invalid values)

---

### **Environment Variable Integration**

**Variable**: `PUBLIC_DEFAULT_LOCALE` (Vite convention for public env vars)

**Usage**:
```bash
# .env file
PUBLIC_DEFAULT_LOCALE=de

# Command line
PUBLIC_DEFAULT_LOCALE=de npm run dev

# Docker Compose
DEFAULT_LOCALE=de docker compose up
```

**Behavior**:
- Overrides hardcoded default (`'en'`)
- Used when localStorage is empty or invalid
- Allows deployment-time language configuration

---

### **Settings Page**

**New Route**: `/settings`

**Features**:
- Language dropdown with native names (English/Deutsch)
- Immediate effect on selection (reactive)
- Automatic persistence (no "Save" button needed)
- Clean, minimal design (room for future settings)

**Navigation Updates**:
- Desktop sidebar: Add "⚙️ Settings" link above "Add Book" button
- Mobile bottom bar: Add 5th tab for settings (20% width per tab)

**Mobile Consideration**:
- Before: 4 tabs (33% width each)
- After: 5 tabs (20% width each)
- Tested minimum: iPhone SE (375px) → 75px per tab (sufficient)

---

## Fallback Behavior

### **Missing Translation Keys**

**Scenario**: Key exists in `en.json` but missing in `de.json`

**Behavior**:
1. Check `de.json` → not found
2. Fall back to `fallbackLocale` (`en.json`) → found
3. Display English translation

**Developer Warning** (dev mode only):
- Log console warning: `[i18n] Missing translation: locale=de, key=book.unknown`

---

### **Unsupported Locale**

**Scenario**: User manually sets `localStorage.setItem('librislog_locale', 'fr')`

**Behavior**:
1. Validation check: `['en', 'de'].includes('fr')` → `false`
2. Ignore invalid value, use `PUBLIC_DEFAULT_LOCALE` or `'en'`
3. User sees default language (not broken state)

---

## Key Files Modified

| File | Changes | Lines |
|------|---------|-------|
| **NEW**: `frontend/src/lib/i18n/index.ts` | i18n setup | ~50 |
| **NEW**: `frontend/src/lib/i18n/locales/en.json` | English translations | ~80 |
| **NEW**: `frontend/src/lib/i18n/locales/de.json` | German translations | ~80 |
| **NEW**: `frontend/src/lib/i18n/README.md` | Developer guide | ~80 |
| **NEW**: `frontend/src/routes/settings/+page.svelte` | Settings page | ~40 |
| `frontend/src/routes/+layout.ts` | Import i18n, waitLocale() | +4 |
| `frontend/src/routes/+layout.svelte` | Translate navigation | ~30 |
| `frontend/src/routes/+page.svelte` | Translate headers, labels | ~20 |
| `frontend/src/lib/components/*.svelte` | Translate all components (11 files) | ~150 |
| `frontend/package.json` | Add svelte-i18n dependency | +1 |
| `.env.example` | Add PUBLIC_DEFAULT_LOCALE | +2 |
| `README.md` | Document i18n | ~15 |

**Total**: ~550 lines (including translations, setup, and component updates)

---

## Component Translation Pattern

**Before**:
```svelte
<button>Add Book</button>
<option value="want_to_read">Want to Read</option>
```

**After**:
```svelte
<script lang="ts">
  import { _ } from 'svelte-i18n';
</script>

<button>{$_('book.add')}</button>
<option value="want_to_read">{$_('nav.want_to_read')}</option>
```

**Components to Translate** (11 files):
- `+layout.svelte` (navigation, app title)
- `+page.svelte` (headers, empty states, sort labels)
- `BookDrawer.svelte` (form labels, buttons)
- `AddBookModal.svelte` (form labels, buttons)
- `ImportSearch.svelte` (search UI, import status)
- `SearchBar.svelte` (placeholder)
- `Toaster.svelte` (toast messages)
- `BookCard.svelte` (tooltips)
- `CoverPicker.svelte` (cover picker UI)
- `BarcodeScanner.svelte` (scanner instructions)
- `StarRating.svelte` (minimal text)

---

## Implementation Phases

### **Phase 1: Infrastructure** (2 hours)
- Install `svelte-i18n`
- Create translation files (`en.json`, `de.json`)
- Setup `i18n/index.ts` (initialization, localStorage)
- Update `+layout.ts` (import i18n, `waitLocale()`)

### **Phase 2: Component Translation** (3 hours)
- Extract all hardcoded strings to `en.json`
- Replace strings with `$_('key')` in components
- Create German translations in `de.json`
- Test language switching after each component

### **Phase 3: Settings Page** (1 hour)
- Create `/settings` route
- Add language dropdown
- Update navigation (desktop + mobile)

### **Phase 4: Testing** (1.5 hours)
- Functional tests (switching, persistence, fallback)
- UI tests (mobile responsive, layout)
- Cross-browser tests (Chrome, Firefox, Safari)

### **Phase 5: Documentation** (30 min)
- Developer guide (`i18n/README.md`)
- Update main README

---

## Testing Checklist

### **Functional Tests** (30 min)
- [ ] Language switcher changes UI immediately
- [ ] Selected language persists after page reload
- [ ] Default language matches `PUBLIC_DEFAULT_LOCALE` env var
- [ ] Invalid localStorage values ignored
- [ ] Missing keys fall back to English
- [ ] No console errors

### **UI/UX Tests** (30 min)
- [ ] Mobile bottom bar: 5 tabs fit without horizontal scroll
- [ ] Navigation labels update when language changes
- [ ] Form labels, buttons, placeholders translated
- [ ] Empty states, toasts translated
- [ ] No FOUC (flash of untranslated content)

### **Cross-Browser Tests** (30 min)
- [ ] Chrome, Firefox, Safari (desktop + mobile)
- [ ] localStorage works in all browsers

---

## Developer Ergonomics

### **Adding a New Language** (5–10 minutes)

1. Copy `en.json` → `[locale].json` (e.g., `es.json`)
2. Translate all values
3. Register in `i18n/index.ts`: `register('es', () => import('./locales/es.json'))`
4. Update validation: `['en', 'de', 'es'].includes(stored)`
5. Add native name: `{ es: 'Español' }`

**No rebuilds needed** (Vite HMR updates immediately)

---

### **Translation Workflow**

**Editing**:
- Open `.json` file in any editor
- Edit values directly (no special tools)
- VSCode provides JSON validation + IntelliSense

**Testing**:
- Switch language in UI → see changes immediately (HMR)
- Missing keys logged to console in dev mode

---

## Time Estimate

| Phase | Time |
|-------|------|
| Infrastructure setup | 2 hours |
| Component translation | 3 hours |
| Settings page | 1 hour |
| Manual testing | 1.5 hours |
| Documentation | 30 min |
| Buffer for unknowns | 1 hour |
| **Total** | **9 hours** |

**Realistic Estimate**: 9 hours (full implementation with testing)  
**Minimum Viable**: 6 hours (skip thorough testing)

---

## Success Criteria

Implementation complete when:

1. ✅ `svelte-i18n` installed and configured
2. ✅ English and German translation files complete
3. ✅ All UI strings use `$_()` (no hardcoded text)
4. ✅ Settings page with language switcher works
5. ✅ Language selection persists across sessions
6. ✅ `PUBLIC_DEFAULT_LOCALE` env var works
7. ✅ Missing keys fall back to English
8. ✅ Invalid locales ignored
9. ✅ Mobile responsive (5-tab bottom bar)
10. ✅ No FOUC
11. ✅ Manual testing passed (60 min)
12. ✅ Documentation complete

---

## Key Decisions Needing Confirmation

**Before implementation, confirm**:

1. **Library Choice**: Approve `svelte-i18n` vs custom solution?
2. **Translation Location**: `lib/i18n/locales/` vs top-level `locales/`?
3. **Mobile Navigation**: 5-tab bottom bar vs hamburger menu for settings?
4. **German Translation Scope**: Full UI (~80 strings) vs partial (navigation only)?
5. **Environment Variable Name**: `PUBLIC_DEFAULT_LOCALE` vs alternative?
6. **Settings Page Route**: Dedicated `/settings` page vs modal overlay?
7. **Future Languages**: Any plans for more languages soon (affects extensibility)?

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Incomplete German translations | Medium | Fallback to English; console warnings in dev |
| FOUC (flash of untranslated content) | Low | Use `waitLocale()` in layout |
| Mobile bottom bar too crowded | Low | Test on iPhone SE; 20% width is standard |
| Translation files unmaintainable | Low | Nested structure, naming conventions, guide |
| localStorage blocked (privacy mode) | Low | Graceful fallback to env var default |

**Overall Risk**: **Low** (non-breaking, well-established library)

---

## Future Enhancements (Out of Scope)

**Not included** (consider later):
1. Browser locale auto-detection (requires UX thought)
2. Backend API localization (internal API, low priority)
3. Date/time localization (MM/DD/YYYY vs DD.MM.YYYY)
4. Pluralization ("1 book" vs "2 books")
5. RTL language support (Arabic, Hebrew)
6. Translation management platform (Crowdin, Lokalise)
7. Automated translation tests (requires frontend test setup)

---

## Deployment

### **Pre-Deployment**
- [ ] All translations reviewed by native speaker
- [ ] Manual testing passed
- [ ] Documentation updated

### **Deployment Steps**
1. Build frontend: `npm run build`
2. Verify bundle size (lazy-loading works)
3. Deploy to production
4. Smoke test: Verify default language, test switching

### **Rollback**
- Complexity: Low (no database changes)
- Steps: Revert commit, rebuild, redeploy
- Impact: Users lose language selection (revert to English)

---

**Plan Status**: ✅ Ready for Implementation  
**Blockers**: None (awaiting 7 key decisions)  
**Complexity**: Medium (frontend-only)  
**Risk**: Low  
**Value**: High (widens user base to non-English speakers)
