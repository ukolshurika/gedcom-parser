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


def generate_signature(data: Dict[str, Any]) -> str:
    """
    Generate HMAC-SHA256 signature for data.

    Args:
        data: Dictionary to sign (will be JSON serialized)

    Returns:
        Hex-encoded signature string
    """
    secret_key = get_secret_key()

    # Serialize data to JSON with sorted keys for consistency
    json_data = json.dumps(data, sort_keys=True, separators=(',', ':'))

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        json_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_signature(data: Dict[str, Any], provided_signature: str) -> bool:
    """
    Verify that the provided signature matches the data.

    Args:
        data: Dictionary to verify
        provided_signature: Signature from X-Signature header

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        expected_signature = generate_signature(data)
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, provided_signature)
    except Exception:
        return False
