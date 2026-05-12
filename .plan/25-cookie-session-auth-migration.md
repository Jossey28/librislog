# Plan: Cookie Session Auth Migration (Keep API Keys)

## Overview

Migrate browser authentication from sessionStorage-held API keys to secure cookie-based sessions, while preserving full API key support for external/API clients.

## Goals

- Keep `X-API-Key` authentication fully functional for non-browser clients.
- Add secure browser session auth using `HttpOnly` cookies.
- Ensure browser login is shared across tabs in one browser session.
- Avoid breaking current endpoints and existing clients during rollout.
- Remove the hidden per-user primary/default API key concept used for browser auth bootstrap.

## Key Requirements

1. **Dual auth modes** must coexist:
   - API key mode (`X-API-Key`) for external clients.
   - Cookie session mode for browser frontend.
2. **Cross-tab browser session**:
   - Login in one tab should apply to other tabs.
   - User should not need to re-login when opening another tab.
3. **Primary key cleanup**:
   - No hidden/default API key should be auto-created for browser usage.
   - API keys remain optional user-managed credentials for external clients.

---

## Target Design

### Authentication resolution order

For protected routes:
1. If `X-API-Key` exists and is valid -> authenticate via API key.
2. Else if session cookie exists and is valid -> authenticate via browser session.
3. Else -> `401`.

### Browser session model

- Use server-side session records (DB-backed), not JS-readable token storage.
- Cookie stores opaque session id only.
- Cookie flags:
  - `HttpOnly`
  - `Secure` (prod)
  - `SameSite=Lax`
  - `Path=/`

---

## Implementation Phases

### Phase 1: Data model and config

#### 1.1 Add browser session table

Add model `BrowserSession` (name may vary) in `backend/app/models.py`:

- `id` (uuid/string, primary key)
- `user_id` (FK)
- `created_at`
- `last_used_at`
- `expires_at` (optional policy)
- `revoked_at` (nullable)
- optional fingerprint fields (e.g., `user_agent_hash`)

#### 1.2 Add migration

Create Alembic migration to add the table + indexes on `user_id`, `revoked_at`, `expires_at`.

#### 1.3 Add config

In `backend/app/config.py`:

- `auth_cookie_name` (default `librislog_session`)
- `auth_cookie_secure` (default `True`)
- `auth_cookie_samesite` (default `lax`)
- `auth_cookie_domain` (optional)
- `auth_cookie_path` (default `/`)
- optional idle/absolute session ttl settings

---

### Phase 2: Backend auth helpers

Add helpers in `backend/app/auth.py` (or dedicated module):

- `create_browser_session(user_id, request_meta) -> session_id`
- `get_browser_session(session_id) -> session or None`
- `revoke_browser_session(session_id)`
- `revoke_all_browser_sessions(user_id)` (optional admin/security utility)
- `set_auth_cookie(response, session_id)`
- `clear_auth_cookie(response)`

---

### Phase 3: Unified dependency

Introduce new dependency (example):

- `require_user()` -> accepts API key OR cookie session.

Keep existing:

- `require_user_by_api_key()` for strict key-only behavior where needed.

Update protected routers to use `require_user()` unless API-key-only is intentional.

---

### Phase 4: Auth endpoint behavior (non-breaking)

#### 4.1 Login

`POST /api/auth/login`:

- Validate credentials.
- Create browser session.
- Set session cookie.
- Return user payload.
- Compatibility option: continue returning `api_key` only when explicitly requested by non-browser clients (e.g., query/header flag), or keep existing contract temporarily.

#### 4.2 Me

`GET /api/auth/me` should work with either auth mode.

#### 4.3 Logout

`POST /api/auth/logout`:

- If cookie-authenticated: revoke that browser session + clear cookie.
- Preserve current API-key logout semantics for key-authenticated flows.

#### 4.4 Setup and OIDC callback

- After setup or OIDC sign-in success, create browser session and set cookie.

#### 4.5 Remove hidden primary key dependency

- Stop auto-creating a default `is_primary` API key during setup/user creation.
- Stop requiring a primary key to exist for browser login/me flows.
- Keep API key CRUD endpoints for user-managed keys (external clients).
- Option A (recommended):
  - Keep `is_primary` column temporarily for compatibility, but set it unused/deprecated.
  - Add migration later to remove it once no code path depends on it.
- Option B (single-step cleanup):
  - Remove `is_primary` semantics now and migrate schema + queries in same release.

Implementation details for cleanup:

- Update setup/auth/user creation services to avoid issuing hidden key material.
- Update any auth fallback logic that assumes "one primary key per user".
- Ensure key list UI/API only represents user-created keys.

---

### Phase 5: Frontend migration

#### 5.1 Remove browser dependency on stored API key

In `frontend/src/lib/stores/auth.ts` and related bootstrap:

- Stop storing `librislog.api_key` in sessionStorage for web auth.
- Initialize auth by calling `/api/auth/me` (cookie automatically sent).
- Keep current user state in-memory.

#### 5.2 Update login/setup pages

- On login/setup success, rely on cookie session; do not persist API key in browser storage.

#### 5.3 Cross-tab sync

- Implement `BroadcastChannel` (or storage event fallback) for logout sync between tabs.
- Opening a new tab should already be authenticated due to shared session cookie.

#### 5.4 Keep API key management UI

- Retain create/list/delete API keys for external clients.
- UI no longer uses generated key as its own auth mechanism.

---

### Phase 6: Security hardening

- Add CSRF protection for cookie-authenticated state-changing routes.
- Tighten CORS and cookie settings per environment.
- Ensure no sensitive token is exposed to JS in browser auth flow.
- Eliminate stale hidden key records that are no longer needed for browser auth.

---

### Phase 7: Primary API key deprecation/removal

- Add one-time data migration for legacy rows marked `is_primary=true`:
  - Preferred: keep records but mark as regular keys only if explicitly user-visible/needed.
  - Otherwise: revoke/delete legacy hidden keys that were created only for browser bootstrapping.
- Remove dead code paths and helpers tied to "primary app key" assumptions.
- If removing schema field:
  - Add migration to drop `is_primary` column.
  - Update ORM model, serializers, and tests accordingly.

---

## Testing Plan

### Backend tests (pytest)

1. Login sets cookie with expected attributes.
2. `/api/auth/me` works via cookie auth.
3. `/api/auth/me` still works via API key auth.
4. Protected endpoints accept API key and cookie auth.
5. Logout revokes session and clears cookie.
6. Revoked/expired session returns `401`.
7. OIDC callback establishes cookie session.
8. API key flows remain unchanged for external-client scenarios.
9. Setup/user creation no longer auto-creates hidden primary keys.
10. Legacy hidden primary-key records are handled according to migration policy.

### Frontend tests (Vitest + manual)

1. No `librislog.api_key` persists for web login.
2. Login in tab A -> tab B opens authenticated.
3. Logout in tab A -> tab B reflects logged-out state.
4. Setup and OIDC login continue working.
5. API-key management screens still function.
6. UI does not depend on any hidden/primary key state.

---

## Files Likely Affected

### Backend

- `backend/app/models.py`
- `backend/alembic/versions/<new_migration>.py`
- `backend/app/config.py`
- `backend/app/auth.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/oidc.py`
- `backend/app/routers/profile.py` (API key list/create/delete behavior)
- `backend/app/routers/users.py` (user creation side effects)
- any routers currently bound to `require_user_by_api_key`
- `backend/tests/test_auth_profile_users.py`
- `backend/tests/test_oidc.py`
- new tests for browser session behavior

### Frontend

- `frontend/src/lib/stores/auth.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/routes/+layout.svelte`
- `frontend/src/routes/login/+page.svelte`
- `frontend/src/routes/setup/+page.svelte`
- optional shared auth/bootstrap utilities

---

## Rollout Strategy

1. Ship backend dual-mode support first (backward compatible).
2. Ship frontend cookie-based auth usage second.
3. Monitor logs/metrics for auth failures and mode adoption.
4. Optional later cleanup: deprecate browser-side API key login return shape.
5. Remove hidden-primary-key behavior and optionally drop `is_primary` schema field.

---

## Risks and Mitigations

### Risk: Breaking external API clients
- **Mitigation**: Keep `X-API-Key` validation unchanged and tested.

### Risk: CSRF exposure after cookie auth
- **Mitigation**: enforce CSRF strategy for state-changing endpoints.

### Risk: Session invalidation edge cases (OIDC/logout)
- **Mitigation**: explicit tests for login/logout callback flows.

### Risk: Removing primary-key assumptions breaks legacy flows
- **Mitigation**: explicit migration tests and staged deprecation (logic first, schema removal second).

---

## Success Criteria

1. Browser UI auth no longer depends on sessionStorage API key.
2. Login persists across tabs in same browser session.
3. External clients can still authenticate with API keys exactly as before.
4. All auth-related tests pass.
5. No regressions in setup, login, logout, OIDC, and protected routes.
6. No hidden default API key is created/required for browser auth.
