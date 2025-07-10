"""
Performance Context Domain Services

Domain services that orchestrate complex performance monitoring and optimization
operations across multiple aggregates.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .aggregates import Benchmark, Metric, MetricType, OptimizationStrategy
from .repositories import (
    BenchmarkRepository,
    MetricRepository,
    OptimizationStrategyRepository,
)
from .value_objects import (
    BenchmarkResult,
    Optimization,
    PerformanceProfile,
    PerformanceThreshold,
    ResourceUsage,
)


class PerformanceMonitoringService:
    """
    Domain service for continuous performance monitoring
    
    Orchestrates metric collection, threshold monitoring, and alerting
    across the performance domain.
    """
    
    def __init__(
        self,
        metric_repo: MetricRepository,
        benchmark_repo: BenchmarkRepository,
    ):
        self.metric_repo = metric_repo
        self.benchmark_repo = benchmark_repo
    
    async def monitor_system_health(self) -> Dict[str, Any]:
        """
        Monitor overall system health and performance
        
        Returns:
            System health report with metrics and status
        """
        # Get all active metrics
        active_metrics = await self.metric_repo.find_active_metrics()
        
        health_report = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
            "violations": [],
            "recommendations": [],
        }
        
        # Check each metric
        for metric in active_metrics:
            latest_value = metric.get_latest_value()
            if latest_value is None:
                continue
            
            metric_health = {
                "value": latest_value,
                "unit": metric.unit,
                "average_1h": metric.get_average(60),
                "p95": metric.get_percentile(95),
                "status": "normal",
            }
            
            # Check for threshold violations
            for threshold in metric.thresholds:
                if threshold.is_exceeded(latest_value):
                    metric_health["status"] = threshold.severity
                    health_report["violations"].append({
                        "metric": metric.name,
                        "threshold": threshold.name,
                        "severity": threshold.severity,
                        "value": latest_value,
                        "threshold_value": threshold.value,
                    })
                    
                    if threshold.severity == "critical":
                        health_report["status"] = "critical"
                    elif threshold.severity == "warning" and health_report["status"] != "critical":
                        health_report["status"] = "warning"
            
            health_report["metrics"][metric.name] = metric_health
        
        # Generate recommendations
        health_report["recommendations"] = self._generate_recommendations(
            health_report["metrics"],
            health_report["violations"]
        )
        
        return health_report
    
    async def analyze_performance_trends(
        self,
        metric_names: List[str],
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Analyze performance trends over a period
        
        Args:
            metric_names: List of metric names to analyze
            period_days: Number of days to analyze
            
        Returns:
            Trend analysis report
        """
        trends = {}
        
        for metric_name in metric_names:
            metric = await self.metric_repo.find_by_name(metric_name)
            if not metric:
                continue
            
            # Calculate trend statistics
            current_avg = metric.get_average(24 * 60)  # Last 24 hours
            previous_avg = metric.get_average(period_days * 24 * 60)  # Full period
            
            if previous_avg > 0:
                trend_percentage = ((current_avg - previous_avg) / previous_avg) * 100
            else:
                trend_percentage = 0
            
            trend_direction = "stable"
            if trend_percentage > 5:
                trend_direction = "increasing"
            elif trend_percentage < -5:
                trend_direction = "decreasing"
            
            trends[metric_name] = {
                "current_average": current_avg,
                "period_average": previous_avg,
                "trend_percentage": trend_percentage,
                "trend_direction": trend_direction,
                "p50": metric.get_percentile(50),
                "p95": metric.get_percentile(95),
                "p99": metric.get_percentile(99),
            }
        
        return {
            "period_days": period_days,
            "analyzed_at": datetime.now().isoformat(),
            "trends": trends,
        }
    
    async def detect_anomalies(
        self,
        metric: Metric,
        sensitivity: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in metric values using statistical methods
        
        Args:
            metric: The metric to analyze
            sensitivity: Standard deviation multiplier for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        if len(metric.values) < 10:
            return []  # Not enough data for anomaly detection
        
        # Calculate mean and standard deviation
        values = [v.value for v in metric.values]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        
        # Detect anomalies
        anomalies = []
        upper_bound = mean + (sensitivity * std_dev)
        lower_bound = mean - (sensitivity * std_dev)
        
        for metric_value in metric.values:
            if metric_value.value > upper_bound or metric_value.value < lower_bound:
                anomalies.append({
                    "timestamp": metric_value.timestamp.isoformat(),
                    "value": metric_value.value,
                    "expected_range": [lower_bound, upper_bound],
                    "deviation": abs(metric_value.value - mean) / std_dev,
                })
        
        return anomalies
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, Any],
        violations: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate performance recommendations based on metrics and violations"""
        recommendations = []
        
        # Check for high resource usage
        if "cpu_usage" in metrics and metrics["cpu_usage"]["average_1h"] > 80:
            recommendations.append(
                "CPU usage is high. Consider scaling horizontally or optimizing CPU-intensive operations."
            )
        
        if "memory_usage" in metrics and metrics["memory_usage"]["average_1h"] > 85:
            recommendations.append(
                "Memory usage is high. Review memory allocations and consider increasing available memory."
            )
        
        # Check for response time issues
        if "response_time" in metrics and metrics["response_time"]["p95"] > 1000:
            recommendations.append(
                "95th percentile response time exceeds 1 second. Investigate slow endpoints and database queries."
            )
        
        # Check for error rate
        if "error_rate" in metrics and metrics["error_rate"]["value"] > 1:
            recommendations.append(
                "Error rate is above 1%. Review error logs and implement proper error handling."
            )
        
        # Critical violations
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        if critical_violations:
            recommendations.insert(0, 
                f"CRITICAL: {len(critical_violations)} critical threshold violations detected. Immediate action required."
            )
        
        return recommendations


class BenchmarkExecutionService:
    """
    Domain service for executing and analyzing performance benchmarks
    
    Provides sophisticated benchmark execution and comparison capabilities.
    """
    
    def __init__(
        self,
        benchmark_repo: BenchmarkRepository,
        metric_repo: MetricRepository,
    ):
        self.benchmark_repo = benchmark_repo
        self.metric_repo = metric_repo
    
    async def execute_benchmark(
        self,
        benchmark: Benchmark,
        profile: PerformanceProfile,
    ) -> Dict[str, Any]:
        """
        Execute a performance benchmark against a profile
        
        Args:
            benchmark: The benchmark to execute
            profile: Performance profile with expectations
            
        Returns:
            Benchmark execution results
        """
        # Start the benchmark
        benchmark.start()
        
        try:
            # Simulate benchmark execution
            # In real implementation, this would run actual performance tests
            results = await self._run_benchmark_scenario(benchmark, profile)
            
            # Record results as metrics
            for result in results:
                metric_name = f"benchmark_{result.metric_name}"
                benchmark.record_metric(metric_name, result.value)
            
            # Complete benchmark
            resource_usage = await self._capture_resource_usage()
            benchmark.complete(resource_usage)
            
            # Save benchmark
            await self.benchmark_repo.save(benchmark)
            
            # Generate and return report
            return benchmark.generate_report()
            
        except Exception as e:
            benchmark.fail(str(e))
            await self.benchmark_repo.save(benchmark)
            raise
    
    async def compare_benchmarks(
        self,
        baseline_id: UUID,
        comparison_ids: List[UUID],
    ) -> Dict[str, Any]:
        """
        Compare multiple benchmark runs
        
        Args:
            baseline_id: ID of the baseline benchmark
            comparison_ids: IDs of benchmarks to compare
            
        Returns:
            Comparison report
        """
        baseline = await self.benchmark_repo.find_by_id(baseline_id)
        if not baseline or not baseline.is_completed:
            raise ValueError("Invalid or incomplete baseline benchmark")
        
        comparisons = []
        for comp_id in comparison_ids:
            comp_benchmark = await self.benchmark_repo.find_by_id(comp_id)
            if comp_benchmark and comp_benchmark.is_completed:
                comparisons.append(comp_benchmark)
        
        baseline_report = baseline.generate_report()
        comparison_report = {
            "baseline": {
                "id": str(baseline_id),
                "name": baseline.name,
                "metrics": baseline_report["metrics"],
            },
            "comparisons": [],
            "summary": {},
        }
        
        # Compare each benchmark against baseline
        for comp in comparisons:
            comp_report = comp.generate_report()
            comp_data = {
                "id": str(comp.id),
                "name": comp.name,
                "differences": {},
            }
            
            # Calculate differences for each metric
            for metric_name, baseline_data in baseline_report["metrics"].items():
                if metric_name in comp_report["metrics"]:
                    comp_metric = comp_report["metrics"][metric_name]
                    baseline_avg = baseline_data["average"]
                    comp_avg = comp_metric["average"]
                    
                    if baseline_avg > 0:
                        diff_percentage = ((comp_avg - baseline_avg) / baseline_avg) * 100
                    else:
                        diff_percentage = 0
                    
                    comp_data["differences"][metric_name] = {
                        "baseline": baseline_avg,
                        "comparison": comp_avg,
                        "difference": comp_avg - baseline_avg,
                        "percentage": diff_percentage,
                        "improved": diff_percentage < 0 if "time" in metric_name else diff_percentage > 0,
                    }
            
            comparison_report["comparisons"].append(comp_data)
        
        # Generate summary
        comparison_report["summary"] = self._generate_comparison_summary(comparison_report)
        
        return comparison_report
    
    async def _run_benchmark_scenario(
        self,
        benchmark: Benchmark,
        profile: PerformanceProfile,
    ) -> List[BenchmarkResult]:
        """Execute the actual benchmark scenario"""
        # This is a simulation - real implementation would run actual tests
        import random
        
        results = []
        
        # Response time benchmark
        response_times = [
            random.uniform(
                profile.expected_response_time_ms * 0.8,
                profile.expected_response_time_ms * 1.2
            )
            for _ in range(100)
        ]
        
        results.append(BenchmarkResult(
            metric_name="response_time",
            value=sum(response_times) / len(response_times),
            unit="ms",
            percentiles={
                "p50": sorted(response_times)[50],
                "p95": sorted(response_times)[95],
                "p99": sorted(response_times)[99],
            }
        ))
        
        # Throughput benchmark
        throughput = random.uniform(
            profile.expected_throughput_rps * 0.9,
            profile.expected_throughput_rps * 1.1
        )
        
        results.append(BenchmarkResult(
            metric_name="throughput",
            value=throughput,
            unit="rps",
        ))
        
        return results
    
    async def _capture_resource_usage(self) -> ResourceUsage:
        """Capture current resource usage"""
        # This would integrate with system monitoring tools
        import random
        
        return ResourceUsage(
            cpu_percent=random.uniform(20, 80),
            memory_percent=random.uniform(30, 70),
            memory_mb=random.uniform(500, 2000),
            disk_io_read_mb=random.uniform(10, 100),
            disk_io_write_mb=random.uniform(5, 50),
            network_io_sent_mb=random.uniform(1, 20),
            network_io_recv_mb=random.uniform(1, 20),
        )
    
    def _generate_comparison_summary(self, comparison_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of benchmark comparisons"""
        summary = {
            "total_comparisons": len(comparison_report["comparisons"]),
            "improved_metrics": 0,
            "degraded_metrics": 0,
            "significant_changes": [],
        }
        
        for comp in comparison_report["comparisons"]:
            for metric_name, diff in comp["differences"].items():
                if abs(diff["percentage"]) > 10:  # Significant change threshold
                    summary["significant_changes"].append({
                        "benchmark": comp["name"],
                        "metric": metric_name,
                        "change": diff["percentage"],
                        "improved": diff["improved"],
                    })
                
                if diff["improved"]:
                    summary["improved_metrics"] += 1
                else:
                    summary["degraded_metrics"] += 1
        
        return summary


class OptimizationManagementService:
    """
    Domain service for managing performance optimizations
    
    Coordinates the identification, application, and validation of
    performance optimizations.
    """
    
    def __init__(
        self,
        optimization_repo: OptimizationStrategyRepository,
        metric_repo: MetricRepository,
    ):
        self.optimization_repo = optimization_repo
        self.metric_repo = metric_repo
    
    async def identify_optimization_opportunities(
        self,
        performance_data: Dict[str, Any],
    ) -> List[OptimizationStrategy]:
        """
        Identify potential optimization opportunities from performance data
        
        Args:
            performance_data: Current performance metrics and analysis
            
        Returns:
            List of identified optimization strategies
        """
        opportunities = []
        
        # Check for database query optimization opportunities
        if "database_query_time" in performance_data:
            avg_query_time = performance_data["database_query_time"]["average"]
            if avg_query_time > 100:  # ms
                optimization = OptimizationStrategy(
                    name="Database Query Optimization",
                    description="Optimize slow database queries through indexing and query restructuring",
                    optimization=Optimization(
                        type="query",
                        target_area="database",
                        technique="indexing",
                        implementation_details={
                            "analyze_slow_queries": True,
                            "add_indexes": True,
                            "optimize_joins": True,
                        },
                        risk_level="low",
                    ),
                    expected_improvement=30.0,  # 30% improvement expected
                )
                opportunities.append(optimization)
        
        # Check for caching opportunities
        if "cache_hit_rate" in performance_data:
            hit_rate = performance_data["cache_hit_rate"]["value"]
            if hit_rate < 80:  # percent
                optimization = OptimizationStrategy(
                    name="Cache Implementation",
                    description="Implement or improve caching strategy",
                    optimization=Optimization(
                        type="cache",
                        target_area="api",
                        technique="caching",
                        implementation_details={
                            "cache_type": "redis",
                            "ttl_seconds": 3600,
                            "cache_warming": True,
                        },
                        risk_level="medium",
                    ),
                    expected_improvement=25.0,
                )
                opportunities.append(optimization)
        
        # Check for parallelization opportunities
        if "cpu_usage" in performance_data and "response_time" in performance_data:
            cpu_usage = performance_data["cpu_usage"]["average"]
            response_time = performance_data["response_time"]["p95"]
            if cpu_usage < 50 and response_time > 500:  # Underutilized CPU with high response time
                optimization = OptimizationStrategy(
                    name="Parallelization",
                    description="Implement parallel processing for CPU-bound operations",
                    optimization=Optimization(
                        type="algorithm",
                        target_area="processing",
                        technique="parallelization",
                        implementation_details={
                            "worker_threads": 4,
                            "batch_processing": True,
                        },
                        risk_level="medium",
                    ),
                    expected_improvement=40.0,
                )
                opportunities.append(optimization)
        
        # Save identified opportunities
        for opp in opportunities:
            await self.optimization_repo.save(opp)
        
        return opportunities
    
    async def validate_optimization(
        self,
        optimization_id: UUID,
        validation_period_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Validate an applied optimization by comparing metrics
        
        Args:
            optimization_id: ID of the optimization to validate
            validation_period_hours: Hours to wait before validation
            
        Returns:
            Validation report
        """
        optimization = await self.optimization_repo.find_by_id(optimization_id)
        if not optimization or optimization.status != OptimizationStatus.APPLIED:
            raise ValueError("Optimization not found or not applied")
        
        # Collect post-optimization metrics
        post_metrics = {}
        for metric_name in optimization.baseline_metrics.keys():
            metric = await self.metric_repo.find_by_name(metric_name)
            if metric:
                # Get average over validation period
                post_metrics[metric_name] = metric.get_average(validation_period_hours * 60)
        
        # Validate the optimization
        optimization.validate(post_metrics)
        await self.optimization_repo.save(optimization)
        
        # Generate validation report
        validation_report = {
            "optimization_id": str(optimization_id),
            "name": optimization.name,
            "status": "successful" if optimization.is_successful else "failed",
            "expected_improvement": optimization.expected_improvement,
            "actual_improvement": optimization.actual_improvement,
            "baseline_metrics": optimization.baseline_metrics,
            "post_metrics": post_metrics,
            "validated_at": datetime.now().isoformat(),
        }
        
        return validation_report