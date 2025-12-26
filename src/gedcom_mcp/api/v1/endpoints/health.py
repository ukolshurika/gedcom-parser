"""
Health check endpoint.

Provides system health status for monitoring and load balancers.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from ....core.config import settings
from ....schemas import HealthResponse, RootResponse

router = APIRouter(tags=["System"])


@router.get(
    "/",
    response_model=RootResponse,
    summary="Root endpoint",
    description="Returns API information and available endpoints"
)
async def root() -> RootResponse:
    """Root endpoint with API information."""
    return RootResponse(
        service="GEDCOM Parser API",
        version="1.0.0",
        endpoints=[
            "/timeline",
            "/persons",
            "/person",
            "/cache/clean",
            "/health"
        ]
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns current system health status"
)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        cache_dir=str(settings.cache_dir),
        s3_configured=settings.s3_configured
    )
