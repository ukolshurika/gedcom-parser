# Events API Documentation

## Overview

The `/events` endpoint processes GEDCOM files stored in S3, extracts person and event data, and sends the results to a webhook URL with signature verification.

## Endpoint

### POST /events

Receives an S3 file path and user ID, validates the request signature, verifies the file exists in S3, and triggers background processing.

**URL**: `/events`

**Method**: `POST`

**Content-Type**: `application/json`

**Headers**:
- `X-Signature` (required): HMAC-SHA256 signature of the request body
- `Content-Type`: `application/json`

**Request Body**:
```json
{
  "s3_file_path": "s3://bucket/path/to/file.ged",
  "user_id": "user123"
}
```

**Request Parameters**:
- `s3_file_path` (string, required): S3 path to the GEDCOM file. Can be in format `s3://bucket/key` or just `key`
- `user_id` (string, required): User ID associated with this file

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "File processing started",
  "task_id": "task-uuid-123"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid signature
```json
{
  "detail": "Invalid signature"
}
```

- `404 Not Found`: File not found in S3
```json
{
  "detail": "File not found in S3: s3://bucket/file.ged"
}
```

- `500 Internal Server Error`: Processing error
```json
{
  "detail": "Error processing request: <error message>"
}
```

## Signature Generation

The signature must be generated using HMAC-SHA256 with the `SECRET_KEY` environment variable.

### Python Example:

```python
import hmac
import hashlib
import json

def generate_signature(data: dict, secret_key: str) -> str:
    # Serialize data to JSON with sorted keys
    json_data = json.dumps(data, sort_keys=True, separators=(',', ':'))

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        json_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature

# Example usage
request_data = {
    "s3_file_path": "s3://my-bucket/genealogy/family.ged",
    "user_id": "user123"
}

secret_key = "your-secret-key"
signature = generate_signature(request_data, secret_key)

# Send request
headers = {
    "X-Signature": signature,
    "Content-Type": "application/json"
}
```

### cURL Example:

```bash
# Generate signature (using Python or your preferred method)
SIGNATURE=$(python3 -c "
import hmac, hashlib, json
data = {'s3_file_path': 's3://my-bucket/file.ged', 'user_id': 'user123'}
json_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
print(hmac.new(b'your-secret-key', json_data.encode(), hashlib.sha256).hexdigest())
")

# Make request
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d '{
    "s3_file_path": "s3://my-bucket/file.ged",
    "user_id": "user123"
  }'
```

## Background Processing

Once the request is validated, the following steps occur in a background Celery task:

1. **Download File**: File is downloaded from S3 to a temporary location
2. **Parse GEDCOM**: All persons and events are extracted from the GEDCOM file
3. **Add User ID**: The `user_id` is added to the resulting JSON
4. **Generate Signature**: A new signature is generated for the complete data
5. **Send Webhook**: POST request is sent to `WEBHOOK_URL` with the data and signature
6. **Retry Logic**: If the webhook returns non-200/201 status, the task is retried up to 5 times with exponential backoff
7. **Cleanup**: Temporary file is deleted

## Webhook Format

The background task sends a POST request to the `WEBHOOK_URL` configured in the environment:

**Webhook Request**:
- **URL**: Value of `WEBHOOK_URL` environment variable
- **Method**: POST
- **Headers**:
  - `X-Signature`: HMAC-SHA256 signature of the request body
  - `Content-Type`: application/json

**Webhook Body**:
```json
{
  "user_id": "user123",
  "persons": [
    {
      "id": "@I1@",
      "name": "John Doe",
      "birth_date": "1 JAN 1900",
      "birth_place": "New York, NY",
      "death_date": "1 JAN 1990",
      "death_place": "Los Angeles, CA",
      "gender": "M"
    }
  ],
  "events": [
    {
      "person_id": "@I1@",
      "type": "BIRT",
      "date": "1 JAN 1900",
      "place": "New York, NY",
      "description": null
    },
    {
      "person_id": "@I1@",
      "type": "DEAT",
      "date": "1 JAN 1990",
      "place": "Los Angeles, CA",
      "description": null
    }
  ]
}
```

## Configuration

The following environment variables must be set:

### Required:
- `SECRET_KEY`: Secret key for HMAC signature generation/verification
- `WEBHOOK_URL`: URL to send the processed data to (e.g., `https://main-service.com/events/hook`)
- `GEDCOM_S3_BUCKET`: S3 bucket name where GEDCOM files are stored

### Optional:
- `GEDCOM_S3_REGION`: AWS region (default: `us-east-1`)
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `AWS_ACCESS_KEY_ID`: AWS access key (or use IAM roles)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (or use IAM roles)

## Running with Docker Compose

1. Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

2. Start all services:
```bash
docker-compose up -d
```

This will start:
- **redis**: Redis server for Celery message broker
- **api**: FastAPI server on port 8000
- **celery-worker**: Celery worker for processing background tasks
- **celery-beat**: Celery beat scheduler (for periodic tasks if needed)

3. Check logs:
```bash
# API logs
docker-compose logs -f api

# Celery worker logs
docker-compose logs -f celery-worker
```

4. Stop services:
```bash
docker-compose down
```

## Testing

### 1. Test Signature Verification

```python
import requests
import hmac
import hashlib
import json

def generate_signature(data: dict, secret_key: str) -> str:
    json_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hmac.new(
        secret_key.encode('utf-8'),
        json_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# Prepare request
data = {
    "s3_file_path": "s3://my-bucket/test.ged",
    "user_id": "test-user"
}

secret_key = "your-secret-key"
signature = generate_signature(data, secret_key)

# Send request
response = requests.post(
    "http://localhost:8000/events",
    json=data,
    headers={"X-Signature": signature}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### 2. Monitor Task Progress

You can monitor Celery tasks using Flower (optional):

```bash
# Install flower
pip install flower

# Start flower
celery -A src.gedcom_mcp.celery_app flower
```

Then visit http://localhost:5555 to see task status and history.

## Security Considerations

1. **Secret Key**: Keep your `SECRET_KEY` secure and never commit it to version control
2. **HTTPS**: Always use HTTPS in production for both the API and webhook endpoints
3. **Signature Verification**: Both endpoints (incoming `/events` and outgoing webhook) verify signatures
4. **AWS Credentials**: Use IAM roles when possible instead of access keys
5. **Rate Limiting**: Consider adding rate limiting to the `/events` endpoint in production

## Error Handling and Retries

The background task includes automatic retry logic:
- **Max Retries**: 5 attempts
- **Retry Delay**: 60 seconds × (retry attempt number) - exponential backoff
- **Retry Conditions**: Any non-200/201 status from the webhook URL

If all retries fail, the task will be marked as failed in Celery and can be inspected using Flower or Celery CLI tools.

## Monitoring

Monitor the health of the system:

```bash
# Health check
curl http://localhost:8000/health

# Check Redis
docker-compose exec redis redis-cli ping

# Check Celery workers
docker-compose exec celery-worker celery -A src.gedcom_mcp.celery_app inspect active
```
