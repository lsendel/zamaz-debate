"""
Unit tests for the Performance Context domain logic

Tests aggregates, value objects, domain services, and business rules.
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.contexts.performance.aggregates import (
    Benchmark,
    BenchmarkStatus,
    Metric,
    MetricType,
    OptimizationStatus,
    OptimizationStrategy,
)
from src.contexts.performance.value_objects import (
    BenchmarkResult,
    MetricValue,
    Optimization,
    PerformanceProfile,
    PerformanceThreshold,
    ResourceUsage,
)
from src.contexts.performance.events import (
    BenchmarkCompleted,
    BenchmarkStarted,
    MetricCollected,
    OptimizationApplied,
    OptimizationIdentified,
    PerformanceThresholdExceeded,
)


class TestMetricValue:
    """Test cases for MetricValue value object"""
    
    def test_create_metric_value(self):
        """Test creating a metric value"""
        timestamp = datetime.now()
        value = MetricValue(
            value=95.5,
            timestamp=timestamp,
            metadata={"source": "api", "endpoint": "/users"}
        )
        
        assert value.value == 95.5
        assert value.timestamp == timestamp
        assert value.metadata["source"] == "api"
        assert value.metadata["endpoint"] == "/users"
    
    def test_metric_value_default_metadata(self):
        """Test metric value with default empty metadata"""
        value = MetricValue(value=100.0, timestamp=datetime.now())
        
        assert value.metadata == {}
    
    def test_metric_value_to_dict(self):
        """Test converting metric value to dictionary"""
        timestamp = datetime.now()
        value = MetricValue(value=50.0, timestamp=timestamp)
        
        result = value.to_dict()
        
        assert result["value"] == 50.0
        assert result["timestamp"] == timestamp.isoformat()
        assert result["metadata"] == {}


class TestPerformanceThreshold:
    """Test cases for PerformanceThreshold value object"""
    
    def test_create_max_threshold(self):
        """Test creating a maximum threshold"""
        threshold = PerformanceThreshold(
            name="High CPU",
            value=80.0,
            type="max",
            severity="warning"
        )
        
        assert threshold.name == "High CPU"
        assert threshold.value == 80.0
        assert threshold.type == "max"
        assert threshold.severity == "warning"
    
    def test_create_min_threshold(self):
        """Test creating a minimum threshold"""
        threshold = PerformanceThreshold(
            name="Low Success Rate",
            value=95.0,
            type="min",
            severity="critical"
        )
        
        assert threshold.type == "min"
        assert threshold.severity == "critical"
    
    def test_threshold_exceeded_max(self):
        """Test checking if max threshold is exceeded"""
        threshold = PerformanceThreshold(
            name="High Response Time",
            value=1000.0,
            type="max"
        )
        
        assert threshold.is_exceeded(1500.0) is True
        assert threshold.is_exceeded(800.0) is False
        assert threshold.is_exceeded(1000.0) is False
    
    def test_threshold_exceeded_min(self):
        """Test checking if min threshold is exceeded"""
        threshold = PerformanceThreshold(
            name="Low Uptime",
            value=99.0,
            type="min"
        )
        
        assert threshold.is_exceeded(98.5) is True
        assert threshold.is_exceeded(99.5) is False
        assert threshold.is_exceeded(99.0) is False
    
    def test_invalid_threshold_values(self):
        """Test that invalid threshold values raise errors"""
        with pytest.raises(ValueError, match="Threshold name cannot be empty"):
            PerformanceThreshold(name="", value=100.0, type="max")
        
        with pytest.raises(ValueError, match="Threshold type must be 'min' or 'max'"):
            PerformanceThreshold(name="Test", value=100.0, type="avg")
        
        with pytest.raises(ValueError, match="Severity must be 'warning' or 'critical'"):
            PerformanceThreshold(name="Test", value=100.0, type="max", severity="info")


class TestResourceUsage:
    """Test cases for ResourceUsage value object"""
    
    def test_create_resource_usage(self):
        """Test creating resource usage snapshot"""
        usage = ResourceUsage(
            cpu_percent=45.5,
            memory_percent=62.0,
            memory_mb=2048.0,
            disk_io_read_mb=100.0,
            disk_io_write_mb=50.0,
            network_io_sent_mb=25.0,
            network_io_recv_mb=30.0
        )
        
        assert usage.cpu_percent == 45.5
        assert usage.memory_percent == 62.0
        assert usage.memory_mb == 2048.0
        assert usage.total_disk_io_mb == 150.0
        assert usage.total_network_io_mb == 55.0
    
    def test_resource_usage_auto_timestamp(self):
        """Test that timestamp is automatically set"""
        usage = ResourceUsage(cpu_percent=50.0, memory_percent=60.0, memory_mb=1024.0)
        
        assert usage.timestamp is not None
        assert isinstance(usage.timestamp, datetime)
    
    def test_invalid_resource_usage(self):
        """Test that invalid resource usage values raise errors"""
        with pytest.raises(ValueError, match="CPU percent must be between 0 and 100"):
            ResourceUsage(cpu_percent=101.0, memory_percent=50.0, memory_mb=1024.0)
        
        with pytest.raises(ValueError, match="Memory percent must be between 0 and 100"):
            ResourceUsage(cpu_percent=50.0, memory_percent=-5.0, memory_mb=1024.0)


class TestOptimization:
    """Test cases for Optimization value object"""
    
    def test_create_optimization(self):
        """Test creating an optimization"""
        optimization = Optimization(
            type="cache",
            target_area="database",
            technique="query_caching",
            implementation_details={"cache_ttl": 3600, "cache_size": "1GB"},
            risk_level="medium"
        )
        
        assert optimization.type == "cache"
        assert optimization.target_area == "database"
        assert optimization.technique == "query_caching"
        assert optimization.implementation_details["cache_ttl"] == 3600
        assert optimization.risk_level == "medium"
    
    def test_optimization_defaults(self):
        """Test optimization with default values"""
        optimization = Optimization()
        
        assert optimization.type == "general"
        assert optimization.target_area == ""
        assert optimization.technique == ""
        assert optimization.implementation_details == {}
        assert optimization.risk_level == "low"
    
    def test_invalid_optimization_values(self):
        """Test that invalid optimization values raise errors"""
        with pytest.raises(ValueError, match="Optimization type must be one of"):
            Optimization(type="unknown")
        
        with pytest.raises(ValueError, match="Risk level must be one of"):
            Optimization(risk_level="extreme")


class TestMetric:
    """Test cases for Metric aggregate root"""
    
    def test_create_metric(self):
        """Test creating a metric"""
        metric = Metric(
            name="response_time",
            type=MetricType.RESPONSE_TIME,
            unit="ms",
            tags={"service": "api", "endpoint": "/users"}
        )
        
        assert metric.name == "response_time"
        assert metric.type == MetricType.RESPONSE_TIME
        assert metric.unit == "ms"
        assert metric.tags["service"] == "api"
        assert metric.values == []
        assert metric.thresholds == []
    
    def test_collect_metric_value(self):
        """Test collecting metric values"""
        metric = Metric(name="cpu_usage", type=MetricType.CPU_USAGE, unit="%")
        
        metric.collect_value(45.5)
        metric.collect_value(52.0)
        
        assert len(metric.values) == 2
        assert metric.values[0].value == 45.5
        assert metric.values[1].value == 52.0
        assert metric.get_latest_value() == 52.0
        
        # Check MetricCollected event
        events = metric.get_events()
        assert len(events) == 2
        assert all(isinstance(e, MetricCollected) for e in events)
        assert events[0].value == 45.5
        assert events[1].value == 52.0
    
    def test_add_threshold(self):
        """Test adding performance thresholds"""
        metric = Metric(name="memory_usage", type=MetricType.MEMORY_USAGE, unit="%")
        
        warning_threshold = PerformanceThreshold(
            name="High Memory",
            value=80.0,
            type="max",
            severity="warning"
        )
        critical_threshold = PerformanceThreshold(
            name="Critical Memory",
            value=95.0,
            type="max",
            severity="critical"
        )
        
        metric.add_threshold(warning_threshold)
        metric.add_threshold(critical_threshold)
        
        assert len(metric.thresholds) == 2
        
        # Cannot add duplicate threshold
        with pytest.raises(ValueError, match="Threshold High Memory already exists"):
            metric.add_threshold(warning_threshold)
    
    def test_threshold_exceeded_events(self):
        """Test that threshold exceeded events are published"""
        metric = Metric(name="error_rate", type=MetricType.ERROR_RATE, unit="%")
        
        threshold = PerformanceThreshold(
            name="High Error Rate",
            value=5.0,
            type="max",
            severity="critical"
        )
        metric.add_threshold(threshold)
        
        # Collect value that exceeds threshold
        metric.collect_value(7.5)
        
        events = metric.get_events()
        threshold_events = [e for e in events if isinstance(e, PerformanceThresholdExceeded)]
        
        assert len(threshold_events) == 1
        assert threshold_events[0].threshold_name == "High Error Rate"
        assert threshold_events[0].actual_value == 7.5
        assert threshold_events[0].severity == "critical"
    
    def test_calculate_average(self):
        """Test calculating average metric value"""
        metric = Metric(name="throughput", type=MetricType.THROUGHPUT, unit="rps")
        
        # Add values with timestamps
        base_time = datetime.now()
        for i in range(5):
            timestamp = base_time - timedelta(minutes=i * 10)
            metric.values.append(MetricValue(value=100 + i * 10, timestamp=timestamp))
        
        # Calculate average over last hour
        avg = metric.get_average(60)
        assert avg > 0
        
        # Empty metric should return 0
        empty_metric = Metric(name="empty", type=MetricType.CUSTOM, unit="")
        assert empty_metric.get_average(60) == 0.0
    
    def test_calculate_percentiles(self):
        """Test calculating percentile values"""
        metric = Metric(name="latency", type=MetricType.RESPONSE_TIME, unit="ms")
        
        # Add values from 1 to 100
        for i in range(1, 101):
            metric.values.append(MetricValue(value=float(i), timestamp=datetime.now()))
        
        assert metric.get_percentile(50) == 50.0  # Median
        assert metric.get_percentile(95) == 95.0
        assert metric.get_percentile(99) == 99.0
        assert metric.get_percentile(100) == 100.0
        
        # Empty metric should return 0
        empty_metric = Metric(name="empty", type=MetricType.CUSTOM, unit="")
        assert empty_metric.get_percentile(50) == 0.0


class TestBenchmark:
    """Test cases for Benchmark aggregate root"""
    
    def test_create_benchmark(self):
        """Test creating a benchmark"""
        scenario = {
            "load": "1000 requests/second",
            "duration": "5 minutes",
            "target": "API endpoint"
        }
        
        benchmark = Benchmark(
            name="API Load Test",
            description="Test API performance under load",
            scenario=scenario
        )
        
        assert benchmark.name == "API Load Test"
        assert benchmark.description == "Test API performance under load"
        assert benchmark.scenario == scenario
        assert benchmark.status == BenchmarkStatus.CREATED
        assert benchmark.metrics == []
        assert benchmark.is_running is False
        assert benchmark.is_completed is False
    
    def test_start_benchmark(self):
        """Test starting a benchmark"""
        benchmark = Benchmark(name="Test Benchmark")
        
        benchmark.start()
        
        assert benchmark.status == BenchmarkStatus.RUNNING
        assert benchmark.started_at is not None
        assert benchmark.is_running is True
        
        # Check BenchmarkStarted event
        events = benchmark.get_events()
        assert len(events) == 1
        assert isinstance(events[0], BenchmarkStarted)
        
        # Cannot start already running benchmark
        with pytest.raises(ValueError, match="Benchmark has already been started"):
            benchmark.start()
    
    def test_add_metrics_to_benchmark(self):
        """Test adding metrics to track during benchmark"""
        benchmark = Benchmark(name="Test Benchmark")
        
        metric1 = Metric(name="response_time", type=MetricType.RESPONSE_TIME, unit="ms")
        metric2 = Metric(name="throughput", type=MetricType.THROUGHPUT, unit="rps")
        
        benchmark.add_metric(metric1)
        benchmark.add_metric(metric2)
        
        assert len(benchmark.metrics) == 2
        
        # Cannot add metrics to running benchmark
        benchmark.start()
        with pytest.raises(ValueError, match="Cannot add metrics to running benchmark"):
            benchmark.add_metric(Metric(name="new", type=MetricType.CUSTOM, unit=""))
    
    def test_record_benchmark_metrics(self):
        """Test recording metric values during benchmark"""
        benchmark = Benchmark(name="Test Benchmark")
        metric = Metric(name="response_time", type=MetricType.RESPONSE_TIME, unit="ms")
        benchmark.add_metric(metric)
        
        benchmark.start()
        
        benchmark.record_metric("response_time", 150.0)
        benchmark.record_metric("response_time", 175.0)
        
        assert len(metric.values) == 2
        assert metric.values[0].value == 150.0
        assert metric.values[1].value == 175.0
        
        # Cannot record for non-existent metric
        with pytest.raises(ValueError, match="Metric cpu_usage not found in benchmark"):
            benchmark.record_metric("cpu_usage", 50.0)
    
    def test_complete_benchmark(self):
        """Test completing a benchmark"""
        benchmark = Benchmark(name="Test Benchmark")
        metric = Metric(name="response_time", type=MetricType.RESPONSE_TIME, unit="ms")
        benchmark.add_metric(metric)
        
        benchmark.start()
        benchmark.record_metric("response_time", 150.0)
        
        resource_usage = ResourceUsage(
            cpu_percent=45.0,
            memory_percent=60.0,
            memory_mb=2048.0
        )
        
        benchmark.complete(resource_usage)
        
        assert benchmark.status == BenchmarkStatus.COMPLETED
        assert benchmark.completed_at is not None
        assert benchmark.resource_usage == resource_usage
        assert benchmark.is_completed is True
        
        # Check BenchmarkCompleted event
        events = benchmark.get_events()
        completed_events = [e for e in events if isinstance(e, BenchmarkCompleted)]
        assert len(completed_events) == 1
        assert completed_events[0].duration_seconds > 0
    
    def test_generate_benchmark_report(self):
        """Test generating a benchmark report"""
        benchmark = Benchmark(name="Test Benchmark")
        metric = Metric(name="response_time", type=MetricType.RESPONSE_TIME, unit="ms")
        benchmark.add_metric(metric)
        
        benchmark.start()
        for value in [100, 150, 200, 250, 300]:
            benchmark.record_metric("response_time", float(value))
        
        benchmark.complete()
        
        report = benchmark.generate_report()
        
        assert report["name"] == "Test Benchmark"
        assert "metrics" in report
        assert "response_time" in report["metrics"]
        
        metric_report = report["metrics"]["response_time"]
        assert metric_report["type"] == "response_time"
        assert metric_report["unit"] == "ms"
        assert metric_report["count"] == 5
        assert metric_report["average"] > 0
        assert metric_report["p50"] is not None
        assert metric_report["p95"] is not None
    
    def test_fail_benchmark(self):
        """Test failing a benchmark"""
        benchmark = Benchmark(name="Test Benchmark")
        benchmark.start()
        
        benchmark.fail("Connection timeout")
        
        assert benchmark.status == BenchmarkStatus.FAILED
        assert benchmark.error_message == "Connection timeout"
        assert benchmark.completed_at is not None


class TestOptimizationStrategy:
    """Test cases for OptimizationStrategy aggregate root"""
    
    def test_create_optimization_strategy(self):
        """Test creating an optimization strategy"""
        optimization = Optimization(
            type="cache",
            target_area="database",
            technique="query_caching"
        )
        
        strategy = OptimizationStrategy(
            name="Database Query Caching",
            description="Implement caching for slow database queries",
            optimization=optimization,
            expected_improvement=30.0
        )
        
        assert strategy.name == "Database Query Caching"
        assert strategy.optimization == optimization
        assert strategy.expected_improvement == 30.0
        assert strategy.status == OptimizationStatus.IDENTIFIED
        
        # Check OptimizationIdentified event
        events = strategy.get_events()
        assert len(events) == 1
        assert isinstance(events[0], OptimizationIdentified)
        assert events[0].expected_improvement == 30.0
    
    def test_approve_optimization(self):
        """Test approving an optimization"""
        strategy = OptimizationStrategy(
            name="Test Optimization",
            optimization=Optimization(),
            expected_improvement=20.0
        )
        
        strategy.approve()
        
        assert strategy.status == OptimizationStatus.APPROVED
        
        # Cannot approve non-identified optimization
        with pytest.raises(ValueError, match="Only identified optimizations can be approved"):
            strategy.approve()
    
    def test_apply_optimization(self):
        """Test applying an optimization"""
        strategy = OptimizationStrategy(
            name="Test Optimization",
            optimization=Optimization(),
            expected_improvement=20.0
        )
        
        strategy.approve()
        
        baseline_metrics = {
            "response_time": 500.0,
            "cpu_usage": 70.0
        }
        
        strategy.apply(baseline_metrics)
        
        assert strategy.status == OptimizationStatus.APPLIED
        assert strategy.applied_at is not None
        assert strategy.baseline_metrics == baseline_metrics
        
        # Check OptimizationApplied event
        events = strategy.get_events()
        applied_events = [e for e in events if isinstance(e, OptimizationApplied)]
        assert len(applied_events) == 1
        assert applied_events[0].baseline_metrics == baseline_metrics
    
    def test_validate_optimization(self):
        """Test validating optimization results"""
        strategy = OptimizationStrategy(
            name="Test Optimization",
            optimization=Optimization(),
            expected_improvement=20.0
        )
        
        strategy.approve()
        strategy.apply({"response_time": 500.0, "cpu_usage": 70.0})
        
        post_metrics = {
            "response_time": 400.0,  # 20% improvement
            "cpu_usage": 60.0        # ~14% improvement
        }
        
        strategy.validate(post_metrics)
        
        assert strategy.status == OptimizationStatus.VALIDATED
        assert strategy.validated_at is not None
        assert strategy.post_optimization_metrics == post_metrics
        assert strategy.actual_improvement is not None
        assert strategy.actual_improvement > 0
        assert strategy.is_successful is True
    
    def test_reject_optimization(self):
        """Test rejecting an optimization"""
        strategy = OptimizationStrategy(
            name="Test Optimization",
            optimization=Optimization(),
            expected_improvement=20.0
        )
        
        strategy.reject("Too risky for production")
        
        assert strategy.status == OptimizationStatus.REJECTED
        
        # Cannot reject applied optimization
        strategy2 = OptimizationStrategy(name="Test", optimization=Optimization())
        strategy2.approve()
        strategy2.apply({})
        
        with pytest.raises(ValueError, match="Cannot reject applied or validated optimizations"):
            strategy2.reject("Too late")
    
    def test_rollback_optimization(self):
        """Test rolling back an optimization"""
        strategy = OptimizationStrategy(
            name="Test Optimization",
            optimization=Optimization(),
            expected_improvement=20.0
        )
        
        strategy.approve()
        strategy.apply({})
        
        strategy.rollback()
        
        assert strategy.status == OptimizationStatus.ROLLED_BACK
        
        # Cannot rollback non-applied optimization
        strategy2 = OptimizationStrategy(name="Test", optimization=Optimization())
        with pytest.raises(ValueError, match="Only applied optimizations can be rolled back"):
            strategy2.rollback()


class TestPerformanceProfile:
    """Test cases for PerformanceProfile value object"""
    
    def test_create_performance_profile(self):
        """Test creating a performance profile"""
        profile = PerformanceProfile(
            name="API Performance Profile",
            expected_response_time_ms=200.0,
            expected_throughput_rps=1000.0,
            max_concurrent_users=5000,
            resource_limits={"cpu": 80.0, "memory": 90.0},
            sla_targets={"uptime": 99.9, "p99_latency": 500.0}
        )
        
        assert profile.name == "API Performance Profile"
        assert profile.expected_response_time_ms == 200.0
        assert profile.expected_throughput_rps == 1000.0
        assert profile.max_concurrent_users == 5000
        assert profile.resource_limits["cpu"] == 80.0
        assert profile.sla_targets["uptime"] == 99.9
    
    def test_meets_sla(self):
        """Test checking if metrics meet SLA targets"""
        profile = PerformanceProfile(
            name="Test Profile",
            expected_response_time_ms=200.0,
            expected_throughput_rps=1000.0,
            max_concurrent_users=5000,
            sla_targets={
                "uptime": 99.9,
                "success_rate": 99.5,
                "p99_latency": 500.0,
                "avg_response_time": 200.0
            }
        )
        
        # Uptime and success rate should be >= target
        assert profile.meets_sla("uptime", 99.95) is True
        assert profile.meets_sla("uptime", 99.8) is False
        assert profile.meets_sla("success_rate", 99.5) is True
        assert profile.meets_sla("success_rate", 99.4) is False
        
        # Latency and response time should be <= target
        assert profile.meets_sla("p99_latency", 450.0) is True
        assert profile.meets_sla("p99_latency", 550.0) is False
        assert profile.meets_sla("avg_response_time", 180.0) is True
        assert profile.meets_sla("avg_response_time", 220.0) is False
        
        # No SLA defined should return True
        assert profile.meets_sla("undefined_metric", 1000.0) is True
    
    def test_invalid_performance_profile(self):
        """Test that invalid profile values raise errors"""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            PerformanceProfile(
                name="",
                expected_response_time_ms=200.0,
                expected_throughput_rps=1000.0,
                max_concurrent_users=5000
            )
        
        with pytest.raises(ValueError, match="Expected response time cannot be negative"):
            PerformanceProfile(
                name="Test",
                expected_response_time_ms=-1.0,
                expected_throughput_rps=1000.0,
                max_concurrent_users=5000
            )
        
        with pytest.raises(ValueError, match="Max concurrent users must be at least 1"):
            PerformanceProfile(
                name="Test",
                expected_response_time_ms=200.0,
                expected_throughput_rps=1000.0,
                max_concurrent_users=0
            )


if __name__ == "__main__":
    pytest.main([__file__])