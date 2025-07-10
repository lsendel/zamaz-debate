"""
Performance Context Domain Events

Domain events that occur within the performance context, including metric collection,
benchmark execution, and optimization management.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from src.events.domain_event import DomainEvent


@dataclass(frozen=True)
class MetricCollected(DomainEvent):
    """Event published when a performance metric is collected"""
    
    metric_id: UUID
    metric_name: str
    metric_type: str
    value: float
    unit: str
    timestamp: datetime
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "MetricCollected")
        object.__setattr__(self, "aggregate_id", self.metric_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "metric_id": str(self.metric_id),
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
        })
        return data


@dataclass(frozen=True)
class BenchmarkStarted(DomainEvent):
    """Event published when a benchmark run starts"""
    
    benchmark_id: UUID
    benchmark_name: str
    scenario: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "BenchmarkStarted")
        object.__setattr__(self, "aggregate_id", self.benchmark_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "benchmark_id": str(self.benchmark_id),
            "benchmark_name": self.benchmark_name,
            "scenario": self.scenario,
        })
        return data


@dataclass(frozen=True)
class BenchmarkCompleted(DomainEvent):
    """Event published when a benchmark run completes"""
    
    benchmark_id: UUID
    benchmark_name: str
    duration_seconds: float
    summary: Dict[str, Any]
    resource_usage: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "BenchmarkCompleted")
        object.__setattr__(self, "aggregate_id", self.benchmark_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "benchmark_id": str(self.benchmark_id),
            "benchmark_name": self.benchmark_name,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "resource_usage": self.resource_usage,
        })
        return data


@dataclass(frozen=True)
class PerformanceReportGenerated(DomainEvent):
    """Event published when a performance report is generated"""
    
    benchmark_id: UUID
    report_type: str
    summary: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "PerformanceReportGenerated")
        object.__setattr__(self, "aggregate_id", self.benchmark_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "benchmark_id": str(self.benchmark_id),
            "report_type": self.report_type,
            "summary": self.summary,
        })
        return data


@dataclass(frozen=True)
class OptimizationIdentified(DomainEvent):
    """Event published when a performance optimization is identified"""
    
    optimization_id: UUID
    optimization_name: str
    optimization_type: str
    target_area: str
    expected_improvement: float
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "OptimizationIdentified")
        object.__setattr__(self, "aggregate_id", self.optimization_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "optimization_id": str(self.optimization_id),
            "optimization_name": self.optimization_name,
            "optimization_type": self.optimization_type,
            "target_area": self.target_area,
            "expected_improvement": self.expected_improvement,
        })
        return data


@dataclass(frozen=True)
class OptimizationApplied(DomainEvent):
    """Event published when an optimization is applied"""
    
    optimization_id: UUID
    optimization_name: str
    baseline_metrics: Dict[str, float]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "OptimizationApplied")
        object.__setattr__(self, "aggregate_id", self.optimization_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "optimization_id": str(self.optimization_id),
            "optimization_name": self.optimization_name,
            "baseline_metrics": self.baseline_metrics,
        })
        return data


@dataclass(frozen=True)
class PerformanceThresholdExceeded(DomainEvent):
    """Event published when a performance threshold is exceeded"""
    
    metric_id: UUID
    metric_name: str
    threshold_name: str
    threshold_value: float
    actual_value: float
    severity: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "PerformanceThresholdExceeded")
        object.__setattr__(self, "aggregate_id", self.metric_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "metric_id": str(self.metric_id),
            "metric_name": self.metric_name,
            "threshold_name": self.threshold_name,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "severity": self.severity,
        })
        return data


@dataclass(frozen=True)
class MetricThresholdSet(DomainEvent):
    """Event published when a metric threshold is defined"""
    
    metric_id: UUID
    threshold_name: str
    threshold_value: float
    threshold_type: str  # "min", "max"
    severity: str  # "warning", "critical"
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "MetricThresholdSet")
        object.__setattr__(self, "aggregate_id", self.metric_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "metric_id": str(self.metric_id),
            "threshold_name": self.threshold_name,
            "threshold_value": self.threshold_value,
            "threshold_type": self.threshold_type,
            "severity": self.severity,
        })
        return data


@dataclass(frozen=True)
class PerformanceAlertTriggered(DomainEvent):
    """Event published when a performance alert is triggered"""
    
    alert_id: UUID
    metric_id: UUID
    alert_type: str
    message: str
    severity: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "PerformanceAlertTriggered")
        object.__setattr__(self, "aggregate_id", self.alert_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "alert_id": str(self.alert_id),
            "metric_id": str(self.metric_id),
            "alert_type": self.alert_type,
            "message": self.message,
            "severity": self.severity,
        })
        return data


@dataclass(frozen=True)
class LoadTestStarted(DomainEvent):
    """Event published when a load test begins"""
    
    load_test_id: UUID
    test_name: str
    target_url: str
    concurrent_users: int
    duration_seconds: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "LoadTestStarted")
        object.__setattr__(self, "aggregate_id", self.load_test_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "load_test_id": str(self.load_test_id),
            "test_name": self.test_name,
            "target_url": self.target_url,
            "concurrent_users": self.concurrent_users,
            "duration_seconds": self.duration_seconds,
        })
        return data


@dataclass(frozen=True)
class LoadTestCompleted(DomainEvent):
    """Event published when a load test finishes"""
    
    load_test_id: UUID
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    requests_per_second: float
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "LoadTestCompleted")
        object.__setattr__(self, "aggregate_id", self.load_test_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "load_test_id": str(self.load_test_id),
            "test_name": self.test_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "average_response_time_ms": self.average_response_time_ms,
            "requests_per_second": self.requests_per_second,
        })
        return data