"""
Cache management endpoints.

Provides operations for managing the file cache.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from ....schemas import CacheCleanResponse
from ....services import get_file_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["Cache"])


@router.post(
    "/clean",
    response_model=CacheCleanResponse,
    summary="Clean old cached files",
    description="Remove cached GEDCOM files that have exceeded their TTL"
)
async def clean_cache() -> CacheCleanResponse:
    """
    Clean old cached GEDCOM files based on TTL configuration.

    Returns:
        Status message with cleanup result
    """
    try:
        file_cache = get_file_cache()
        removed_count = file_cache.clean_old_files()
        return CacheCleanResponse(
            status="success",
            message=f"Cache cleaned successfully. Removed {removed_count} files."
        )
    except Exception as e:
        logger.error(f"Error cleaning cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cleaning cache: {str(e)}"
        )
