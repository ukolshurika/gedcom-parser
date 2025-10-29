# TODO: File Management and Cache Cleanup

This document outlines the planned improvements for file management and cache cleanup in the GEDCOM FastAPI server.

## Overview

The current implementation provides basic file caching with S3 support, but several improvements are needed for production use.

## Priority Tasks

### 1. Accurate File Update Detection

**Status**: Not Implemented
**Priority**: High

#### Current State
- Files are cached based on TTL (Time To Live)
- No detection of file updates on S3 or local filesystem
- Cached files may become stale if source file is updated

#### Required Changes
- [ ] Implement ETag-based versioning for S3 files
  - Store S3 ETag alongside cached file
  - Compare ETag before using cached version
  - Download new version if ETag differs
- [ ] Implement mtime checking for local files
  - Store original file modification time
  - Compare mtime before using cached version
  - Reload file if mtime changed
- [ ] Add cache invalidation API endpoint
  - `POST /cache/invalidate?file_path=...` to force reload
  - Clear specific cached file and GEDCOM context
- [ ] Add version metadata to cached files
  - Store metadata JSON alongside cached files
  - Include: original path, timestamp, ETag/mtime, file size

#### Implementation Notes
```python
# Example metadata structure
{
    "original_path": "s3://bucket/file.ged",
    "cached_at": "2025-10-27T10:00:00Z",
    "etag": "abc123...",
    "file_size": 1024000,
    "last_accessed": "2025-10-27T12:00:00Z"
}
```

### 2. Intelligent Cache Cleanup

**Status**: Partially Implemented
**Priority**: High

#### Current State
- `POST /cache/clean` endpoint exists
- Only removes files older than TTL
- No size-based cleanup
- No LRU (Least Recently Used) eviction

#### Required Changes
- [ ] Implement size-based cache eviction
  - Monitor total cache directory size
  - Trigger cleanup when size exceeds `MAX_CACHE_SIZE_MB`
  - Use LRU algorithm to determine which files to remove
- [ ] Track file access times
  - Update "last_accessed" in metadata on each use
  - Use for LRU calculation
- [ ] Add cache statistics endpoint
  - `GET /cache/stats` to show:
    - Total cache size
    - Number of cached files
    - Cache hit/miss ratio
    - Oldest/newest cached files
- [ ] Implement automatic background cleanup
  - Run cleanup task periodically (e.g., every hour)
  - Use FastAPI background tasks or separate scheduler
- [ ] Add cache warmup functionality
  - `POST /cache/warmup` to preload frequently used files
  - Support batch preloading from list of files

#### Implementation Notes
```python
# LRU cache implementation pseudocode
def cleanup_by_size():
    current_size = get_cache_size()
    if current_size > MAX_CACHE_SIZE_MB:
        files = list_cached_files_with_metadata()
        files.sort(key=lambda f: f.last_accessed)  # LRU order

        while current_size > MAX_CACHE_SIZE_MB * 0.8:  # Clean to 80%
            oldest_file = files.pop(0)
            remove_cached_file(oldest_file)
            current_size -= oldest_file.size
```

### 3. GEDCOM Context Management

**Status**: Basic Implementation
**Priority**: Medium

#### Current State
- GEDCOM contexts stored in global dictionary
- Never cleared except on server restart
- Memory usage grows unbounded

#### Required Changes
- [ ] Implement context cache with size limits
  - Limit number of loaded GEDCOM contexts in memory
  - Use LRU eviction when limit reached
- [ ] Add context refresh mechanism
  - Reload context when underlying file changes
  - Clear context when cached file is invalidated
- [ ] Add memory usage monitoring
  - Track size of each GEDCOM context
  - Include in cache statistics
- [ ] Implement weak references for contexts
  - Allow garbage collection of unused contexts
  - Reload only when needed

### 4. S3 Integration Improvements

**Status**: Basic Implementation
**Priority**: Medium

#### Current State
- Basic S3 download functionality
- No upload support
- No streaming for large files
- No multipart download optimization

#### Required Changes
- [ ] Implement streaming downloads for large files
  - Use boto3 streaming API
  - Avoid loading entire file in memory
- [ ] Add multipart download for very large files
  - Download in chunks concurrently
  - Improve performance for large GEDCOM files
- [ ] Add S3 upload support
  - `POST /upload` endpoint to upload GEDCOM files to S3
  - Support direct upload and multipart upload
- [ ] Implement S3 presigned URLs
  - Generate temporary URLs for direct S3 access
  - Reduce server bandwidth usage
- [ ] Add S3 bucket listing
  - `GET /files` to list available GEDCOM files in S3
  - Support pagination and filtering

### 5. Error Handling and Resilience

**Status**: Basic Implementation
**Priority**: Medium

#### Current State
- Basic error handling
- No retry logic for S3 operations
- No circuit breaker for repeated failures

#### Required Changes
- [ ] Implement retry logic with exponential backoff
  - Retry failed S3 downloads
  - Configurable max retries
- [ ] Add circuit breaker pattern
  - Prevent repeated attempts to download failing files
  - Temporarily skip S3 for persistent failures
- [ ] Improve error messages
  - Distinguish between different error types
  - Provide actionable error messages
- [ ] Add request timeout configuration
  - Prevent long-running requests
  - Configurable per-endpoint timeouts
- [ ] Implement health checks for S3 connectivity
  - Test S3 access on startup
  - Include in `/health` endpoint

### 6. Monitoring and Logging

**Status**: Basic Logging
**Priority**: Low

#### Current State
- Basic logging with Python logging module
- No metrics collection
- No structured logging

#### Required Changes
- [ ] Implement structured logging
  - Use JSON format for logs
  - Include request IDs, user IDs, etc.
- [ ] Add Prometheus metrics
  - Request counts and durations
  - Cache hit/miss ratios
  - File download sizes and times
- [ ] Add OpenTelemetry tracing
  - Trace requests through the system
  - Monitor S3 operation latency
- [ ] Implement log aggregation
  - Ship logs to centralized logging service
  - Support ELK stack, CloudWatch, etc.

### 7. Security Enhancements

**Status**: Minimal
**Priority**: High (for production)

#### Current State
- No authentication
- No authorization
- No input validation beyond FastAPI schema
- No rate limiting

#### Required Changes
- [ ] Implement authentication
  - Support API keys
  - Support JWT tokens
  - Support OAuth2
- [ ] Add authorization
  - Per-user or per-role file access control
  - Restrict S3 bucket access
- [ ] Implement rate limiting
  - Limit requests per user/IP
  - Prevent abuse and DoS
- [ ] Add input validation
  - Validate file paths to prevent path traversal
  - Validate S3 URLs
  - Sanitize person IDs
- [ ] Implement audit logging
  - Log all file access
  - Log all cache operations
  - Include user information

### 8. Configuration Management

**Status**: Environment Variables
**Priority**: Low

#### Current State
- Configuration via environment variables
- No configuration file support
- No runtime configuration updates

#### Required Changes
- [ ] Add configuration file support
  - YAML or JSON configuration files
  - Override environment variables
- [ ] Implement configuration validation
  - Validate on startup
  - Fail fast on invalid configuration
- [ ] Add runtime configuration updates
  - API endpoint to update configuration
  - Reload without server restart
- [ ] Add configuration profiles
  - Development, staging, production profiles
  - Easy switching between profiles

## Testing Requirements

### Unit Tests
- [x] Basic endpoint tests
- [ ] Cache eviction logic tests
- [ ] ETag/mtime comparison tests
- [ ] LRU algorithm tests
- [ ] S3 retry logic tests

### Integration Tests
- [ ] Full workflow tests with real S3
- [ ] Large file handling tests
- [ ] Concurrent request tests
- [ ] Cache invalidation tests

### Performance Tests
- [ ] Load testing with multiple concurrent users
- [ ] Memory usage profiling
- [ ] Cache performance benchmarks
- [ ] S3 download speed tests

## Deployment Considerations

### Docker Support
- [ ] Create Dockerfile
- [ ] Add docker-compose.yml
- [ ] Include health checks in container

### Kubernetes
- [ ] Create Kubernetes manifests
- [ ] Add readiness and liveness probes
- [ ] Configure resource limits

### Environment Variables Documentation
- [ ] Document all environment variables
- [ ] Provide example configurations
- [ ] Create deployment guide

## Documentation Needs

- [ ] API usage guide with examples
- [ ] Cache management best practices
- [ ] S3 configuration guide
- [ ] Performance tuning guide
- [ ] Troubleshooting guide

## Maintenance Schedule

### Daily
- Automatic cache cleanup (background task)
- Log rotation

### Weekly
- Review cache statistics
- Check for stale contexts

### Monthly
- Security audit
- Performance review
- Dependency updates

## Migration Path

For existing deployments:

1. **Phase 1**: Add ETag/mtime tracking (backward compatible)
2. **Phase 2**: Implement size-based cleanup
3. **Phase 3**: Add context management improvements
4. **Phase 4**: Implement security features
5. **Phase 5**: Add monitoring and observability

## Notes

- All changes should maintain backward compatibility where possible
- Configuration changes should have sensible defaults
- Performance improvements should be measured and documented
- Security features are critical before production deployment

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html)
- [Caching Strategies](https://aws.amazon.com/caching/best-practices/)
