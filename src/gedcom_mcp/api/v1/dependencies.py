"""
Shared dependencies for API v1 endpoints.

Contains FastAPI dependency injection functions used across multiple endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from ...services import GedcomService, get_gedcom_service
from ...core.security import verify_request_signature


# Type aliases for cleaner endpoint signatures
GedcomServiceDep = Annotated[GedcomService, Depends(get_gedcom_service)]
SignatureVerified = Annotated[str, Depends(verify_request_signature)]


# Common query parameters
FilePathQuery = Annotated[str, Query(description="Path to GEDCOM file")]
PersonIdQuery = Annotated[str, Query(description="Person ID (e.g., @I1@)")]
