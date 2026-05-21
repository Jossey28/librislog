"""Tests for ISBN utility functions."""

from app.services.isbn_utils import isbn13_to_isbn10, normalize_isbn


def test_normalize_isbn_strips_hyphens_and_spaces() -> None:
    """Hyphens and spaces should be stripped from ISBN strings."""
    assert normalize_isbn("978-0-545-01022-1") == "9780545010221"
    assert normalize_isbn("0 545 01022 5") == "9780545010221"


def test_normalize_isbn_10_to_13() -> None:
    """ISBN-10 should be converted to ISBN-13."""
    assert normalize_isbn("0545010225") == "9780545010221"


def test_normalize_isbn_13_passthrough() -> None:
    """ISBN-13 should pass through unchanged."""
    assert normalize_isbn("9780545010221") == "9780545010221"


def test_normalize_isbn_rejects_invalid() -> None:
    """Invalid ISBN strings should raise ValueError."""
    import pytest
    with pytest.raises(ValueError):
        normalize_isbn("not-an-isbn")


def test_isbn13_to_isbn10_check_value_11() -> None:
    """When weighted_sum mod 11 == 0, check_value is 11, check_digit becomes '0'."""
    assert isbn13_to_isbn10("9780000000007") == "0000000000"


def test_isbn13_to_isbn10_x_check_digit() -> None:
    """check_value 10 should map to 'X'."""
    assert isbn13_to_isbn10("9781234567897") == "123456789X"


def test_isbn13_to_isbn10_non_978_returns_none() -> None:
    """Non-978 ISBN-13 should return None."""
    assert isbn13_to_isbn10("9791234567896") is None


def test_isbn13_to_isbn10_invalid_format_returns_none() -> None:
    """Invalid input strings should return None."""
    assert isbn13_to_isbn10("123") is None
    assert isbn13_to_isbn10("") is None
