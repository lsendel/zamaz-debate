#!/usr/bin/env python3
"""
Rate Limiting Configuration Management

This module provides configuration management for the API rate limiting system,
including environment-based configuration, dynamic updates, and monitoring.
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Set

from .api_rate_limiting import RateLimitConfig, RateLimitScope, RateLimitAction, EndpointRiskLevel


@dataclass
class GlobalRateLimitSettings:
    """Global rate limiting settings"""
    enabled: bool = True
    log_level: str = "INFO"
    metrics_enabled: bool = True
    cleanup_interval_seconds: int = 300
    store_type: str = "memory"  # memory, redis, database
    max_limiters: int = 10000
    default_ttl_seconds: int = 3600


class RateLimitConfigManager:
    """Manager for rate limiting configuration"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/rate_limits.json"
        self.global_settings = GlobalRateLimitSettings()
        self.endpoint_configs: Dict[str, RateLimitConfig] = {}
        self.load_configuration()
    
    def load_configuration(self):
        """Load configuration from file and environment variables"""
        # Load from file if exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    self._parse_config_data(config_data)
            except Exception as e:
                print(f"Warning: Could not load rate limit config from {self.config_file}: {e}")
        
        # Load from environment variables
        self._load_from_environment()
        
        # Apply default configurations if none loaded
        if not self.endpoint_configs:
            self._apply_default_configurations()
    
    def _parse_config_data(self, config_data: Dict[str, Any]):
        """Parse configuration data from JSON"""
        # Parse global settings
        if "global" in config_data:
            global_data = config_data["global"]
            self.global_settings = GlobalRateLimitSettings(
                enabled=global_data.get("enabled", True),
                log_level=global_data.get("log_level", "INFO"),
                metrics_enabled=global_data.get("metrics_enabled", True),
                cleanup_interval_seconds=global_data.get("cleanup_interval_seconds", 300),
                store_type=global_data.get("store_type", "memory"),
                max_limiters=global_data.get("max_limiters", 10000),
                default_ttl_seconds=global_data.get("default_ttl_seconds", 3600),
            )
        
        # Parse endpoint configurations
        if "endpoints" in config_data:
            for endpoint, config in config_data["endpoints"].items():
                self.endpoint_configs[endpoint] = RateLimitConfig(
                    requests_per_second=config.get("requests_per_second", 10.0),
                    burst_capacity=config.get("burst_capacity", 20),
                    window_seconds=config.get("window_seconds", 60),
                    scope=RateLimitScope(config.get("scope", "ip")),
                    action=RateLimitAction(config.get("action", "reject")),
                    risk_level=EndpointRiskLevel(config.get("risk_level", "medium")),
                    enabled=config.get("enabled", True),
                    bypass_patterns=set(config.get("bypass_patterns", [])),
                    custom_headers=config.get("custom_headers", {}),
                )
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Global settings
        self.global_settings.enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.global_settings.log_level = os.getenv("RATE_LIMIT_LOG_LEVEL", "INFO")
        self.global_settings.metrics_enabled = os.getenv("RATE_LIMIT_METRICS_ENABLED", "true").lower() == "true"
        
        # Default rate limits
        default_rps = float(os.getenv("RATE_LIMIT_DEFAULT_RPS", "10.0"))
        default_burst = int(os.getenv("RATE_LIMIT_DEFAULT_BURST", "20"))
        default_window = int(os.getenv("RATE_LIMIT_DEFAULT_WINDOW", "60"))
        
        # Apply to all endpoints if not specifically configured
        if not self.endpoint_configs:
            self.endpoint_configs["default"] = RateLimitConfig(
                requests_per_second=default_rps,
                burst_capacity=default_burst,
                window_seconds=default_window,
            )
    
    def _apply_default_configurations(self):
        """Apply default rate limiting configurations"""
        # Production-ready defaults based on endpoint risk levels
        
        # Critical endpoints (very restrictive)
        critical_config = RateLimitConfig(
            requests_per_second=1.0,
            burst_capacity=3,
            window_seconds=60,
            risk_level=EndpointRiskLevel.CRITICAL,
            action=RateLimitAction.REJECT,
        )
        
        # High-risk endpoints (resource intensive)
        high_risk_config = RateLimitConfig(
            requests_per_second=3.0,
            burst_capacity=10,
            window_seconds=60,
            risk_level=EndpointRiskLevel.HIGH,
            action=RateLimitAction.REJECT,
        )
        
        # Medium-risk endpoints (regular operations)
        medium_risk_config = RateLimitConfig(
            requests_per_second=15.0,
            burst_capacity=30,
            window_seconds=60,
            risk_level=EndpointRiskLevel.MEDIUM,
            action=RateLimitAction.REJECT,
        )
        
        # Low-risk endpoints (read operations)
        low_risk_config = RateLimitConfig(
            requests_per_second=100.0,
            burst_capacity=200,
            window_seconds=60,
            risk_level=EndpointRiskLevel.LOW,
            action=RateLimitAction.THROTTLE,
        )
        
        # Apply configurations to specific endpoints
        self.endpoint_configs.update({
            # Critical endpoints
            "POST /evolve": critical_config,
            
            # High-risk endpoints
            "POST /decide": high_risk_config,
            "POST /review-pr": high_risk_config,
            "POST /webhooks/retry-failed": high_risk_config,
            "POST /webhooks/endpoints/*/test": high_risk_config,
            "POST /errors/resilience/reset/*": high_risk_config,
            
            # Medium-risk endpoints
            "POST /webhooks/endpoints": medium_risk_config,
            "PUT /webhooks/endpoints/*": medium_risk_config,
            "DELETE /webhooks/endpoints/*": medium_risk_config,
            
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
        })
    
    def get_endpoint_config(self, endpoint: str) -> Optional[RateLimitConfig]:
        """Get configuration for a specific endpoint"""
        return self.endpoint_configs.get(endpoint)
    
    def get_all_configs(self) -> Dict[str, RateLimitConfig]:
        """Get all endpoint configurations"""
        return self.endpoint_configs.copy()
    
    def update_endpoint_config(self, endpoint: str, config: RateLimitConfig) -> bool:
        """Update configuration for an endpoint"""
        try:
            self.endpoint_configs[endpoint] = config
            self.save_configuration()
            return True
        except Exception as e:
            print(f"Error updating endpoint config: {e}")
            return False
    
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            # Ensure config directory exists
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare configuration data
            config_data = {
                "global": asdict(self.global_settings),
                "endpoints": {}
            }
            
            # Convert endpoint configs to JSON-serializable format
            for endpoint, config in self.endpoint_configs.items():
                config_data["endpoints"][endpoint] = {
                    "requests_per_second": config.requests_per_second,
                    "burst_capacity": config.burst_capacity,
                    "window_seconds": config.window_seconds,
                    "scope": config.scope.value,
                    "action": config.action.value,
                    "risk_level": config.risk_level.value,
                    "enabled": config.enabled,
                    "bypass_patterns": list(config.bypass_patterns),
                    "custom_headers": config.custom_headers,
                }
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def reload_configuration(self):
        """Reload configuration from file"""
        self.load_configuration()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for monitoring"""
        return {
            "global_settings": asdict(self.global_settings),
            "endpoint_count": len(self.endpoint_configs),
            "enabled_endpoints": sum(1 for c in self.endpoint_configs.values() if c.enabled),
            "risk_levels": {
                level.value: sum(1 for c in self.endpoint_configs.values() if c.risk_level == level)
                for level in EndpointRiskLevel
            },
            "actions": {
                action.value: sum(1 for c in self.endpoint_configs.values() if c.action == action)
                for action in RateLimitAction
            },
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration"""
        issues = []
        warnings = []
        
        # Check global settings
        if not self.global_settings.enabled:
            warnings.append("Rate limiting is globally disabled")
        
        if self.global_settings.max_limiters < 1000:
            warnings.append("Max limiters setting is quite low")
        
        # Check endpoint configurations
        for endpoint, config in self.endpoint_configs.items():
            if config.requests_per_second <= 0:
                issues.append(f"Invalid requests_per_second for {endpoint}: {config.requests_per_second}")
            
            if config.burst_capacity <= 0:
                issues.append(f"Invalid burst_capacity for {endpoint}: {config.burst_capacity}")
            
            if config.window_seconds <= 0:
                issues.append(f"Invalid window_seconds for {endpoint}: {config.window_seconds}")
            
            if config.requests_per_second > 1000:
                warnings.append(f"Very high rate limit for {endpoint}: {config.requests_per_second}/sec")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }


# Global configuration manager instance
config_manager = RateLimitConfigManager()


def get_rate_limit_config() -> RateLimitConfigManager:
    """Get the global rate limit configuration manager"""
    return config_manager


def create_default_config_file(file_path: str = "config/rate_limits.json"):
    """Create a default configuration file"""
    default_config = {
        "global": {
            "enabled": True,
            "log_level": "INFO",
            "metrics_enabled": True,
            "cleanup_interval_seconds": 300,
            "store_type": "memory",
            "max_limiters": 10000,
            "default_ttl_seconds": 3600
        },
        "endpoints": {
            "POST /decide": {
                "requests_per_second": 3.0,
                "burst_capacity": 10,
                "window_seconds": 60,
                "scope": "ip",
                "action": "reject",
                "risk_level": "high",
                "enabled": True,
                "bypass_patterns": [],
                "custom_headers": {}
            },
            "POST /evolve": {
                "requests_per_second": 1.0,
                "burst_capacity": 3,
                "window_seconds": 60,
                "scope": "ip",
                "action": "reject",
                "risk_level": "critical",
                "enabled": True,
                "bypass_patterns": [],
                "custom_headers": {}
            },
            "GET /stats": {
                "requests_per_second": 100.0,
                "burst_capacity": 200,
                "window_seconds": 60,
                "scope": "ip",
                "action": "throttle",
                "risk_level": "low",
                "enabled": True,
                "bypass_patterns": [],
                "custom_headers": {}
            }
        }
    }
    
    # Ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save default configuration
    with open(file_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    return file_path