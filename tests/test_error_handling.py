#!/usr/bin/env python3
"""
Tests for error handling and recovery system
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from src.core.error_handler import (
    ErrorHandler,
    ErrorClassifier,
    RecoveryManager,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy,
    get_error_handler,
    with_error_handling,
    CircuitBreaker,
)

from src.core.resilience import (
    RetryPolicy,
    retry_async,
    retry_sync,
    timeout_async,
    Bulkhead,
    RateLimiter,
    FallbackChain,
    HealthCheck,
    ResilienceManager,
    with_resilience,
)


class TestErrorClassifier:
    """Test suite for error classification"""

    def test_classify_network_errors(self):
        """Test classification of network errors"""
        classifier = ErrorClassifier()

        # Connection error
        category, severity = classifier.classify(ConnectionError("Connection failed"))
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.MEDIUM

        # Timeout error
        category, severity = classifier.classify(TimeoutError("Request timed out"))
        assert category == ErrorCategory.TIMEOUT
        assert severity == ErrorSeverity.MEDIUM

    def test_classify_validation_errors(self):
        """Test classification of validation errors"""
        classifier = ErrorClassifier()

        # ValueError
        category, severity = classifier.classify(ValueError("Invalid input"))
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.LOW

        # TypeError
        category, severity = classifier.classify(TypeError("Wrong type"))
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.LOW

    def test_classify_resource_errors(self):
        """Test classification of resource errors"""
        classifier = ErrorClassifier()

        # Memory error
        category, severity = classifier.classify(MemoryError("Out of memory"))
        assert category == ErrorCategory.RESOURCE
        assert severity == ErrorSeverity.CRITICAL

        # OS error
        category, severity = classifier.classify(OSError("Disk full"))
        assert category == ErrorCategory.RESOURCE
        assert severity == ErrorSeverity.HIGH

    def test_classify_by_message_patterns(self):
        """Test classification by error message patterns"""
        classifier = ErrorClassifier()

        # API rate limit
        error = Exception("API rate limit exceeded")
        category, severity = classifier.classify(error)
        assert category == ErrorCategory.RATE_LIMIT
        assert severity == ErrorSeverity.MEDIUM

        # AI client error
        error = Exception("Claude API error: 500")
        category, severity = classifier.classify(error)
        assert category == ErrorCategory.AI_CLIENT
        assert severity == ErrorSeverity.MEDIUM

        # Configuration error
        error = Exception("Configuration setting not found")
        category, severity = classifier.classify(error)
        assert category == ErrorCategory.CONFIGURATION
        assert severity == ErrorSeverity.HIGH


class TestRecoveryManager:
    """Test suite for recovery management"""

    @pytest.mark.asyncio
    async def test_retry_recovery_strategy(self):
        """Test retry recovery strategy"""
        manager = RecoveryManager()

        # Get AI client strategies
        strategies = manager.get_strategies(ErrorCategory.AI_CLIENT)
        assert len(strategies) >= 1

        # Test retry strategy
        retry_strategy = strategies[0]

        context = ErrorContext(
            error=Exception("API error"),
            category=ErrorCategory.AI_CLIENT,
            severity=ErrorSeverity.MEDIUM,
            component="test",
            operation="test_op",
            retry_count=0,
        )

        # Should be able to recover
        assert retry_strategy.can_recover(context) is True

        # After max retries, should not recover
        context.retry_count = 3
        assert retry_strategy.can_recover(context) is False

    @pytest.mark.asyncio
    async def test_fallback_recovery(self):
        """Test fallback recovery strategy"""
        manager = RecoveryManager()

        # Add mock operation to context
        mock_operation = AsyncMock(return_value="success")

        context = ErrorContext(
            error=Exception("API error"),
            category=ErrorCategory.AI_CLIENT,
            severity=ErrorSeverity.MEDIUM,
            component="test",
            operation="test_op",
            retry_count=3,  # Already retried
            metadata={"operation_func": mock_operation},
        )

        # Get fallback strategy
        strategies = manager.get_strategies(ErrorCategory.AI_CLIENT)
        fallback_strategy = next((s for s in strategies if s.name == "ai_client_fallback"), None)

        assert fallback_strategy is not None
        assert fallback_strategy.can_recover(context) is True

        # Test fallback
        result = await fallback_strategy.recover(context)
        assert result["fallback"] is True
        assert "error" in result

    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self):
        """Test rate limit recovery"""
        manager = RecoveryManager()

        context = ErrorContext(
            error=Exception("Rate limit exceeded"),
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            component="test",
            operation="test_op",
            metadata={"retry_after": 1},  # 1 second wait
        )

        strategies = manager.get_strategies(ErrorCategory.RATE_LIMIT)
        assert len(strategies) >= 1

        rate_limit_strategy = strategies[0]
        assert rate_limit_strategy.can_recover(context) is True


class TestErrorHandler:
    """Test suite for main error handler"""

    @pytest.mark.asyncio
    async def test_handle_low_severity_error(self):
        """Test handling of low severity errors"""
        handler = ErrorHandler()

        error = ValueError("Invalid input")

        # Mock successful recovery
        with patch.object(handler.recovery_manager, "get_strategies") as mock_strategies:
            mock_strategy = Mock()
            mock_strategy.can_recover.return_value = True
            mock_strategy.recover = AsyncMock(return_value="recovered")
            mock_strategies.return_value = [mock_strategy]

            result = await handler.handle_error(error=error, component="test", operation="test_op")

            assert result == "recovered"
            assert len(handler.error_history) == 1

    @pytest.mark.asyncio
    async def test_handle_critical_error(self):
        """Test handling of critical errors"""
        handler = ErrorHandler()

        error = MemoryError("Out of memory")

        with pytest.raises(MemoryError):
            await handler.handle_error(error=error, component="test", operation="test_op")

        # Error should be logged in history
        assert len(handler.error_history) == 1
        assert handler.error_history[0].severity == ErrorSeverity.CRITICAL

    def test_error_summary(self):
        """Test error summary generation"""
        handler = ErrorHandler()

        # Add some test errors
        test_errors = [
            ErrorContext(
                error=ValueError("Test"),
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                component="comp1",
                operation="op1",
            ),
            ErrorContext(
                error=ConnectionError("Test"),
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                component="comp2",
                operation="op2",
                recovery_attempted=True,
            ),
            ErrorContext(
                error=MemoryError("Test"),
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                component="comp1",
                operation="op3",
            ),
        ]

        handler.error_history.extend(test_errors)

        summary = handler.get_error_summary(60)

        assert summary["total_errors"] == 3
        assert summary["by_category"][ErrorCategory.VALIDATION.value] == 1
        assert summary["by_category"][ErrorCategory.NETWORK.value] == 1
        assert summary["by_category"][ErrorCategory.RESOURCE.value] == 1
        assert summary["by_severity"][ErrorSeverity.LOW.value] == 1
        assert summary["by_severity"][ErrorSeverity.MEDIUM.value] == 1
        assert summary["by_severity"][ErrorSeverity.CRITICAL.value] == 1
        assert summary["recovery_rate"] == 1 / 3
        assert len(summary["critical_errors"]) == 1


class TestErrorHandlingDecorator:
    """Test error handling decorator"""

    @pytest.mark.asyncio
    async def test_async_decorator_success(self):
        """Test decorator with successful execution"""

        @with_error_handling(component="test", operation="test_op")
        async def test_function(x, y):
            return x + y

        result = await test_function(1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_async_decorator_with_recovery(self):
        """Test decorator with error recovery"""
        call_count = 0

        @with_error_handling(component="test", operation="test_op", reraise=False, fallback=42)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        result = await test_function()
        assert result == 42  # Fallback value
        assert call_count == 1

    def test_sync_decorator(self):
        """Test sync decorator"""

        @with_error_handling(component="test", operation="test_op", reraise=False, fallback="failed")
        def test_function():
            raise ValueError("Test error")

        result = test_function()
        assert result == "failed"


class TestCircuitBreaker:
    """Test circuit breaker pattern"""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state"""
        breaker = CircuitBreaker("test", failure_threshold=3, recovery_timeout=1.0)

        # Successful calls
        for i in range(5):
            result = breaker.call(lambda: "success")
            assert result == "success"

        assert breaker._state == "closed"

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opening on failures"""
        breaker = CircuitBreaker("test", failure_threshold=3, recovery_timeout=1.0)

        def failing_function():
            raise Exception("Test failure")

        # Fail threshold times
        for i in range(3):
            with pytest.raises(Exception):
                breaker.call(failing_function)

        # Circuit should be open
        assert breaker._state == "open"

        # Further calls should be rejected
        with pytest.raises(Exception) as exc_info:
            breaker.call(lambda: "success")

        assert "Circuit breaker test is open" in str(exc_info.value)

    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state"""
        breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)

        def failing_function():
            raise Exception("Test failure")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                breaker.call(failing_function)

        assert breaker._state == "open"

        # Wait for recovery timeout
        time.sleep(0.2)

        # Try again - should go to half-open
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker._state == "closed"


class TestRetryPolicy:
    """Test retry policy"""

    def test_retry_policy_delay_calculation(self):
        """Test retry delay calculation"""
        policy = RetryPolicy(max_attempts=5, backoff_multiplier=2.0, initial_delay=1.0, max_delay=10.0, jitter=False)

        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 2.0
        assert policy.get_delay(3) == 4.0
        assert policy.get_delay(4) == 8.0
        assert policy.get_delay(5) == 10.0  # Capped at max_delay

    @pytest.mark.asyncio
    async def test_async_retry_decorator(self):
        """Test async retry decorator"""
        call_count = 0

        @retry_async(RetryPolicy(max_attempts=3, initial_delay=0.01))
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert call_count == 3

    def test_sync_retry_decorator(self):
        """Test sync retry decorator"""
        call_count = 0

        @retry_sync(RetryPolicy(max_attempts=3, initial_delay=0.01))
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3


class TestTimeout:
    """Test timeout patterns"""

    @pytest.mark.asyncio
    async def test_timeout_success(self):
        """Test timeout with successful execution"""

        @timeout_async(1.0)
        async def fast_function():
            await asyncio.sleep(0.1)
            return "success"

        result = await fast_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test timeout exceeded"""

        @timeout_async(0.1)
        async def slow_function():
            await asyncio.sleep(0.5)
            return "too late"

        with pytest.raises(TimeoutError):
            await slow_function()

    @pytest.mark.asyncio
    async def test_timeout_with_fallback(self):
        """Test timeout with fallback value"""

        @timeout_async(0.1, fallback="default")
        async def slow_function():
            await asyncio.sleep(0.5)
            return "too late"

        result = await slow_function()
        assert result == "default"


class TestBulkhead:
    """Test bulkhead pattern"""

    @pytest.mark.asyncio
    async def test_bulkhead_concurrent_limit(self):
        """Test bulkhead concurrent execution limit"""
        bulkhead = Bulkhead("test", max_concurrent=2, max_queued=5)

        async def slow_task(id):
            await asyncio.sleep(0.1)
            return id

        # Start 3 tasks (1 will queue)
        tasks = []
        for i in range(3):

            async def task_wrapper(task_id):
                async with bulkhead:
                    return await slow_task(task_id)

            tasks.append(asyncio.create_task(task_wrapper(i)))

        # Wait a bit to ensure tasks are running
        await asyncio.sleep(0.05)

        # Check that only 2 are active
        assert bulkhead._active == 2
        assert bulkhead._queue_size == 1

        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        assert sorted(results) == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_bulkhead_queue_rejection(self):
        """Test bulkhead queue rejection"""
        bulkhead = Bulkhead("test", max_concurrent=1, max_queued=1)

        async def slow_task():
            await asyncio.sleep(0.1)

        # Start max concurrent + max queued tasks
        tasks = []
        for i in range(2):

            async def task_wrapper():
                async with bulkhead:
                    await slow_task()

            tasks.append(asyncio.create_task(task_wrapper()))

        await asyncio.sleep(0.01)  # Let tasks start

        # Try to add one more - should be rejected
        with pytest.raises(Exception) as exc_info:
            async with bulkhead:
                pass

        assert "queue full" in str(exc_info.value)

        # Clean up
        await asyncio.gather(*tasks)


class TestRateLimiter:
    """Test rate limiting"""

    @pytest.mark.asyncio
    async def test_rate_limiter_token_bucket(self):
        """Test token bucket rate limiting"""
        limiter = RateLimiter("test", rate=10.0, capacity=10)  # 10 tokens/sec

        # Should be able to acquire initial tokens
        assert await limiter.acquire(5) is True
        assert limiter._tokens == 5.0

        # Should be able to acquire remaining
        assert await limiter.acquire(5) is True
        assert limiter._tokens == 0.0

        # Should not be able to acquire more
        assert await limiter.acquire(1) is False

        # Wait for tokens to regenerate
        await asyncio.sleep(0.2)  # Should add ~2 tokens

        assert await limiter.acquire(1) is True

    @pytest.mark.asyncio
    async def test_rate_limiter_wait_for_tokens(self):
        """Test waiting for tokens"""
        limiter = RateLimiter("test", rate=10.0, capacity=5)

        # Use all tokens
        await limiter.acquire(5)

        # Wait for tokens should succeed
        start_time = time.time()
        await limiter.wait_for_tokens(2)
        elapsed = time.time() - start_time

        # Should have waited approximately 0.2 seconds
        assert 0.15 < elapsed < 0.25


class TestFallbackChain:
    """Test fallback chain pattern"""

    @pytest.mark.asyncio
    async def test_fallback_chain_success(self):
        """Test fallback chain with successful primary"""
        chain = FallbackChain("test")

        async def primary():
            return "primary"

        async def fallback():
            return "fallback"

        chain.add_fallback(primary)
        chain.add_fallback(fallback)

        result = await chain.execute()
        assert result == "primary"

    @pytest.mark.asyncio
    async def test_fallback_chain_with_failure(self):
        """Test fallback chain with primary failure"""
        chain = FallbackChain("test")

        async def primary():
            raise ValueError("Primary failed")

        async def fallback():
            return "fallback"

        chain.add_fallback(primary)
        chain.add_fallback(fallback)

        result = await chain.execute()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_chain_conditional(self):
        """Test fallback chain with conditional handling"""
        chain = FallbackChain("test")

        async def primary():
            raise ValueError("Not found")

        async def handle_not_found():
            return "default"

        async def handle_other():
            return "other"

        # Only handle ValueError
        chain.add_fallback(primary)
        chain.add_fallback(handle_not_found, condition=lambda e: isinstance(e, ValueError))
        chain.add_fallback(handle_other, condition=lambda e: not isinstance(e, ValueError))

        result = await chain.execute()
        assert result == "default"


class TestHealthCheck:
    """Test health check pattern"""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check with healthy component"""
        check_count = 0

        def check_func():
            nonlocal check_count
            check_count += 1
            return True

        health_check = HealthCheck("test", check_func, interval=0.1, timeout=1.0, failure_threshold=3)

        assert health_check.is_healthy is True

        await health_check.start()
        await asyncio.sleep(0.25)  # Let it run a few checks
        await health_check.stop()

        assert check_count >= 2
        assert health_check.is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure_threshold(self):
        """Test health check failure threshold"""
        check_count = 0

        def check_func():
            nonlocal check_count
            check_count += 1
            return False  # Always fail

        health_check = HealthCheck("test", check_func, interval=0.05, timeout=1.0, failure_threshold=2)

        assert health_check.is_healthy is True

        await health_check.start()
        await asyncio.sleep(0.15)  # Let it fail multiple times
        await health_check.stop()

        assert check_count >= 2
        assert health_check.is_healthy is False
        assert health_check._consecutive_failures >= 2


class TestResilienceManager:
    """Test resilience manager"""

    def test_resilience_manager_components(self):
        """Test resilience manager component management"""
        manager = ResilienceManager()

        # Get bulkhead
        bulkhead1 = manager.get_bulkhead("service1", max_concurrent=5)
        bulkhead2 = manager.get_bulkhead("service1", max_concurrent=10)
        assert bulkhead1 is bulkhead2  # Same instance

        # Get rate limiter
        limiter = manager.get_rate_limiter("api", rate=100.0, capacity=100)
        assert limiter.rate == 100.0

        # Get fallback chain
        chain = manager.get_fallback_chain("service")
        assert chain.name == "service"

    def test_resilience_status(self):
        """Test resilience status reporting"""
        manager = ResilienceManager()

        # Create some components
        bulkhead = manager.get_bulkhead("test", max_concurrent=10)
        limiter = manager.get_rate_limiter("test", rate=10.0, capacity=10)

        # Add health check
        health_check = HealthCheck("test", lambda: True)
        manager.add_health_check(health_check)

        status = manager.get_status()

        assert "bulkheads" in status
        assert "rate_limiters" in status
        assert "health_checks" in status

        assert "test" in status["bulkheads"]
        assert status["bulkheads"]["test"]["max_concurrent"] == 10

        assert "test" in status["rate_limiters"]
        assert status["rate_limiters"]["test"]["rate"] == 10.0


class TestComprehensiveResilience:
    """Test comprehensive resilience decorator"""

    @pytest.mark.asyncio
    async def test_with_resilience_decorator(self):
        """Test comprehensive resilience decorator"""
        call_count = 0

        @with_resilience(
            name="test_service", retry=True, timeout=1.0, bulkhead=True, rate_limit=10.0, fallback="default"
        )
        async def resilient_function():
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise ValueError("Temporary error")

            await asyncio.sleep(0.1)
            return "success"

        # First call should retry and succeed
        result = await resilient_function()
        assert result == "success"
        assert call_count == 2  # 1 failure + 1 success

        # Multiple concurrent calls should be limited by bulkhead
        tasks = [resilient_function() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        assert all(r == "success" for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
