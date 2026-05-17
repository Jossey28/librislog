# 42 — Health Endpoint Enhancement

## Overview

Replace the current trivial `/api/health` endpoint (which just returns `{"status": "ok"}` with zero checks) with a comprehensive health check that probes database connectivity, schema integrity, filesystem writability, external dependency health, and reports the application version.

---

## 1. Design Decisions

### 1.1 Response Format

Return **HTTP 200** in all cases, with a top-level `status` field:

```json
{
  "status": "healthy" | "unhealthy",
  "checks": {
    "database_connectivity": { "status": "healthy" },
    "database_schema": { "status": "healthy" },
    "data_dir_writable": { "status": "healthy" },
    "quote_service": { "status": "healthy", "detail": "..." } | { "status": "unhealthy", "detail": "..." },
    "app_version": { "version": "0.1.0", "git_sha": "fea7738" }
  }
}
```

**Rationale:**
- Returning 200 regardless allows monitoring systems (load balancers, Kubernetes, etc.) to distinguish between "app is reachable but degraded" (200 + `"status": "unhealthy"`) vs "app is down" (connection refused / 5xx).
- Individual check results let operators pinpoint failures without parsing error messages.
- The `detail` field in check results carries the error message for failed checks.

### 1.2 Endpoint: Sync vs Async

Make the endpoint **async** (`async def`) because:
- The quote service health check makes an HTTP request (naturally async).
- FastAPI transparently supports both sync and async — switching doesn't break existing clients.
- Future checks (e.g., querying external services) may also benefit from async.

Individual synchronous checks (DB query, filesystem access) will be wrapped in `anyio.to_thread.run_sync()` or called directly since they're fast — the async runtime handles them without blocking the event loop for negligible wait times. For simplicity and because these are sub-millisecond operations, they can remain synchronous calls within an async function.

### 1.3 Logging

Log a `logger.warning(...)` for each failing check so that failures appear in the application logs independently of who calls the endpoint. This helps operators detect problems proactively rather than only when a monitoring system polls the endpoint.

Use the standard `logging.getLogger(__name__)` pattern already used throughout the codebase.

### 1.4 App Version Source

| Source | Method |
|---|---|
| **Package version** | `importlib.metadata.version("librislog-backend")` — reads from pyproject.toml at runtime. |
| **Git SHA** | `GIT_SHA` environment variable. This is the standard approach for Docker deployments: CI injects the commit hash as `GIT_SHA` at build time. Falls back to `"unknown"` if unset. |

The `__init__.py` is currently empty — no need to add a `__version__` there since `importlib.metadata` covers the package version automatically.

---

## 2. Files to Modify

| File | Change |
|---|---|
| `backend/app/main.py` | Replace the `health()` function with the enhanced async version. Add `import` statements. |
| `backend/tests/test_books.py` | Update the existing `test_health` to match the new response shape; add new test cases. |

No new files needed. No config changes needed (all required settings already exist).

---

## 3. Detailed Implementation Steps

### Step 1: Add Imports to `backend/app/main.py`

Add these imports at the top of the file, alongside the existing ones:

```python
import logging
import os
from importlib.metadata import version, PackageNotFoundError

import httpx
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.database import engine
```

**Rationale for each import:**
- `logging` — for logging check failures.
- `os` — for `os.access()` to check data directory writability.
- `importlib.metadata.version` — to read app version from installed package metadata.
- `httpx` — to make the async health check request to the quote service (same library already used in `quote_cache.py`).
- `sqlalchemy.inspect` — to introspect the database schema and list existing table names.
- `sqlalchemy.text` — to construct the raw `SELECT 1` query.
- `sqlalchemy.exc.OperationalError, ProgrammingError` — to catch database connection / query errors.
- `app.database.engine` — the shared SQLAlchemy engine used by the rest of the app.

### Step 2: Define the Health Response Helper

At the module level (before the endpoint function), add a small helper to reduce boilerplate:

```python
def _check_result(*, healthy: bool, detail: str | None = None) -> dict:
    return {
        "status": "healthy" if healthy else "unhealthy",
        **( {"detail": detail} if detail else {} ),
    }
```

### Step 3: Replace the `health()` Function

Replace the current stub at lines 158–160 with the full implementation:

```python
logger = logging.getLogger(__name__)


@app.get("/api/health", tags=["meta"])
async def health() -> dict:
    checks: dict[str, dict] = {}
    overall_healthy = True

    # ── 1. Database connectivity ────────────────────────────────────────────
    db_healthy = True
    db_detail: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except (OperationalError, ProgrammingError) as exc:
        db_healthy = False
        db_detail = str(exc)
        logger.warning("Health check failed — database connectivity: %s", exc)
    checks["database_connectivity"] = _check_result(healthy=db_healthy, detail=db_detail)
    overall_healthy = overall_healthy and db_healthy

    # ── 2. Database schema ──────────────────────────────────────────────────
    schema_healthy = True
    schema_detail: str | None = None
    try:
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        required = {"user", "book"}
        missing = required - existing
        if missing:
            schema_healthy = False
            schema_detail = f"Missing tables: {', '.join(sorted(missing))}"
    except (OperationalError, ProgrammingError) as exc:
        schema_healthy = False
        schema_detail = str(exc)
        logger.warning("Health check failed — database schema: %s", exc)
    checks["database_schema"] = _check_result(healthy=schema_healthy, detail=schema_detail)
    overall_healthy = overall_healthy and schema_healthy

    # ── 3. Data directory writable ──────────────────────────────────────────
    dir_healthy = True
    dir_detail: str | None = None
    data_dir = Path(settings.database_url.removeprefix("sqlite:///")).parent
    if not data_dir.exists():
        dir_healthy = False
        dir_detail = f"Data directory does not exist: {data_dir}"
    elif not os.access(str(data_dir), os.W_OK):
        dir_healthy = False
        dir_detail = f"Data directory is not writable: {data_dir}"
    if not dir_healthy:
        logger.warning("Health check failed — data directory writable: %s", dir_detail)
    checks["data_dir_writable"] = _check_result(healthy=dir_healthy, detail=dir_detail)
    overall_healthy = overall_healthy and dir_healthy

    # ── 4. Quote service health ────────────────────────────────────────────
    quote_healthy = True
    quote_detail: str | None = None
    if settings.dashboard_quote_enabled:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(settings.dashboard_quote_url)
                resp.raise_for_status()
        except Exception as exc:
            quote_healthy = False
            quote_detail = str(exc)
            logger.warning("Health check failed — quote service: %s", exc)
        checks["quote_service"] = _check_result(healthy=quote_healthy, detail=quote_detail)
    else:
        checks["quote_service"] = {
            "status": "healthy",
            "detail": "Quote service is disabled via configuration",
        }
    overall_healthy = overall_healthy and quote_healthy

    # ── 5. App version ──────────────────────────────────────────────────────
    app_version = "unknown"
    try:
        app_version = version("librislog-backend")
    except PackageNotFoundError:
        pass

    git_sha = os.environ.get("GIT_SHA", "unknown")

    checks["app_version"] = {
        "version": app_version,
        "git_sha": git_sha,
    }

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "checks": checks,
    }
```

### Step 4: Update the Existing Health Test

In `backend/tests/test_books.py`, replace the current `test_health` function (lines 732–735) with an updated version that accounts for the new response shape.

The test needs to handle that tests run with an in-memory SQLite engine (override via conftest), so the `engine` import in `main.py` will point to the real engine, not the test session's engine. This is a **key consideration** — see §6 (Edge Cases) for the full discussion.

**Approach:** The existing test fixture overrides `get_session` dependency but does **not** override the module-level `engine` in `database.py`. We have two options:

1. **Option A (recommended)** — Make the health endpoint use the same `get_session` dependency (via `next(get_session())`) for the DB check instead of importing `engine` directly. This way tests automatically use the in-memory test database.
2. **Option B** — Allow the health check to use the production-style SQLite engine by temporarily configuring `settings.database_url = "sqlite://"` in tests.

**Decision: Use Option A — reuse the `get_session` dependency.**

This is more testable and architecturally cleaner: the health endpoint should validate the same database connection that the rest of the app uses. If we later add a database pool or connection failover, the health check automatically benefits from it.

**Updated implementation for DB check:**

Replace the direct `engine.connect()` / `inspect(engine)` calls with usage of `get_session`:

```python
from app.database import get_session

# Inside health():
try:
    with next(get_session()) as session:
        session.execute(text("SELECT 1"))
except Exception as exc:
    ...
```

And for schema check, use `inspect(engine)` but note that in tests the engine is overridden — see §6.

**Simpler alternative:** Keep using `engine` directly but modify the test to set an in-memory database URL. Given that tests currently override the session (not the engine), the cleanest approach is:

**Decision revised:** Keep using `engine` directly for the DB checks, since:
- The `engine` is a module-level singleton that represents the real database connection.
- `SQLModel.metadata.create_all(engine)` already runs at startup (via `create_db_and_tables()`).
- In tests, the `engine` is not overridden, but test fixtures use a separate in-memory engine via dependency injection.
- To make tests work, import `app.database` in conftest and replace `engine` during tests, or simply update the test to use the same engine.

**Final decision:** Keep `engine` imports in `main.py`. In the test, monkey-patch `app.database.engine` with the test's in-memory engine before calling the health endpoint. This is the least invasive approach and follows the same monkey-patching pattern already used in `test_dashboard.py`.

However, this creates coupling to the module-level engine. Let me reconsider.

**Revised-and-final decision: Inject `Session` as a FastAPI dependency for the DB check.**

```python
from fastapi import Depends
from sqlmodel import Session
from app.database import get_session

@app.get("/api/health", tags=["meta"])
async def health(db_session: Session = Depends(get_session)) -> dict:
    ...
```

This way:
- The health endpoint uses the same dependency injection as every other route.
- Tests automatically get the in-memory test session through the existing `dependency_overrides` mechanism in conftest.
- No monkey-patching needed.
- The `inspect(engine)` call for schema check uses `db_session.bind` to get the engine associated with the current session.

**Schema check via session:**

```python
inspector = inspect(db_session.bind)
existing = set(inspector.get_table_names())
```

This keeps everything consistent.

---

## 4. Final Implementation Code for `main.py`

```python
import logging
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import httpx
from fastapi import Depends
from sqlalchemy import inspect, text
from sqlmodel import Session

from app.database import get_session

logger = logging.getLogger(__name__)


@app.get("/api/health", tags=["meta"])
async def health(db_session: Session = Depends(get_session)) -> dict:
    checks: dict[str, dict] = {}
    overall_healthy = True

    def _result(*, healthy: bool, detail: str | None = None) -> dict:
        return {
            "status": "healthy" if healthy else "unhealthy",
            **( {"detail": detail} if detail else {} ),
        }

    # ── 1. Database connectivity ────────────────────────────────────────────
    db_ok = True
    db_detail = None
    try:
        db_session.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok = False
        db_detail = str(exc)
        logger.warning("Health check failed — database connectivity: %s", exc)
    checks["database_connectivity"] = _result(healthy=db_ok, detail=db_detail)
    overall_healthy = overall_healthy and db_ok

    # ── 2. Database schema ──────────────────────────────────────────────────
    schema_ok = True
    schema_detail = None
    try:
        inspector = inspect(db_session.bind)
        existing = set(inspector.get_table_names())
        required = {"user", "book"}
        missing = required - existing
        if missing:
            schema_ok = False
            schema_detail = f"Missing tables: {', '.join(sorted(missing))}"
    except Exception as exc:
        schema_ok = False
        schema_detail = str(exc)
        logger.warning("Health check failed — database schema: %s", exc)
    checks["database_schema"] = _result(healthy=schema_ok, detail=schema_detail)
    overall_healthy = overall_healthy and schema_ok

    # ── 3. Data directory writable ──────────────────────────────────────────
    dir_ok = True
    dir_detail = None
    # Extract directory path from sqlite URL: "sqlite:///./data/librislog.db" → Path("./data")
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        data_path_str = db_url.removeprefix("sqlite:///")
        data_dir = Path(data_path_str).parent
        if not data_dir.exists():
            dir_ok = False
            dir_detail = f"Data directory does not exist: {data_dir}"
        elif not os.access(str(data_dir), os.W_OK):
            dir_ok = False
            dir_detail = f"Data directory is not writable: {data_dir}"
    else:
        # Non-SQLite databases: skip directory check (or implement per-adapter logic)
        dir_detail = "Skipped — not a SQLite database"
    if not dir_ok:
        logger.warning("Health check failed — data directory: %s", dir_detail)
    checks["data_dir_writable"] = _result(healthy=dir_ok, detail=dir_detail)
    overall_healthy = overall_healthy and dir_ok

    # ── 4. Quote service health ────────────────────────────────────────────
    quote_ok = True
    quote_detail = None
    if settings.dashboard_quote_enabled:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(settings.dashboard_quote_url)
                resp.raise_for_status()
        except Exception as exc:
            quote_ok = False
            quote_detail = str(exc)
            logger.warning("Health check failed — quote service: %s", exc)
        checks["quote_service"] = _result(healthy=quote_ok, detail=quote_detail)
    else:
        checks["quote_service"] = {
            "status": "healthy",
            "detail": "Quote service is disabled via configuration",
        }
    overall_healthy = overall_healthy and quote_ok

    # ── 5. App version ──────────────────────────────────────────────────────
    app_ver = "unknown"
    try:
        app_ver = version("librislog-backend")
    except PackageNotFoundError:
        pass

    checks["app_version"] = {
        "version": app_ver,
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
    }

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "checks": checks,
    }
```

> **Note about the `_result` helper:** It is defined as a closure inside `health()` rather than as a module-level function. This avoids any import-time / module-level execution concerns. The closure captures nothing from the enclosing scope beyond what's passed as arguments.

---

## 5. Testing

### 5.1 Existing Test

Update `backend/tests/test_books.py` function `test_health` (line 732):

```python
def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["checks"]["database_connectivity"]["status"] == "healthy"
    assert data["checks"]["database_schema"]["status"] == "healthy"
    assert data["checks"]["data_dir_writable"]["status"] == "healthy"
    # quote_service may be healthy or skipped depending on config; just assert it exists
    assert "quote_service" in data["checks"]
    assert "version" in data["checks"]["app_version"]
    assert "git_sha" in data["checks"]["app_version"]
```

### 5.2 Additional Test Cases

Add these to `backend/tests/test_books.py`:

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_health_database_down` | Monkey-patch `db_session.execute` to raise an exception; assert `"status": "unhealthy"` and `database_connectivity.status == "unhealthy"`. |
| 2 | `test_health_missing_tables` | Monkey-patch `inspect(db_session.bind).get_table_names` to return an empty list; assert `database_schema.status == "unhealthy"` and `detail` mentions missing tables. |
| 3 | `test_health_data_dir_not_writable` | Monkey-patch `os.access` to return `False`; assert `data_dir_writable.status == "unhealthy"`. |
| 4 | `test_health_quote_service_unhealthy` | Monkey-patch `httpx.AsyncClient` to raise an exception (same pattern as `test_dashboard.py`); assert `quote_service.status == "unhealthy"`. |
| 5 | `test_health_quote_service_disabled` | Monkey-patch `settings.dashboard_quote_enabled` to `False`; assert `quote_service.status == "healthy"` with `detail` about being disabled. |

**Test patterns to follow:**

- Use `monkeypatch` fixture (already available in pytest) as done in existing tests (`test_dashboard.py` lines 80–87, 112–121).
- For monkey-patching `os.access`, pass a path to the test.
- For monkey-patching the DB session, use `app.dependency_overrides` to inject a broken session, then clean up in `finally`.

### 5.3 Test Example (pattern for DB failure)

```python
def test_health_database_down(client: TestClient):
    def broken_session():
        raise Exception("Connection refused")
    from app.main import app as fastapi_app
    from app.database import get_session
    fastapi_app.dependency_overrides[get_session] = broken_session
    try:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database_connectivity"]["status"] == "unhealthy"
        assert "Connection refused" in data["checks"]["database_connectivity"]["detail"]
    finally:
        fastapi_app.dependency_overrides.clear()
```

### 5.4 Test Example (pattern for quote service failure)

```python
def test_health_quote_service_unhealthy(client: TestClient, monkeypatch):
    async def fake_get(*args, **kwargs):
        raise Exception("Connection timeout")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self, *args, **kwargs): return self
        async def __aexit__(self, *args, **kwargs): pass
        async def get(self, url): return await fake_get(url)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: FakeAsyncClient())

    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["quote_service"]["status"] == "unhealthy"
```

---

## 6. Edge Cases & Considerations

### 6.1 SQLite `check_same_thread = False`

The `engine` is configured with `check_same_thread=False` (see `database.py` line 9). The health endpoint's `Depends(get_session)` will create a new session on the same engine, which is fine — the session is opened and closed within the request scope. No thread-safety issue.

### 6.2 Non-SQLite Databases

If a user configures `database_url` to point to PostgreSQL or MySQL, the `removeprefix("sqlite:///")` call for the data directory check will fail to parse the path. The implementation already has an `if db_url.startswith("sqlite"):` guard. For non-SQLite databases:
- **Data directory check**: Skipped with `detail: "Skipped — not a SQLite database"`.
- **DB connectivity check**: Still works via `SELECT 1` (valid for PostgreSQL, MySQL, etc.).
- **Schema check**: Still works via `inspect(db_session.bind)`.

### 6.3 Quote Service Timeout

The quote service health check uses a 5-second timeout (via `httpx.AsyncClient(timeout=5.0)`). If the service is slow, the health endpoint could take up to 5 extra seconds. This is acceptable because:
- Health endpoints are expected to be slightly slower than regular endpoints.
- 5 seconds is within standard load-balancer health check intervals (usually 10–30s).
- If faster response is desired, use a HEAD request or a dedicated health endpoint on the quote service.

### 6.4 App Version Not Installed

If the package is not installed (e.g., running `python app/main.py` directly without `pip install -e .`), `importlib.metadata.version("librislog-backend")` raises `PackageNotFoundError`. The try/except handles this gracefully by returning `"unknown"`.

### 6.5 FastAPI Dependency Overrides in Tests

The health endpoint uses `Depends(get_session)`. Test fixtures already override `get_session` for authenticated endpoints. However, the health endpoint typically shouldn't require authentication. The `dependency_overrides` in `conftest.py` will still apply, meaning the health check in tests will use the in-memory test database. This is **desired behavior** — we want tests to verify against the test database, not the real one.

**Caution:** If the health endpoint is called before authentication setup in tests (e.g., in a fixture that runs before `client_fixture`), the dependency override won't be set yet and the health check will try to use the real engine. The existing `test_health` test is called within the `client` fixture context, so the override is active. This is fine.

### 6.6 Quote Service in Test Environments

Tests configure `settings` via environment variables / monkeypatch. The default `dashboard_quote_enabled = True` means the health check in tests will try to hit the real quote service URL. To avoid network calls in tests:

- Option 1: Set `dashboard_quote_enabled = False` in the test environment (e.g., in `conftest.py` or via monkeypatch in `test_health`).
- Option 2: Monkey-patch `httpx.AsyncClient` (as shown in the test example).

**Decision:** Update `test_health` to set `dashboard_quote_enabled = False` via monkeypatch so the baseline test remains fast and doesn't depend on external services. Add a separate test for the quote service health check behavior (as outlined in §5.2).

### 6.7 Startup Readiness vs Liveness

The current endpoint acts as both a **liveness** (is the app running?) and **readiness** (is the app ready to serve traffic?) probe. The enhanced version leans more toward readiness because it checks database and external dependencies. For pure liveness, a simpler `/api/healthz` endpoint could be added later if needed — but the current design is sufficient for a single-endpoint approach.

---

## 7. Implementation Checklist

1. **Add imports** to `backend/app/main.py` (logging, os, httpx, importlib.metadata, sqlalchemy inspect/text, Session, get_session).
2. **Add `logger = logging.getLogger(__name__)`** before the endpoint.
3. **Rewrite the `health()` function** as `async def health(db_session: Session = Depends(get_session))` with all five checks.
4. **Remove** the unused direct `from app.database import engine` reference (if it was added — actually, we use `get_session` instead).
5. **Update `test_health`** in `backend/tests/test_books.py` to match new response shape and disable quote service for baseline test.
6. **Add 5 new tests** (DB down, missing tables, data dir not writable, quote service unhealthy, quote service disabled).
7. **Run `pytest`** to verify all existing and new tests pass.
8. **Run `uvicorn`** locally and hit `/api/health` to verify the response shape manually.
