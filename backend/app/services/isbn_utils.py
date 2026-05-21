"""ISBN-13/ISBN-10 conversion and normalization utilities."""

import re
from typing import Optional

_ISBN10_RE: re.Pattern = re.compile(r"^\d{9}[\dX]$")
_ISBN13_RE: re.Pattern = re.compile(r"^\d{13}$")


def normalize_isbn(isbn: str) -> str:
    """Normalize an ISBN to its ISBN-13 representation.

    Strips whitespace and hyphens, then converts ISBN-10 to ISBN-13
    if needed. Raises ValueError for invalid input.

    Args:
        isbn: Raw ISBN string (ISBN-10 or ISBN-13).

    Returns:
        Normalized ISBN-13 string.

    Raises:
        ValueError: If the input is not a valid ISBN.
    """
    compact = re.sub(r"[^0-9Xx]", "", isbn).upper()
    if _ISBN13_RE.fullmatch(compact):
        return compact
    if not _ISBN10_RE.fullmatch(compact):
        raise ValueError("Invalid ISBN format")
    core = compact[:-1]
    isbn13_core = f"978{core}"
    checksum_sum = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(isbn13_core))
    checksum_digit = (10 - (checksum_sum % 10)) % 10
    return f"{isbn13_core}{checksum_digit}"


def isbn13_to_isbn10(isbn13: str) -> str | None:
    """Convert an ISBN-13 starting with '978' to its ISBN-10 equivalent.

    Args:
        isbn13: A 13-digit ISBN-13 string.

    Returns:
        The 10-character ISBN-10 string (last char may be 'X'), or None
        if conversion is not possible (non-978 prefix or invalid format).
    """
    if not _ISBN13_RE.fullmatch(isbn13):
        return None
    if not isbn13.startswith("978"):
        return None
    core9 = isbn13[3:-1]
    weighted_sum = sum(int(digit) * (10 - idx) for idx, digit in enumerate(core9))
    remainder = weighted_sum % 11
    check_value = 11 - remainder
    if check_value == 10:
        check_digit = "X"
    elif check_value == 11:
        check_digit = "0"
    else:
        check_digit = str(check_value)
    return f"{core9}{check_digit}"
