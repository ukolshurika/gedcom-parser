#!/usr/bin/env python3

"""
FastAPI server for GEDCOM file operations with S3 support and file caching.

This module provides backward compatibility by re-exporting from the new
modular structure. For new development, import from the specific modules:

- gedcom_mcp.app - Application instance and factory
- gedcom_mcp.core.config - Configuration settings
- gedcom_mcp.services - Business logic services
- gedcom_mcp.schemas - Pydantic models
- gedcom_mcp.api.v1 - API endpoints
"""

# Re-export the app instance for backward compatibility
from .app import app, main

# Re-export commonly used components
from .core.config import settings
from .services import FileCache, GedcomService, get_file_cache, get_gedcom_service
from .schemas import (
    PersonSummary,
    TimelineResponse,
    PersonsResponse,
    PersonDetailResponse,
)


# Backward compatibility: config alias and properties
class _ConfigCompat:
    """Backward compatible config wrapper for tests."""

    @property
    def CACHE_DIR(self) -> str:
        return settings.cache_dir

    @property
    def CACHE_TTL_HOURS(self) -> int:
        return settings.cache_ttl_hours

    @property
    def S3_BUCKET(self) -> str:
        return settings.s3_bucket


config = _ConfigCompat()

# Backward compatibility: access to contexts via singleton service
_gedcom_service_instance = None


def _get_service_instance() -> GedcomService:
    global _gedcom_service_instance
    if _gedcom_service_instance is None:
        _gedcom_service_instance = get_gedcom_service()
    return _gedcom_service_instance


class _GedcomContextsProxy:
    """Proxy to access GedcomService's internal contexts dict."""

    def clear(self):
        service = _get_service_instance()
        service._contexts.clear()

    def __contains__(self, key):
        service = _get_service_instance()
        return key in service._contexts

    def __getitem__(self, key):
        service = _get_service_instance()
        return service._contexts[key]

    def __setitem__(self, key, value):
        service = _get_service_instance()
        service._contexts[key] = value


_gedcom_contexts = _GedcomContextsProxy()

__all__ = [
    "app",
    "main",
    "settings",
    "config",
    "FileCache",
    "GedcomService",
    "get_file_cache",
    "get_gedcom_service",
    "PersonSummary",
    "TimelineResponse",
    "PersonsResponse",
    "PersonDetailResponse",
    "_gedcom_contexts",
]

if __name__ == "__main__":
    main()
