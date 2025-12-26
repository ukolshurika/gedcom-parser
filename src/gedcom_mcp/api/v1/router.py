"""
Main router for API v1.

Aggregates all endpoint routers into a single router.
"""

from __future__ import annotations

from fastapi import APIRouter

from .endpoints import cache, health, persons, timeline

router = APIRouter()

# Include all endpoint routers
router.include_router(health.router)
router.include_router(timeline.router)
router.include_router(persons.router)
router.include_router(cache.router)
