#!/usr/bin/env python3

"""
Signature verification utilities for webhook security.

Provides HMAC-SHA256 based signature generation and verification
for securing API requests with X-Signature header.
"""

import hashlib
import hmac
import json
import os
from typing import Any, Dict


def get_secret_key() -> str:
    """
    Get the secret key for signature generation.

    Returns:
        Secret key from environment variable

    Raises:
        ValueError: If SECRET_KEY environment variable is not set
    """
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError("SECRET_KEY environment variable is not set")
    return secret_key


def generate_signature(data: Dict[str, Any] | str) -> str:
    secret_key = get_secret_key()

    # If data is a string (e.g., URL), use it directly
    # Otherwise, serialize dict to JSON
    if isinstance(data, str):
        message = data
    else:
        message = json.dumps(data, sort_keys=False, separators=(',', ':'))

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_signature(data: Dict[str, Any] | str, provided_signature: str) -> bool:
    try:
        expected_signature = generate_signature(data)
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, provided_signature)
    except Exception:
        return False
