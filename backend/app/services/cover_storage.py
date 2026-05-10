"""
Local cover image storage service.

Downloads cover images from external URLs, stores them on disk with an atomic
write, and returns the local filename.  Callers fall back to the original URL
when this module returns None.
"""

import hashlib
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_MIN_COVER_BYTES = 5_000

_CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


async def download_cover(
    url: str,
    covers_dir: str | Path,
    client: httpx.AsyncClient,
) -> str | None:
    """Download a cover image and persist it locally.

    Parameters
    ----------
    url:
        External URL of the cover image.
    covers_dir:
        Directory where cover files are stored.
    client:
        An ``httpx.AsyncClient`` to use for the download.

    Returns
    -------
    str | None
        The local filename (e.g. ``"abc123def456.jpg"``) on success, or
        ``None`` if the download failed or the image did not pass validation.
    """
    covers_path = Path(covers_dir)

    digest = hashlib.sha256(url.encode()).hexdigest()[:32]

    # Deduplication: if any file with this digest already exists, skip download.
    existing = list(covers_path.glob(f"{digest}.*"))
    if existing:
        logger.debug("Cover already cached: %s", existing[0].name)
        return existing[0].name

    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        body = resp.content
    except Exception as exc:
        logger.warning("Cover download failed for %s: %s", url, exc)
        return None

    if len(body) < _MIN_COVER_BYTES:
        logger.warning("Cover too small (%d bytes) for %s — skipping", len(body), url)
        return None

    content_type = resp.headers.get("content-type", "").split(";")[0].strip()
    if not content_type.startswith("image/"):
        logger.warning(
            "Cover content-type not an image (%s) for %s — skipping",
            content_type,
            url,
        )
        return None

    ext = _CONTENT_TYPE_TO_EXT.get(content_type, ".jpg")
    filename = f"{digest}{ext}"
    tmp_path = covers_path / f"{filename}.tmp"
    final_path = covers_path / filename

    try:
        covers_path.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(body)
        os.replace(tmp_path, final_path)
    except OSError as exc:
        logger.error("Failed to write cover %s: %s", filename, exc)
        return None

    logger.debug("Cover saved: %s (%d bytes)", filename, len(body))
    return filename
