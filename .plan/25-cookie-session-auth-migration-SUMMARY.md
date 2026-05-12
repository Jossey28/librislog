# Plan Summary: Cookie Session Auth Migration (Keep API Keys)

## Overview

Move browser auth from sessionStorage API keys to secure cookie sessions, while preserving API key auth for external clients.

## Core Decisions

- Keep dual auth support:
  - `X-API-Key` for external/API clients
  - HttpOnly cookie session for browser UI
- Browser session must work across tabs in same browser session.
- Remove hidden/default primary API key behavior used for browser bootstrap.

## What Will Change

### Backend

1. Add cookie-session auth flow and a unified auth dependency (`API key OR cookie`).
2. Update protected endpoints to accept cookie sessions.
3. Login/setup/OIDC create browser session cookie.
4. Keep API key CRUD and header auth functional.
5. Remove code paths relying on hidden `is_primary` app key.

### Frontend

1. Stop persisting `librislog.api_key` for browser login.
2. Bootstrap auth via `/api/auth/me` using cookie session.
3. Keep API-key management UI for external-client keys.
4. Ensure logout/login state sync across tabs.

## Primary API Key Cleanup

- Stop auto-creating hidden primary keys at setup/user creation.
- Remove auth/login assumptions that a primary key must exist.
- Keep user-generated keys only.
- Remove/deprecate `is_primary` logic and later drop schema field once safe.

## Testing Focus

- Cookie login/me/logout flows.
- API key header auth remains working.
- Protected routes work with both auth modes.
- Cross-tab session behavior.
- No hidden primary-key dependency remains.

## Success Criteria

1. Browser auth works without storing API keys in sessionStorage.
2. Opening a new tab does not require re-login.
3. External clients continue to use `X-API-Key` unchanged.
4. Hidden default primary-key behavior is removed.
5. Test suite passes without auth regressions.
