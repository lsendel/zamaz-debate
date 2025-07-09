#!/usr/bin/env python3
"""
Resilience Patterns for Zamaz Debate System
Implements retry, timeout, fallback, and bulkhead patterns
"""

import asyncio
import functools
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union

# Monitoring imports will be injected at runtime to avoid circular imports
counter = lambda *args, **kwargs: None
gauge = lambda *args, **kwargs: None
histogram = lambda *args, **kwargs: None


# Mock traced context manager
class MockTraced:
    def __init__(self, operation):
        self.operation = operation
        self.tags = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


traced = MockTraced


T = TypeVar("T")


class RetryPolicy:
    """Retry policy configuration"""

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_multiplier: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        exceptions: tuple = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.backoff_multiplier = backoff_multiplier
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.exceptions = exceptions

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = min(
            self.initial_delay * (self.backoff_multiplier ** (attempt - 1)),
            self.max_delay,
        )

        if self.jitter:
            import random

            delay *= 0.5 + random.random()

        return delay


def retry_async(policy: RetryPolicy = None):
    """Async retry decorator with configurable policy"""
    if policy is None:
        policy = RetryPolicy()

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    with traced(f"retry.{func.__name__}") as span:
                        span.tags["attempt"] = attempt
                        result = await func(*args, **kwargs)

                        if attempt > 1:
                            counter(
                                "resilience.retry.success",
                                tags={"function": func.__name__},
                            )

                        return result

                except policy.exceptions as e:
                    last_exception = e
                    counter(
                        "resilience.retry.attempt", tags={"function": func.__name__}
                    )

                    if attempt < policy.max_attempts:
                        delay = policy.get_delay(attempt)
                        histogram("resilience.retry.delay", delay)
                        await asyncio.sleep(delay)
                    else:
                        counter(
                            "resilience.retry.exhausted",
                            tags={"function": func.__name__},
                        )

            # All retries exhausted
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_sync(policy: RetryPolicy = None):
    """Sync retry decorator with configurable policy"""
    if policy is None:
        policy = RetryPolicy()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)

                    if attempt > 1:
                        counter(
                            "resilience.retry.success", tags={"function": func.__name__}
                        )

                    return result

                except policy.exceptions as e:
                    last_exception = e
                    counter(
                        "resilience.retry.attempt", tags={"function": func.__name__}
                    )

                    if attempt < policy.max_attempts:
                        delay = policy.get_delay(attempt)
                        histogram("resilience.retry.delay", delay)
                        time.sleep(delay)
                    else:
                        counter(
                            "resilience.retry.exhausted",
                            tags={"function": func.__name__},
                        )

            # All retries exhausted
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def timeout_async(seconds: float, fallback: Any = None):
    """Async timeout decorator"""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                with traced(f"timeout.{func.__name__}") as span:
                    span.tags["timeout_seconds"] = seconds

                    result = await asyncio.wait_for(
                        func(*args, **kwargs), timeout=seconds
                    )

                    return result

            except asyncio.TimeoutError:
                counter("resilience.timeout.exceeded", tags={"function": func.__name__})
                histogram("resilience.timeout.duration", seconds)

                if fallback is not None:
                    return fallback

                raise TimeoutError(f"{func.__name__} timed out after {seconds} seconds")

        return wrapper

    return decorator


class Bulkhead:
    """Bulkhead pattern to limit concurrent executions"""

    def __init__(self, name: str, max_concurrent: int = 10, max_queued: int = 50):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_queued = max_queued
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue_size = 0
        self._active = 0

    async def acquire(self):
        """Acquire bulkhead permit"""
        if self._queue_size >= self.max_queued:
            counter(f"resilience.bulkhead.{self.name}.rejected")
            raise Exception(f"Bulkhead {self.name} queue full")

        self._queue_size += 1
        gauge(f"resilience.bulkhead.{self.name}.queue_size", self._queue_size)

        try:
            await self._semaphore.acquire()
            self._queue_size -= 1
            self._active += 1
            gauge(f"resilience.bulkhead.{self.name}.active", self._active)
            counter(f"resilience.bulkhead.{self.name}.acquired")

        except Exception:
            self._queue_size -= 1
            raise

    def release(self):
        """Release bulkhead permit"""
        self._semaphore.release()
        self._active -= 1
        gauge(f"resilience.bulkhead.{self.name}.active", self._active)
        counter(f"resilience.bulkhead.{self.name}.released")

    def __enter__(self):
        raise TypeError("Use async with")

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


def bulkhead(name: str, max_concurrent: int = 10, max_queued: int = 50):
    """Bulkhead decorator to limit concurrent executions"""
    bh = Bulkhead(name, max_concurrent, max_queued)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async with bh:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(
        self,
        name: str,
        rate: float,  # tokens per second
        capacity: int,  # bucket capacity
        burst: int = None,  # burst capacity
    ):
        self.name = name
        self.rate = rate
        self.capacity = capacity
        self.burst = burst or capacity

        self._tokens = float(capacity)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from bucket"""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_update

            # Add tokens based on elapsed time
            self._tokens = min(self.capacity, self._tokens + (elapsed * self.rate))
            self._last_update = now

            # Check if we have enough tokens
            if self._tokens >= tokens:
                self._tokens -= tokens
                gauge(f"resilience.rate_limiter.{self.name}.tokens", self._tokens)
                counter(f"resilience.rate_limiter.{self.name}.acquired", value=tokens)
                return True

            counter(f"resilience.rate_limiter.{self.name}.rejected")
            return False

    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """Wait until tokens are available"""
        while not await self.acquire(tokens):
            wait_time = tokens / self.rate
            await asyncio.sleep(wait_time)


def rate_limit(name: str, rate: float, capacity: int):
    """Rate limiting decorator"""
    limiter = RateLimiter(name, rate, capacity)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.wait_for_tokens(1)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class FallbackChain:
    """Chain of fallback functions"""

    def __init__(self, name: str):
        self.name = name
        self.fallbacks = []

    def add_fallback(
        self, func: Callable, condition: Callable[[Exception], bool] = None
    ):
        """Add a fallback function"""
        self.fallbacks.append((func, condition or (lambda e: True)))

    async def execute(self, *args, **kwargs) -> Any:
        """Execute with fallback chain"""
        last_error = None

        for i, (func, condition) in enumerate(self.fallbacks):
            try:
                with traced(f"fallback.{self.name}.{i}") as span:
                    span.tags["fallback_index"] = i

                    result = await func(*args, **kwargs)

                    if i > 0:
                        counter(
                            f"resilience.fallback.{self.name}.used", tags={"index": i}
                        )

                    return result

            except Exception as e:
                last_error = e

                if not condition(e):
                    # This fallback doesn't handle this error
                    raise

                counter(f"resilience.fallback.{self.name}.failed", tags={"index": i})

                # Continue to next fallback
                continue

        # All fallbacks exhausted
        if last_error:
            counter(f"resilience.fallback.{self.name}.exhausted")
            raise last_error


class HealthCheck:
    """Health check for components"""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], bool],
        interval: float = 60.0,
        timeout: float = 10.0,
        failure_threshold: int = 3,
    ):
        self.name = name
        self.check_func = check_func
        self.interval = interval
        self.timeout = timeout
        self.failure_threshold = failure_threshold

        self._consecutive_failures = 0
        self._last_check = None
        self._is_healthy = True
        self._task = None

    async def start(self):
        """Start health check loop"""
        self._task = asyncio.create_task(self._check_loop())

    async def stop(self):
        """Stop health check loop"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _check_loop(self):
        """Main health check loop"""
        while True:
            try:
                await asyncio.sleep(self.interval)
                await self._perform_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                counter(f"resilience.health_check.{self.name}.error")

    async def _perform_check(self):
        """Perform single health check"""
        try:
            # Run check with timeout
            result = await asyncio.wait_for(self._run_check(), timeout=self.timeout)

            if result:
                self._on_success()
            else:
                self._on_failure()

        except asyncio.TimeoutError:
            counter(f"resilience.health_check.{self.name}.timeout")
            self._on_failure()

        except Exception as e:
            counter(f"resilience.health_check.{self.name}.exception")
            self._on_failure()

    async def _run_check(self) -> bool:
        """Run the actual check function"""
        if asyncio.iscoroutinefunction(self.check_func):
            return await self.check_func()
        else:
            return self.check_func()

    def _on_success(self):
        """Handle successful check"""
        self._consecutive_failures = 0

        if not self._is_healthy:
            self._is_healthy = True
            counter(f"resilience.health_check.{self.name}.recovered")
            gauge(f"resilience.health_check.{self.name}.status", 1)  # 1 = healthy

        counter(f"resilience.health_check.{self.name}.success")
        self._last_check = datetime.now()

    def _on_failure(self):
        """Handle failed check"""
        self._consecutive_failures += 1
        counter(f"resilience.health_check.{self.name}.failure")

        if self._consecutive_failures >= self.failure_threshold and self._is_healthy:
            self._is_healthy = False
            counter(f"resilience.health_check.{self.name}.unhealthy")
            gauge(f"resilience.health_check.{self.name}.status", 0)  # 0 = unhealthy

        self._last_check = datetime.now()

    @property
    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self._is_healthy


class ResilienceManager:
    """Central manager for resilience patterns"""

    def __init__(self):
        self.bulkheads: Dict[str, Bulkhead] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.fallback_chains: Dict[str, FallbackChain] = {}

    def get_bulkhead(self, name: str, max_concurrent: int = 10) -> Bulkhead:
        """Get or create bulkhead"""
        if name not in self.bulkheads:
            self.bulkheads[name] = Bulkhead(name, max_concurrent)
        return self.bulkheads[name]

    def get_rate_limiter(self, name: str, rate: float, capacity: int) -> RateLimiter:
        """Get or create rate limiter"""
        if name not in self.rate_limiters:
            self.rate_limiters[name] = RateLimiter(name, rate, capacity)
        return self.rate_limiters[name]

    def add_health_check(self, health_check: HealthCheck):
        """Add health check"""
        self.health_checks[health_check.name] = health_check

    def get_fallback_chain(self, name: str) -> FallbackChain:
        """Get or create fallback chain"""
        if name not in self.fallback_chains:
            self.fallback_chains[name] = FallbackChain(name)
        return self.fallback_chains[name]

    async def start_health_checks(self):
        """Start all health checks"""
        for check in self.health_checks.values():
            await check.start()

    async def stop_health_checks(self):
        """Stop all health checks"""
        for check in self.health_checks.values():
            await check.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get resilience status"""
        return {
            "bulkheads": {
                name: {
                    "active": bh._active,
                    "queue_size": bh._queue_size,
                    "max_concurrent": bh.max_concurrent,
                }
                for name, bh in self.bulkheads.items()
            },
            "rate_limiters": {
                name: {"tokens": rl._tokens, "rate": rl.rate, "capacity": rl.capacity}
                for name, rl in self.rate_limiters.items()
            },
            "health_checks": {
                name: {
                    "is_healthy": hc.is_healthy,
                    "consecutive_failures": hc._consecutive_failures,
                    "last_check": hc._last_check.isoformat()
                    if hc._last_check
                    else None,
                }
                for name, hc in self.health_checks.items()
            },
        }


# Global resilience manager
_resilience_manager = None


def get_resilience_manager() -> ResilienceManager:
    """Get global resilience manager"""
    global _resilience_manager
    if _resilience_manager is None:
        _resilience_manager = ResilienceManager()
    return _resilience_manager


# Convenience functions
def with_resilience(
    name: str,
    retry: bool = True,
    timeout: float = None,
    bulkhead: bool = True,
    rate_limit: float = None,
    fallback: Any = None,
):
    """Comprehensive resilience decorator"""

    def decorator(func):
        wrapped = func

        # Apply retry
        if retry:
            policy = RetryPolicy(max_attempts=3)
            wrapped = retry_async(policy)(wrapped)

        # Apply timeout
        if timeout:
            wrapped = timeout_async(timeout, fallback)(wrapped)

        # Apply bulkhead
        if bulkhead:
            manager = get_resilience_manager()
            bh = manager.get_bulkhead(name)

            @functools.wraps(wrapped)
            async def bulkhead_wrapper(*args, **kwargs):
                async with bh:
                    return await wrapped(*args, **kwargs)

            wrapped = bulkhead_wrapper

        # Apply rate limiting
        if rate_limit:
            manager = get_resilience_manager()
            rl = manager.get_rate_limiter(name, rate_limit, int(rate_limit * 10))

            @functools.wraps(wrapped)
            async def rate_limit_wrapper(*args, **kwargs):
                await rl.wait_for_tokens(1)
                return await wrapped(*args, **kwargs)

            wrapped = rate_limit_wrapper

        return wrapped

    return decorator
