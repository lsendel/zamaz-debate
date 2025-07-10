"""
Web Integration for Monitoring

FastAPI router and middleware for monitoring endpoints and metrics collection.
Integrates with the existing Zamaz Debate System web interface.
"""

import time
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import MonitoringConfig
from .prometheus_metrics import PrometheusMetricsExporter
from .collector import MetricsCollector
from .health_checker import HealthChecker, SystemHealth

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.
    
    Records response times, request counts, and error rates.
    """
    
    def __init__(self, app, prometheus_exporter: PrometheusMetricsExporter):
        super().__init__(app)
        self.prometheus_exporter = prometheus_exporter
    
    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics"""
        start_time = time.time()
        
        # Call the next middleware/endpoint
        response = await call_next(request)
        
        # Calculate response time
        duration = time.time() - start_time
        
        # Record metrics
        if self.prometheus_exporter.is_enabled():
            endpoint = request.url.path
            method = request.method
            
            # Record response time
            self.prometheus_exporter.record_response_time(endpoint, method, duration)
            
            # Update error rate if this was an error response
            if response.status_code >= 400:
                # Increment error counter (this would need to be implemented in the exporter)
                pass
        
        return response


class MonitoringRouter:
    """
    Router for monitoring endpoints.
    
    Provides endpoints for:
    - Prometheus metrics export
    - Health checks
    - Monitoring status and configuration
    """
    
    def __init__(
        self,
        config: Optional[MonitoringConfig] = None,
        prometheus_exporter: Optional[PrometheusMetricsExporter] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        health_checker: Optional[HealthChecker] = None
    ):
        """
        Initialize monitoring router.
        
        Args:
            config: Monitoring configuration
            prometheus_exporter: Prometheus metrics exporter
            metrics_collector: Metrics collector instance
            health_checker: Health checker instance
        """
        self.config = config or MonitoringConfig.from_env()
        self.prometheus_exporter = prometheus_exporter or PrometheusMetricsExporter(self.config)
        self.metrics_collector = metrics_collector
        self.health_checker = health_checker or HealthChecker(self.config)
        
        self.router = APIRouter(prefix="/monitoring", tags=["monitoring"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up monitoring routes"""
        
        @self.router.get("/metrics", response_class=PlainTextResponse)
        async def get_prometheus_metrics():
            """
            Prometheus metrics endpoint.
            
            Returns metrics in Prometheus text format for scraping.
            """
            if not self.prometheus_exporter.is_enabled():
                raise HTTPException(status_code=503, detail="Prometheus metrics disabled")
            
            try:
                metrics = self.prometheus_exporter.get_metrics()
                return PlainTextResponse(
                    content=metrics,
                    media_type="text/plain; charset=utf-8"
                )
            except Exception as e:
                logger.error(f"Error generating Prometheus metrics: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to generate metrics")
        
        @self.router.get("/health")
        async def get_system_health():
            """
            System health check endpoint.
            
            Returns comprehensive health status of all system components.
            """
            try:
                health = await self.health_checker.check_system_health()
                return self.health_checker.to_dict(health)
            except Exception as e:
                logger.error(f"Error checking system health: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to check system health")
        
        @self.router.get("/health/summary")
        async def get_health_summary():
            """
            Quick health summary endpoint.
            
            Returns a simplified health status for quick checks.
            """
            try:
                summary = await self.health_checker.get_health_summary()
                return summary
            except Exception as e:
                logger.error(f"Error getting health summary: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to get health summary")
        
        @self.router.get("/status")
        async def get_monitoring_status():
            """
            Monitoring system status endpoint.
            
            Returns status and configuration of the monitoring system itself.
            """
            status = {
                "monitoring_enabled": True,
                "prometheus_enabled": self.prometheus_exporter.is_enabled(),
                "kafka_monitoring": self.config.kafka_monitoring,
                "performance_monitoring": self.config.performance_monitoring,
                "health_checks": self.config.health_checks,
                "collection_interval": self.config.collection_interval,
                "prometheus_config": {
                    "port": self.config.prometheus.port,
                    "host": self.config.prometheus.host,
                    "metrics_path": self.config.prometheus.metrics_path,
                    "scrape_interval": self.config.prometheus.scrape_interval,
                },
                "grafana_config": {
                    "enabled": self.config.grafana.enabled,
                    "port": self.config.grafana.port,
                    "refresh_interval": self.config.grafana.refresh_interval,
                },
                "alerting_config": {
                    "enabled": self.config.alerting.enabled,
                    "webhook_url": self.config.alerting.webhook_url is not None,
                },
            }
            
            # Add collector status if available
            if self.metrics_collector:
                try:
                    current_metrics = self.metrics_collector.get_current_metrics()
                    status["current_metrics"] = current_metrics
                except Exception as e:
                    status["collector_error"] = str(e)
            
            return status
        
        @self.router.get("/config")
        async def get_monitoring_config():
            """
            Get monitoring configuration.
            
            Returns the current monitoring configuration (sanitized).
            """
            # Return sanitized config without sensitive information
            config_dict = {
                "prometheus": {
                    "enabled": self.config.prometheus.enabled,
                    "port": self.config.prometheus.port,
                    "host": self.config.prometheus.host,
                    "metrics_path": self.config.prometheus.metrics_path,
                    "scrape_interval": self.config.prometheus.scrape_interval,
                },
                "grafana": {
                    "enabled": self.config.grafana.enabled,
                    "port": self.config.grafana.port,
                    "refresh_interval": self.config.grafana.refresh_interval,
                    "time_range": self.config.grafana.time_range,
                },
                "alerting": {
                    "enabled": self.config.alerting.enabled,
                    "kafka_consumer_lag_threshold": self.config.alerting.kafka_consumer_lag_threshold,
                    "high_cpu_threshold": self.config.alerting.high_cpu_threshold,
                    "high_memory_threshold": self.config.alerting.high_memory_threshold,
                    "error_rate_threshold": self.config.alerting.error_rate_threshold,
                    "response_time_threshold": self.config.alerting.response_time_threshold,
                },
                "collection_interval": self.config.collection_interval,
                "retention_days": self.config.retention_days,
                "feature_flags": {
                    "kafka_monitoring": self.config.kafka_monitoring,
                    "performance_monitoring": self.config.performance_monitoring,
                    "health_checks": self.config.health_checks,
                    "consumer_lag_monitoring": self.config.consumer_lag_monitoring,
                },
            }
            
            return config_dict
        
        @self.router.post("/health/refresh")
        async def refresh_health_check():
            """
            Force refresh of health checks.
            
            Triggers immediate health check of all components.
            """
            try:
                health = await self.health_checker.check_system_health()
                return {
                    "message": "Health checks refreshed",
                    "status": health.status.value,
                    "timestamp": health.timestamp.isoformat(),
                    "components_checked": len(health.checks),
                }
            except Exception as e:
                logger.error(f"Error refreshing health checks: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to refresh health checks")


def create_monitoring_router(
    config: Optional[MonitoringConfig] = None,
    prometheus_exporter: Optional[PrometheusMetricsExporter] = None,
    metrics_collector: Optional[MetricsCollector] = None,
    health_checker: Optional[HealthChecker] = None
) -> APIRouter:
    """
    Create and configure monitoring router.
    
    Args:
        config: Monitoring configuration
        prometheus_exporter: Prometheus metrics exporter
        metrics_collector: Metrics collector instance
        health_checker: Health checker instance
        
    Returns:
        Configured APIRouter for monitoring endpoints
    """
    monitoring_router = MonitoringRouter(
        config=config,
        prometheus_exporter=prometheus_exporter,
        metrics_collector=metrics_collector,
        health_checker=health_checker
    )
    
    return monitoring_router.router


def create_monitoring_middleware(prometheus_exporter: PrometheusMetricsExporter) -> MonitoringMiddleware:
    """
    Create monitoring middleware.
    
    Args:
        prometheus_exporter: Prometheus metrics exporter
        
    Returns:
        Configured monitoring middleware
    """
    return MonitoringMiddleware(None, prometheus_exporter)


class MonitoringIntegration:
    """
    Main integration class for monitoring system.
    
    Provides a simple interface to integrate monitoring into FastAPI applications.
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        """
        Initialize monitoring integration.
        
        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitoringConfig.from_env()
        
        # Initialize monitoring components
        self.prometheus_exporter = PrometheusMetricsExporter(self.config)
        self.health_checker = HealthChecker(self.config)
        self.metrics_collector: Optional[MetricsCollector] = None
        
        # Create router and middleware
        self.router = create_monitoring_router(
            config=self.config,
            prometheus_exporter=self.prometheus_exporter,
            health_checker=self.health_checker
        )
        self.middleware = create_monitoring_middleware(self.prometheus_exporter)
        
        logger.info("Monitoring integration initialized")
    
    def set_kafka_bridge(self, kafka_bridge):
        """Set Kafka bridge for metrics collection"""
        self.metrics_collector = MetricsCollector(
            config=self.config,
            kafka_bridge=kafka_bridge,
            prometheus_exporter=self.prometheus_exporter
        )
        
        # Update router with metrics collector
        self.router = create_monitoring_router(
            config=self.config,
            prometheus_exporter=self.prometheus_exporter,
            metrics_collector=self.metrics_collector,
            health_checker=self.health_checker
        )
    
    async def start(self):
        """Start monitoring services"""
        if self.metrics_collector:
            await self.metrics_collector.start()
        logger.info("Monitoring services started")
    
    async def stop(self):
        """Stop monitoring services"""
        if self.metrics_collector:
            await self.metrics_collector.stop()
        logger.info("Monitoring services stopped")