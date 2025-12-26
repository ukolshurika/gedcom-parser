"""
Pydantic response models for API endpoints.

Defines the structure of all API responses with proper validation
and documentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PersonSummary(BaseModel):
    """Summary information about a person."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Person ID in GEDCOM format (e.g., @I1@)")
    name: str = Field(..., description="Full name of the person")
    birth_date: Optional[str] = Field(None, description="Birth date")
    birth_place: Optional[str] = Field(None, description="Birth place")
    death_date: Optional[str] = Field(None, description="Death date")
    death_place: Optional[str] = Field(None, description="Death place")
    gender: Optional[str] = Field(None, description="Gender (M/F)")


class TimelineResponse(BaseModel):
    """Response model for timeline endpoint."""

    person_id: str = Field(..., description="Person ID")
    timeline: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of timeline events"
    )


class PersonsResponse(BaseModel):
    """Response model for persons list endpoint."""

    total: int = Field(..., description="Total number of persons")
    persons: List[str] = Field(
        default_factory=list,
        description="List of person IDs"
    )


class PersonDetailResponse(BaseModel):
    """Response model for person detail endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Person ID in GEDCOM format")
    name: str = Field(..., description="Full name of the person")
    givn: Optional[str] = Field(None, description="Given name (first name)")
    surn: Optional[str] = Field(None, description="Surname (family name)")
    birth_date: Optional[str] = Field(None, description="Birth date")
    birth_place: Optional[str] = Field(None, description="Birth place")
    death_date: Optional[str] = Field(None, description="Death date")
    death_place: Optional[str] = Field(None, description="Death place")
    gender: Optional[str] = Field(None, description="Gender (M/F)")
    occupation: Optional[str] = Field(None, description="Occupation")
    parents: List[str] = Field(
        default_factory=list,
        description="List of parent IDs"
    )
    spouses: List[str] = Field(
        default_factory=list,
        description="List of spouse IDs"
    )
    children: List[str] = Field(
        default_factory=list,
        description="List of children IDs"
    )


class CacheCleanResponse(BaseModel):
    """Response model for cache clean operation."""

    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    cache_dir: str = Field(..., description="Cache directory path")
    s3_configured: bool = Field(..., description="Whether S3 is configured")


class RootResponse(BaseModel):
    """Response model for root endpoint."""

    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    endpoints: List[str] = Field(..., description="Available endpoints")
