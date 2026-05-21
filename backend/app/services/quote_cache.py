"""Thread-safe TTL cache for the dashboard quote."""

import logging
import threading
from typing import Final, Optional

import httpx
from cachetools import TTLCache

from app.config import settings
from app.schemas import DashboardQuote

logger = logging.getLogger(__name__)

_CACHE_KEY: Final[str] = "dashboard_quote"
_cache_lock = threading.Lock()
_quote_cache: TTLCache[str, DashboardQuote] = TTLCache(maxsize=1, ttl=settings.dashboard_quote_cache_ttl)


def configure_quote_cache_ttl(ttl_seconds: int) -> None:
    """Replace the internal quote cache with a new TTL.

    Args:
        ttl_seconds: Time-to-live in seconds for cached quotes.
    """
    global _quote_cache
    with _cache_lock:
        _quote_cache = TTLCache(maxsize=1, ttl=ttl_seconds)


def invalidate_quote_cache() -> None:
    """Clear the cached quote so the next access re-fetches."""
    with _cache_lock:
        _quote_cache.clear()


def get_cached_quote() -> DashboardQuote | None:
    """Return the cached quote, or None if the cache is empty or expired."""
    with _cache_lock:
        return _quote_cache.get(_CACHE_KEY)


def _cache_quote(quote: DashboardQuote) -> None:
    """Store *quote* in the cache under the fixed cache key."""
    with _cache_lock:
        _quote_cache[_CACHE_KEY] = quote


async def get_or_fetch_dashboard_quote() -> DashboardQuote | None:
    """Return the cached quote or fetch a fresh one from the external API.

    On fetch failure the quote is simply skipped (returns None).

    Returns:
        A DashboardQuote or None.
    """
    cached = get_cached_quote()
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(settings.dashboard_quote_url)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("dashboard quote fetch failed: %s", exc)
        return None

    if not isinstance(payload, dict):
        return None

    quote_text = payload.get("quote")
    if not isinstance(quote_text, str) or not quote_text.strip():
        return None

    author = payload.get("author")
    if not isinstance(author, str):
        author = None

    quote = DashboardQuote(quote=quote_text.strip(), author=author)
    _cache_quote(quote)
    return quote
