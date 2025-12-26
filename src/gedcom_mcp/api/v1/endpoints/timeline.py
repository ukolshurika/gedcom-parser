"""
Timeline endpoint.

Provides chronological timeline generation for persons.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from ....schemas import TimelineResponse
from ..dependencies import (
    FilePathQuery,
    GedcomServiceDep,
    PersonIdQuery,
    SignatureVerified,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Timeline"])


@router.get(
    "/timeline",
    response_model=TimelineResponse,
    summary="Get person timeline",
    description="Generate a chronological timeline of events for a person",
    responses={
        401: {"description": "Invalid signature"},
        404: {"description": "Person or GEDCOM file not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_person_timeline(
    gedcom_id: PersonIdQuery,
    file: FilePathQuery,
    service: GedcomServiceDep,
    _signature: SignatureVerified,
) -> TimelineResponse:
    """
    Generate a chronological timeline of events for a person.

    The request URL must be signed with HMAC-SHA256.

    Args:
        gedcom_id: Person ID (e.g., @I1@)
        file: Path to GEDCOM file (local or S3)
        service: GEDCOM service instance
        _signature: Validated signature (dependency)

    Returns:
        Timeline of events for the person
    """
    try:
        timeline = service.get_person_timeline(gedcom_id, file)

        return TimelineResponse(
            person_id=gedcom_id,
            timeline=timeline
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline for {gedcom_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting timeline: {str(e)}"
        )
