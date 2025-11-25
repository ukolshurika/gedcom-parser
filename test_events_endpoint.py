#!/usr/bin/env python3

"""
Test script for the POST /events endpoint.

This script demonstrates how to:
1. Generate a valid HMAC-SHA256 signature
2. Send a request to the /events endpoint
3. Handle the response

Usage:
    python test_events_endpoint.py
"""

import os
import sys
import hmac
import hashlib
import json
import requests
from typing import Dict, Any


def generate_signature(data: Dict[str, Any], secret_key: str) -> str:
    """
    Generate HMAC-SHA256 signature for data.

    Args:
        data: Dictionary to sign
        secret_key: Secret key for HMAC

    Returns:
        Hex-encoded signature string
    """
    # Serialize data to JSON with sorted keys for consistency
    json_data = json.dumps(data, sort_keys=True, separators=(',', ':'))

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        json_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def test_events_endpoint(
    api_url: str,
    s3_file_path: str,
    user_id: str,
    secret_key: str
):
    """
    Test the POST /events endpoint.

    Args:
        api_url: Base URL of the API (e.g., http://localhost:8000)
        s3_file_path: S3 path to GEDCOM file
        user_id: User ID
        secret_key: Secret key for signature generation
    """
    # Prepare request data
    data = {
        "s3_file_path": s3_file_path,
        "user_id": user_id
    }

    # Generate signature
    signature = generate_signature(data, secret_key)
    print(f"Generated signature: {signature}")

    # Prepare headers
    headers = {
        "X-Signature": signature,
        "Content-Type": "application/json"
    }

    # Make request
    endpoint = f"{api_url}/events"
    print(f"\nSending POST request to: {endpoint}")
    print(f"Request body: {json.dumps(data, indent=2)}")

    try:
        response = requests.post(endpoint, json=data, headers=headers, timeout=10)

        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("\n✅ Success! Background task has been queued.")
            task_id = response.json().get("task_id")
            if task_id:
                print(f"Task ID: {task_id}")
                print("\nYou can monitor the task progress in the Celery worker logs:")
                print("  docker-compose logs -f celery-worker")
        elif response.status_code == 401:
            print("\n❌ Authentication failed: Invalid signature")
            print("Please check your SECRET_KEY")
        elif response.status_code == 404:
            print("\n❌ File not found in S3")
            print("Please verify the file exists at the specified path")
        else:
            print(f"\n❌ Request failed with status {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection error: Could not connect to {api_url}")
        print("Make sure the API server is running:")
        print("  docker-compose up -d")
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout: API did not respond in time")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    """Main function."""
    # Get configuration from environment variables or use defaults
    api_url = os.getenv("API_URL", "http://localhost:8000")
    secret_key = os.getenv("SECRET_KEY", "")

    # Example test data
    s3_file_path = os.getenv("TEST_S3_FILE", "s3://my-bucket/sample.ged")
    user_id = os.getenv("TEST_USER_ID", "test-user-123")

    print("=" * 60)
    print("POST /events Endpoint Test")
    print("=" * 60)

    # Validate inputs
    if not secret_key:
        print("\n❌ ERROR: SECRET_KEY environment variable is not set")
        print("\nUsage:")
        print("  export SECRET_KEY='your-secret-key'")
        print("  export TEST_S3_FILE='s3://bucket/file.ged'  # optional")
        print("  export TEST_USER_ID='user123'  # optional")
        print("  python test_events_endpoint.py")
        sys.exit(1)

    print(f"\nConfiguration:")
    print(f"  API URL: {api_url}")
    print(f"  S3 File: {s3_file_path}")
    print(f"  User ID: {user_id}")
    print(f"  Secret Key: {'*' * len(secret_key)}")

    # Run test
    test_events_endpoint(api_url, s3_file_path, user_id, secret_key)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
