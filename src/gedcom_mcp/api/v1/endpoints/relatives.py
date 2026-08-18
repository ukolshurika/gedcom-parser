"""
Relatives endpoint.

Provides closest relatives for a person: parents, children, and siblings.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from ....schemas import PersonSummary, RelativesResponse
from ..dependencies import (
    FilePathQuery,
    GedcomServiceDep,
    PersonIdQuery,
    SignatureVerified,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Relatives"])


def _to_summary(person) -> PersonSummary:
    """Convert a PersonDetails object into a PersonSummary."""
    return PersonSummary(
        id=person.id,
        name=person.name,
        birth_date=person.birth_date,
        birth_place=person.birth_place,
        death_date=person.death_date,
        death_place=person.death_place,
        gender=person.gender,
    )


@router.get(
    "/relatives",
    response_model=RelativesResponse,
    summary="Get closest relatives",
    description="Get a person's closest relatives: parents, children, and siblings",
    responses={
        401: {"description": "Invalid signature"},
        404: {"description": "Person or GEDCOM file not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_relatives(
    id: PersonIdQuery,
    file: FilePathQuery,
    service: GedcomServiceDep,
    _signature: SignatureVerified,
) -> RelativesResponse:
    """
    Get a person's closest relatives from the family tree.

    The request URL must be signed with HMAC-SHA256.

    Args:
        id: Person ID (e.g., @I1@)
        file: Path to GEDCOM file (local or S3)
        service: GEDCOM service instance
        _signature: Validated signature (dependency)

    Returns:
        Closest relatives grouped into parents, children, and siblings
    """
    try:
        relatives = service.get_person_relatives(id, file)

        return RelativesResponse(
            person_id=id,
            parents=[
                _to_summary(service.get_person_details(parent_id, file))
                for parent_id in relatives.parents
            ],
            children=[
                _to_summary(service.get_person_details(child_id, file))
                for child_id in relatives.children
            ],
            siblings=[
                _to_summary(service.get_person_details(sibling_id, file))
                for sibling_id in relatives.siblings
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relatives for {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting relatives: {str(e)}"
        )
