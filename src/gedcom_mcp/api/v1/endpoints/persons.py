"""
Person-related endpoints.

Provides operations for querying person information from GEDCOM files.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from ....schemas import PersonDetailResponse, PersonsResponse
from ..dependencies import (
    FilePathQuery,
    GedcomServiceDep,
    PersonIdQuery,
    SignatureVerified,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Persons"])


@router.get(
    "/persons",
    response_model=PersonsResponse,
    summary="List all persons",
    description="Get a list of all person IDs in the GEDCOM file",
    responses={
        401: {"description": "Invalid signature"},
        404: {"description": "GEDCOM file not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_all_persons(
    file: FilePathQuery,
    service: GedcomServiceDep,
    _signature: SignatureVerified,
) -> PersonsResponse:
    """
    Get a list of all person IDs in the GEDCOM file.

    The request URL must be signed with HMAC-SHA256.

    Args:
        file: Path to GEDCOM file (local or S3)
        service: GEDCOM service instance
        _signature: Validated signature (dependency)

    Returns:
        List of all person IDs with total count
    """
    try:
        person_ids = service.get_all_person_ids(file)
        return PersonsResponse(
            total=len(person_ids),
            persons=person_ids
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persons list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting persons: {str(e)}"
        )


@router.get(
    "/person",
    response_model=PersonDetailResponse,
    summary="Get person details",
    description="Get detailed information about a specific person",
    responses={
        401: {"description": "Invalid signature"},
        404: {"description": "Person or GEDCOM file not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_person_details(
    id: PersonIdQuery,
    file: FilePathQuery,
    service: GedcomServiceDep,
    _signature: SignatureVerified,
) -> PersonDetailResponse:
    """
    Get detailed information about a specific person.

    Note: This endpoint does not require signature verification.

    Args:
        id: Person ID (e.g., @I1@)
        file: Path to GEDCOM file (local or S3)
        service: GEDCOM service instance

    Returns:
        Detailed information about the person
    """
    try:
        person = service.get_person_details(id, file)

        return PersonDetailResponse(
            id=person.id,
            name=person.name,
            givn=person.givn,
            surn=person.surn,
            birth_date=person.birth_date,
            birth_place=person.birth_place,
            death_date=person.death_date,
            death_place=person.death_place,
            gender=person.gender,
            occupation=person.occupation,
            parents=person.parents,
            spouses=person.spouses,
            children=person.children
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting person {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting person details: {str(e)}"
        )
