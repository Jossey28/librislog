"""Tests for cover import safety checks."""

from unittest.mock import patch

from app.services.cover_import import is_external_cover_url, is_safe_cover_import_url


def test_is_external_cover_url_http_and_https():
    assert is_external_cover_url("https://example.com/cover.jpg") is True
    assert is_external_cover_url("http://example.com/cover.jpg") is True


def test_is_external_cover_url_relative_and_local():
    assert is_external_cover_url("/covers/abc.jpg") is False
    assert is_external_cover_url("covers/abc.jpg") is False
    assert is_external_cover_url(None) is False
    assert is_external_cover_url("") is False


def test_is_safe_cover_import_url_valid_https():
    assert is_safe_cover_import_url("https://example.com/cover.jpg") is True


def test_is_safe_cover_import_url_rejects_invalid_url():
    assert is_safe_cover_import_url("not-a-url") is False


def test_is_safe_cover_import_url_rejects_no_hostname():
    assert is_safe_cover_import_url("https:///path") is False


def test_is_safe_cover_import_url_rejects_localhost():
    assert is_safe_cover_import_url("http://localhost:8000/cover.jpg") is False
    assert is_safe_cover_import_url("http://127.0.0.1/cover.jpg") is False
    assert is_safe_cover_import_url("http://[::1]/cover.jpg") is False
    assert is_safe_cover_import_url("http://0.0.0.0/cover.jpg") is False


def test_is_safe_cover_import_url_rejects_url_with_credentials():
    assert is_safe_cover_import_url("https://user:pass@example.com/cover.jpg") is False
    assert is_safe_cover_import_url("https://user@example.com/cover.jpg") is False


def test_is_safe_cover_import_url_rejects_private_ips():
    assert is_safe_cover_import_url("http://10.0.0.1/cover.jpg") is False
    assert is_safe_cover_import_url("http://172.16.0.1/cover.jpg") is False
    assert is_safe_cover_import_url("http://192.168.1.1/cover.jpg") is False


def test_is_safe_cover_import_url_rejects_multicast():
    assert is_safe_cover_import_url("http://224.0.0.1/cover.jpg") is False


def test_is_safe_cover_import_url_dns_failure():
    """OSError from getaddrinfo should return False."""
    with patch(
        "app.services.cover_import.socket.getaddrinfo",
        side_effect=OSError("DNS failure"),
    ):
        assert is_safe_cover_import_url("https://unresolvable.example/cover.jpg") is False


def test_is_safe_cover_import_url_resolved_restricted_ip():
    """Resolved IP that is restricted should return False."""
    with patch(
        "app.services.cover_import.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("127.0.0.1", 443))],
    ):
        assert is_safe_cover_import_url("https://localhost-via-dns.example/cover.jpg") is False


def test_is_safe_cover_import_url_resolved_invalid_ip():
    """Resolved address that is not a valid IP should return False."""
    with patch(
        "app.services.cover_import.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("not-an-ip", 443))],
    ):
        assert is_safe_cover_import_url("https://invalid-addr.example/cover.jpg") is False
