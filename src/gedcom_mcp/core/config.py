"""
Application configuration module.

Centralizes all configuration settings loaded from environment variables
with sensible defaults.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    For example, GEDCOM_CACHE_DIR overrides cache_dir.
    """

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Cache settings
    cache_dir: str = "/tmp/gedcom_cache"
    cache_ttl_hours: int = 24
    max_cache_size_mb: int = 1000

    # S3 settings
    s3_bucket: str = ""
    s3_region: str = "ru-central1"
    s3_endpoint_url: str = "https://storage.yandexcloud.net"

    # Security
    secret_key: Optional[str] = None

    class Config:
        env_prefix = "GEDCOM_"
        env_file = ".env"
        extra = "ignore"

    @property
    def s3_configured(self) -> bool:
        """Check if S3 is properly configured."""
        return bool(self.s3_bucket)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance (cached for performance)
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()
