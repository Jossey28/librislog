"""
Endpoint tests for GET /api/covers/{filename}.

Uses a dedicated fixture that monkeypatches settings.covers_dir to a
temporary directory so tests never touch the real filesystem.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture()
def covers_client(tmp_path, monkeypatch):
    """TestClient with covers_dir pointed at a fresh tmp directory."""
    monkeypatch.setattr(settings, "covers_dir", str(tmp_path))
    with TestClient(app) as client:
        yield client, tmp_path
    app.dependency_overrides.clear()


def test_get_cover_serves_file(covers_client):
    """A file placed in covers_dir is served with HTTP 200."""
    client, covers_dir = covers_client
    filename = "abc123.jpg"
    (covers_dir / filename).write_bytes(b"fake-image-data")

    resp = client.get(f"/api/covers/{filename}")
    assert resp.status_code == 200
    assert resp.content == b"fake-image-data"


def test_get_cover_404_for_missing(covers_client):
    """Requesting a file that does not exist returns HTTP 404."""
    client, _ = covers_client
    resp = client.get("/api/covers/nonexistent.jpg")
    assert resp.status_code == 404
