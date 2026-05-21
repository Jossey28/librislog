from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as an aware datetime object."""
    return datetime.now(timezone.utc)
