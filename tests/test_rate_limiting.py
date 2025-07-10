#!/usr/bin/env python3
"""
Tests for API Rate Limiting System

This module contains comprehensive tests for the rate limiting system,
including middleware, configuration, and integration tests.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from src.core.api_rate_limiting import (
    APIRateLimitMiddleware,
    RateLimitConfig,
    RateLimitScope,
    RateLimitAction,
    EndpointRiskLevel,
    RateLimitStore,
    RateLimitManager,
    create_rate_limit_middleware,
)
from src.core.rate_limit_config import RateLimitConfigManager, create_default_config_file
from src.core.resilience import RateLimiter


class TestRateLimitConfig:
    """Test rate limit configuration"""
    
    def test_config_defaults(self):
        """Test default configuration values"""
        config = RateLimitConfig()
        
        assert config.requests_per_second == 10.0
        assert config.burst_capacity == 20
        assert config.window_seconds == 60
        assert config.scope == RateLimitScope.IP
        assert config.action == RateLimitAction.REJECT
        assert config.risk_level == EndpointRiskLevel.MEDIUM
        assert config.enabled is True
        assert config.bypass_patterns == set()
        assert config.custom_headers == {}
    
    def test_config_custom_values(self):
        """Test configuration with custom values"""
        config = RateLimitConfig(
            requests_per_second=5.0,
            burst_capacity=10,
            window_seconds=30,
            scope=RateLimitScope.API_KEY,
            action=RateLimitAction.THROTTLE,
            risk_level=EndpointRiskLevel.HIGH,
            enabled=False,
            bypass_patterns={"health", "internal"},
            custom_headers={"X-Custom": "value"},
        )
        
        assert config.requests_per_second == 5.0
        assert config.burst_capacity == 10
        assert config.window_seconds == 30
        assert config.scope == RateLimitScope.API_KEY
        assert config.action == RateLimitAction.THROTTLE
        assert config.risk_level == EndpointRiskLevel.HIGH
        assert config.enabled is False
        assert config.bypass_patterns == {"health", "internal"}
        assert config.custom_headers == {"X-Custom": "value"}


class TestRateLimitStore:
    """Test rate limit store"""
    
    @pytest.fixture
    def store(self):
        return RateLimitStore()
    
    @pytest.fixture
    def config(self):
        return RateLimitConfig(requests_per_second=10.0, burst_capacity=20)
    
    @pytest.mark.asyncio
    async def test_get_limiter_creates_new(self, store, config):
        """Test that get_limiter creates a new limiter"""
        limiter = await store.get_limiter("test_key", config)
        
        assert limiter is not None
        assert limiter.name == "test_key"
        assert limiter.rate == 10.0
        assert limiter.capacity == 20
    
    @pytest.mark.asyncio
    async def test_get_limiter_returns_existing(self, store, config):
        """Test that get_limiter returns existing limiter"""
        limiter1 = await store.get_limiter("test_key", config)
        limiter2 = await store.get_limiter("test_key", config)
        
        assert limiter1 is limiter2
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, store):
        """Test statistics tracking"""
        await store.increment_stat("test_key", "requests", 5)
        await store.increment_stat("test_key", "errors", 1)
        
        stats = await store.get_stats("test_key")
        assert stats["requests"] == 5
        assert stats["errors"] == 1
    
    @pytest.mark.asyncio
    async def test_stats_default_empty(self, store):
        """Test that stats default to empty dict"""
        stats = await store.get_stats("nonexistent_key")
        assert stats == {}


class TestRateLimitManager:
    """Test rate limit manager"""
    
    @pytest.fixture
    def manager(self):
        return RateLimitManager()
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_stats(self, manager):
        """Test getting rate limit statistics"""
        stats = await manager.get_rate_limit_stats()
        
        assert "total_limiters" in stats
        assert "client_stats" in stats
        assert isinstance(stats["total_limiters"], int)
        assert isinstance(stats["client_stats"], dict)
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, manager):
        """Test resetting rate limits"""
        # First add a limiter
        config = RateLimitConfig()
        await manager.store.get_limiter("test_client:test_endpoint", config)
        
        # Reset it
        success = await manager.reset_rate_limit("test_client", "test_endpoint")
        assert success is True
        
        # Check it's gone
        assert "test_client:test_endpoint" not in manager.store._limiters
    
    @pytest.mark.asyncio
    async def test_reset_all_client_limits(self, manager):
        """Test resetting all limits for a client"""
        # Add multiple limiters for the same client
        config = RateLimitConfig()
        await manager.store.get_limiter("test_client:endpoint1", config)
        await manager.store.get_limiter("test_client:endpoint2", config)
        await manager.store.get_limiter("other_client:endpoint1", config)
        
        # Reset all for test_client
        success = await manager.reset_rate_limit("test_client")
        assert success is True
        
        # Check only test_client limiters are gone
        assert "test_client:endpoint1" not in manager.store._limiters
        assert "test_client:endpoint2" not in manager.store._limiters
        assert "other_client:endpoint1" in manager.store._limiters


class TestAPIRateLimitMiddleware:
    """Test API rate limiting middleware"""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.post("/slow")
        async def slow_endpoint():
            await asyncio.sleep(0.1)
            return {"message": "slow"}
        
        return app
    
    @pytest.fixture
    def middleware(self):
        config = RateLimitConfig(
            requests_per_second=10.0,
            burst_capacity=20,
            window_seconds=60,
        )
        return APIRateLimitMiddleware(
            app=None,
            default_config=config,
            endpoint_configs={"GET /test": config},
        )
    
    def test_get_client_identifier_with_api_key(self, middleware):
        """Test client identification with API key"""
        request = Mock(spec=Request)
        request.headers = {"x-api-key": "test-api-key-123"}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        client_id = middleware._get_client_identifier(request)
        assert client_id == "api_key:test-api-ke"  # Truncated for privacy
    
    def test_get_client_identifier_with_ip(self, middleware):
        """Test client identification with IP address"""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        client_id = middleware._get_client_identifier(request)
        assert client_id == "ip:192.168.1.100"
    
    def test_get_endpoint_key_exact_match(self, middleware):
        """Test endpoint key generation with exact match"""
        key = middleware._get_endpoint_key("GET", "/test")
        assert key == "GET /test"
    
    def test_get_endpoint_key_wildcard_match(self, middleware):
        """Test endpoint key generation with wildcard match"""
        middleware.endpoint_configs["GET /users/*"] = RateLimitConfig()
        key = middleware._get_endpoint_key("GET", "/users/123")
        assert key == "GET /users/*"
    
    def test_should_bypass_rate_limit_disabled(self, middleware):
        """Test bypass when rate limiting is disabled"""
        config = RateLimitConfig(enabled=False)
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/test"
        
        should_bypass = middleware._should_bypass_rate_limit(request, config)
        assert should_bypass is True
    
    def test_should_bypass_rate_limit_pattern(self, middleware):
        """Test bypass with pattern matching"""
        config = RateLimitConfig(bypass_patterns={"health"})
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/health/check"
        
        should_bypass = middleware._should_bypass_rate_limit(request, config)
        assert should_bypass is True
    
    def test_should_bypass_rate_limit_internal(self, middleware):
        """Test bypass for internal endpoints"""
        config = RateLimitConfig()
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/internal/status"
        
        should_bypass = middleware._should_bypass_rate_limit(request, config)
        assert should_bypass is True
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, middleware):
        """Test rate limit check when allowed"""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        config = RateLimitConfig(requests_per_second=10.0, burst_capacity=20)
        
        result = await middleware._check_rate_limit(request, config)
        
        assert result.allowed is True
        assert result.remaining >= 0
        assert result.reset_time is not None
        assert result.retry_after is None
        assert result.message is None
        assert "X-RateLimit-Limit" in result.headers
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_rejected(self, middleware):
        """Test rate limit check when rejected"""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        config = RateLimitConfig(requests_per_second=0.1, burst_capacity=1)
        
        # First request should be allowed
        result1 = await middleware._check_rate_limit(request, config)
        assert result1.allowed is True
        
        # Second request should be rejected
        result2 = await middleware._check_rate_limit(request, config)
        assert result2.allowed is False
        assert result2.retry_after is not None
        assert result2.message is not None
        assert "Retry-After" in result2.headers
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_exceeded_reject(self, middleware):
        """Test handling rate limit exceeded with reject action"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        config = RateLimitConfig(action=RateLimitAction.REJECT)
        result = Mock()
        result.message = "Rate limit exceeded"
        result.retry_after = 10
        result.remaining = 0
        result.reset_time = Mock()
        result.reset_time.isoformat.return_value = "2023-01-01T00:00:00"
        result.headers = {"X-RateLimit-Limit": "10"}
        
        response = await middleware._handle_rate_limit_exceeded(request, config, result)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_exceeded_throttle(self, middleware):
        """Test handling rate limit exceeded with throttle action"""
        request = Mock(spec=Request)
        
        config = RateLimitConfig(action=RateLimitAction.THROTTLE)
        result = Mock()
        result.retry_after = 0.1  # Small delay for testing
        
        with patch('asyncio.sleep') as mock_sleep:
            response = await middleware._handle_rate_limit_exceeded(request, config, result)
            
            assert response is None  # Should continue processing
            mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_exceeded_warn(self, middleware):
        """Test handling rate limit exceeded with warn action"""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        config = RateLimitConfig(action=RateLimitAction.WARN)
        result = Mock()
        
        with patch.object(middleware.logger, 'warning') as mock_warning:
            response = await middleware._handle_rate_limit_exceeded(request, config, result)
            
            assert response is None  # Should continue processing
            mock_warning.assert_called_once()


class TestRateLimitConfigManager:
    """Test rate limit configuration manager"""
    
    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create a temporary config file"""
        config_file = tmp_path / "test_rate_limits.json"
        config_data = {
            "global": {
                "enabled": True,
                "log_level": "DEBUG",
                "metrics_enabled": True,
            },
            "endpoints": {
                "GET /test": {
                    "requests_per_second": 5.0,
                    "burst_capacity": 10,
                    "window_seconds": 60,
                    "scope": "ip",
                    "action": "reject",
                    "risk_level": "medium",
                    "enabled": True,
                    "bypass_patterns": [],
                    "custom_headers": {},
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        return str(config_file)
    
    def test_load_configuration_from_file(self, temp_config_file):
        """Test loading configuration from file"""
        manager = RateLimitConfigManager(temp_config_file)
        
        assert manager.global_settings.enabled is True
        assert manager.global_settings.log_level == "DEBUG"
        assert "GET /test" in manager.endpoint_configs
        
        config = manager.endpoint_configs["GET /test"]
        assert config.requests_per_second == 5.0
        assert config.burst_capacity == 10
    
    def test_load_configuration_from_environment(self, monkeypatch):
        """Test loading configuration from environment variables"""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("RATE_LIMIT_LOG_LEVEL", "ERROR")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_RPS", "20.0")
        
        manager = RateLimitConfigManager("nonexistent_file.json")
        
        assert manager.global_settings.enabled is False
        assert manager.global_settings.log_level == "ERROR"
        # Should have default config with env values
        assert "default" in manager.endpoint_configs
        assert manager.endpoint_configs["default"].requests_per_second == 20.0
    
    def test_get_endpoint_config(self, temp_config_file):
        """Test getting endpoint configuration"""
        manager = RateLimitConfigManager(temp_config_file)
        
        config = manager.get_endpoint_config("GET /test")
        assert config is not None
        assert config.requests_per_second == 5.0
        
        config = manager.get_endpoint_config("GET /nonexistent")
        assert config is None
    
    def test_update_endpoint_config(self, temp_config_file):
        """Test updating endpoint configuration"""
        manager = RateLimitConfigManager(temp_config_file)
        
        new_config = RateLimitConfig(requests_per_second=15.0)
        success = manager.update_endpoint_config("GET /test", new_config)
        
        assert success is True
        assert manager.endpoint_configs["GET /test"].requests_per_second == 15.0
    
    def test_validate_configuration_valid(self, temp_config_file):
        """Test configuration validation with valid config"""
        manager = RateLimitConfigManager(temp_config_file)
        
        validation = manager.validate_configuration()
        
        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
    
    def test_validate_configuration_invalid(self):
        """Test configuration validation with invalid config"""
        manager = RateLimitConfigManager("nonexistent_file.json")
        manager.endpoint_configs["invalid"] = RateLimitConfig(requests_per_second=-1.0)
        
        validation = manager.validate_configuration()
        
        assert validation["valid"] is False
        assert len(validation["issues"]) > 0
        assert "Invalid requests_per_second" in validation["issues"][0]
    
    def test_get_config_summary(self, temp_config_file):
        """Test getting configuration summary"""
        manager = RateLimitConfigManager(temp_config_file)
        
        summary = manager.get_config_summary()
        
        assert "global_settings" in summary
        assert "endpoint_count" in summary
        assert "enabled_endpoints" in summary
        assert "risk_levels" in summary
        assert "actions" in summary
        assert isinstance(summary["endpoint_count"], int)


class TestIntegration:
    """Integration tests for the rate limiting system"""
    
    @pytest.fixture
    def app_with_rate_limiting(self):
        """Create FastAPI app with rate limiting"""
        app = FastAPI()
        
        # Add rate limiting middleware
        config = RateLimitConfig(
            requests_per_second=2.0,
            burst_capacity=3,
            window_seconds=60,
        )
        
        middleware = APIRateLimitMiddleware(
            app=app,
            default_config=config,
            endpoint_configs={"GET /test": config},
        )
        
        app.add_middleware(type(middleware), **middleware.__dict__)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.get("/unlimited")
        async def unlimited_endpoint():
            return {"message": "unlimited"}
        
        return app
    
    def test_rate_limiting_blocks_excess_requests(self, app_with_rate_limiting):
        """Test that rate limiting blocks excess requests"""
        client = TestClient(app_with_rate_limiting)
        
        # First few requests should succeed
        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
        
        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
        assert "Retry-After" in response.headers
    
    def test_rate_limiting_headers_present(self, app_with_rate_limiting):
        """Test that rate limiting headers are present"""
        client = TestClient(app_with_rate_limiting)
        
        response = client.get("/test")
        assert response.status_code == 200
        
        # Check required headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "X-RateLimit-Window" in response.headers
    
    def test_rate_limiting_per_client(self, app_with_rate_limiting):
        """Test that rate limiting is per-client"""
        client1 = TestClient(app_with_rate_limiting)
        client2 = TestClient(app_with_rate_limiting)
        
        # Each client should have its own rate limit
        # This test is limited by the TestClient architecture
        # but demonstrates the concept
        
        response1 = client1.get("/test")
        assert response1.status_code == 200
        
        response2 = client2.get("/test")
        assert response2.status_code == 200


def test_create_default_config_file(tmp_path):
    """Test creating default configuration file"""
    config_file = tmp_path / "test_config.json"
    
    created_file = create_default_config_file(str(config_file))
    
    assert created_file == str(config_file)
    assert config_file.exists()
    
    # Verify content
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    assert "global" in config_data
    assert "endpoints" in config_data
    assert config_data["global"]["enabled"] is True
    assert "POST /decide" in config_data["endpoints"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])