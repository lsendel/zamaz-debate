"""
Performance Context

This bounded context handles performance monitoring, metrics collection,
benchmarking, and optimization strategies.
"""

from .aggregates import Benchmark, Metric, OptimizationStrategy
from .domain_services import (
    BenchmarkExecutionService,
    OptimizationManagementService,
    PerformanceMonitoringService,
)
from .events import (
    BenchmarkCompleted,
    BenchmarkStarted,
    LoadTestCompleted,
    LoadTestStarted,
    MetricCollected,
    MetricThresholdSet,
    OptimizationApplied,
    OptimizationIdentified,
    PerformanceAlertTriggered,
    PerformanceReportGenerated,
    PerformanceThresholdExceeded,
)
from .repositories import (
    BenchmarkRepository,
    MetricRepository,
    OptimizationStrategyRepository,
    PerformanceReportRepository,
)
from .value_objects import (
    BenchmarkResult,
    MetricValue,
    Optimization,
    PerformanceProfile,
    PerformanceThreshold,
    ResourceUsage,
)


class PerformanceContext:
    """Main context class for Performance"""
    pass


__all__ = [
    "PerformanceContext",
    # Aggregates
    "Metric",
    "Benchmark",
    "OptimizationStrategy",
    # Value Objects
    "MetricValue",
    "PerformanceThreshold",
    "ResourceUsage",
    "Optimization",
    "PerformanceProfile",
    "BenchmarkResult",
    # Events
    "MetricCollected",
    "BenchmarkStarted",
    "BenchmarkCompleted",
    "PerformanceReportGenerated",
    "OptimizationIdentified",
    "OptimizationApplied",
    "PerformanceThresholdExceeded",
    "MetricThresholdSet",
    "PerformanceAlertTriggered",
    "LoadTestStarted",
    "LoadTestCompleted",
    # Repositories
    "MetricRepository",
    "BenchmarkRepository",
    "OptimizationStrategyRepository",
    "PerformanceReportRepository",
    # Domain Services
    "PerformanceMonitoringService",
    "BenchmarkExecutionService",
    "OptimizationManagementService",
]