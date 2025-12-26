"""
Security utilities for API request authentication.

Provides signature verification for securing API endpoints
using HMAC-SHA256 signatures.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from ..signature_utils import verify_signature

logger = logging.getLogger(__name__)


async def verify_request_signature(
    request: Request,
    x_signature: Annotated[str, Header(description="HMAC-SHA256 signature of request URL")]
) -> str:
    """
    Verify the request signature from X-Signature header.

    This dependency validates that the request URL is properly signed
    with HMAC-SHA256 using the application's secret key.

    Args:
        request: FastAPI Request object
        x_signature: Signature from X-Signature header

    Returns:
        The validated signature string

    Raises:
        HTTPException: If signature is invalid (401 Unauthorized)
    """
    url_path = request.url.path
    if request.url.query:
        url_path += f"?{request.url.query}"

    if not verify_signature(url_path, x_signature):
        logger.warning(f"Invalid signature for path: {url_path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    return x_signature
