#!/usr/bin/env python3
"""
Test script for signature verification on /persons and /timeline endpoints.
"""

import os
import sys
import hashlib
import hmac
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location("signature_utils", "src/gedcom_mcp/signature_utils.py")
signature_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signature_utils)
generate_signature = signature_utils.generate_signature

# Example test URLs
def test_signature_generation():
    """Test that signature generation works for URLs"""

    # Set a test secret key
    os.environ['SECRET_KEY'] = 'test_secret_key_12345'

    # Test path for /persons endpoint (without host)
    persons_path = "/persons?file=test.ged"
    persons_signature = generate_signature(persons_path)
    print(f"Path: {persons_path}")
    print(f"Signature: {persons_signature}")
    print()

    # Test path for /timeline endpoint (without host)
    timeline_path = "/timeline?gedcom_id=@I1@&file=test.ged"
    timeline_signature = generate_signature(timeline_path)
    print(f"Path: {timeline_path}")
    print(f"Signature: {timeline_signature}")
    print()

    # Test with dict (like /events endpoint)
    event_data = {"file": "s3://bucket/test.ged", "user_id": 123}
    event_signature = generate_signature(event_data)
    print(f"Event data: {event_data}")
    print(f"Signature: {event_signature}")
    print()

    print("✓ Signature generation test passed!")
    print("\nTo test the endpoints, run:")
    print(f'curl -H "X-Signature: {persons_signature}" "http://localhost:8000/persons?file=test.ged"')
    print(f'curl -H "X-Signature: {timeline_signature}" "http://localhost:8000/timeline?gedcom_id=@I1@&file=test.ged"')

if __name__ == "__main__":
    test_signature_generation()
