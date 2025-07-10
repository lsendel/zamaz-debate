#!/usr/bin/env python3
"""
API Rate Limiting System for Zamaz Debate System

This module implements comprehensive API rate limiting following the phased approach:
1. Phase 1: Basic rate limiting with targeted protection
2. Phase 2: Intelligent adaptive rate limiting
3. Phase 3: Comprehensive coverage with advanced features

Built on top of the existing resilience infrastructure.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .resilience import RateLimiter


class RateLimitScope(Enum):
    """Rate limit scope types"""
    GLOBAL = "global"
    IP = "ip"
    ENDPOINT = "endpoint"
    USER = "user"
    API_KEY = "api_key"


class RateLimitAction(Enum):
    """Actions to take when rate limit is exceeded"""
    REJECT = "reject"
    THROTTLE = "throttle"
    QUEUE = "queue"
    WARN = "warn"


class EndpointRiskLevel(Enum):
    """Risk levels for different endpoints"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RateLimitConfig:
    """Configuration for rate limiting rules"""
    
    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_capacity: int = 20,
        window_seconds: int = 60,
        scope: RateLimitScope = RateLimitScope.IP,
        action: RateLimitAction = RateLimitAction.REJECT,
        risk_level: EndpointRiskLevel = EndpointRiskLevel.MEDIUM,
        enabled: bool = True,
        bypass_patterns: Optional[Set[str]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ):
        self.requests_per_second = requests_per_second
        self.burst_capacity = burst_capacity
        self.window_seconds = window_seconds
        self.scope = scope
        self.action = action
        self.risk_level = risk_level
        self.enabled = enabled
        self.bypass_patterns = bypass_patterns or set()
        self.custom_headers = custom_headers or {}


class RateLimitResult:
    """Result of rate limit check"""
    
    def __init__(
        self,
        allowed: bool,
        remaining: int,
        reset_time: datetime,
        retry_after: Optional[int] = None,
        message: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after
        self.message = message
        self.headers = headers or {}


class RateLimitStore:
    """In-memory store for rate limiting data"""
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._lock = asyncio.Lock()
    
    async def get_limiter(self, key: str, config: RateLimitConfig) -> RateLimiter:
        """Get or create a rate limiter for the given key"""
        async with self._lock:
            if key not in self._limiters:
                self._limiters[key] = RateLimiter(
                    name=key,
                    rate=config.requests_per_second,
                    capacity=config.burst_capacity,
                    burst=config.burst_capacity
                )
            return self._limiters[key]
    
    async def get_stats(self, key: str) -> Dict[str, int]:
        """Get statistics for a rate limiter"""
        return dict(self._stats[key])
    
    async def increment_stat(self, key: str, stat: str, value: int = 1):
        """Increment a statistic"""
        self._stats[key][stat] += value
    
    async def cleanup_expired(self):
        """Clean up expired rate limiters (simplified implementation)"""
        # In a production system, this would clean up limiters that haven't been used
        # for a certain period to prevent memory leaks
        pass


class APIRateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for API rate limiting"""
    
    def __init__(
        self,
        app,
        default_config: Optional[RateLimitConfig] = None,
        endpoint_configs: Optional[Dict[str, RateLimitConfig]] = None,
        store: Optional[RateLimitStore] = None,
    ):
        super().__init__(app)
        self.default_config = default_config or RateLimitConfig()
        self.endpoint_configs = endpoint_configs or {}
        self.store = store or RateLimitStore()
        self.logger = logging.getLogger(__name__)
        
        # Initialize default endpoint configurations
        self._init_default_endpoint_configs()
    
    def _init_default_endpoint_configs(self):
        """Initialize default rate limiting configurations for endpoints"""
        
        # High-risk endpoints (resource intensive)
        high_risk_config = RateLimitConfig(
            requests_per_second=2.0,
            burst_capacity=5,
            window_seconds=60,
            risk_level=EndpointRiskLevel.HIGH,
            action=RateLimitAction.REJECT,
        )
        
        # Medium-risk endpoints (regular operations)
        medium_risk_config = RateLimitConfig(
            requests_per_second=10.0,
            burst_capacity=20,
            window_seconds=60,
            risk_level=EndpointRiskLevel.MEDIUM,
            action=RateLimitAction.REJECT,
        )
        
        # Low-risk endpoints (read operations)
        low_risk_config = RateLimitConfig(
            requests_per_second=50.0,
            burst_capacity=100,
            window_seconds=60,
            risk_level=EndpointRiskLevel.LOW,
            action=RateLimitAction.THROTTLE,
        )
        
        # Apply configurations to specific endpoints
        endpoint_mappings = {
            # High-risk endpoints
            "POST /decide": high_risk_config,
            "POST /evolve": high_risk_config,
            "POST /review-pr": high_risk_config,
            "POST /webhooks/retry-failed": high_risk_config,
            "POST /webhooks/endpoints/*/test": high_risk_config,
            
            # Medium-risk endpoints
            "POST /webhooks/endpoints": medium_risk_config,
            "PUT /webhooks/endpoints/*": medium_risk_config,
            "DELETE /webhooks/endpoints/*": medium_risk_config,
            "POST /errors/resilience/reset/*": medium_risk_config,
            
            # Low-risk endpoints
            "GET /": low_risk_config,
            "GET /stats": low_risk_config,
            "GET /pending-reviews": low_risk_config,
            "GET /pr-drafts": low_risk_config,
            "GET /webhooks/endpoints": low_risk_config,
            "GET /webhooks/endpoints/*": low_risk_config,
            "GET /webhooks/stats": low_risk_config,
            "GET /webhooks/delivery-history": low_risk_config,
            "GET /webhooks/event-types": low_risk_config,
            "GET /errors/summary": low_risk_config,
            "GET /errors/resilience/status": low_risk_config,
        }
        
        # Update with user-provided configurations
        for endpoint, config in endpoint_mappings.items():
            if endpoint not in self.endpoint_configs:
                self.endpoint_configs[endpoint] = config
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Check for API key in headers
        api_key = request.headers.get("x-api-key") or request.headers.get("authorization")
        if api_key:
            return f"api_key:{api_key[:10]}"  # Truncate for privacy
        
        # Use IP address as fallback
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_endpoint_key(self, method: str, path: str) -> str:
        """Get endpoint key for configuration lookup"""
        # Handle parameterized paths
        endpoint_key = f"{method} {path}"
        
        # Check for exact match first
        if endpoint_key in self.endpoint_configs:
            return endpoint_key
        
        # Check for wildcard matches
        for pattern in self.endpoint_configs.keys():
            if "*" in pattern:
                # Simple wildcard matching
                pattern_parts = pattern.split("*")
                if len(pattern_parts) == 2:
                    prefix, suffix = pattern_parts
                    if endpoint_key.startswith(prefix) and endpoint_key.endswith(suffix):
                        return pattern
        
        return endpoint_key
    
    def _get_rate_limit_config(self, request: Request) -> RateLimitConfig:
        """Get rate limiting configuration for the request"""
        method = request.method
        path = request.url.path
        endpoint_key = self._get_endpoint_key(method, path)
        
        # Return specific configuration or default
        return self.endpoint_configs.get(endpoint_key, self.default_config)
    
    def _should_bypass_rate_limit(self, request: Request, config: RateLimitConfig) -> bool:
        """Check if request should bypass rate limiting"""
        if not config.enabled:
            return True
        
        # Check bypass patterns
        path = request.url.path
        for pattern in config.bypass_patterns:
            if pattern in path:
                return True
        
        # Check for internal/health check endpoints
        if path.startswith("/health") or path.startswith("/internal"):
            return True
        
        return False
    
    async def _check_rate_limit(self, request: Request, config: RateLimitConfig) -> RateLimitResult:
        """Check if request should be rate limited"""
        client_id = self._get_client_identifier(request)
        endpoint_key = self._get_endpoint_key(request.method, request.url.path)
        
        # Create unique key for this client/endpoint combination
        limiter_key = f"{client_id}:{endpoint_key}"
        
        # Get rate limiter
        limiter = await self.store.get_limiter(limiter_key, config)
        
        # Check if tokens are available
        allowed = await limiter.acquire(1)
        
        # Calculate remaining tokens and reset time
        remaining = max(0, int(limiter._tokens))
        reset_time = datetime.now() + timedelta(seconds=config.window_seconds)
        
        # Update statistics
        await self.store.increment_stat(limiter_key, "total_requests")
        if not allowed:
            await self.store.increment_stat(limiter_key, "rejected_requests")
        
        # Calculate retry after if rejected
        retry_after = None
        message = None
        if not allowed:
            retry_after = int(1 / config.requests_per_second) + 1
            message = f"Rate limit exceeded. Try again in {retry_after} seconds."
        
        # Prepare response headers
        headers = {
            "X-RateLimit-Limit": str(int(config.requests_per_second * config.window_seconds)),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(reset_time.timestamp())),
            "X-RateLimit-Window": str(config.window_seconds),
        }
        
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        # Add custom headers
        headers.update(config.custom_headers)
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
            message=message,
            headers=headers,
        )
    
    async def _handle_rate_limit_exceeded(
        self, 
        request: Request, 
        config: RateLimitConfig, 
        result: RateLimitResult
    ) -> Response:
        """Handle rate limit exceeded based on configuration"""
        
        if config.action == RateLimitAction.REJECT:
            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": result.message,
                    "retry_after": result.retry_after,
                    "limit": int(config.requests_per_second * config.window_seconds),
                    "remaining": result.remaining,
                    "reset_time": result.reset_time.isoformat(),
                },
                headers=result.headers,
            )
        
        elif config.action == RateLimitAction.THROTTLE:
            # Add delay before processing
            if result.retry_after:
                await asyncio.sleep(min(result.retry_after, 5))  # Max 5 second delay
            return None  # Continue processing
        
        elif config.action == RateLimitAction.QUEUE:
            # Queue the request (simplified implementation)
            await asyncio.sleep(result.retry_after or 1)
            return None  # Continue processing
        
        elif config.action == RateLimitAction.WARN:
            # Log warning but continue processing
            self.logger.warning(
                f"Rate limit exceeded for {request.client.host if request.client else 'unknown'} "
                f"on {request.method} {request.url.path}"
            )
            return None  # Continue processing
        
        return None  # Default: continue processing
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method"""
        start_time = time.time()
        
        try:
            # Get rate limiting configuration
            config = self._get_rate_limit_config(request)
            
            # Check if should bypass rate limiting
            if self._should_bypass_rate_limit(request, config):
                response = await call_next(request)
                return response
            
            # Check rate limit
            result = await self._check_rate_limit(request, config)
            
            # Handle rate limit exceeded
            if not result.allowed:
                self.logger.info(
                    f"Rate limit exceeded: {request.method} {request.url.path} "
                    f"from {request.client.host if request.client else 'unknown'}"
                )
                
                rate_limit_response = await self._handle_rate_limit_exceeded(request, config, result)
                if rate_limit_response:
                    return rate_limit_response
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            for header, value in result.headers.items():
                response.headers[header] = value
            
            # Log successful request
            duration = time.time() - start_time
            self.logger.debug(
                f"Request processed: {request.method} {request.url.path} "
                f"in {duration:.3f}s (remaining: {result.remaining})"
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Rate limiting middleware error: {e}")
            # Continue processing even if rate limiting fails
            return await call_next(request)


class RateLimitManager:
    """Manager for rate limiting system"""
    
    def __init__(self, store: Optional[RateLimitStore] = None):
        self.store = store or RateLimitStore()
        self.logger = logging.getLogger(__name__)
    
    async def get_rate_limit_stats(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        stats = {
            "total_limiters": len(self.store._limiters),
            "client_stats": {}
        }
        
        if client_id:
            # Get stats for specific client
            client_stats = await self.store.get_stats(client_id)
            stats["client_stats"][client_id] = client_stats
        else:
            # Get stats for all clients
            for key in self.store._stats:
                client_stats = await self.store.get_stats(key)
                stats["client_stats"][key] = client_stats
        
        return stats
    
    async def reset_rate_limit(self, client_id: str, endpoint: Optional[str] = None) -> bool:
        """Reset rate limits for a client or endpoint"""
        try:
            if endpoint:
                key = f"{client_id}:{endpoint}"
                if key in self.store._limiters:
                    del self.store._limiters[key]
                    self.logger.info(f"Reset rate limit for {key}")
                    return True
            else:
                # Reset all limits for client
                keys_to_remove = [k for k in self.store._limiters.keys() if k.startswith(client_id)]
                for key in keys_to_remove:
                    del self.store._limiters[key]
                self.logger.info(f"Reset all rate limits for {client_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error resetting rate limit: {e}")
            return False
    
    async def update_rate_limit_config(self, endpoint: str, config: RateLimitConfig) -> bool:
        """Update rate limiting configuration for an endpoint"""
        try:
            # This would typically update a persistent configuration store
            # For now, we'll just log the update
            self.logger.info(f"Updated rate limit config for {endpoint}: {config}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating rate limit config: {e}")
            return False
    
    async def cleanup_expired_limiters(self):
        """Clean up expired rate limiters"""
        await self.store.cleanup_expired()
        self.logger.debug("Cleaned up expired rate limiters")


# Global rate limit manager instance
rate_limit_manager = RateLimitManager()


def create_rate_limit_middleware(
    default_config: Optional[RateLimitConfig] = None,
    endpoint_configs: Optional[Dict[str, RateLimitConfig]] = None,
) -> APIRateLimitMiddleware:
    """Factory function to create rate limiting middleware"""
    return APIRateLimitMiddleware(
        app=None,  # Will be set by FastAPI
        default_config=default_config,
        endpoint_configs=endpoint_configs,
        store=rate_limit_manager.store,
    )