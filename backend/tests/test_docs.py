"""Tests for custom Swagger / ReDoc documentation endpoints."""

from fastapi.testclient import TestClient


def test_custom_swagger_docs_available(client: TestClient) -> None:
    """Swagger UI should be served at /api/docs."""
    resp = client.get("/api/docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Swagger UI" in resp.text
    assert "LibrisLog API - Swagger UI" in resp.text


def test_custom_redoc_docs_available(client: TestClient) -> None:
    """ReDoc should be served at /api/redoc."""
    resp = client.get("/api/redoc")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "ReDoc" in resp.text
    assert "LibrisLog API - ReDoc" in resp.text


def test_default_docs_disabled(client: TestClient) -> None:
    """Default /docs and /redoc should be disabled (404)."""
    swagger_default = client.get("/docs")
    redoc_default = client.get("/redoc")
    assert swagger_default.status_code == 404
    assert redoc_default.status_code == 404
