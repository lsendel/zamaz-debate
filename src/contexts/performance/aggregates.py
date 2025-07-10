"""
Performance Context Aggregates

This module contains the aggregate roots for the performance context.
Aggregates manage performance metrics, benchmarks, and optimization strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .events import (
    BenchmarkCompleted,
    BenchmarkStarted,
    MetricCollected,
    OptimizationApplied,
    OptimizationIdentified,
    PerformanceReportGenerated,
    PerformanceThresholdExceeded,
)
from .value_objects import (
    MetricValue,
    Optimization,
    PerformanceThreshold,
    ResourceUsage,
)


class MetricType(Enum):
    """Types of performance metrics"""
    
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"


class BenchmarkStatus(Enum):
    """Status of a benchmark run"""
    
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationStatus(Enum):
    """Status of an optimization"""
    
    IDENTIFIED = "identified"
    APPROVED = "approved"
    APPLIED = "applied"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class Metric:
    """
    Performance Metric Aggregate Root
    
    Manages individual performance metrics and their history.
    Enforces business rules around metric collection and threshold monitoring.
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    type: MetricType = MetricType.CUSTOM
    unit: str = ""
    values: List[MetricValue] = field(default_factory=list)
    thresholds: List[PerformanceThreshold] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    
    def collect_value(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """
        Collect a new metric value
        
        Args:
            value: The metric value
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        metric_value = MetricValue(value=value, timestamp=timestamp)
        self.values.append(metric_value)
        
        self._publish_event(
            MetricCollected(
                metric_id=self.id,
                metric_name=self.name,
                metric_type=self.type.value,
                value=value,
                unit=self.unit,
                timestamp=timestamp,
                occurred_at=datetime.now(),
            )
        )
        
        # Check thresholds
        self._check_thresholds(value)
    
    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """Add a performance threshold to monitor"""
        if any(t.name == threshold.name for t in self.thresholds):
            raise ValueError(f"Threshold {threshold.name} already exists")
        self.thresholds.append(threshold)
    
    def remove_threshold(self, threshold_name: str) -> None:
        """Remove a performance threshold"""
        self.thresholds = [t for t in self.thresholds if t.name != threshold_name]
    
    def get_latest_value(self) -> Optional[float]:
        """Get the most recent metric value"""
        if not self.values:
            return None
        return max(self.values, key=lambda v: v.timestamp).value
    
    def get_average(self, window_minutes: int = 60) -> float:
        """
        Calculate average value over a time window
        
        Args:
            window_minutes: Time window in minutes
            
        Returns:
            Average value or 0.0 if no values
        """
        if not self.values:
            return 0.0
        
        cutoff_time = datetime.now().timestamp() - (window_minutes * 60)
        recent_values = [
            v.value for v in self.values
            if v.timestamp.timestamp() > cutoff_time
        ]
        
        return sum(recent_values) / len(recent_values) if recent_values else 0.0
    
    def get_percentile(self, percentile: float) -> float:
        """
        Calculate a percentile value
        
        Args:
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value or 0.0 if no values
        """
        if not self.values or not (0 <= percentile <= 100):
            return 0.0
        
        sorted_values = sorted(v.value for v in self.values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _check_thresholds(self, value: float) -> None:
        """Check if value exceeds any thresholds"""
        for threshold in self.thresholds:
            if threshold.is_exceeded(value):
                self._publish_event(
                    PerformanceThresholdExceeded(
                        metric_id=self.id,
                        metric_name=self.name,
                        threshold_name=threshold.name,
                        threshold_value=threshold.value,
                        actual_value=value,
                        severity=threshold.severity,
                        occurred_at=datetime.now(),
                    )
                )
    
    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events


@dataclass
class Benchmark:
    """
    Benchmark Aggregate Root
    
    Manages performance benchmark runs including setup, execution, and results.
    Enforces rules around benchmark validity and reproducibility.
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    scenario: Dict[str, Any] = field(default_factory=dict)
    status: BenchmarkStatus = BenchmarkStatus.CREATED
    metrics: List[Metric] = field(default_factory=list)
    resource_usage: Optional[ResourceUsage] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    
    def start(self) -> None:
        """Start the benchmark run"""
        if self.status != BenchmarkStatus.CREATED:
            raise ValueError("Benchmark has already been started")
        
        self.status = BenchmarkStatus.RUNNING
        self.started_at = datetime.now()
        
        self._publish_event(
            BenchmarkStarted(
                benchmark_id=self.id,
                benchmark_name=self.name,
                scenario=self.scenario,
                occurred_at=datetime.now(),
            )
        )
    
    def add_metric(self, metric: Metric) -> None:
        """Add a metric to track during the benchmark"""
        if self.status != BenchmarkStatus.CREATED:
            raise ValueError("Cannot add metrics to running benchmark")
        if any(m.id == metric.id for m in self.metrics):
            raise ValueError(f"Metric {metric.id} already in benchmark")
        self.metrics.append(metric)
    
    def record_metric(self, metric_name: str, value: float) -> None:
        """Record a metric value during benchmark execution"""
        if self.status != BenchmarkStatus.RUNNING:
            raise ValueError("Benchmark must be running to record metrics")
        
        metric = next((m for m in self.metrics if m.name == metric_name), None)
        if not metric:
            raise ValueError(f"Metric {metric_name} not found in benchmark")
        
        metric.collect_value(value)
    
    def complete(self, resource_usage: Optional[ResourceUsage] = None) -> None:
        """Complete the benchmark run"""
        if self.status != BenchmarkStatus.RUNNING:
            raise ValueError("Benchmark must be running to complete")
        
        self.status = BenchmarkStatus.COMPLETED
        self.completed_at = datetime.now()
        self.resource_usage = resource_usage
        
        # Calculate summary statistics
        duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        summary = {
            "duration_seconds": duration_seconds,
            "metrics_collected": sum(len(m.values) for m in self.metrics),
        }
        
        self._publish_event(
            BenchmarkCompleted(
                benchmark_id=self.id,
                benchmark_name=self.name,
                duration_seconds=duration_seconds,
                summary=summary,
                resource_usage=resource_usage.to_dict() if resource_usage else {},
                occurred_at=datetime.now(),
            )
        )
    
    def fail(self, error_message: str) -> None:
        """Mark the benchmark as failed"""
        if self.status not in [BenchmarkStatus.CREATED, BenchmarkStatus.RUNNING]:
            raise ValueError("Cannot fail completed or cancelled benchmark")
        
        self.status = BenchmarkStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
    
    def cancel(self) -> None:
        """Cancel the benchmark run"""
        if self.status in [BenchmarkStatus.COMPLETED, BenchmarkStatus.CANCELLED]:
            raise ValueError("Cannot cancel completed or already cancelled benchmark")
        
        self.status = BenchmarkStatus.CANCELLED
        self.completed_at = datetime.now()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a performance report from the benchmark"""
        if self.status != BenchmarkStatus.COMPLETED:
            raise ValueError("Benchmark must be completed to generate report")
        
        report = {
            "benchmark_id": str(self.id),
            "name": self.name,
            "scenario": self.scenario,
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
            "metrics": {},
            "resource_usage": self.resource_usage.to_dict() if self.resource_usage else None,
        }
        
        for metric in self.metrics:
            report["metrics"][metric.name] = {
                "type": metric.type.value,
                "unit": metric.unit,
                "count": len(metric.values),
                "average": metric.get_average(),
                "p50": metric.get_percentile(50),
                "p95": metric.get_percentile(95),
                "p99": metric.get_percentile(99),
                "latest": metric.get_latest_value(),
            }
        
        self._publish_event(
            PerformanceReportGenerated(
                benchmark_id=self.id,
                report_type="benchmark",
                summary=report,
                occurred_at=datetime.now(),
            )
        )
        
        return report
    
    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def is_running(self) -> bool:
        """Check if benchmark is currently running"""
        return self.status == BenchmarkStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if benchmark has completed successfully"""
        return self.status == BenchmarkStatus.COMPLETED


@dataclass
class OptimizationStrategy:
    """
    Optimization Strategy Aggregate Root
    
    Manages performance optimization strategies and their application.
    Tracks the lifecycle of optimizations from identification to validation.
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    optimization: Optimization = field(default_factory=Optimization)
    status: OptimizationStatus = OptimizationStatus.IDENTIFIED
    expected_improvement: float = 0.0  # Percentage improvement expected
    actual_improvement: Optional[float] = None
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    post_optimization_metrics: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize and publish optimization identified event"""
        if self.status == OptimizationStatus.IDENTIFIED and not self._events:
            self._publish_event(
                OptimizationIdentified(
                    optimization_id=self.id,
                    optimization_name=self.name,
                    optimization_type=self.optimization.type,
                    target_area=self.optimization.target_area,
                    expected_improvement=self.expected_improvement,
                    occurred_at=datetime.now(),
                )
            )
    
    def approve(self) -> None:
        """Approve the optimization for application"""
        if self.status != OptimizationStatus.IDENTIFIED:
            raise ValueError("Only identified optimizations can be approved")
        self.status = OptimizationStatus.APPROVED
    
    def apply(self, baseline_metrics: Dict[str, float]) -> None:
        """Apply the optimization"""
        if self.status != OptimizationStatus.APPROVED:
            raise ValueError("Only approved optimizations can be applied")
        
        self.status = OptimizationStatus.APPLIED
        self.applied_at = datetime.now()
        self.baseline_metrics = baseline_metrics
        
        self._publish_event(
            OptimizationApplied(
                optimization_id=self.id,
                optimization_name=self.name,
                baseline_metrics=baseline_metrics,
                occurred_at=datetime.now(),
            )
        )
    
    def validate(self, post_metrics: Dict[str, float]) -> None:
        """Validate the optimization results"""
        if self.status != OptimizationStatus.APPLIED:
            raise ValueError("Only applied optimizations can be validated")
        
        self.status = OptimizationStatus.VALIDATED
        self.validated_at = datetime.now()
        self.post_optimization_metrics = post_metrics
        
        # Calculate actual improvement
        if self.baseline_metrics and post_metrics:
            improvements = []
            for metric_name, baseline_value in self.baseline_metrics.items():
                if metric_name in post_metrics and baseline_value > 0:
                    post_value = post_metrics[metric_name]
                    improvement = ((baseline_value - post_value) / baseline_value) * 100
                    improvements.append(improvement)
            
            self.actual_improvement = sum(improvements) / len(improvements) if improvements else 0.0
    
    def reject(self, reason: str) -> None:
        """Reject the optimization"""
        if self.status not in [OptimizationStatus.IDENTIFIED, OptimizationStatus.APPROVED]:
            raise ValueError("Cannot reject applied or validated optimizations")
        self.status = OptimizationStatus.REJECTED
    
    def rollback(self) -> None:
        """Roll back an applied optimization"""
        if self.status != OptimizationStatus.APPLIED:
            raise ValueError("Only applied optimizations can be rolled back")
        self.status = OptimizationStatus.ROLLED_BACK
    
    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def is_successful(self) -> bool:
        """Check if optimization was successful"""
        return (
            self.status == OptimizationStatus.VALIDATED
            and self.actual_improvement is not None
            and self.actual_improvement > 0
        )