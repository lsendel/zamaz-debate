# API Rate Limiting System

## Overview

The Zamaz Debate System implements comprehensive API rate limiting to protect against abuse, ensure fair resource allocation, and maintain system stability. The rate limiting system follows a phased approach as recommended by the AI consensus debate, starting with targeted protection and expanding to comprehensive coverage.

## Architecture

### Core Components

1. **APIRateLimitMiddleware** - FastAPI middleware that intercepts requests and applies rate limiting
2. **RateLimitStore** - In-memory store for rate limiting data and statistics
3. **RateLimitManager** - Manager for rate limiting operations and monitoring
4. **RateLimitConfigManager** - Configuration management and validation

### Rate Limiting Algorithms

- **Token Bucket Algorithm**: Used for smooth rate limiting with burst capacity
- **Per-Client Limiting**: Rate limits applied per IP address or API key
- **Endpoint-Specific Limits**: Different limits for different API endpoints
- **Risk-Based Categorization**: Endpoints categorized by risk level (LOW, MEDIUM, HIGH, CRITICAL)

## Configuration

### Global Settings

```json
{
  "global": {
    "enabled": true,
    "log_level": "INFO",
    "metrics_enabled": true,
    "cleanup_interval_seconds": 300,
    "store_type": "memory",
    "max_limiters": 10000,
    "default_ttl_seconds": 3600
  }
}
```

### Endpoint Configuration

Each endpoint can be configured with:

- `requests_per_second`: Number of requests allowed per second
- `burst_capacity`: Maximum burst requests allowed
- `window_seconds`: Time window for rate limiting
- `scope`: Rate limiting scope (IP, API_KEY, USER, etc.)
- `action`: Action when limit exceeded (REJECT, THROTTLE, QUEUE, WARN)
- `risk_level`: Endpoint risk level (LOW, MEDIUM, HIGH, CRITICAL)
- `enabled`: Whether rate limiting is enabled for this endpoint
- `bypass_patterns`: Patterns to bypass rate limiting
- `custom_headers`: Additional headers to include in responses

## Risk Levels and Default Limits

### CRITICAL Endpoints
- **Rate**: 1 request/second
- **Burst**: 3 requests
- **Action**: REJECT
- **Examples**: `POST /evolve`

### HIGH Risk Endpoints
- **Rate**: 2-3 requests/second
- **Burst**: 5-10 requests
- **Action**: REJECT
- **Examples**: `POST /decide`, `POST /review-pr`, `POST /webhooks/retry-failed`

### MEDIUM Risk Endpoints
- **Rate**: 5-15 requests/second
- **Burst**: 10-30 requests
- **Action**: REJECT
- **Examples**: `POST /webhooks/endpoints`, `PUT /webhooks/endpoints/*`

### LOW Risk Endpoints
- **Rate**: 20-100 requests/second
- **Burst**: 40-200 requests
- **Action**: THROTTLE
- **Examples**: `GET /stats`, `GET /webhooks/endpoints`, `GET /errors/summary`

## Rate Limiting Actions

### REJECT
- Returns `429 Too Many Requests` immediately
- Includes `Retry-After` header
- Provides detailed error message

### THROTTLE
- Adds delay before processing request
- Maximum delay capped at 5 seconds
- Request still processed after delay

### QUEUE
- Queues the request for later processing
- Simplified implementation with delay
- Useful for batch operations

### WARN
- Logs warning but continues processing
- Useful for monitoring suspicious activity
- No impact on user experience

## Headers

All responses include rate limiting headers:

- `X-RateLimit-Limit`: Total requests allowed in window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when window resets
- `X-RateLimit-Window`: Window duration in seconds
- `Retry-After`: Seconds to wait before retrying (when rate limited)

## Monitoring and Management

### Statistics Endpoint
```
GET /rate-limits/stats
```

Returns:
```json
{
  "total_limiters": 42,
  "client_stats": {
    "ip:127.0.0.1:GET /stats": {
      "total_requests": 150,
      "rejected_requests": 5
    }
  }
}
```

### Configuration Endpoint
```
GET /rate-limits/config
```

Returns current configuration summary including:
- Global settings
- Endpoint count
- Risk level distribution
- Action distribution

### Health Check
```
GET /rate-limits/health
```

Returns:
```json
{
  "status": "healthy",
  "enabled": true,
  "total_limiters": 42,
  "validation": {
    "valid": true,
    "issues": [],
    "warnings": []
  }
}
```

### Reset Rate Limits
```
POST /rate-limits/reset/{client_id}?endpoint=optional
```

Resets rate limits for a specific client or client/endpoint combination.

## Implementation Details

### Client Identification

1. **API Key Priority**: Uses `x-api-key` or `authorization` header if present
2. **IP Address Fallback**: Uses client IP address if no API key
3. **Privacy**: API keys are truncated in logs and identifiers

### Bypass Mechanisms

Rate limiting can be bypassed for:
- Disabled endpoints (`enabled: false`)
- Patterns in `bypass_patterns`
- Internal endpoints (`/internal/*`, `/health/*`)

### Error Handling

The rate limiting system is designed to fail open:
- If rate limiting fails, requests continue processing
- Errors are logged but don't block legitimate traffic
- Graceful degradation during high load

## Environment Variables

- `RATE_LIMIT_ENABLED`: Enable/disable rate limiting (default: true)
- `RATE_LIMIT_LOG_LEVEL`: Log level (default: INFO)
- `RATE_LIMIT_METRICS_ENABLED`: Enable metrics collection (default: true)
- `RATE_LIMIT_DEFAULT_RPS`: Default requests per second (default: 10.0)
- `RATE_LIMIT_DEFAULT_BURST`: Default burst capacity (default: 20)
- `RATE_LIMIT_DEFAULT_WINDOW`: Default time window (default: 60)

## Testing

The rate limiting system includes comprehensive tests:

```bash
# Run rate limiting tests
pytest tests/test_rate_limiting.py -v

# Run specific test categories
pytest tests/test_rate_limiting.py::TestRateLimitConfig -v
pytest tests/test_rate_limiting.py::TestAPIRateLimitMiddleware -v
pytest tests/test_rate_limiting.py::TestIntegration -v
```

## Performance Considerations

### Memory Usage
- Each rate limiter uses minimal memory (< 1KB)
- Automatic cleanup of expired limiters
- Configurable maximum number of limiters

### Latency Impact
- Minimal overhead: < 1ms per request
- Async operations throughout
- Efficient token bucket algorithm

### Scalability
- Current implementation supports thousands of concurrent clients
- For higher scale, consider Redis backend (planned for Phase 2)

## Security Features

### Protection Against
- **DDoS Attacks**: Rate limiting prevents overwhelming the system
- **Brute Force**: Limits repeated attempts on sensitive endpoints
- **API Abuse**: Prevents excessive usage of resource-intensive operations
- **Scraping**: Limits automated data extraction

### Monitoring
- Comprehensive logging of rate limiting events
- Statistics collection for abuse detection
- Real-time monitoring of rate limit violations

## Future Enhancements (Phase 2 & 3)

### Phase 2: Intelligent Rate Limiting
- **Adaptive Limits**: Adjust limits based on system load
- **User Reputation**: Different limits for trusted vs. new users
- **Anomaly Detection**: ML-based abuse pattern recognition
- **Geographic Limits**: Region-specific rate limiting

### Phase 3: Advanced Features
- **Distributed Storage**: Redis/Database backend for scalability
- **API Key Management**: Full API key lifecycle management
- **Advanced Analytics**: Detailed usage patterns and reporting
- **Custom Policies**: Rule-based rate limiting policies

## Troubleshooting

### Common Issues

1. **Rate Limits Too Restrictive**
   - Check endpoint configuration in `config/rate_limits.json`
   - Verify `requests_per_second` and `burst_capacity` settings
   - Consider using `throttle` action instead of `reject`

2. **Rate Limiting Not Working**
   - Verify `RATE_LIMIT_ENABLED=true` in environment
   - Check logs for initialization errors
   - Ensure middleware is properly registered

3. **High Memory Usage**
   - Reduce `max_limiters` setting
   - Increase `cleanup_interval_seconds`
   - Monitor `total_limiters` in health endpoint

### Debug Mode
Set `RATE_LIMIT_LOG_LEVEL=DEBUG` to see detailed rate limiting activity.

### Monitoring Commands
```bash
# Check rate limiting status
curl http://localhost:8000/rate-limits/health

# View current statistics
curl http://localhost:8000/rate-limits/stats

# Check configuration
curl http://localhost:8000/rate-limits/config

# Reset rate limits (if needed)
curl -X POST http://localhost:8000/rate-limits/reset/ip:127.0.0.1
```

## Best Practices

1. **Start Conservative**: Begin with restrictive limits and adjust based on usage
2. **Monitor Continuously**: Use statistics and logs to understand patterns
3. **Test Thoroughly**: Verify rate limiting doesn't break legitimate use cases
4. **Document Limits**: Clearly communicate rate limits to API consumers
5. **Provide Feedback**: Include helpful error messages and retry guidance
6. **Plan for Growth**: Design limits that can scale with your user base

## Configuration Examples

### Development Environment
```json
{
  "global": {
    "enabled": true,
    "log_level": "DEBUG"
  },
  "endpoints": {
    "POST /decide": {
      "requests_per_second": 10.0,
      "burst_capacity": 20,
      "action": "warn"
    }
  }
}
```

### Production Environment
```json
{
  "global": {
    "enabled": true,
    "log_level": "INFO",
    "metrics_enabled": true
  },
  "endpoints": {
    "POST /decide": {
      "requests_per_second": 3.0,
      "burst_capacity": 10,
      "action": "reject"
    }
  }
}
```

### High-Traffic Environment
```json
{
  "global": {
    "enabled": true,
    "max_limiters": 50000,
    "cleanup_interval_seconds": 120
  },
  "endpoints": {
    "GET /stats": {
      "requests_per_second": 200.0,
      "burst_capacity": 500,
      "action": "throttle"
    }
  }
}
```