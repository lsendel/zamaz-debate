"""
Monitoring Configuration

Configuration for Prometheus, Grafana, and monitoring infrastructure.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PrometheusConfig:
    """Configuration for Prometheus metrics"""
    
    enabled: bool = True
    port: int = 8090
    host: str = "0.0.0.0"
    metrics_path: str = "/metrics"
    scrape_interval: int = 15  # seconds
    
    # Metric prefixes
    kafka_prefix: str = "zamaz_kafka"
    performance_prefix: str = "zamaz_performance"
    debate_prefix: str = "zamaz_debate"
    system_prefix: str = "zamaz_system"
    
    @classmethod
    def from_env(cls) -> "PrometheusConfig":
        """Create configuration from environment variables"""
        return cls(
            enabled=os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
            port=int(os.getenv("PROMETHEUS_PORT", "8090")),
            host=os.getenv("PROMETHEUS_HOST", "0.0.0.0"),
            metrics_path=os.getenv("PROMETHEUS_METRICS_PATH", "/metrics"),
            scrape_interval=int(os.getenv("PROMETHEUS_SCRAPE_INTERVAL", "15")),
        )


@dataclass
class GrafanaConfig:
    """Configuration for Grafana dashboards"""
    
    enabled: bool = True
    port: int = 3000
    host: str = "0.0.0.0"
    admin_password: str = "admin"
    
    # Dashboard settings
    refresh_interval: str = "5s"
    time_range: str = "1h"
    
    @classmethod
    def from_env(cls) -> "GrafanaConfig":
        """Create configuration from environment variables"""
        return cls(
            enabled=os.getenv("GRAFANA_ENABLED", "true").lower() == "true",
            port=int(os.getenv("GRAFANA_PORT", "3000")),
            host=os.getenv("GRAFANA_HOST", "0.0.0.0"),
            admin_password=os.getenv("GRAFANA_ADMIN_PASSWORD", "admin"),
            refresh_interval=os.getenv("GRAFANA_REFRESH_INTERVAL", "5s"),
            time_range=os.getenv("GRAFANA_TIME_RANGE", "1h"),
        )


@dataclass
class AlertingConfig:
    """Configuration for alerting rules"""
    
    enabled: bool = True
    webhook_url: Optional[str] = None
    slack_webhook: Optional[str] = None
    
    # Alert thresholds
    kafka_consumer_lag_threshold: int = 1000
    high_cpu_threshold: float = 80.0  # percentage
    high_memory_threshold: float = 85.0  # percentage
    error_rate_threshold: float = 5.0  # percentage
    response_time_threshold: float = 2000.0  # milliseconds
    
    @classmethod
    def from_env(cls) -> "AlertingConfig":
        """Create configuration from environment variables"""
        return cls(
            enabled=os.getenv("ALERTING_ENABLED", "true").lower() == "true",
            webhook_url=os.getenv("ALERT_WEBHOOK_URL"),
            slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
            kafka_consumer_lag_threshold=int(os.getenv("KAFKA_LAG_THRESHOLD", "1000")),
            high_cpu_threshold=float(os.getenv("HIGH_CPU_THRESHOLD", "80.0")),
            high_memory_threshold=float(os.getenv("HIGH_MEMORY_THRESHOLD", "85.0")),
            error_rate_threshold=float(os.getenv("ERROR_RATE_THRESHOLD", "5.0")),
            response_time_threshold=float(os.getenv("RESPONSE_TIME_THRESHOLD", "2000.0")),
        )


@dataclass
class MonitoringConfig:
    """Main monitoring configuration"""
    
    prometheus: PrometheusConfig
    grafana: GrafanaConfig
    alerting: AlertingConfig
    
    # Collection settings
    collection_interval: int = 30  # seconds
    retention_days: int = 30
    
    # Feature flags
    kafka_monitoring: bool = True
    performance_monitoring: bool = True
    health_checks: bool = True
    consumer_lag_monitoring: bool = True
    
    @classmethod
    def from_env(cls) -> "MonitoringConfig":
        """Create configuration from environment variables"""
        return cls(
            prometheus=PrometheusConfig.from_env(),
            grafana=GrafanaConfig.from_env(),
            alerting=AlertingConfig.from_env(),
            collection_interval=int(os.getenv("MONITORING_COLLECTION_INTERVAL", "30")),
            retention_days=int(os.getenv("MONITORING_RETENTION_DAYS", "30")),
            kafka_monitoring=os.getenv("KAFKA_MONITORING_ENABLED", "true").lower() == "true",
            performance_monitoring=os.getenv("PERFORMANCE_MONITORING_ENABLED", "true").lower() == "true",
            health_checks=os.getenv("HEALTH_CHECKS_ENABLED", "true").lower() == "true",
            consumer_lag_monitoring=os.getenv("CONSUMER_LAG_MONITORING_ENABLED", "true").lower() == "true",
        )


# Metric definitions for consistent naming
KAFKA_METRICS = {
    "events_produced_total": "Total number of events produced to Kafka",
    "events_consumed_total": "Total number of events consumed from Kafka", 
    "consumer_lag": "Consumer lag for each topic partition",
    "producer_send_rate": "Rate of events sent to Kafka per second",
    "consumer_consumption_rate": "Rate of events consumed from Kafka per second",
    "bridged_event_types": "Number of event types bridged to Kafka",
    "active_consumers": "Number of active Kafka consumers",
    "connection_status": "Kafka connection status (0=disconnected, 1=connected)",
}

PERFORMANCE_METRICS = {
    "response_time_seconds": "HTTP response time in seconds",
    "cpu_usage_percent": "CPU usage percentage",
    "memory_usage_percent": "Memory usage percentage", 
    "disk_io_bytes": "Disk I/O in bytes",
    "network_io_bytes": "Network I/O in bytes",
    "error_rate_percent": "Error rate percentage",
    "throughput_requests_per_second": "Request throughput per second",
    "benchmark_duration_seconds": "Benchmark execution duration",
    "optimization_improvement_percent": "Performance improvement from optimizations",
}

DEBATE_METRICS = {
    "debates_started_total": "Total number of debates started",
    "debates_completed_total": "Total number of debates completed",
    "debate_duration_seconds": "Duration of debates in seconds",
    "decision_complexity_score": "Complexity score of decisions",
    "tasks_created_total": "Total number of implementation tasks created",
    "pull_requests_created_total": "Total number of pull requests created",
}

SYSTEM_METRICS = {
    "uptime_seconds": "System uptime in seconds",
    "health_check_status": "Health check status (0=unhealthy, 1=healthy)",
    "event_bus_size": "Number of events in event bus",
    "active_contexts": "Number of active bounded contexts",
}