"""
Prometheus Metrics Exporter

Exports Zamaz Debate System metrics to Prometheus format.
Integrates with existing Kafka infrastructure and performance monitoring.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary, 
        CollectorRegistry, generate_latest,
        start_http_server, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from .config import MonitoringConfig, KAFKA_METRICS, PERFORMANCE_METRICS, DEBATE_METRICS, SYSTEM_METRICS

logger = logging.getLogger(__name__)


class PrometheusMetricsExporter:
    """
    Exports system metrics to Prometheus format.
    
    Integrates with:
    - Kafka event bridge metrics
    - Performance context metrics 
    - Debate system metrics
    - System health metrics
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        """
        Initialize Prometheus metrics exporter.
        
        Args:
            config: Monitoring configuration
        """
        if not PROMETHEUS_AVAILABLE:
            logger.warning("prometheus_client not available, metrics export disabled")
            self.enabled = False
            return
            
        self.config = config or MonitoringConfig.from_env()
        self.enabled = self.config.prometheus.enabled
        
        if not self.enabled:
            logger.info("Prometheus metrics export disabled")
            return
            
        # Create custom registry to avoid conflicts
        self.registry = CollectorRegistry()
        
        # Initialize metrics
        self._init_kafka_metrics()
        self._init_performance_metrics()
        self._init_debate_metrics()
        self._init_system_metrics()
        
        self._start_time = time.time()
        logger.info("Prometheus metrics exporter initialized")
    
    def _init_kafka_metrics(self) -> None:
        """Initialize Kafka-related metrics"""
        prefix = self.config.prometheus.kafka_prefix
        
        self.kafka_events_produced = Counter(
            f"{prefix}_events_produced_total",
            KAFKA_METRICS["events_produced_total"],
            ["context", "topic"],
            registry=self.registry
        )
        
        self.kafka_events_consumed = Counter(
            f"{prefix}_events_consumed_total", 
            KAFKA_METRICS["events_consumed_total"],
            ["context", "topic"],
            registry=self.registry
        )
        
        self.kafka_consumer_lag = Gauge(
            f"{prefix}_consumer_lag",
            KAFKA_METRICS["consumer_lag"],
            ["context", "topic", "partition"],
            registry=self.registry
        )
        
        self.kafka_producer_send_rate = Gauge(
            f"{prefix}_producer_send_rate",
            KAFKA_METRICS["producer_send_rate"],
            ["context"],
            registry=self.registry
        )
        
        self.kafka_consumer_rate = Gauge(
            f"{prefix}_consumer_consumption_rate",
            KAFKA_METRICS["consumer_consumption_rate"],
            ["context"],
            registry=self.registry
        )
        
        self.kafka_bridged_event_types = Gauge(
            f"{prefix}_bridged_event_types",
            KAFKA_METRICS["bridged_event_types"],
            registry=self.registry
        )
        
        self.kafka_active_consumers = Gauge(
            f"{prefix}_active_consumers",
            KAFKA_METRICS["active_consumers"],
            registry=self.registry
        )
        
        self.kafka_connection_status = Gauge(
            f"{prefix}_connection_status",
            KAFKA_METRICS["connection_status"],
            registry=self.registry
        )
    
    def _init_performance_metrics(self) -> None:
        """Initialize performance-related metrics"""
        prefix = self.config.prometheus.performance_prefix
        
        self.response_time = Histogram(
            f"{prefix}_response_time_seconds",
            PERFORMANCE_METRICS["response_time_seconds"],
            ["endpoint", "method"],
            registry=self.registry
        )
        
        self.cpu_usage = Gauge(
            f"{prefix}_cpu_usage_percent",
            PERFORMANCE_METRICS["cpu_usage_percent"],
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            f"{prefix}_memory_usage_percent",
            PERFORMANCE_METRICS["memory_usage_percent"],
            registry=self.registry
        )
        
        self.disk_io = Counter(
            f"{prefix}_disk_io_bytes_total",
            PERFORMANCE_METRICS["disk_io_bytes"],
            ["operation"],  # read/write
            registry=self.registry
        )
        
        self.network_io = Counter(
            f"{prefix}_network_io_bytes_total",
            PERFORMANCE_METRICS["network_io_bytes"],
            ["direction"],  # inbound/outbound
            registry=self.registry
        )
        
        self.error_rate = Gauge(
            f"{prefix}_error_rate_percent",
            PERFORMANCE_METRICS["error_rate_percent"],
            ["service"],
            registry=self.registry
        )
        
        self.throughput = Gauge(
            f"{prefix}_throughput_requests_per_second",
            PERFORMANCE_METRICS["throughput_requests_per_second"],
            ["service"],
            registry=self.registry
        )
        
        self.benchmark_duration = Histogram(
            f"{prefix}_benchmark_duration_seconds",
            PERFORMANCE_METRICS["benchmark_duration_seconds"],
            ["benchmark_name"],
            registry=self.registry
        )
        
        self.optimization_improvement = Gauge(
            f"{prefix}_optimization_improvement_percent",
            PERFORMANCE_METRICS["optimization_improvement_percent"],
            ["optimization_name", "metric_type"],
            registry=self.registry
        )
    
    def _init_debate_metrics(self) -> None:
        """Initialize debate system metrics"""
        prefix = self.config.prometheus.debate_prefix
        
        self.debates_started = Counter(
            f"{prefix}_debates_started_total",
            DEBATE_METRICS["debates_started_total"],
            ["complexity"],
            registry=self.registry
        )
        
        self.debates_completed = Counter(
            f"{prefix}_debates_completed_total",
            DEBATE_METRICS["debates_completed_total"],
            ["complexity", "outcome"],
            registry=self.registry
        )
        
        self.debate_duration = Histogram(
            f"{prefix}_debate_duration_seconds",
            DEBATE_METRICS["debate_duration_seconds"],
            ["complexity"],
            registry=self.registry
        )
        
        self.decision_complexity = Gauge(
            f"{prefix}_decision_complexity_score",
            DEBATE_METRICS["decision_complexity_score"],
            ["decision_type"],
            registry=self.registry
        )
        
        self.tasks_created = Counter(
            f"{prefix}_tasks_created_total",
            DEBATE_METRICS["tasks_created_total"],
            ["task_type", "assignee"],
            registry=self.registry
        )
        
        self.pull_requests_created = Counter(
            f"{prefix}_pull_requests_created_total",
            DEBATE_METRICS["pull_requests_created_total"],
            ["type"],
            registry=self.registry
        )
    
    def _init_system_metrics(self) -> None:
        """Initialize system health metrics"""
        prefix = self.config.prometheus.system_prefix
        
        self.uptime = Gauge(
            f"{prefix}_uptime_seconds",
            SYSTEM_METRICS["uptime_seconds"],
            registry=self.registry
        )
        
        self.health_check_status = Gauge(
            f"{prefix}_health_check_status",
            SYSTEM_METRICS["health_check_status"],
            ["component"],
            registry=self.registry
        )
        
        self.event_bus_size = Gauge(
            f"{prefix}_event_bus_size",
            SYSTEM_METRICS["event_bus_size"],
            registry=self.registry
        )
        
        self.active_contexts = Gauge(
            f"{prefix}_active_contexts",
            SYSTEM_METRICS["active_contexts"],
            registry=self.registry
        )
    
    def update_kafka_metrics(self, kafka_metrics: Dict[str, Any]) -> None:
        """
        Update Kafka metrics from the event bridge.
        
        Args:
            kafka_metrics: Metrics from KafkaEventBridge.get_metrics()
        """
        if not self.enabled:
            return
            
        try:
            # Update bridged event types and active consumers
            self.kafka_bridged_event_types.set(kafka_metrics.get("bridged_event_types", 0))
            self.kafka_active_consumers.set(kafka_metrics.get("active_consumers", 0))
            
            # Update event bus metrics
            event_bus_metrics = kafka_metrics.get("event_bus_metrics", {})
            if isinstance(event_bus_metrics, dict):
                for event_type, count in event_bus_metrics.items():
                    if isinstance(count, (int, float)):
                        # Extract context from event type (assumes format like 'DebateStarted')
                        context = "unknown"
                        if "Debate" in event_type:
                            context = "debate"
                        elif "Test" in event_type:
                            context = "testing"
                        elif "Metric" in event_type or "Benchmark" in event_type:
                            context = "performance"
                        elif "Task" in event_type or "PullRequest" in event_type:
                            context = "implementation"
                        elif "Evolution" in event_type:
                            context = "evolution"
                        
                        self.kafka_events_produced.labels(
                            context=context, 
                            topic=f"zamaz.{context}.events"
                        ).inc(count)
            
            # Set connection status (assume connected if we have metrics)
            self.kafka_connection_status.set(1)
            
        except Exception as e:
            logger.error(f"Error updating Kafka metrics: {str(e)}")
    
    def update_performance_metrics(self, performance_data: Dict[str, Any]) -> None:
        """
        Update performance metrics from the performance context.
        
        Args:
            performance_data: Performance metrics data
        """
        if not self.enabled:
            return
            
        try:
            # Update system resource metrics
            if "cpu_usage" in performance_data:
                self.cpu_usage.set(performance_data["cpu_usage"])
            
            if "memory_usage" in performance_data:
                self.memory_usage.set(performance_data["memory_usage"])
            
            if "error_rate" in performance_data:
                self.error_rate.labels(service="api").set(performance_data["error_rate"])
            
            if "throughput" in performance_data:
                self.throughput.labels(service="api").set(performance_data["throughput"])
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {str(e)}")
    
    def record_debate_started(self, complexity: str) -> None:
        """Record a debate started event"""
        if self.enabled:
            self.debates_started.labels(complexity=complexity).inc()
    
    def record_debate_completed(self, complexity: str, outcome: str, duration_seconds: float) -> None:
        """Record a debate completed event"""
        if self.enabled:
            self.debates_completed.labels(complexity=complexity, outcome=outcome).inc()
            self.debate_duration.labels(complexity=complexity).observe(duration_seconds)
    
    def record_response_time(self, endpoint: str, method: str, duration_seconds: float) -> None:
        """Record HTTP response time"""
        if self.enabled:
            self.response_time.labels(endpoint=endpoint, method=method).observe(duration_seconds)
    
    def record_benchmark_completion(self, benchmark_name: str, duration_seconds: float) -> None:
        """Record benchmark completion"""
        if self.enabled:
            self.benchmark_duration.labels(benchmark_name=benchmark_name).observe(duration_seconds)
    
    def update_system_metrics(self) -> None:
        """Update system-level metrics"""
        if not self.enabled:
            return
            
        # Update uptime
        uptime = time.time() - self._start_time
        self.uptime.set(uptime)
    
    def set_health_status(self, component: str, healthy: bool) -> None:
        """Set health status for a component"""
        if self.enabled:
            self.health_check_status.labels(component=component).set(1 if healthy else 0)
    
    def get_metrics(self) -> str:
        """
        Get metrics in Prometheus format.
        
        Returns:
            Metrics in Prometheus text format
        """
        if not self.enabled:
            return ""
            
        # Update system metrics before export
        self.update_system_metrics()
        
        return generate_latest(self.registry).decode('utf-8')
    
    def start_http_server(self) -> None:
        """Start HTTP server for metrics endpoint"""
        if not self.enabled:
            logger.info("Prometheus HTTP server disabled")
            return
            
        try:
            start_http_server(
                self.config.prometheus.port,
                addr=self.config.prometheus.host,
                registry=self.registry
            )
            logger.info(
                f"Prometheus metrics server started on "
                f"http://{self.config.prometheus.host}:{self.config.prometheus.port}{self.config.prometheus.metrics_path}"
            )
        except Exception as e:
            logger.error(f"Failed to start Prometheus HTTP server: {str(e)}")
    
    def is_enabled(self) -> bool:
        """Check if metrics export is enabled"""
        return self.enabled