# Webhook Safety Enhancements

## Critical Issues Addressed

### 1. Race Condition in Retry Logic (src/webhooks/service.py:294-325)
**Issue**: The retry logic modifies the _delivery_attempts list while potentially being called concurrently with send_webhook_notification().
**Risk**: Could lead to data corruption or missed retries.
**Solution**: Implement proper locking with `asyncio.Lock()` or use thread-safe data structures.

### 2. Unbounded Event Processing (src/webhooks/event_handler.py:97-415)
**Issue**: Event handlers don't have any rate limiting or circuit breaker patterns.
**Risk**: Could overwhelm the system during event storms.
**Solution**: Add rate limiting and circuit breaker patterns.

## Proposed Enhancements

### 1. Thread-Safe Webhook Service

```python
import asyncio
from threading import RLock

class WebhookService:
    def __init__(self, data_dir: Optional[Path] = None):
        # ... existing init code ...
        # Add locks for thread safety
        self._delivery_lock = asyncio.Lock()
        self._endpoints_lock = RLock()
        
    async def send_webhook_notification(self, ...):
        # Use lock when modifying delivery attempts
        async with self._delivery_lock:
            # ... existing code ...
            
    async def retry_failed_deliveries(self):
        # Ensure thread-safe access to delivery attempts
        async with self._delivery_lock:
            # Create a copy to avoid modification during iteration
            attempts_snapshot = list(self._delivery_attempts)
            
        # Process retries outside the lock
        for attempt in attempts_snapshot:
            # ... retry logic ...
```

### 2. Rate Limiting for Event Handler

```python
from src.core.resilience import RateLimiter

class WebhookEventHandler:
    def __init__(self, webhook_service: WebhookService, event_bus: EventBus):
        # ... existing init ...
        # Add rate limiter
        self._rate_limiter = RateLimiter(
            name="webhook_events",
            rate=100.0,  # 100 events per second
            capacity=200  # burst capacity
        )
        
    async def _handle_any_event(self, event_type: str, event_data: dict):
        # Apply rate limiting
        if not await self._rate_limiter.acquire():
            logger.warning(f"Rate limit exceeded for {event_type}")
            return
            
        # Process event
        await self.webhook_service.send_webhook_notification(...)
```

### 3. Circuit Breaker Pattern

```python
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
                
        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            raise
```

### 4. Event Storm Protection

```python
class EventStormProtection:
    def __init__(self, window_size=60, max_events=1000):
        self.window_size = window_size  # seconds
        self.max_events = max_events
        self.event_timestamps = deque()
        self._lock = asyncio.Lock()
        
    async def should_process_event(self) -> bool:
        async with self._lock:
            now = time.time()
            # Remove old events outside the window
            while self.event_timestamps and self.event_timestamps[0] < now - self.window_size:
                self.event_timestamps.popleft()
                
            # Check if we're under the limit
            if len(self.event_timestamps) >= self.max_events:
                return False
                
            self.event_timestamps.append(now)
            return True
```

## Implementation Priority

1. **High Priority**: Fix race condition with proper locking
2. **High Priority**: Add rate limiting to prevent event storms
3. **Medium Priority**: Implement circuit breaker for webhook endpoints
4. **Low Priority**: Add comprehensive event storm protection

## Testing Recommendations

1. **Concurrent Access Test**: Simulate multiple threads accessing the retry logic
2. **Event Storm Test**: Send 10,000 events in rapid succession
3. **Circuit Breaker Test**: Simulate failing webhook endpoints
4. **Load Test**: Measure system performance under high load

## Monitoring Additions

- Add metrics for:
  - Rate limit hits
  - Circuit breaker state changes
  - Concurrent access attempts
  - Event processing latency
  - Queue depths