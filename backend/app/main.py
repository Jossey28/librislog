import logging
import os as os_module
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlmodel import Session
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import get_session
from app.logging_config import configure_logging
from app.routers import auth, books, covers, import_, oidc, profile, progress, users

logger = logging.getLogger(__name__)

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.covers_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="LibrisLog API",
    description="Backend API for LibrisLog.",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
def _clean_env_value(value: str) -> str:
    return value.split("#", 1)[0].strip()


cookie_domain_raw = _clean_env_value(settings.auth_cookie_domain)
cookie_domain = cookie_domain_raw or None
cookie_samesite = _clean_env_value(settings.auth_cookie_samesite).lower()
if cookie_samesite not in {"lax", "strict", "none"}:
    cookie_samesite = "lax"
cookie_name = _clean_env_value(settings.auth_cookie_name) or "librislog_session"
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.api_key_encryption_key,
    session_cookie=cookie_name,
    same_site=cookie_samesite,
    https_only=settings.auth_cookie_secure,
    domain=cookie_domain,
)

app.include_router(books.router)
app.include_router(import_.router)
app.include_router(covers.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(oidc.router)
app.include_router(progress.router)


def _wrap_docs_html(html: str) -> HTMLResponse:
    custom_css = """
<style>
  :root {
    --bg: #f4f6f8;
    --surface: #ffffff;
    --text: #1f2937;
    --muted: #6b7280;
    --primary: #2563eb;
    --border: #e5e7eb;
  }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  }
  .topbar, .menu-content {
    display: none !important;
  }
  .swagger-ui .scheme-container,
  .swagger-ui .info,
  .swagger-ui .wrapper {
    background: transparent;
    box-shadow: none;
  }
  .swagger-ui .opblock,
  .swagger-ui .responses-inner,
  .swagger-ui .model-box,
  .swagger-ui .auth-container,
  .swagger-ui .dialog-ux {
    border-color: var(--border);
  }
  .swagger-ui .btn.execute,
  .swagger-ui .btn.authorize,
  .swagger-ui .btn.modal-btn.auth.authorize {
    background: var(--primary);
    border-color: var(--primary);
    color: #fff;
  }
  .swagger-ui .opblock-tag,
  .swagger-ui .opblock-summary,
  .swagger-ui .info .title,
  .swagger-ui,
  .swagger-ui p,
  .swagger-ui table,
  .swagger-ui .response-col_status,
  .swagger-ui .response-col_description {
    color: var(--text);
  }
  .swagger-ui .info .description,
  .swagger-ui .markdown p,
  .swagger-ui .markdown li,
  .swagger-ui .response-col_links,
  .swagger-ui .model-title small {
    color: var(--muted);
  }
  .redoc-wrap {
    background: var(--bg);
  }
  .redoc-wrap > div {
    border-left: 1px solid var(--border);
  }
</style>
"""
    return HTMLResponse(html.replace("</head>", f"{custom_css}</head>"))


@app.get("/api/docs", include_in_schema=False)
def custom_swagger_docs() -> HTMLResponse:
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
            "docExpansion": "list",
        },
    ).body.decode("utf-8")
    return _wrap_docs_html(html)


@app.get("/api/redoc", include_in_schema=False)
def custom_redoc_docs() -> HTMLResponse:
    html = get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
    ).body.decode("utf-8")
    return _wrap_docs_html(html)


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
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        if db_url == "sqlite:///:memory:":
            dir_detail = "Skipped — in-memory database"
        else:
            data_path_str = db_url.removeprefix("sqlite:///")
            if "?" in data_path_str:
                data_path_str = data_path_str.split("?", 1)[0]
            data_path = Path(data_path_str)
            data_dir = data_path.parent
            if not data_path.is_absolute():
                data_dir = Path.cwd() / data_dir
            if not data_dir.exists():
                dir_ok = False
                dir_detail = f"Data directory does not exist: {data_dir}"
            elif not os_module.access(str(data_dir), os_module.W_OK):
                dir_ok = False
                dir_detail = f"Data directory is not writable: {data_dir}"
    else:
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
        "git_sha": os_module.environ.get("GIT_SHA", "unknown"),
    }

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "checks": checks,
    }
