#!/usr/bin/env python3
"""
Comprehensive Error Handling and Recovery System for Zamaz Debate System
Provides error classification, recovery strategies, and resilience patterns
"""

import asyncio
import functools
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

# Monitoring imports will be injected at runtime to avoid circular imports
counter = lambda *args, **kwargs: None
gauge = lambda *args, **kwargs: None
histogram = lambda *args, **kwargs: None
health_check = lambda *args, **kwargs: None


# Mock traced context manager
class MockTraced:
    def __init__(self, operation):
        self.operation = operation
        self.tags = {}
        self.logs = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def log(self, message, level="info", **kwargs):
        self.logs.append({"message": message, "level": level, **kwargs})


traced = MockTraced

# This will be set by the application during initialization
_monitoring_enabled = False


def set_monitoring_functions(counter_func, gauge_func, histogram_func, traced_func, health_check_func):
    """Set monitoring functions to avoid circular imports"""
    global counter, gauge, histogram, traced, health_check, _monitoring_enabled
    counter = counter_func
    gauge = gauge_func
    histogram = histogram_func
    traced = traced_func
    health_check = health_check_func
    _monitoring_enabled = True


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"  # Recoverable, minimal impact
    MEDIUM = "medium"  # Recoverable, moderate impact
    HIGH = "high"  # Critical, requires intervention
    CRITICAL = "critical"  # System failure, immediate action needed


class ErrorCategory(Enum):
    """Error categories for classification"""

    AI_CLIENT = "ai_client"  # AI service errors (Claude/Gemini)
    NETWORK = "network"  # Network connectivity issues
    VALIDATION = "validation"  # Input validation errors
    BUSINESS_LOGIC = "business_logic"  # Application logic errors
    RESOURCE = "resource"  # Resource exhaustion (memory, disk)
    CONFIGURATION = "configuration"  # Configuration/setup errors
    AUTHENTICATION = "authentication"  # Auth/permission errors
    RATE_LIMIT = "rate_limit"  # API rate limiting
    TIMEOUT = "timeout"  # Operation timeouts
    UNKNOWN = "unknown"  # Unclassified errors


@dataclass
class ErrorContext:
    """Context information for error handling"""

    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    recovery_attempted: bool = False


@dataclass
class RecoveryStrategy:
    """Recovery strategy for error handling"""

    name: str
    can_recover: Callable[[ErrorContext], bool]
    recover: Callable[[ErrorContext], Any]
    max_retries: int = 3
    backoff_base: float = 2.0
    max_backoff: float = 60.0


class ErrorClassifier:
    """Classifies errors into categories and severities"""

    def __init__(self):
        self.patterns = self._init_patterns()

    def _init_patterns(
        self,
    ) -> Dict[Type[Exception], tuple[ErrorCategory, ErrorSeverity]]:
        """Initialize error classification patterns"""
        return {
            # Network errors
            ConnectionError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            TimeoutError: (ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM),
            # Validation errors
            ValueError: (ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            TypeError: (ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            # Resource errors
            MemoryError: (ErrorCategory.RESOURCE, ErrorSeverity.CRITICAL),
            OSError: (ErrorCategory.RESOURCE, ErrorSeverity.HIGH),
            # Auth errors
            PermissionError: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH),
            # Generic errors
            RuntimeError: (ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.MEDIUM),
            Exception: (ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM),
        }

    def classify(self, error: Exception, context: Dict[str, Any] = None) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify an error into category and severity"""
        error_type = type(error)

        # Check exact type match first (but don't return for base Exception)
        if error_type in self.patterns and error_type != Exception:
            return self.patterns[error_type]

        # Check error message patterns before inheritance for base Exception
        error_msg = str(error).lower()

        # Rate limit errors (check first as they often contain "api")
        if "rate" in error_msg and "limit" in error_msg:
            return ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM

        # AI client errors
        if "api" in error_msg or "claude" in error_msg or "gemini" in error_msg:
            return ErrorCategory.AI_CLIENT, ErrorSeverity.MEDIUM

        # Network errors
        if any(word in error_msg for word in ["connection", "network", "socket"]):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM

        # Timeout errors
        if "timeout" in error_msg:
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM

        # Configuration errors
        if any(word in error_msg for word in ["config", "setting", "environment"]):
            return ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH

        # Check inheritance
        for pattern_type, classification in self.patterns.items():
            if isinstance(error, pattern_type):
                return classification

        # Default classification
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM


class RecoveryManager:
    """Manages error recovery strategies"""

    def __init__(self):
        self.strategies: Dict[ErrorCategory, List[RecoveryStrategy]] = {}
        self._init_strategies()

    def _init_strategies(self):
        """Initialize default recovery strategies"""
        # AI Client recovery strategies
        self.add_strategy(
            ErrorCategory.AI_CLIENT,
            RecoveryStrategy(
                name="ai_client_retry",
                can_recover=lambda ctx: ctx.retry_count < 3,
                recover=self._retry_with_backoff,
                max_retries=3,
            ),
        )

        self.add_strategy(
            ErrorCategory.AI_CLIENT,
            RecoveryStrategy(
                name="ai_client_fallback",
                can_recover=lambda ctx: ctx.retry_count >= 3,
                recover=self._fallback_to_mock,
                max_retries=1,
            ),
        )

        # Network recovery strategies
        self.add_strategy(
            ErrorCategory.NETWORK,
            RecoveryStrategy(
                name="network_retry",
                can_recover=lambda ctx: ctx.retry_count < 5,
                recover=self._retry_with_backoff,
                max_retries=5,
                backoff_base=3.0,
            ),
        )

        # Rate limit recovery
        self.add_strategy(
            ErrorCategory.RATE_LIMIT,
            RecoveryStrategy(
                name="rate_limit_backoff",
                can_recover=lambda ctx: True,
                recover=self._handle_rate_limit,
                max_retries=10,
                backoff_base=5.0,
                max_backoff=300.0,
            ),
        )

        # Timeout recovery
        self.add_strategy(
            ErrorCategory.TIMEOUT,
            RecoveryStrategy(
                name="timeout_retry",
                can_recover=lambda ctx: ctx.retry_count < 2,
                recover=self._retry_with_increased_timeout,
                max_retries=2,
            ),
        )

    def add_strategy(self, category: ErrorCategory, strategy: RecoveryStrategy):
        """Add a recovery strategy for a category"""
        if category not in self.strategies:
            self.strategies[category] = []
        self.strategies[category].append(strategy)

    def get_strategies(self, category: ErrorCategory) -> List[RecoveryStrategy]:
        """Get recovery strategies for a category"""
        return self.strategies.get(category, [])

    async def _retry_with_backoff(self, context: ErrorContext) -> Any:
        """Retry operation with exponential backoff"""
        backoff = min(
            context.metadata.get("backoff_base", 2.0) ** context.retry_count,
            context.metadata.get("max_backoff", 60.0),
        )

        await asyncio.sleep(backoff)

        # Re-execute the original operation
        if "operation_func" in context.metadata:
            return await context.metadata["operation_func"]()

        raise context.error

    async def _fallback_to_mock(self, context: ErrorContext) -> Any:
        """Fallback to mock response for AI clients"""
        counter("error_recovery.ai_fallback_to_mock")

        return {
            "response": "Mock response due to AI service error",
            "error": str(context.error),
            "fallback": True,
        }

    async def _handle_rate_limit(self, context: ErrorContext) -> Any:
        """Handle rate limit errors with smart backoff"""
        # Extract wait time from error if available
        wait_time = context.metadata.get("retry_after", 60)

        counter("error_recovery.rate_limit_wait")
        gauge("error_recovery.rate_limit_wait_time", wait_time)

        await asyncio.sleep(wait_time)

        # Re-execute the original operation
        if "operation_func" in context.metadata:
            return await context.metadata["operation_func"]()

        raise context.error

    async def _retry_with_increased_timeout(self, context: ErrorContext) -> Any:
        """Retry with increased timeout"""
        # Increase timeout by 50%
        new_timeout = context.metadata.get("timeout", 30) * 1.5
        context.metadata["timeout"] = new_timeout

        counter("error_recovery.timeout_retry")

        if "operation_func" in context.metadata:
            return await context.metadata["operation_func"](timeout=new_timeout)

        raise context.error


class ErrorHandler:
    """Main error handler for the system"""

    def __init__(self):
        self.classifier = ErrorClassifier()
        self.recovery_manager = RecoveryManager()
        self.logger = logging.getLogger(__name__)
        self.error_history: List[ErrorContext] = []
        self.max_history = 1000

    async def handle_error(
        self,
        error: Exception,
        component: str,
        operation: str,
        context: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Handle an error with classification and recovery"""
        with traced("error_handler.handle_error") as span:
            # Classify error
            category, severity = self.classifier.classify(error, context)

            # Create error context
            error_context = ErrorContext(
                error=error,
                category=category,
                severity=severity,
                component=component,
                operation=operation,
                user_id=user_id,
                correlation_id=correlation_id,
                metadata=context or {},
            )

            # Record metrics
            counter("errors.total")
            counter("errors.by_category", tags={"category": category.value})
            counter("errors.by_severity", tags={"severity": severity.value})
            counter("errors.by_component", tags={"component": component})

            span.tags["error_category"] = category.value
            span.tags["error_severity"] = severity.value
            span.log(f"Error: {str(error)}", level="error")

            # Log error
            self._log_error(error_context)

            # Store in history
            self._store_error(error_context)

            # Update health status
            self._update_health(error_context)

            # Attempt recovery
            if severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]:
                recovery_result = await self._attempt_recovery(error_context)
                if recovery_result is not None:
                    counter("errors.recovered")
                    return recovery_result

            # Re-raise if critical or recovery failed
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                counter("errors.critical")
                raise error

            return None

    async def _attempt_recovery(self, context: ErrorContext) -> Optional[Any]:
        """Attempt to recover from an error"""
        strategies = self.recovery_manager.get_strategies(context.category)

        for strategy in strategies:
            if strategy.can_recover(context):
                try:
                    counter("error_recovery.attempts")
                    counter(f"error_recovery.{strategy.name}.attempts")

                    result = await strategy.recover(context)

                    counter("error_recovery.success")
                    counter(f"error_recovery.{strategy.name}.success")

                    context.recovery_attempted = True
                    return result

                except Exception as recovery_error:
                    counter("error_recovery.failures")
                    counter(f"error_recovery.{strategy.name}.failures")

                    self.logger.error(f"Recovery strategy {strategy.name} failed: {recovery_error}")

                    # Update retry count
                    context.retry_count += 1

        return None

    def _log_error(self, context: ErrorContext):
        """Log error with appropriate level"""
        log_message = (
            f"Error in {context.component}.{context.operation}: " f"{context.category.value} - {str(context.error)}"
        )

        if context.correlation_id:
            log_message += f" [correlation_id: {context.correlation_id}]"

        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif context.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

        # Log stack trace for high severity errors
        if context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(traceback.format_exc())

    def _store_error(self, context: ErrorContext):
        """Store error in history"""
        self.error_history.append(context)

        # Trim history if too large
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history :]

    def _update_health(self, context: ErrorContext):
        """Update health status based on error"""
        if context.severity == ErrorSeverity.CRITICAL:
            health_check(
                context.component,
                "unhealthy",
                f"Critical error: {context.category.value}",
                {"error": str(context.error)},
            )
        elif context.severity == ErrorSeverity.HIGH:
            health_check(
                context.component,
                "degraded",
                f"High severity error: {context.category.value}",
                {"error": str(context.error)},
            )

    def get_error_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get error summary for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff_time]

        summary = {
            "total_errors": len(recent_errors),
            "by_category": {},
            "by_severity": {},
            "by_component": {},
            "recovery_rate": 0.0,
            "critical_errors": [],
        }

        if not recent_errors:
            return summary

        # Count by category
        for error in recent_errors:
            cat = error.category.value
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

            sev = error.severity.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1

            comp = error.component
            summary["by_component"][comp] = summary["by_component"].get(comp, 0) + 1

            if error.severity == ErrorSeverity.CRITICAL:
                summary["critical_errors"].append(
                    {
                        "timestamp": error.timestamp.isoformat(),
                        "component": error.component,
                        "operation": error.operation,
                        "error": str(error.error),
                    }
                )

        # Calculate recovery rate
        recovered = sum(1 for e in recent_errors if e.recovery_attempted)
        if recent_errors:
            summary["recovery_rate"] = recovered / len(recent_errors)

        return summary


# Global error handler instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# Decorator for automatic error handling
def with_error_handling(component: str, operation: str = None, reraise: bool = True, fallback: Any = None):
    """Decorator for automatic error handling"""

    def decorator(func):
        op_name = operation or func.__name__

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    handler = get_error_handler()

                    # Add operation function to context for recovery
                    context = {
                        "operation_func": lambda: func(*args, **kwargs),
                        "args": args,
                        "kwargs": kwargs,
                    }

                    result = await handler.handle_error(
                        error=e, component=component, operation=op_name, context=context
                    )

                    if result is not None:
                        return result

                    if reraise:
                        raise

                    return fallback

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    handler = get_error_handler()

                    # Run async handler in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    try:
                        context = {
                            "operation_func": lambda: func(*args, **kwargs),
                            "args": args,
                            "kwargs": kwargs,
                        }

                        result = loop.run_until_complete(
                            handler.handle_error(
                                error=e,
                                component=component,
                                operation=op_name,
                                context=context,
                            )
                        )

                        if result is not None:
                            return result

                        if reraise:
                            raise

                        return fallback

                    finally:
                        loop.close()

            return sync_wrapper

    return decorator


# Circuit breaker pattern
class CircuitBreaker:
    """Circuit breaker for preventing cascading failures"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection"""
        if self._state == "open":
            if self._should_attempt_reset():
                self._state = "half-open"
            else:
                counter(f"circuit_breaker.{self.name}.rejected")
                raise Exception(f"Circuit breaker {self.name} is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        return self._last_failure_time and time.time() - self._last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        self._failure_count = 0
        self._state = "closed"
        counter(f"circuit_breaker.{self.name}.success")

    def _on_failure(self):
        """Handle failed call"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        counter(f"circuit_breaker.{self.name}.failure")

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            counter(f"circuit_breaker.{self.name}.opened")
            gauge(f"circuit_breaker.{self.name}.state", 0)  # 0 = open

        elif self._state == "half-open":
            self._state = "open"
            gauge(f"circuit_breaker.{self.name}.state", 0)
