"""
Metrics Collector

Collects metrics from all system components and forwards them to monitoring systems.
Integrates with existing Kafka bridge, performance context, and domain events.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.events import subscribe, get_event_bus
from src.infrastructure.kafka.event_bridge import KafkaEventBridge
from .config import MonitoringConfig
from .prometheus_metrics import PrometheusMetricsExporter

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics"""
    
    cpu_usage: float
    memory_usage: float
    disk_io_read: int
    disk_io_write: int
    network_io_sent: int
    network_io_recv: int
    timestamp: datetime


class MetricsCollector:
    """
    Collects metrics from all system components.
    
    Integrates with:
    - Kafka event bridge for event flow metrics
    - Performance context for performance metrics
    - System resources for health monitoring
    - Domain events for business metrics
    """
    
    def __init__(
        self,
        config: Optional[MonitoringConfig] = None,
        kafka_bridge: Optional[KafkaEventBridge] = None,
        prometheus_exporter: Optional[PrometheusMetricsExporter] = None
    ):
        """
        Initialize metrics collector.
        
        Args:
            config: Monitoring configuration
            kafka_bridge: Kafka event bridge instance
            prometheus_exporter: Prometheus metrics exporter
        """
        self.config = config or MonitoringConfig.from_env()
        self.kafka_bridge = kafka_bridge
        self.prometheus_exporter = prometheus_exporter or PrometheusMetricsExporter(self.config)
        
        self.event_bus = get_event_bus()
        self._running = False
        self._collection_task: Optional[asyncio.Task] = None
        
        # Initialize system metrics tracking
        self._last_disk_io = psutil.disk_io_counters()
        self._last_network_io = psutil.net_io_counters()
        self._last_collection_time = time.time()
        
        # Debate tracking
        self._active_debates: Dict[str, datetime] = {}
        
        # Subscribe to domain events
        self._subscribe_to_events()
        
        logger.info("Metrics collector initialized")
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant domain events for metrics collection"""
        
        # Debate events
        @subscribe("DebateStarted", context="monitoring", priority=10)
        async def on_debate_started(event):
            complexity = getattr(event, 'complexity', 'unknown')
            debate_id = str(getattr(event, 'debate_id', ''))
            
            self._active_debates[debate_id] = datetime.now()
            self.prometheus_exporter.record_debate_started(complexity)
            logger.debug(f"Debate started: {debate_id} (complexity: {complexity})")
        
        @subscribe("DebateCompleted", context="monitoring", priority=10)
        async def on_debate_completed(event):
            debate_id = str(getattr(event, 'debate_id', ''))
            complexity = getattr(event, 'complexity', 'unknown')
            outcome = getattr(event, 'outcome', 'unknown')
            
            # Calculate duration if we tracked the start
            duration_seconds = 0.0
            if debate_id in self._active_debates:
                start_time = self._active_debates.pop(debate_id)
                duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self.prometheus_exporter.record_debate_completed(complexity, outcome, duration_seconds)
            logger.debug(f"Debate completed: {debate_id} (duration: {duration_seconds}s)")
        
        # Performance events
        @subscribe("MetricCollected", context="monitoring", priority=10)
        async def on_metric_collected(event):
            metric_name = getattr(event, 'metric_name', '')
            metric_type = getattr(event, 'metric_type', '')
            value = getattr(event, 'value', 0.0)
            
            # Forward to Prometheus based on metric type
            if 'response_time' in metric_name.lower():
                endpoint = getattr(event, 'endpoint', 'unknown')
                method = getattr(event, 'method', 'GET')
                self.prometheus_exporter.record_response_time(endpoint, method, value / 1000.0)  # Convert ms to seconds
            
            logger.debug(f"Metric collected: {metric_name} = {value}")
        
        @subscribe("BenchmarkCompleted", context="monitoring", priority=10)
        async def on_benchmark_completed(event):
            benchmark_name = getattr(event, 'benchmark_name', 'unknown')
            duration_seconds = getattr(event, 'duration_seconds', 0.0)
            
            self.prometheus_exporter.record_benchmark_completion(benchmark_name, duration_seconds)
            logger.debug(f"Benchmark completed: {benchmark_name} (duration: {duration_seconds}s)")
        
        # Task and PR events
        @subscribe("TaskCreated", context="monitoring", priority=10)
        async def on_task_created(event):
            task_type = getattr(event, 'task_type', 'unknown')
            assignee = getattr(event, 'assignee', 'unknown')
            
            if hasattr(self.prometheus_exporter, 'tasks_created'):
                self.prometheus_exporter.tasks_created.labels(
                    task_type=task_type, 
                    assignee=assignee
                ).inc()
        
        @subscribe("PullRequestCreated", context="monitoring", priority=10)
        async def on_pull_request_created(event):
            pr_type = getattr(event, 'type', 'unknown')
            
            if hasattr(self.prometheus_exporter, 'pull_requests_created'):
                self.prometheus_exporter.pull_requests_created.labels(type=pr_type).inc()
    
    async def start(self) -> None:
        """Start metrics collection"""
        if self._running:
            logger.warning("Metrics collector already running")
            return
        
        self._running = True
        
        # Start Prometheus HTTP server if enabled
        if self.prometheus_exporter.is_enabled():
            self.prometheus_exporter.start_http_server()
        
        # Start collection task
        self._collection_task = asyncio.create_task(self._collection_loop())
        
        logger.info("Metrics collection started")
    
    async def stop(self) -> None:
        """Stop metrics collection"""
        self._running = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Metrics collection stopped")
    
    async def _collection_loop(self) -> None:
        """Main collection loop"""
        while self._running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.config.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {str(e)}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _collect_metrics(self) -> None:
        """Collect metrics from all sources"""
        try:
            # Collect system metrics
            system_metrics = self._collect_system_metrics()
            self._update_system_metrics(system_metrics)
            
            # Collect Kafka metrics if available
            if self.kafka_bridge and self.config.kafka_monitoring:
                kafka_metrics = self.kafka_bridge.get_metrics()
                self.prometheus_exporter.update_kafka_metrics(kafka_metrics)
            
            # Collect event bus metrics
            if self.config.performance_monitoring:
                event_metrics = self._collect_event_bus_metrics()
                self._update_event_metrics(event_metrics)
            
            # Update health status
            await self._check_health_status()
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system resource metrics"""
        try:
            # CPU and memory
            cpu_usage = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk I/O
            current_disk_io = psutil.disk_io_counters()
            disk_io_read = current_disk_io.read_bytes - self._last_disk_io.read_bytes
            disk_io_write = current_disk_io.write_bytes - self._last_disk_io.write_bytes
            self._last_disk_io = current_disk_io
            
            # Network I/O
            current_network_io = psutil.net_io_counters()
            network_io_sent = current_network_io.bytes_sent - self._last_network_io.bytes_sent
            network_io_recv = current_network_io.bytes_recv - self._last_network_io.bytes_recv
            self._last_network_io = current_network_io
            
            return SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_io_read=disk_io_read,
                disk_io_write=disk_io_write,
                network_io_sent=network_io_sent,
                network_io_recv=network_io_recv,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return SystemMetrics(0, 0, 0, 0, 0, 0, datetime.now())
    
    def _update_system_metrics(self, metrics: SystemMetrics) -> None:
        """Update system metrics in Prometheus"""
        if not self.prometheus_exporter.is_enabled():
            return
        
        performance_data = {
            "cpu_usage": metrics.cpu_usage,
            "memory_usage": metrics.memory_usage,
        }
        
        self.prometheus_exporter.update_performance_metrics(performance_data)
        
        # Update disk I/O counters
        if hasattr(self.prometheus_exporter, 'disk_io'):
            time_delta = time.time() - self._last_collection_time
            if time_delta > 0:
                self.prometheus_exporter.disk_io.labels(operation="read").inc(metrics.disk_io_read)
                self.prometheus_exporter.disk_io.labels(operation="write").inc(metrics.disk_io_write)
                
                # Update network I/O
                if hasattr(self.prometheus_exporter, 'network_io'):
                    self.prometheus_exporter.network_io.labels(direction="outbound").inc(metrics.network_io_sent)
                    self.prometheus_exporter.network_io.labels(direction="inbound").inc(metrics.network_io_recv)
        
        self._last_collection_time = time.time()
    
    def _collect_event_bus_metrics(self) -> Dict[str, Any]:
        """Collect event bus metrics"""
        try:
            event_history = self.event_bus.get_event_history()
            event_metrics_data = self.event_bus.get_event_metrics()
            
            return {
                "event_history_size": len(event_history),
                "event_metrics": event_metrics_data,
            }
        except Exception as e:
            logger.error(f"Error collecting event bus metrics: {str(e)}")
            return {}
    
    def _update_event_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update event bus metrics in Prometheus"""
        if not self.prometheus_exporter.is_enabled():
            return
        
        # Update event bus size
        if hasattr(self.prometheus_exporter, 'event_bus_size'):
            self.prometheus_exporter.event_bus_size.set(metrics.get("event_history_size", 0))
    
    async def _check_health_status(self) -> None:
        """Check health status of system components"""
        if not self.config.health_checks:
            return
        
        # Check event bus health
        event_bus_healthy = True
        try:
            self.event_bus.get_event_metrics()
        except Exception:
            event_bus_healthy = False
        
        self.prometheus_exporter.set_health_status("event_bus", event_bus_healthy)
        
        # Check Kafka health
        if self.kafka_bridge:
            kafka_healthy = True
            try:
                metrics = self.kafka_bridge.get_metrics()
                # Consider unhealthy if no active consumers when there should be
                if metrics.get("bridged_event_types", 0) > 0 and metrics.get("active_consumers", 0) == 0:
                    kafka_healthy = False
            except Exception:
                kafka_healthy = False
            
            self.prometheus_exporter.set_health_status("kafka", kafka_healthy)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.
        
        Returns:
            Dictionary of current metrics
        """
        metrics = {}
        
        # System metrics
        system_metrics = self._collect_system_metrics()
        metrics["system"] = {
            "cpu_usage": system_metrics.cpu_usage,
            "memory_usage": system_metrics.memory_usage,
            "timestamp": system_metrics.timestamp.isoformat(),
        }
        
        # Kafka metrics
        if self.kafka_bridge:
            metrics["kafka"] = self.kafka_bridge.get_metrics()
        
        # Event bus metrics  
        metrics["events"] = self._collect_event_bus_metrics()
        
        # Active debates
        metrics["debates"] = {
            "active_count": len(self._active_debates),
            "active_debates": list(self._active_debates.keys()),
        }
        
        return metrics