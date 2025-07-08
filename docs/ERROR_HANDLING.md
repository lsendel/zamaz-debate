# Error Handling and Recovery System

The Zamaz Debate System includes a comprehensive error handling and recovery framework that provides automatic error classification, recovery strategies, and resilience patterns.

## Overview

The error handling system is designed to:
- **Classify Errors**: Automatically categorize errors by type and severity
- **Recover Gracefully**: Apply appropriate recovery strategies based on error type
- **Prevent Cascading Failures**: Use circuit breakers and bulkheads
- **Monitor Error Patterns**: Track errors for analysis and improvement
- **Ensure System Resilience**: Implement retry, timeout, and fallback patterns

## Architecture

### Core Components

#### ErrorHandler (`src/core/error_handler.py`)
The main error handling coordinator:

```python
from src.core.error_handler import get_error_handler, with_error_handling

# Get global error handler
handler = get_error_handler()

# Handle error manually
await handler.handle_error(
    error=exception,
    component="nucleus",
    operation="decide",
    context={"user_id": "123"}
)

# Use decorator for automatic handling
@with_error_handling(component="api", operation="process_request")
async def process_request(data):
    # Function automatically protected
    return process(data)
```

#### ErrorClassifier
Classifies errors into categories and severities:

- **Categories**: AI_CLIENT, NETWORK, VALIDATION, BUSINESS_LOGIC, RESOURCE, etc.
- **Severities**: LOW, MEDIUM, HIGH, CRITICAL

#### RecoveryManager
Manages recovery strategies for different error types:

- **Retry with Backoff**: For transient errors
- **Fallback to Mock**: For AI client failures
- **Rate Limit Handling**: For API throttling
- **Timeout Recovery**: For slow operations

#### ResiliencePatterns (`src/core/resilience.py`)
Implements various resilience patterns:

- **Retry**: Configurable retry policies with exponential backoff
- **Timeout**: Prevent operations from running too long
- **Circuit Breaker**: Prevent cascading failures
- **Bulkhead**: Limit concurrent operations
- **Rate Limiting**: Control request rates
- **Fallback**: Alternative execution paths

## Error Categories

### AI Client Errors
Errors from Claude or Gemini API calls:
- **Recovery**: Retry with backoff, fallback to mock responses
- **Monitoring**: Track success/failure rates per AI provider

### Network Errors
Connection failures, timeouts, DNS issues:
- **Recovery**: Aggressive retry with longer backoff
- **Monitoring**: Track network reliability metrics

### Validation Errors
Invalid input, type errors, business rule violations:
- **Recovery**: Return error to user, no retry
- **Monitoring**: Track common validation failures

### Resource Errors
Memory exhaustion, disk full, quota exceeded:
- **Recovery**: Alert and degrade gracefully
- **Monitoring**: Track resource usage patterns

### Rate Limit Errors
API throttling from external services:
- **Recovery**: Smart backoff based on retry-after headers
- **Monitoring**: Track rate limit hits by service

## Recovery Strategies

### Retry with Exponential Backoff
```python
from src.core.resilience import retry_async, RetryPolicy

policy = RetryPolicy(
    max_attempts=3,
    backoff_multiplier=2.0,
    initial_delay=1.0,
    max_delay=60.0,
    jitter=True
)

@retry_async(policy)
async def flaky_operation():
    # Automatically retried on failure
    return await external_api_call()
```

### Circuit Breaker Pattern
```python
from src.core.error_handler import CircuitBreaker

breaker = CircuitBreaker(
    name="ai_service",
    failure_threshold=5,
    recovery_timeout=60.0
)

# Use circuit breaker
result = breaker.call(ai_service_function, *args)
```

### Bulkhead Pattern
```python
from src.core.resilience import bulkhead

@bulkhead(name="debate_service", max_concurrent=10, max_queued=50)
async def process_debate(question):
    # Limited concurrent executions
    return await nucleus.decide(question)
```

### Fallback Chain
```python
from src.core.resilience import FallbackChain

chain = FallbackChain("ai_response")

# Primary function
async def get_claude_response():
    return await claude_client.query()

# Fallback function
async def get_gemini_response():
    return await gemini_client.query()

# Mock fallback
async def get_mock_response():
    return {"response": "Mock response", "fallback": True}

chain.add_fallback(get_claude_response)
chain.add_fallback(get_gemini_response)
chain.add_fallback(get_mock_response)

result = await chain.execute()
```

## Usage Patterns

### Comprehensive Protection
```python
from src.core.resilience import with_resilience

@with_resilience(
    name="critical_operation",
    retry=True,
    timeout=30.0,
    bulkhead=True,
    rate_limit=10.0,  # 10 requests per second
    fallback={"status": "degraded"}
)
async def critical_operation(data):
    # Protected with all resilience patterns
    return await process_critical_data(data)
```

### Manual Error Handling
```python
from src.core.error_handler import get_error_handler

try:
    result = await risky_operation()
except Exception as e:
    handler = get_error_handler()
    
    # Attempt recovery
    recovery_result = await handler.handle_error(
        error=e,
        component="my_service",
        operation="risky_operation",
        context={
            "operation_func": lambda: risky_operation(),
            "user_id": user_id
        }
    )
    
    if recovery_result:
        result = recovery_result
    else:
        # Recovery failed, handle gracefully
        raise
```

### Health Monitoring
```python
from src.core.resilience import HealthCheck, get_resilience_manager

# Define health check
async def check_database():
    try:
        await db.ping()
        return True
    except:
        return False

# Register health check
health_check = HealthCheck(
    name="database",
    check_func=check_database,
    interval=60.0,
    failure_threshold=3
)

manager = get_resilience_manager()
manager.add_health_check(health_check)
await manager.start_health_checks()
```

## API Endpoints

### Error Summary
```bash
GET /errors/summary?minutes=60

Response:
{
    "total_errors": 42,
    "by_category": {
        "ai_client": 15,
        "network": 8,
        "validation": 19
    },
    "by_severity": {
        "low": 20,
        "medium": 18,
        "high": 3,
        "critical": 1
    },
    "recovery_rate": 0.85,
    "critical_errors": [...]
}
```

### Resilience Status
```bash
GET /errors/resilience/status

Response:
{
    "bulkheads": {
        "debate_service": {
            "active": 3,
            "queue_size": 0,
            "max_concurrent": 10
        }
    },
    "rate_limiters": {
        "ai_api": {
            "tokens": 45.5,
            "rate": 100.0,
            "capacity": 100
        }
    },
    "health_checks": {
        "database": {
            "is_healthy": true,
            "consecutive_failures": 0,
            "last_check": "2023-01-01T12:00:00"
        }
    }
}
```

## Integration with Monitoring

The error handling system integrates with the monitoring system:

### Metrics Collected
- `errors.total` - Total error count
- `errors.by_category.{category}` - Errors by category
- `errors.by_severity.{severity}` - Errors by severity
- `errors.recovered` - Successfully recovered errors
- `errors.critical` - Critical errors requiring attention
- `error_recovery.attempts` - Recovery attempts
- `error_recovery.success` - Successful recoveries
- `resilience.retry.attempts` - Retry attempts
- `resilience.circuit_breaker.{name}.state` - Circuit breaker states
- `resilience.bulkhead.{name}.active` - Active bulkhead operations
- `resilience.rate_limiter.{name}.tokens` - Available rate limit tokens

### Distributed Tracing
All error handling operations are automatically traced:
- Error classification and severity determination
- Recovery strategy selection and execution
- Retry attempts with timing
- Circuit breaker state changes

## Configuration

### Environment Variables
```bash
# Error handling settings
ERROR_MAX_HISTORY=1000
ERROR_RECOVERY_ENABLED=true

# Retry defaults
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_MULTIPLIER=2.0
RETRY_MAX_DELAY=60.0

# Circuit breaker defaults
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60.0

# Bulkhead defaults
BULKHEAD_MAX_CONCURRENT=10
BULKHEAD_MAX_QUEUED=50

# Rate limiter defaults
RATE_LIMIT_TOKENS_PER_SECOND=100.0
RATE_LIMIT_BURST_CAPACITY=200
```

### Programmatic Configuration
```python
# Configure retry policy
policy = RetryPolicy(
    max_attempts=5,
    backoff_multiplier=3.0,
    initial_delay=2.0,
    max_delay=120.0,
    jitter=True,
    exceptions=(NetworkError, TimeoutError)
)

# Configure circuit breaker
breaker = CircuitBreaker(
    name="external_api",
    failure_threshold=10,
    recovery_timeout=300.0,
    expected_exception=APIError
)

# Configure bulkhead
bulkhead = Bulkhead(
    name="cpu_intensive",
    max_concurrent=4,
    max_queued=20
)
```

## Best Practices

### Error Classification
- Be specific with error categories
- Use appropriate severity levels
- Include context in error messages
- Preserve stack traces for debugging

### Recovery Strategies
- Match recovery to error type
- Use exponential backoff for retries
- Implement proper timeout handling
- Provide meaningful fallbacks
- Log all recovery attempts

### Circuit Breakers
- Set appropriate failure thresholds
- Use reasonable recovery timeouts
- Monitor circuit breaker states
- Alert on circuit breaker trips

### Bulkheads
- Isolate critical operations
- Set limits based on resources
- Monitor queue lengths
- Adjust limits based on load

### Health Checks
- Check actual functionality
- Use appropriate check intervals
- Set reasonable failure thresholds
- Include dependency checks

## Testing

### Unit Tests
```python
# Test error classification
def test_error_classification():
    classifier = ErrorClassifier()
    category, severity = classifier.classify(ConnectionError("Failed"))
    assert category == ErrorCategory.NETWORK
    assert severity == ErrorSeverity.MEDIUM

# Test recovery strategy
@pytest.mark.asyncio
async def test_retry_recovery():
    @retry_async(RetryPolicy(max_attempts=3))
    async def flaky_function():
        # Test implementation
        pass
```

### Integration Tests
```python
# Test full error handling flow
@pytest.mark.asyncio
async def test_error_handling_integration():
    handler = get_error_handler()
    
    # Simulate error
    error = APIError("Service unavailable")
    
    # Handle with recovery
    result = await handler.handle_error(
        error=error,
        component="test",
        operation="api_call"
    )
    
    assert result is not None  # Recovery succeeded
```

## Troubleshooting

### Common Issues

#### High Error Rates
1. Check error summary endpoint
2. Identify top error categories
3. Review recovery success rates
4. Adjust retry policies if needed

#### Circuit Breaker Trips
1. Check resilience status
2. Review error logs for root cause
3. Verify external service health
4. Adjust failure thresholds if needed

#### Bulkhead Rejection
1. Monitor active operations
2. Check queue sizes
3. Increase limits if resources allow
4. Consider adding more bulkheads

#### Recovery Failures
1. Review error handler logs
2. Check recovery strategy configuration
3. Verify fallback implementations
4. Monitor recovery metrics

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger('src.core.error_handler').setLevel(logging.DEBUG)
logging.getLogger('src.core.resilience').setLevel(logging.DEBUG)

# Check error handler state
handler = get_error_handler()
print(f"Error history: {len(handler.error_history)}")
print(f"Recent errors: {handler.get_error_summary(10)}")

# Check resilience state
manager = get_resilience_manager()
print(f"Resilience status: {manager.get_status()}")
```

## Future Enhancements

### Planned Features
- **Error Prediction**: ML-based error prediction
- **Adaptive Recovery**: Dynamic strategy selection
- **Chaos Engineering**: Automated failure injection
- **Error Analytics**: Advanced error pattern analysis
- **Dependency Mapping**: Service dependency tracking
- **SLA Monitoring**: Service level agreement tracking

### External Integration
- **PagerDuty**: Alert on critical errors
- **Sentry**: Error tracking and analysis
- **Prometheus**: Export error metrics
- **Grafana**: Error dashboards
- **ELK Stack**: Log aggregation