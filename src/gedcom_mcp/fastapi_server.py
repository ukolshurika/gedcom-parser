#!/usr/bin/env python3

"""
FastAPI server for GEDCOM file operations with S3 support and file caching.

This server provides endpoints for:
- Getting timeline for a person
- Listing all persons in a GEDCOM file
- Getting details about a specific person
"""

import os
import logging
import tempfile
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import boto3
from botocore.exceptions import ClientError

from .gedcom_context import GedcomContext, get_gedcom_context
from .gedcom_data_access import (
    load_gedcom_file,
    get_person_record,
    _extract_person_details
)
from .gedcom_analysis import _get_timeline_internal
from .get_timeline import get_timeline
from .signature_utils import verify_signature
from .celery_app import process_gedcom_file


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GEDCOM Parser API",
    description="API for parsing and querying GEDCOM genealogy files with S3 support",
    version="1.0.0"
)

# Add middleware to ensure UTF-8 charset in responses
@app.middleware("http")
async def add_utf8_charset(request: Request, call_next):
    response = await call_next(request)
    if "application/json" in response.headers.get("content-type", ""):
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


# ===== Configuration =====
class Config:
    """Application configuration"""
    CACHE_DIR = os.getenv("GEDCOM_CACHE_DIR", "/tmp/gedcom_cache")
    CACHE_TTL_HOURS = int(os.getenv("GEDCOM_CACHE_TTL_HOURS", "24"))
    S3_BUCKET = os.getenv("GEDCOM_S3_BUCKET", "")
    S3_REGION = os.getenv("GEDCOM_S3_REGION", "ru-central1")
    S3_ENDPOINT_URL = os.getenv("GEDCOM_S3_ENDPOINT_URL", "https://storage.yandexcloud.net")
    MAX_CACHE_SIZE_MB = int(os.getenv("GEDCOM_MAX_CACHE_SIZE_MB", "1000"))


config = Config()


# ===== Models =====
class PersonSummary(BaseModel):
    """Summary information about a person"""
    id: str
    name: str
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    death_date: Optional[str] = None
    death_place: Optional[str] = None
    gender: Optional[str] = None


class TimelineResponse(BaseModel):
    """Response model for timeline endpoint"""
    person_id: str
    timeline: str


class PersonsResponse(BaseModel):
    """Response model for persons list endpoint"""
    total: int
    persons: List[str]


class PersonDetailResponse(BaseModel):
    """Response model for person detail endpoint"""
    id: str
    name: str
    givn: Optional[str] = None  # Given name
    surn: Optional[str] = None  # Surname
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    death_date: Optional[str] = None
    death_place: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    parents: List[str] = Field(default_factory=list)
    spouses: List[str] = Field(default_factory=list)
    children: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            str: lambda v: v  # Ensure strings are passed through as-is
        }


class EventRequest(BaseModel):
    """Request model for POST /events endpoint"""
    file: str = Field(..., description="S3 path to GEDCOM file (e.g., s3://bucket/file.ged or just key)")
    user_id: int = Field(..., description="User ID associated with this file")


class EventResponse(BaseModel):
    """Response model for POST /events endpoint"""
    status: str
    message: str
    task_id: Optional[str] = None


# ===== File Caching System =====
class FileCache:
    """Handles file caching operations"""

    def __init__(self):
        self.cache_dir = Path(config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.s3_client = None
        if config.S3_BUCKET:
            try:
                self.s3_client = boto3.client(
                    's3',
                    region_name=config.S3_REGION,
                    endpoint_url=config.S3_ENDPOINT_URL
                )
                logger.info(f"S3 client initialized with endpoint: {config.S3_ENDPOINT_URL}")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")

    def _get_cache_key(self, file_path: str) -> str:
        """Generate a cache key from file path"""
        return hashlib.md5(file_path.encode()).hexdigest()

    def _get_cached_file_path(self, file_path: str) -> Path:
        """Get the local cache path for a file"""
        cache_key = self._get_cache_key(file_path)
        # Keep original extension if present
        ext = Path(file_path).suffix or '.ged'
        return self.cache_dir / f"{cache_key}{ext}"

    def _is_cache_valid(self, cached_path: Path) -> bool:
        """Check if cached file is still valid based on TTL"""
        if not cached_path.exists():
            return False

        file_age = datetime.now() - datetime.fromtimestamp(cached_path.stat().st_mtime)
        return file_age < timedelta(hours=config.CACHE_TTL_HOURS)

    def _download_from_s3(self, s3_path: str, local_path: Path) -> bool:
        """Download file from S3 to local cache"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False

        try:
            # Remove s3:// prefix if present
            s3_key = s3_path.replace("s3://", "").replace(f"{config.S3_BUCKET}/", "")

            logger.info(f"Downloading from S3: s3://{config.S3_BUCKET}/{s3_key}")
            self.s3_client.download_file(config.S3_BUCKET, s3_key, str(local_path))
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

        Args:
            file_path: Can be a local path or S3 URL (s3://bucket/key)

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
        if file_path.startswith("s3://") or (config.S3_BUCKET and not local_file.exists()):
            if self._download_from_s3(file_path, cached_path):
                return cached_path

        logger.error(f"File not found: {file_path}")
        return None

    def clean_old_files(self):
        """Remove old cached files based on TTL"""
        if not self.cache_dir.exists():
            return

        current_time = datetime.now()
        ttl = timedelta(hours=config.CACHE_TTL_HOURS)

        for cached_file in self.cache_dir.glob("*"):
            if cached_file.is_file():
                file_age = current_time - datetime.fromtimestamp(cached_file.stat().st_mtime)
                if file_age > ttl:
                    try:
                        cached_file.unlink()
                        logger.info(f"Removed old cached file: {cached_file}")
                    except Exception as e:
                        logger.error(f"Failed to remove cached file {cached_file}: {e}")


# Initialize file cache
file_cache = FileCache()


# ===== GEDCOM Context Management =====
# Store loaded GEDCOM contexts to avoid reloading
_gedcom_contexts: Dict[str, GedcomContext] = {}


def get_or_load_gedcom(file_path: str) -> GedcomContext:
    """
    Get or load a GEDCOM file context.

    Args:
        file_path: Path to GEDCOM file (local or S3)

    Returns:
        GedcomContext instance

    Raises:
        HTTPException if file cannot be loaded
    """
    # Get the file (from cache or download)
    local_path = file_cache.get_file(file_path)
    if not local_path:
        raise HTTPException(
            status_code=404,
            detail=f"GEDCOM file not found: {file_path}"
        )

    local_path_str = str(local_path)

    # Check if we already have this context loaded
    if local_path_str in _gedcom_contexts:
        return _gedcom_contexts[local_path_str]

    # Load the GEDCOM file
    try:
        gedcom_ctx = GedcomContext()
        gedcom_ctx.file_path = local_path_str
        load_gedcom_file(local_path_str, gedcom_ctx)

        # Cache the context
        _gedcom_contexts[local_path_str] = gedcom_ctx
        logger.info(f"Loaded GEDCOM file: {local_path_str}")

        return gedcom_ctx
    except Exception as e:
        logger.error(f"Failed to load GEDCOM file {local_path_str}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load GEDCOM file: {str(e)}"
        )


# ===== API Endpoints =====

@app.get("/", summary="Root endpoint")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "GEDCOM Parser API",
        "version": "1.0.0",
        "endpoints": [
            "/timeline",
            "/persons",
            "/person",
            "/events",
            "/cache/clean",
            "/health"
        ]
    }


@app.get("/timeline", response_model=TimelineResponse, summary="Get person timeline")
async def get_person_timeline(
    request: Request,
    gedcom_id: str = Query(..., description="Person ID in the GEDCOM file (e.g., @I1@)"),
    file: str = Query(..., description="Path to GEDCOM file (local path or S3 URL)"),
    x_signature: str = Header(..., description="HMAC-SHA256 signature of request URL")
):
    """
    Generate a chronological timeline of events for a person.

    The full request URL must be signed with HMAC-SHA256 using the SECRET_KEY.
    The signature must be provided in the X-Signature header.

    Args:
        request: FastAPI Request object
        gedcom_id: The person ID (e.g., @I1@)
        file: Path to GEDCOM file (can be local or s3://bucket/key)
        x_signature: Signature from X-Signature header

    Returns:
        Timeline of events for the person
    """
    try:
        # Validate signature using only path (without host)
        url_path = request.url.path
        if request.url.query:
            url_path += f"?{request.url.query}"

        if not verify_signature(url_path, x_signature):
            logger.warning(f"Invalid signature for path: {url_path}")
            raise HTTPException(
                status_code=401,
                detail="Invalid signature"
            )

        # Load GEDCOM file
        gedcom_ctx = get_or_load_gedcom(file)

        # Generate timeline
        timeline_result = get_timeline(gedcom_id, gedcom_ctx)

        return TimelineResponse(
            person_id=gedcom_id,
            timeline=timeline_result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline for {gedcom_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting timeline: {str(e)}"
        )


@app.get("/persons", response_model=PersonsResponse, summary="List all persons")
async def get_all_persons(
    request: Request,
    file: str = Query(..., description="Path to GEDCOM file (local path or S3 URL)"),
    x_signature: str = Header(..., description="HMAC-SHA256 signature of request URL")
):
    """
    Get a list of all person IDs in the GEDCOM file.

    The full request URL must be signed with HMAC-SHA256 using the SECRET_KEY.
    The signature must be provided in the X-Signature header.

    Args:
        request: FastAPI Request object
        file: Path to GEDCOM file (can be local or s3://bucket/key)
        x_signature: Signature from X-Signature header

    Returns:
        List of all person IDs
    """
    try:
        # Validate signature using only path (without host)
        url_path = request.url.path
        if request.url.query:
            url_path += f"?{request.url.query}"

        if not verify_signature(url_path, x_signature):
            logger.warning(f"Invalid signature for path: {url_path}")
            raise HTTPException(
                status_code=401,
                detail="Invalid signature"
            )

        # Load GEDCOM file
        gedcom_ctx = get_or_load_gedcom(file)
        logger.warning(f"CONTEXT: {gedcom_ctx}")

        # Get all person IDs
        person_ids = list(gedcom_ctx.individual_lookup.keys())
        logger.info(f"Found {len(person_ids)} persons in GEDCOM file")
        return PersonsResponse(
            total=len(person_ids),
            persons=person_ids
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persons list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting persons: {str(e)}"
        )


@app.get("/person", response_model=PersonDetailResponse, summary="Get person details")
async def get_person_details(
    id: str = Query(..., description="Person ID in the GEDCOM file (e.g., @I1@)"),
    file: str = Query(..., description="Path to GEDCOM file (local path or S3 URL)")
):
    """
    Get detailed information about a specific person.

    Args:
        id: The person ID (e.g., @I1@)
        file: Path to GEDCOM file (can be local or s3://bucket/key)

    Returns:
        Detailed information about the person
    """
    try:
        # Load GEDCOM file
        gedcom_ctx = get_or_load_gedcom(file)

        # Get person details
        person = get_person_record(id, gedcom_ctx)

        if not person:
            raise HTTPException(
                status_code=404,
                detail=f"Person not found: {id}"
            )

        # Convert PersonDetails to response model
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
            status_code=500,
            detail=f"Error getting person details: {str(e)}"
        )


@app.post("/cache/clean", summary="Clean old cached files")
async def clean_cache():
    """
    Clean old cached GEDCOM files based on TTL configuration.

    Returns:
        Status message
    """
    try:
        file_cache.clean_old_files()
        return {"status": "success", "message": "Cache cleaned successfully"}
    except Exception as e:
        logger.error(f"Error cleaning cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning cache: {str(e)}"
        )


@app.post("/events", response_model=EventResponse, summary="Process GEDCOM file from S3")
async def create_event(
    request: EventRequest,
    x_signature: str = Header(..., description="HMAC-SHA256 signature of request body")
):
    """
    Receive S3 file path and user ID, validate signature, and trigger background processing.

    The request body must be signed with HMAC-SHA256 using the SECRET_KEY.
    The signature must be provided in the X-Signature header.

    Args:
        request: Event request with s3_file_path and user_id
        x_signature: Signature from X-Signature header

    Returns:
        Status and task ID for the background job
    """
    try:
        # Validate signature
        request_data = request.model_dump()
        if not verify_signature(request_data, x_signature):
            logger.warning(f"Invalid signature for request: {request_data}")
            raise HTTPException(
                status_code=401,
                detail="Invalid signature"
            )


        # Check if file exists in S3
        s3_file_path = request.file
        s3_key = s3_file_path.replace("s3://", "").replace(f"{config.S3_BUCKET}/", "")

        if not config.S3_BUCKET:
            raise HTTPException(
                status_code=500,
                detail="S3 bucket not configured"
            )

        # Verify file exists in S3
        try:
            s3_client = boto3.client('s3', region_name=config.S3_REGION, endpoint_url='https://storage.yandexcloud.net')
            s3_client.head_object(Bucket=config.S3_BUCKET, Key=s3_key)
            logger.info(f"File found in S3: s3://{config.S3_BUCKET}/{s3_key}")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.error(f"File not found in S3: s3://{config.S3_BUCKET}/{s3_key}")
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found in S3: {s3_file_path}"
                )
            else:
                logger.error(f"S3 error checking file: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error checking S3 file: {str(e)}"
                )

        # Queue background task
        task = process_gedcom_file.delay(s3_file_path, request.user_id)
        logger.info(f"Queued background task {task.id} for {s3_file_path}")

        return EventResponse(
            status="ok",
            message="File processing started",
            task_id=task.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing event request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@app.get("/health", summary="Health check")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_dir": str(config.CACHE_DIR),
        "s3_configured": bool(config.S3_BUCKET)
    }


# ===== Application Entry Point =====

def main():
    """Run the FastAPI server"""
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting GEDCOM API server on {host}:{port}")
    logger.info(f"Cache directory: {config.CACHE_DIR}")
    logger.info(f"S3 bucket: {config.S3_BUCKET or 'Not configured'}")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
