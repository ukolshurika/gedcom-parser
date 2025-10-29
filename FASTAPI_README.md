# GEDCOM FastAPI Server

A REST API server for parsing and querying GEDCOM genealogy files with S3 support and intelligent file caching.

## Features

- **Timeline Generation**: Get chronological timelines of life events for individuals
- **Person Listing**: List all persons in a GEDCOM file
- **Person Details**: Retrieve detailed information about specific individuals
- **S3 Integration**: Automatic download and caching of GEDCOM files from S3
- **File Caching**: Intelligent local caching to improve performance
- **Auto-generated Documentation**: Interactive Swagger UI and OpenAPI specification

## Quick Start

### Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables (optional):

```bash
export GEDCOM_CACHE_DIR="/tmp/gedcom_cache"
export GEDCOM_CACHE_TTL_HOURS="24"
export GEDCOM_S3_BUCKET="your-bucket-name"
export GEDCOM_S3_REGION="us-east-1"
export PORT="8000"
export HOST="0.0.0.0"
```

### Running the Server

#### Method 1: Using Python directly

```bash
python -m gedcom_mcp.fastapi_server
```

#### Method 2: Using uvicorn

```bash
uvicorn gedcom_mcp.fastapi_server:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

### Accessing the Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### GET /timeline

Generate a chronological timeline of events for a person.

**Parameters:**
- `gedcom_id` (required): Person ID in the GEDCOM file (e.g., `@I1@`)
- `gedcom_file_path` (required): Path to GEDCOM file (local path or S3 URL)

**Example:**

```bash
curl "http://localhost:8000/timeline?gedcom_id=@I1@&gedcom_file_path=/path/to/file.ged"
```

**Response:**

```json
{
  "person_id": "@I1@",
  "timeline": "Timeline for John Doe (@I1@):\n1950-01-01: Birth - New York, USA\n..."
}
```

### GET /persons

Get a list of all person IDs in a GEDCOM file.

**Parameters:**
- `gedcom_file_path` (required): Path to GEDCOM file (local path or S3 URL)

**Example:**

```bash
curl "http://localhost:8000/persons?gedcom_file_path=/path/to/file.ged"
```

**Response:**

```json
{
  "total": 150,
  "persons": ["@I1@", "@I2@", "@I3@", ...]
}
```

### GET /person

Get detailed information about a specific person.

**Parameters:**
- `id` (required): Person ID in the GEDCOM file (e.g., `@I1@`)
- `gedcom_file_path` (required): Path to GEDCOM file (local path or S3 URL)

**Example:**

```bash
curl "http://localhost:8000/person?id=@I1@&gedcom_file_path=/path/to/file.ged"
```

**Response:**

```json
{
  "id": "@I1@",
  "name": "John Doe",
  "birth_date": "1 JAN 1950",
  "birth_place": "New York, USA",
  "death_date": "1 JAN 2020",
  "death_place": "Los Angeles, USA",
  "gender": "M",
  "occupation": "Engineer",
  "parents": ["@I2@", "@I3@"],
  "spouses": ["@I4@"],
  "children": ["@I5@", "@I6@"]
}
```

### POST /cache/clean

Clean old cached GEDCOM files based on TTL configuration.

**Example:**

```bash
curl -X POST "http://localhost:8000/cache/clean"
```

**Response:**

```json
{
  "status": "success",
  "message": "Cache cleaned successfully"
}
```

### GET /health

Health check endpoint.

**Example:**

```bash
curl "http://localhost:8000/health"
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-10-27T12:00:00",
  "cache_dir": "/tmp/gedcom_cache",
  "s3_configured": true
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEDCOM_CACHE_DIR` | Directory for caching files | `/tmp/gedcom_cache` |
| `GEDCOM_CACHE_TTL_HOURS` | Cache time-to-live in hours | `24` |
| `GEDCOM_S3_BUCKET` | S3 bucket name for file storage | _(empty)_ |
| `GEDCOM_S3_REGION` | AWS region for S3 | `us-east-1` |
| `GEDCOM_MAX_CACHE_SIZE_MB` | Maximum cache size in MB | `1000` |
| `HOST` | Server host address | `0.0.0.0` |
| `PORT` | Server port | `8000` |

### AWS Credentials

For S3 access, configure AWS credentials using one of these methods:

1. **Environment variables:**
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   ```

2. **AWS credentials file** (`~/.aws/credentials`):
   ```ini
   [default]
   aws_access_key_id = your-access-key
   aws_secret_access_key = your-secret-key
   ```

3. **IAM role** (when running on EC2/ECS)

## File Storage

### Local Files

Use absolute or relative paths:

```bash
curl "http://localhost:8000/persons?gedcom_file_path=/home/user/family.ged"
```

### S3 Files

Use S3 URLs:

```bash
curl "http://localhost:8000/persons?gedcom_file_path=s3://my-bucket/family.ged"
```

The server will automatically:
1. Check if the file is in the local cache
2. If not cached or cache expired, download from S3
3. Cache the file locally for future requests

## Caching System

The server implements a two-level caching system:

### 1. File Cache
- GEDCOM files are cached locally in `GEDCOM_CACHE_DIR`
- Files are cached for `GEDCOM_CACHE_TTL_HOURS` hours
- Local files are used directly (not copied to cache)
- S3 files are downloaded and cached

### 2. GEDCOM Context Cache
- Parsed GEDCOM data structures are kept in memory
- Significantly improves performance for repeated queries
- Automatically cleared when server restarts

### Cache Management

To manually clean old cached files:

```bash
curl -X POST "http://localhost:8000/cache/clean"
```

## Testing

### Run all tests:

```bash
pytest tests/test_fastapi_server.py -v
```

### Run specific test class:

```bash
pytest tests/test_fastapi_server.py::TestTimelineEndpoint -v
```

### Run with coverage:

```bash
pytest tests/test_fastapi_server.py --cov=gedcom_mcp.fastapi_server --cov-report=html
```

## Development

### Running in development mode with auto-reload:

```bash
uvicorn gedcom_mcp.fastapi_server:app --reload --host 0.0.0.0 --port 8000
```

### Generating OpenAPI specification:

The OpenAPI specification is available at `/openapi.json` when the server is running, or you can use the pre-generated `openapi.yaml` file.

## Production Deployment

### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["python", "-m", "gedcom_mcp.fastapi_server"]
```

Build and run:

```bash
docker build -t gedcom-api .
docker run -p 8000:8000 \
  -e GEDCOM_S3_BUCKET=my-bucket \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=yyy \
  gedcom-api
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  gedcom-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEDCOM_CACHE_DIR=/cache
      - GEDCOM_S3_BUCKET=${S3_BUCKET}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    volumes:
      - gedcom-cache:/cache
    restart: unless-stopped

volumes:
  gedcom-cache:
```

Run with:

```bash
docker-compose up -d
```

### Production Recommendations

1. **Use a reverse proxy** (nginx, traefik) for SSL termination
2. **Set appropriate resource limits** in Docker/Kubernetes
3. **Configure logging** to a centralized system
4. **Monitor cache size** and disk usage
5. **Use IAM roles** instead of access keys when running on AWS
6. **Implement rate limiting** for public endpoints
7. **Enable CORS** if needed for web applications
8. **Set up health check** probes in orchestration systems

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### File not found error

**Problem**: `404: GEDCOM file not found`

**Solutions:**
- Verify the file path is correct
- Check file permissions
- For S3 files, verify AWS credentials and bucket permissions
- Check S3 bucket name and region configuration

### S3 download fails

**Problem**: S3 downloads fail or timeout

**Solutions:**
- Verify AWS credentials are configured correctly
- Check S3 bucket policy allows read access
- Verify network connectivity to S3
- Check CloudWatch logs for detailed error messages

### High memory usage

**Problem**: Server uses too much memory

**Solutions:**
- Reduce the number of cached contexts by restarting the server
- Process large GEDCOM files in smaller chunks
- Increase server memory allocation
- Implement context eviction (see TODO_FILE_MANAGEMENT.md)

### Cache directory full

**Problem**: Cache directory fills up disk space

**Solutions:**
- Run cache cleanup: `POST /cache/clean`
- Reduce `GEDCOM_CACHE_TTL_HOURS`
- Reduce `GEDCOM_MAX_CACHE_SIZE_MB`
- Manually clear cache directory
- Implement size-based eviction (see TODO_FILE_MANAGEMENT.md)

## Future Improvements

See `TODO_FILE_MANAGEMENT.md` for a comprehensive list of planned improvements including:

- ETag-based file update detection
- LRU cache eviction
- Better S3 integration (streaming, multipart downloads)
- Authentication and authorization
- Rate limiting
- Monitoring and observability
- And much more!

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Check the troubleshooting section above
- Review `TODO_FILE_MANAGEMENT.md` for known limitations
- Open an issue on the project repository

## API Examples

### Complete workflow example:

```bash
# 1. Check server health
curl http://localhost:8000/health

# 2. Get list of all persons
curl "http://localhost:8000/persons?gedcom_file_path=s3://my-bucket/family.ged" | jq

# 3. Get details for a specific person
curl "http://localhost:8000/person?id=@I1@&gedcom_file_path=s3://my-bucket/family.ged" | jq

# 4. Get timeline for the person
curl "http://localhost:8000/timeline?gedcom_id=@I1@&gedcom_file_path=s3://my-bucket/family.ged" | jq

# 5. Clean cache when done
curl -X POST http://localhost:8000/cache/clean
```

### Python client example:

```python
import requests

API_BASE = "http://localhost:8000"
GEDCOM_FILE = "s3://my-bucket/family.ged"

# Get all persons
response = requests.get(f"{API_BASE}/persons", params={"gedcom_file_path": GEDCOM_FILE})
persons = response.json()
print(f"Found {persons['total']} persons")

# Get details for first person
person_id = persons['persons'][0]
response = requests.get(f"{API_BASE}/person", params={
    "id": person_id,
    "gedcom_file_path": GEDCOM_FILE
})
person = response.json()
print(f"Person: {person['name']}")

# Get timeline
response = requests.get(f"{API_BASE}/timeline", params={
    "gedcom_id": person_id,
    "gedcom_file_path": GEDCOM_FILE
})
timeline = response.json()
print(timeline['timeline'])
```
