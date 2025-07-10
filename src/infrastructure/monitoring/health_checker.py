"""
Health Checker

Provides health monitoring and status endpoints for the Zamaz Debate System.
Checks the health of all system components including Kafka, event bus, and contexts.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.events import get_event_bus
from src.infrastructure.kafka.event_bridge import KafkaEventBridge
from .config import MonitoringConfig

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealth:
    """Overall system health status"""
    status: HealthStatus
    checks: List[HealthCheck]
    timestamp: datetime
    uptime_seconds: float


class HealthChecker:
    """
    Performs health checks on all system components.
    
    Monitors:
    - Event bus functionality
    - Kafka connectivity and performance
    - System resources
    - Individual bounded contexts
    - Web interface availability
    """
    
    def __init__(
        self,
        config: Optional[MonitoringConfig] = None,
        kafka_bridge: Optional[KafkaEventBridge] = None
    ):
        """
        Initialize health checker.
        
        Args:
            config: Monitoring configuration
            kafka_bridge: Optional Kafka event bridge for connectivity checks
        """
        self.config = config or MonitoringConfig.from_env()
        self.kafka_bridge = kafka_bridge
        self.event_bus = get_event_bus()
        
        self._start_time = time.time()
        self._last_health_check: Optional[SystemHealth] = None
        
        logger.info("Health checker initialized")
    
    async def check_system_health(self) -> SystemHealth:
        """
        Perform comprehensive system health check.
        
        Returns:
            SystemHealth with overall status and individual component checks
        """
        checks = []
        
        # Check all components in parallel
        check_tasks = [
            self._check_event_bus(),
            self._check_system_resources(),
            self._check_web_interface(),
        ]
        
        # Add Kafka check if available
        if self.kafka_bridge and self.config.kafka_monitoring:
            check_tasks.append(self._check_kafka())
        
        # Execute all checks
        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        for result in check_results:
            if isinstance(result, HealthCheck):
                checks.append(result)
            elif isinstance(result, Exception):
                checks.append(HealthCheck(
                    component="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(result)}",
                    timestamp=datetime.now()
                ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        
        # Calculate uptime
        uptime_seconds = time.time() - self._start_time
        
        system_health = SystemHealth(
            status=overall_status,
            checks=checks,
            timestamp=datetime.now(),
            uptime_seconds=uptime_seconds
        )
        
        self._last_health_check = system_health
        return system_health
    
    async def _check_event_bus(self) -> HealthCheck:
        """Check event bus health"""
        start_time = time.time()
        
        try:
            # Test basic event bus functionality
            event_metrics = self.event_bus.get_event_metrics()
            event_history = self.event_bus.get_event_history()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Check if event bus is responsive
            if response_time_ms > 1000:  # > 1 second is concerning
                status = HealthStatus.DEGRADED
                message = f"Event bus responding slowly ({response_time_ms:.1f}ms)"
            else:
                status = HealthStatus.HEALTHY
                message = "Event bus operational"
            
            return HealthCheck(
                component="event_bus",
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time_ms=response_time_ms,
                details={
                    "event_types": len(event_metrics) if isinstance(event_metrics, dict) else 0,
                    "history_size": len(event_history),
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="event_bus",
                status=HealthStatus.UNHEALTHY,
                message=f"Event bus error: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_kafka(self) -> HealthCheck:
        """Check Kafka connectivity and performance"""
        start_time = time.time()
        
        try:
            # Get Kafka metrics
            kafka_metrics = self.kafka_bridge.get_metrics()
            response_time_ms = (time.time() - start_time) * 1000
            
            # Analyze metrics for health
            bridged_types = kafka_metrics.get("bridged_event_types", 0)
            active_consumers = kafka_metrics.get("active_consumers", 0)
            
            if bridged_types > 0 and active_consumers == 0:
                status = HealthStatus.DEGRADED
                message = "Kafka configured but no active consumers"
            elif bridged_types == 0:
                status = HealthStatus.DEGRADED
                message = "No events bridged to Kafka"
            elif response_time_ms > 2000:
                status = HealthStatus.DEGRADED
                message = f"Kafka responding slowly ({response_time_ms:.1f}ms)"
            else:
                status = HealthStatus.HEALTHY
                message = "Kafka operational"
            
            return HealthCheck(
                component="kafka",
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time_ms=response_time_ms,
                details=kafka_metrics
            )
            
        except Exception as e:
            return HealthCheck(
                component="kafka",
                status=HealthStatus.UNHEALTHY,
                message=f"Kafka error: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource health"""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Determine status based on thresholds
            issues = []
            
            if cpu_percent > self.config.alerting.high_cpu_threshold:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory.percent > self.config.alerting.high_memory_threshold:
                issues.append(f"High memory usage: {memory.percent:.1f}%")
            
            if disk.percent > 90:  # High disk usage threshold
                issues.append(f"High disk usage: {disk.percent:.1f}%")
            
            if issues:
                status = HealthStatus.DEGRADED if len(issues) == 1 else HealthStatus.UNHEALTHY
                message = "; ".join(issues)
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            
            return HealthCheck(
                component="system_resources",
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time_ms=response_time_ms,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_free_gb": disk.free / (1024**3),
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"Resource check error: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_web_interface(self) -> HealthCheck:
        """Check web interface health"""
        start_time = time.time()
        
        try:
            # This is a basic check - in a real scenario you might make an HTTP request
            # For now, we'll assume the web interface is healthy if we can import the module
            from src.web.app import app
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthCheck(
                component="web_interface",
                status=HealthStatus.HEALTHY,
                message="Web interface available",
                timestamp=datetime.now(),
                response_time_ms=response_time_ms,
                details={
                    "app_name": getattr(app, 'title', 'Zamaz Debate System'),
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="web_interface",
                status=HealthStatus.UNHEALTHY,
                message=f"Web interface error: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """
        Determine overall system health from individual checks.
        
        Args:
            checks: List of individual health checks
            
        Returns:
            Overall health status
        """
        if not checks:
            return HealthStatus.UNKNOWN
        
        # Count statuses
        status_counts = {}
        for check in checks:
            status = check.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Determine overall status
        if status_counts.get(HealthStatus.UNHEALTHY, 0) > 0:
            return HealthStatus.UNHEALTHY
        elif status_counts.get(HealthStatus.DEGRADED, 0) > 0:
            return HealthStatus.DEGRADED
        elif status_counts.get(HealthStatus.HEALTHY, 0) > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def get_last_health_check(self) -> Optional[SystemHealth]:
        """Get the last health check result"""
        return self._last_health_check
    
    def to_dict(self, health: SystemHealth) -> Dict[str, Any]:
        """
        Convert SystemHealth to dictionary for JSON serialization.
        
        Args:
            health: SystemHealth instance
            
        Returns:
            Dictionary representation
        """
        return {
            "status": health.status.value,
            "timestamp": health.timestamp.isoformat(),
            "uptime_seconds": health.uptime_seconds,
            "checks": [
                {
                    "component": check.component,
                    "status": check.status.value,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "response_time_ms": check.response_time_ms,
                    "details": check.details,
                }
                for check in health.checks
            ],
        }
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a quick health summary.
        
        Returns:
            Health summary dictionary
        """
        health = await self.check_system_health()
        
        return {
            "status": health.status.value,
            "timestamp": health.timestamp.isoformat(),
            "uptime_seconds": health.uptime_seconds,
            "component_count": len(health.checks),
            "healthy_components": len([c for c in health.checks if c.status == HealthStatus.HEALTHY]),
            "degraded_components": len([c for c in health.checks if c.status == HealthStatus.DEGRADED]),
            "unhealthy_components": len([c for c in health.checks if c.status == HealthStatus.UNHEALTHY]),
        }