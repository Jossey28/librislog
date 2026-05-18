# 44 — Version Injection via Build-time File Generation

## Overview

Replace the current version mechanism (`importlib.metadata.version()` reading from `pyproject.toml` + optional `GIT_SHA` env var) with a build-time file injection approach. The version is derived from git tags (`git describe`) at build time, baked into both backend and frontend artifacts, and never read from VCS at runtime.

**Single source of truth: git tags.** Format: `vMAJOR.MINOR.PATCH` (e.g., `v0.4.0`). The fallback value uses the same `v` prefix convention so displayed versions are consistent regardless of build environment.

---

## 1. Files to Create

### 1.1 `backend/app/_build_info.py` (committed with fallback)

```python
# Auto-generated at Docker build time. Committed with fallback values.
__version__ = "v0.0.0-dev"
__git_sha__ = "unknown"
```

This file is **committed to git** with the fallback values. The Docker build overwrites it with real values. When running locally without Docker, it stays at `v0.0.0-dev`, which is fine.

### 1.2 `frontend/src/lib/version.ts` (NOT committed, generated at build time)

```typescript
// Auto-generated at Docker build time, NOT in version control.
export const version = "v0.0.0-dev";
export const gitSha = "unknown";
```

This file is **not committed** — it's added to `.gitignore`. During Docker build, it's generated before `npm run build` runs.

---

## 2. Files to Modify

### 2.1 `backend/app/routers/health.py` — change version source

**Current:**
```python
from importlib.metadata import PackageNotFoundError, version

app_ver = "unknown"
try:
    app_ver = version("librislog-backend")
except PackageNotFoundError:
    pass
checks["app_version"] = {
    "version": app_ver,
    "git_sha": os_module.environ.get("GIT_SHA", "unknown"),
}
```

**New:**
```python
from app._build_info import __version__, __git_sha__

checks["app_version"] = {
    "version": __version__,
    "git_sha": __git_sha__,
}
```

Remove `from importlib.metadata import PackageNotFoundError, version` (keep `os_module` — it's still used for the data directory check).

### 2.2 `backend/Dockerfile` — inject version at build time

Add build args and overwrite `_build_info.py` after copying app source:

```dockerfile
ARG APP_VERSION=v0.0.0-dev
ARG GIT_SHA=unknown

# After `COPY app/ ./app/`:
RUN echo "__version__ = \"$APP_VERSION\"" > app/_build_info.py && \
    echo "__git_sha__ = \"$GIT_SHA\"" >> app/_build_info.py
```

### 2.3 `frontend/Dockerfile` — inject version into Svelte build

```dockerfile
ARG APP_VERSION=v0.0.0-dev
ARG GIT_SHA=unknown

# After `COPY . .`, before `RUN npm run build`:
RUN echo "export const version = '${APP_VERSION}'; export const gitSha = '${GIT_SHA}';" > src/lib/version.ts
```

### 2.4 `frontend/.gitignore` — exclude generated version file

Add line:
```
src/lib/version.ts
```

### 2.5 `frontend/src/routes/+layout.svelte` — show version in sidebar

After the `<nav>` end tag inside the sidebar `<aside>`, add:
```svelte
<div class="text-[10px] text-base-content/40 px-1 mt-auto">
	{version}{#if gitSha !== 'unknown'} ({gitSha.slice(0, 7)}){/if}
</div>
```

Add import at top of `<script>`:
```typescript
import { version, gitSha } from '$lib/version';
```

### 2.6 `docker-compose.yml` — pass build args from host

```yaml
backend:
  build:
    context: ./backend
    args:
      APP_VERSION: ${APP_VERSION:-v0.0.0-dev}
      GIT_SHA: ${GIT_SHA:-unknown}

frontend:
  build:
    context: ./frontend
    args:
      PUBLIC_DEFAULT_LOCALE: ${PUBLIC_DEFAULT_LOCALE:-en}
      APP_VERSION: ${APP_VERSION:-v0.0.0-dev}
      GIT_SHA: ${GIT_SHA:-unknown}
```

### 2.7 `pyproject.toml` — leave as-is

No change needed. `version = "0.1.0"` is no longer read by anything but doesn't cause harm.

### 2.8 `README.md` — document version build args

After the existing Quick Start docker-compose command, add:

~~~bash
# Optional: inject app version from git
export APP_VERSION=$(git describe --tags --always)
export GIT_SHA=$(git rev-parse HEAD)
docker compose up --build -d
~~~

Add a brief note: *"Omitting the vars leaves the fallback `v0.0.0-dev` / `unknown`."*

---

## 3. Build Usage

### Docker Compose (with real version)

```bash
export APP_VERSION=$(git describe --tags --always)
export GIT_SHA=$(git rev-parse HEAD)
docker compose up -d --build
```

### Without version (dev fallback)

```bash
docker compose up -d --build
# Version shows as "v0.0.0-dev" (fallback)
```

---

## 4. Testing

No test changes needed. The health endpoint tests only check for key existence (`"version"` in `checks["app_version"]`), not specific values.

---

## 5. Edge Cases

| Scenario | Behavior |
|---|---|
| **No build args provided** | `APP_VERSION=v0.0.0-dev`, `GIT_SHA=unknown` (fallback) |
| **Docker build cache** | `RUN echo...` layer invalidates when build args change — no stale cache |
| **`version.ts` import missing** | SvelteKit throws compile-time error (fails fast) |
| **`version.ts` not in `.gitignore`** | Would show as untracked — adding to `.gitignore` prevents this |
| **Branch builds (no tag)** | `git describe --tags --always` produces `v0.4.0-3-gabc1234` |
| **No git tags exist** | `git describe --always` returns bare commit hash |

---

## 6. Implementation Checklist

- [ ] Create `backend/app/_build_info.py` with fallback values
- [ ] Update `backend/app/routers/health.py` to import from `_build_info`
- [ ] Update `backend/Dockerfile` with build args and `RUN echo...`
- [ ] Add `src/lib/version.ts` to `frontend/.gitignore`
- [ ] Update `frontend/Dockerfile` to generate `version.ts` before build
- [ ] Update `frontend/src/routes/+layout.svelte` to import and display version
- [ ] Update `docker-compose.yml` with build args for both services
- [ ] Update `README.md` Quick Start section with version build-arg example
- [ ] Run `cd backend && pytest` to verify no regressions
- [ ] Build and verify `docker compose up -d --build` with version env vars
