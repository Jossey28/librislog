# 41 — Profile Anchor Navigation Menu

Add a sticky/floating side-navigation card with anchor jump-links to each section of the user profile page, positioned to the right of the main content on large screens.

---

## 1. Overview

The profile page (`frontend/src/routes/profile/+page.svelte`) currently displays 4–5 card sections in a single vertical column. On large screens, a sticky card with jump links to each section should appear to the right of the content, improving navigation for users with many settings.

### Sections to link

| Section | Heading i18n key | Proposed `id` |
|---|---|---|
| Profile (name + password) | `user.profile` | `section-profile` |
| Language | `settings.languageTitle` | `section-language` |
| Timezone | `settings.timezone` | `section-timezone` |
| API Keys | `user.apiKeys` | `section-api-keys` |
| SSO / OIDC *(conditional)* | `oidc.profileTitle` | `section-oidc` |

---

## 2. Files to Modify

### 2.1 `frontend/src/routes/profile/+page.svelte`

This is the only file that needs structural changes.

**a) Add `id` attributes to each section card**

Each card `<div class="card ...">` (lines 163, 202, 214, 240, 276) gets an `id={...}` attribute matching the table above. The OIDC card already has `{#if oidcConfig.enabled}` wrapping it — the `id` goes on the card div inside that block.

**b) Restructure the outer container for two-column layout**

Replace the single-column wrapper:

```svelte
<div class="max-w-3xl mx-auto flex flex-col gap-6">
  …cards…
</div>
```

With a responsive two-column wrapper:

```svelte
<div class="lg:flex lg:justify-center lg:gap-8">
  <div class="max-w-3xl mx-auto flex flex-col gap-6">
    …existing cards…
  </div>

  <!-- Anchor nav – only visible lg+ -->
  <nav class="hidden lg:block w-52 shrink-0" aria-label="{$_('profile.sectionNav')}">
    <div class="sticky top-8 card bg-base-100 border border-base-200 shadow-sm">
      <div class="card-body p-4 gap-2">
        <h3 class="text-sm font-semibold text-base-content/70 uppercase tracking-wider">
          {$_('profile.sectionNav')}
        </h3>
        <ul class="flex flex-col gap-1">
          <li><a href="#section-profile" class="link link-hover text-sm" data-section="section-profile">{$_('user.profile')}</a></li>
          <li><a href="#section-language" class="link link-hover text-sm" data-section="section-language">{$_('settings.languageTitle')}</a></li>
          <li><a href="#section-timezone" class="link link-hover text-sm" data-section="section-timezone">{$_('settings.timezone')}</a></li>
          <li><a href="#section-api-keys" class="link link-hover text-sm" data-section="section-api-keys">{$_('user.apiKeys')}</a></li>
          {#if oidcConfig.enabled}
            <li><a href="#section-oidc" class="link link-hover text-sm" data-section="section-oidc">{$_('oidc.profileTitle')}</a></li>
          {/if}
        </ul>
      </div>
    </div>
  </nav>
</div>
```

Key details:
- `lg:flex lg:justify-center lg:gap-8` — on `lg`+ screens, the wrapper becomes a centered flex row; below that it falls back to block (single column).
- `max-w-3xl mx-auto` stays on the content div so form widths don't change.
- The nav card is `hidden` below `lg` and `block` above.
- `w-52 shrink-0` gives the nav a fixed 208px width and prevents it from shrinking.
- `sticky top-8` makes it follow the scroll with an 8-unit (2rem) gap from the viewport top.
- `card bg-base-100 border border-base-200 shadow-sm` follows the existing card pattern.
- The `#section-*` hrefs use native anchor jumps. Combined with `scroll-behavior: smooth` (see §2.3) this gives smooth scrolling without JS.

**c) Smooth scroll CSS**

No separate file needed — add to the global app.css or inline. See §2.3.

**d) (Optional) Active section highlighting**

For extra polish, use an `IntersectionObserver` to add an `active` class to the link whose section is currently in view. This is optional and can be deferred.

### 2.2 `frontend/src/lib/i18n/locales/en.json`

Add under the `"profile"` key (create if it doesn't exist — currently `profile.*` keys are only used in error messages from the save functions):

```json
"profile": {
  "sectionNav": "On this page",
  "profileSaveSuccess": "Profile saved",
  "profileSaveFailed": "Failed to save profile",
  "passwordChangeSuccess": "Password changed",
  "passwordChangeFailed": "Failed to change password"
}
```

> **Note:** The four `profile.*` keys already exist as inline string literals in the `.svelte` file (lines 64, 69 — `$_('profile.profileSaveSuccess')`, etc.), so the `"profile"` block should merge those existing keys. Verify current usage. If `"profile.profileSaveSuccess"` etc. already exist in the JSON, just add `"sectionNav"` to that block.

### 2.3 `frontend/src/lib/i18n/locales/de.json`

Add the German translation:

```json
"profile": {
  "sectionNav": "Auf dieser Seite",
  "profileSaveSuccess": "Profil gespeichert",
  "profileSaveFailed": "Profil konnte nicht gespeichert werden",
  "passwordChangeSuccess": "Passwort geändert",
  "passwordChangeFailed": "Passwort konnte nicht geändert werden"
}
```

Same note about merging existing keys.

### 2.4 `frontend/src/app.css`

Add smooth scrolling to the html element:

```css
html {
  scroll-behavior: smooth;
}
```

This enables native smooth scrolling for all anchor jumps site-wide. If you prefer to scope it to the profile page, use a `<style>` block in `+page.svelte` instead.

---

## 3. Edge Cases & Considerations

### Mobile / Small screens
- The nav is `hidden` below `lg` (Tailwind's `1024px` breakpoint). On tablets and phones the page remains single-column.
- **Alternative for mobile** (optional): Add a `<select>` based "Jump to section" dropdown at the top of the page that appears only below `lg`. This is nice-to-have and not required for the initial implementation.

### OIDC section conditionality
- The OIDC card only renders when `oidcConfig.enabled` is true. The nav link must be wrapped in the same `{#if oidcConfig.enabled}` so the link disappears when the section is absent.

### Scroll margin (preventing header overlap)
- Each section card should have `scroll-mt-24` (or a similar scroll-margin class) so that when the user clicks a jump link, the section heading doesn't sit flush against the top of the viewport — plus there's the sticky nav itself to consider.
- In Tailwind v4: add `class="scroll-mt-24"` to each section card's outer `<div>`. The exact value depends on how much top spacing feels right (try `scroll-mt-24` = 6rem = 96px first).

### Sticky nav overlap with page bottom
- If the page content is shorter than the nav, the sticky card may extend below the content. This is acceptable because `sticky` respects the parent container boundaries — the card stops sticking once the parent scrolls out of view.
- If the parent flex container is exactly the same height as the content (default), the sticky element will be limited to the container height. To fix: the wrapper needs `lg:items-start` to prevent the flex container from stretching to the nav's height.
  → Add `lg:items-start` to the outer `lg:flex` container.

### Long section names in other languages
- The nav card is `w-52` (208px). If translations produce longer text, the link text will wrap to the next line inside the card. That's acceptable, but test with German (`"Single Sign-On"` vs `"API-Schlüssel"`).

### Multiple users / data loading
- The anchor nav is purely presentational and does not interact with API data. No loading states needed.

### Keyboard accessibility
- Using `<a href="#section-*">` provides native keyboard navigation (Tab, Enter). The `aria-label` on `<nav>` provides screen reader context.

---

## 4. Implementation Steps (Checklist)

1. **Add `id` attributes** to each section card div in `+page.svelte`.
2. **Add `scroll-mt-24`** class to each section card div.
3. **Restructure the outer container** from single-column to the two-column flex layout described above.
4. **Insert the anchor nav** card with the links, matching the `{#if oidcConfig.enabled}` condition.
5. **Add `html { scroll-behavior: smooth }`** to `app.css` (or inline).
6. **Add i18n keys** to `en.json` and `de.json`.
7. **Test** at `lg` and below (`1024px` breakpoint):
   - Links navigate to correct sections.
   - Nav card stays sticky while scrolling.
   - On mobile, nav is hidden; page is unchanged.
   - OIDC section: link appears/disappears with the card.
   - Smooth scroll works (click a link, page scrolls smoothly to the target).
8. *(Optional)* Add active-section tracking via `IntersectionObserver`.

---

## 5. Visual Reference (ASCII)

```
┌──────────────────────────────────────────────┐
│  [lg+ screens]                               │
│                                              │
│  ┌──────────────────────┐  ┌──────────────┐  │
│  │  Profile             │  │ ┌──────────┐  │  │
│  │  ┌────────────────┐  │  │ │On this   │  │  │
│  │  │  First name    │  │  │ │page      │  │  │
│  │  │  Last name     │  │  │ │          │  │  │
│  │  │  Password      │  │  │ │• Profile │  │  │
│  │  │  [Save]        │  │  │ │• Language│  │  │
│  │  └────────────────┘  │  │ │• Timezone│  │  │
│  │                      │  │ │• API Keys│  │  │
│  │  Language            │  │ │• SSO     │  │  │
│  │  ┌────────────────┐  │  │ └──────────┘  │  │
│  │  │  [en ▼]        │  │  │ [sticky]      │  │
│  │  │  [Save]        │  │  └──────────────┘  │
│  │  └────────────────┘  │                    │
│  │  ...                 │                    │
│  └──────────────────────┘                    │
└──────────────────────────────────────────────┘
```
