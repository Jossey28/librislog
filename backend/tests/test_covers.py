"""
Endpoint tests for GET /api/covers/{filename} and POST /api/covers/upload.

Uses a dedicated fixture that monkeypatches settings.covers_dir to a
temporary directory so tests never touch the real filesystem.
"""

import io
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth import require_user
from app.config import settings
from app.main import app
from app.models import User, UserRole


@pytest.fixture()
def covers_client(tmp_path: Path, monkeypatch) -> Generator[tuple[TestClient, Path], None, None]:
    """TestClient with covers_dir pointed at a fresh tmp directory."""
    monkeypatch.setattr(settings, "covers_dir", str(tmp_path))

    def _fake_user() -> User:
        return User(
            id=1, firstname="Test", lastname="User",
            email="test@example.com", role=UserRole.user, hashed_password="x",
        )

    app.dependency_overrides[require_user] = _fake_user
    with TestClient(app) as client:
        yield client, tmp_path
    app.dependency_overrides.clear()


# ── GET /api/covers/{filename} ─────────────────────────────────────────────────


def test_get_cover_serves_file(covers_client: tuple[TestClient, Path]) -> None:
    """A file placed in covers_dir is served with HTTP 200."""
    client, covers_dir = covers_client
    filename = "abc123.jpg"
    (covers_dir / filename).write_bytes(b"fake-image-data")

    resp = client.get(f"/api/covers/{filename}")
    assert resp.status_code == 200
    assert resp.content == b"fake-image-data"


def test_get_cover_404_for_missing(covers_client: tuple[TestClient, Path]) -> None:
    """Requesting a file that does not exist returns HTTP 404."""
    client, _ = covers_client
    resp = client.get("/api/covers/nonexistent.jpg")
    assert resp.status_code == 404


def test_get_cover_rejects_path_traversal_dotdot(covers_client: tuple[TestClient, Path]) -> None:
    """Filename containing '..' returns 400."""
    client, _ = covers_client
    resp = client.get("/api/covers/test..jpg")
    assert resp.status_code == 400


def test_get_cover_rejects_backslash(covers_client: tuple[TestClient, Path]) -> None:
    """Filename with backslash returns 400."""
    client, _ = covers_client
    resp = client.get("/api/covers/sub%5Cfile.jpg")
    assert resp.status_code == 400


# ── POST /api/covers/upload ────────────────────────────────────────────────────

_VALID_IMAGE: bytes = b"I" * 10_000


def test_upload_cover_valid_jpeg(covers_client: tuple[TestClient, Path]) -> None:
    """A valid JPEG upload returns 200 and a local cover_url."""
    client, covers_dir = covers_client
    resp = client.post(
        "/api/covers/upload",
        files={"file": ("cover.jpg", io.BytesIO(_VALID_IMAGE), "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cover_url" in data
    assert data["cover_url"].startswith("/api/covers/")
    filename = data["cover_url"].removeprefix("/api/covers/")
    assert (covers_dir / filename).exists()


def test_upload_cover_valid_png(covers_client: tuple[TestClient, Path]) -> None:
    """A valid PNG upload returns 200 and a .png filename."""
    client, covers_dir = covers_client
    resp = client.post(
        "/api/covers/upload",
        files={"file": ("cover.png", io.BytesIO(_VALID_IMAGE), "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    filename = data["cover_url"].removeprefix("/api/covers/")
    assert filename.endswith(".png")


def test_upload_cover_too_small_returns_422(covers_client: tuple[TestClient, Path]) -> None:
    """Images smaller than 5 KB are rejected with HTTP 422."""
    client, _ = covers_client
    small = b"X" * 100
    resp = client.post(
        "/api/covers/upload",
        files={"file": ("tiny.jpg", io.BytesIO(small), "image/jpeg")},
    )
    assert resp.status_code == 422


def test_upload_cover_non_image_returns_422(covers_client: tuple[TestClient, Path]) -> None:
    """A non-image content-type is rejected with HTTP 422."""
    client, _ = covers_client
    resp = client.post(
        "/api/covers/upload",
        files={"file": ("data.txt", io.BytesIO(_VALID_IMAGE), "text/plain")},
    )
    assert resp.status_code == 422


def test_upload_cover_dedup_returns_same_url(covers_client: tuple[TestClient, Path]) -> None:
    """Uploading the same bytes twice returns the same cover_url."""
    client, _ = covers_client
    def make():
        return client.post(
            "/api/covers/upload",
            files={"file": ("cover.jpg", io.BytesIO(_VALID_IMAGE), "image/jpeg")},
        )
    r1 = make()
    r2 = make()
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["cover_url"] == r2.json()["cover_url"]


def test_import_cover_url_rejects_non_http_scheme(covers_client: tuple[TestClient, Path]) -> None:
    """file:// and other non-HTTP schemes are rejected."""
    client, _ = covers_client
    resp = client.post("/api/covers/import-url", json={"url": "file:///etc/passwd"})
    assert resp.status_code == 422


def test_import_cover_url_rejects_restricted_network_targets(covers_client: tuple[TestClient, Path]) -> None:
    """Localhost, private IPs, and link-local addresses are rejected."""
    client, _ = covers_client
    for url in (
        "http://localhost:8000/secret",
        "http://127.0.0.1/internal",
        "http://10.1.2.3/admin",
        "http://192.168.1.50/admin",
        "http://169.254.169.254/latest/meta-data/",
    ):
        resp = client.post("/api/covers/import-url", json={"url": url})
        assert resp.status_code == 422


def test_import_cover_url_downloads_and_returns_local_cover(
    covers_client: tuple[TestClient, Path], monkeypatch,
) -> None:
    """A successful download should return the local cover URL."""
    client, _ = covers_client

    async def _fake_download(
        url: str, covers_dir: str, http_client: object, user_id: int,
    ) -> str:
        return "1__imported.jpg"

    import app.routers.covers as covers_router
    monkeypatch.setattr(covers_router, "import_cover_from_url", _fake_download)

    resp = client.post("/api/covers/import-url", json={"url": "https://example.com/cover.jpg"})
    assert resp.status_code == 200
    assert resp.json()["cover_url"] == "/api/covers/1__imported.jpg"


def test_import_cover_url_returns_422_when_download_fails(
    covers_client: tuple[TestClient, Path], monkeypatch,
) -> None:
    """A failed download should return HTTP 422."""
    client, _ = covers_client

    async def _fake_download(
        url: str, covers_dir: str, http_client: object, user_id: int,
    ) -> None:
        return None

    import app.routers.covers as covers_router
    monkeypatch.setattr(covers_router, "import_cover_from_url", _fake_download)

    resp = client.post("/api/covers/import-url", json={"url": "https://example.com/missing.jpg"})
    assert resp.status_code == 422


def test_get_cover_returns_400_when_resolve_cover_path_returns_none(
    covers_client: tuple[TestClient, Path], monkeypatch,
) -> None:
    """If resolve_cover_path returns None, the endpoint returns 400."""
    client, _ = covers_client
    import app.routers.covers as covers_router

    monkeypatch.setattr(covers_router, "resolve_cover_path", lambda *args, **kwargs: None)
    resp = client.get("/api/covers/anything.jpg")
    assert resp.status_code == 400
