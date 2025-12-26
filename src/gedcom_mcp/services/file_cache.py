"""
File caching service with S3 support.

Provides functionality to cache files locally and download them from S3
when needed, with TTL-based cache invalidation.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from ..core.config import settings

logger = logging.getLogger(__name__)


class FileCache:
    """
    Handles file caching operations with S3 integration.

    This service manages a local file cache that can automatically
    download files from S3 when they're not available locally.
    Files are cached based on TTL configuration.
    """

    def __init__(self) -> None:
        """Initialize the file cache with configured settings."""
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.s3_client = None

        if settings.s3_configured:
            self._init_s3_client()

    def _init_s3_client(self) -> None:
        """Initialize the S3 client if configured."""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=settings.s3_region,
                endpoint_url=settings.s3_endpoint_url
            )
            logger.info(f"S3 client initialized with endpoint: {settings.s3_endpoint_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize S3 client: {e}")

    def _get_cache_key(self, file_path: str) -> str:
        """
        Generate a cache key from file path.

        Args:
            file_path: Original file path or S3 URL

        Returns:
            MD5 hash of the file path
        """
        return hashlib.md5(file_path.encode()).hexdigest()

    def _get_cached_file_path(self, file_path: str) -> Path:
        """
        Get the local cache path for a file.

        Args:
            file_path: Original file path or S3 URL

        Returns:
            Path to the cached file location
        """
        cache_key = self._get_cache_key(file_path)
        ext = Path(file_path).suffix or '.ged'
        return self.cache_dir / f"{cache_key}{ext}"

    def _is_cache_valid(self, cached_path: Path) -> bool:
        """
        Check if cached file is still valid based on TTL.

        Args:
            cached_path: Path to the cached file

        Returns:
            True if cache is valid, False otherwise
        """
        if not cached_path.exists():
            return False

        file_age = datetime.now() - datetime.fromtimestamp(cached_path.stat().st_mtime)
        return file_age < timedelta(hours=settings.cache_ttl_hours)

    def _download_from_s3(self, s3_path: str, local_path: Path) -> bool:
        """
        Download file from S3 to local cache.

        Args:
            s3_path: S3 URL or key
            local_path: Local path to save the file

        Returns:
            True if download succeeded, False otherwise
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False

        try:
            # Remove s3:// prefix if present
            s3_key = s3_path.replace("s3://", "").replace(f"{settings.s3_bucket}/", "")

            logger.info(f"Downloading from S3: s3://{settings.s3_bucket}/{s3_key}")
            self.s3_client.download_file(settings.s3_bucket, s3_key, str(local_path))
            logger.info(f"Successfully downloaded to {local_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            return False

    def get_file(self, file_path: str) -> Optional[Path]:
        """
        Get file from cache or download it if needed.

        This method checks for:
        1. Local file existence
        2. Valid cache entry
        3. S3 download if applicable

        Args:
            file_path: Path to GEDCOM file (local path or S3 URL)

        Returns:
            Path to local file, or None if file cannot be retrieved
        """
        # Check if it's a local file that exists
        local_file = Path(file_path)
        if local_file.exists() and local_file.is_file():
            logger.info(f"Using local file: {file_path}")
            return local_file

        # Check cache
        cached_path = self._get_cached_file_path(file_path)
        if self._is_cache_valid(cached_path):
            logger.info(f"Using cached file: {cached_path}")
            return cached_path

        # Try to download from S3 if it looks like an S3 path
        if file_path.startswith("s3://") or (settings.s3_configured and not local_file.exists()):
            if self._download_from_s3(file_path, cached_path):
                return cached_path

        logger.error(f"File not found: {file_path}")
        return None

    def clean_old_files(self) -> int:
        """
        Remove old cached files based on TTL configuration.

        Returns:
            Number of files removed
        """
        if not self.cache_dir.exists():
            return 0

        current_time = datetime.now()
        ttl = timedelta(hours=settings.cache_ttl_hours)
        removed_count = 0

        for cached_file in self.cache_dir.glob("*"):
            if cached_file.is_file():
                file_age = current_time - datetime.fromtimestamp(cached_file.stat().st_mtime)
                if file_age > ttl:
                    try:
                        cached_file.unlink()
                        logger.info(f"Removed old cached file: {cached_file}")
                        removed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to remove cached file {cached_file}: {e}")

        return removed_count


@lru_cache
def get_file_cache() -> FileCache:
    """
    Get cached FileCache instance.

    Returns:
        FileCache singleton instance
    """
    return FileCache()
