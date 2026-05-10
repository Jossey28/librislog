"""
Router for serving locally cached cover images.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/covers", tags=["covers"])


@router.get("/{filename}")
async def get_cover(filename: str) -> FileResponse:
    """Serve a locally cached cover image by filename."""
    # Path-traversal guard: reject any filename that tries to escape the directory.
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    covers_path = Path(settings.covers_dir)
    file_path = covers_path / filename

    if not file_path.exists():
        logger.debug("Cover not found: %s", filename)
        raise HTTPException(status_code=404, detail="Cover not found.")

    return FileResponse(file_path)
