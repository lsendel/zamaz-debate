"""
Performance Context Repository Implementations

JSON-based implementations of Performance context repositories.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from src.contexts.performance import (
    Benchmark,
    BenchmarkRepository,
    BenchmarkStatus,
    Metric,
    MetricRepository,
    MetricType,
    OptimizationStrategy,
    OptimizationStrategyRepository,
    PerformanceAlertRepository,
)

from .base import JsonRepository


class JsonMetricRepository(JsonRepository, MetricRepository):
    """JSON-based implementation of MetricRepository"""
    
    def __init__(self, storage_path: str = "data/metrics"):
        super().__init__(storage_path, "metric")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metric data for indexing"""
        return {
            "name": data.get("name"),
            "type": data.get("type"),
            "source": data.get("source"),
            "recorded_at": data.get("recorded_at"),
        }
    
    async def save(self, metric: Metric) -> None:
        """Save a metric"""
        await self.save_entity(metric, metric.id)
    
    async def find_by_id(self, metric_id: UUID) -> Optional[Metric]:
        """Find a metric by ID"""
        return await self.load_entity(metric_id, Metric)
    
    async def find_by_name(self, name: str) -> List[Metric]:
        """Find metrics by name"""
        all_metrics = await self.find_all(Metric)
        return [m for m in all_metrics if m.name == name]
    
    async def find_by_type(self, metric_type: MetricType) -> List[Metric]:
        """Find metrics by type"""
        all_metrics = await self.find_all(Metric)
        return [m for m in all_metrics if m.type == metric_type]
    
    async def find_by_source(self, source: str) -> List[Metric]:
        """Find metrics by source"""
        all_metrics = await self.find_all(Metric)
        return [m for m in all_metrics if m.source == source]
    
    async def find_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Metric]:
        """Find metrics within a time range"""
        all_metrics = await self.find_all(Metric)
        
        filtered = []
        for metric in all_metrics:
            if start_time <= metric.recorded_at <= end_time:
                filtered.append(metric)
        
        return filtered
    
    async def find_above_threshold(
        self,
        metric_name: str,
        threshold: float,
    ) -> List[Metric]:
        """Find metrics above a threshold"""
        all_metrics = await self.find_all(Metric)
        
        return [
            m for m in all_metrics
            if m.name == metric_name and m.values.current > threshold
        ]
    
    async def get_latest(self, metric_name: str) -> Optional[Metric]:
        """Get the latest metric by name"""
        metrics = await self.find_by_name(metric_name)
        
        if not metrics:
            return None
        
        # Sort by recorded_at descending
        metrics.sort(key=lambda m: m.recorded_at, reverse=True)
        
        return metrics[0]
    
    async def update(self, metric: Metric) -> bool:
        """Update a metric"""
        if await self.exists(metric.id):
            await self.save(metric)
            return True
        return False
    
    async def delete(self, metric_id: UUID) -> bool:
        """Delete a metric"""
        return await self.delete_entity(metric_id)
    
    async def get_aggregated_metrics(
        self,
        metric_name: str,
        aggregation_type: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """Get aggregated metrics over time intervals"""
        metrics = await self.find_by_time_range(start_time, end_time)
        metrics = [m for m in metrics if m.name == metric_name]
        
        if not metrics:
            return []
        
        # Sort by time
        metrics.sort(key=lambda m: m.recorded_at)
        
        # Simple aggregation (in real implementation, would use proper time series logic)
        aggregated = []
        
        if interval == "hour":
            # Group by hour
            current_hour = None
            hour_metrics = []
            
            for metric in metrics:
                metric_hour = metric.recorded_at.replace(minute=0, second=0, microsecond=0)
                
                if current_hour != metric_hour:
                    if hour_metrics:
                        aggregated.append(self._aggregate_metrics(
                            hour_metrics,
                            aggregation_type,
                            current_hour
                        ))
                    current_hour = metric_hour
                    hour_metrics = [metric]
                else:
                    hour_metrics.append(metric)
            
            # Don't forget the last group
            if hour_metrics:
                aggregated.append(self._aggregate_metrics(
                    hour_metrics,
                    aggregation_type,
                    current_hour
                ))
        
        return aggregated
    
    def _aggregate_metrics(
        self,
        metrics: List[Metric],
        aggregation_type: str,
        timestamp: datetime,
    ) -> Dict[str, Any]:
        """Aggregate a list of metrics"""
        values = [m.values.current for m in metrics]
        
        if aggregation_type == "avg":
            result = sum(values) / len(values)
        elif aggregation_type == "sum":
            result = sum(values)
        elif aggregation_type == "max":
            result = max(values)
        elif aggregation_type == "min":
            result = min(values)
        else:
            result = sum(values) / len(values)  # Default to average
        
        return {
            "timestamp": timestamp.isoformat(),
            "value": result,
            "count": len(metrics),
        }
    
    async def count_by_type(self) -> Dict[str, int]:
        """Count metrics by type"""
        all_metrics = await self.find_all(Metric)
        
        counts = {}
        for metric in all_metrics:
            type_name = metric.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        
        return counts


class JsonBenchmarkRepository(JsonRepository, BenchmarkRepository):
    """JSON-based implementation of BenchmarkRepository"""
    
    def __init__(self, storage_path: str = "data/benchmarks"):
        super().__init__(storage_path, "benchmark")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract benchmark data for indexing"""
        return {
            "name": data.get("name"),
            "status": data.get("status"),
            "environment": data.get("environment"),
            "started_at": data.get("started_at"),
            "completed_at": data.get("completed_at"),
        }
    
    async def save(self, benchmark: Benchmark) -> None:
        """Save a benchmark"""
        await self.save_entity(benchmark, benchmark.id)
    
    async def find_by_id(self, benchmark_id: UUID) -> Optional[Benchmark]:
        """Find a benchmark by ID"""
        return await self.load_entity(benchmark_id, Benchmark)
    
    async def find_by_name(self, name: str) -> List[Benchmark]:
        """Find benchmarks by name"""
        all_benchmarks = await self.find_all(Benchmark)
        return [b for b in all_benchmarks if b.name == name]
    
    async def find_by_status(self, status: BenchmarkStatus) -> List[Benchmark]:
        """Find benchmarks by status"""
        all_benchmarks = await self.find_all(Benchmark)
        return [b for b in all_benchmarks if b.status == status]
    
    async def find_running(self) -> List[Benchmark]:
        """Find currently running benchmarks"""
        return await self.find_by_status(BenchmarkStatus.RUNNING)
    
    async def find_completed_between(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Benchmark]:
        """Find benchmarks completed within a time range"""
        all_benchmarks = await self.find_all(Benchmark)
        
        completed = []
        for benchmark in all_benchmarks:
            if (benchmark.status == BenchmarkStatus.COMPLETED and
                benchmark.completed_at and
                start_time <= benchmark.completed_at <= end_time):
                completed.append(benchmark)
        
        return completed
    
    async def find_by_environment(self, environment: str) -> List[Benchmark]:
        """Find benchmarks by environment"""
        all_benchmarks = await self.find_all(Benchmark)
        return [b for b in all_benchmarks if b.environment == environment]
    
    async def update(self, benchmark: Benchmark) -> bool:
        """Update a benchmark"""
        if await self.exists(benchmark.id):
            await self.save(benchmark)
            return True
        return False
    
    async def delete(self, benchmark_id: UUID) -> bool:
        """Delete a benchmark"""
        return await self.delete_entity(benchmark_id)
    
    async def get_baseline_comparison(
        self,
        benchmark_id: UUID,
    ) -> Dict[str, Any]:
        """Compare benchmark results to baseline"""
        benchmark = await self.find_by_id(benchmark_id)
        
        if not benchmark or not benchmark.results:
            return {}
        
        # Find previous benchmarks of the same name
        same_name_benchmarks = await self.find_by_name(benchmark.name)
        
        # Filter to completed benchmarks before this one
        baselines = [
            b for b in same_name_benchmarks
            if (b.id != benchmark_id and
                b.status == BenchmarkStatus.COMPLETED and
                b.completed_at and
                b.completed_at < benchmark.started_at)
        ]
        
        if not baselines:
            return {
                "has_baseline": False,
                "message": "No baseline found for comparison",
            }
        
        # Sort by completion time and get the most recent
        baselines.sort(key=lambda b: b.completed_at, reverse=True)
        baseline = baselines[0]
        
        # Compare results
        comparison = {}
        
        for metric_name, current_value in benchmark.results.items():
            if metric_name in baseline.results:
                baseline_value = baseline.results[metric_name]
                
                if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
                    change_percent = ((current_value - baseline_value) / baseline_value) * 100
                    comparison[metric_name] = {
                        "current": current_value,
                        "baseline": baseline_value,
                        "change_percent": change_percent,
                        "improved": change_percent < 0 if "time" in metric_name.lower() else change_percent > 0,
                    }
        
        return {
            "has_baseline": True,
            "baseline_id": str(baseline.id),
            "baseline_date": baseline.completed_at.isoformat(),
            "comparison": comparison,
        }
    
    async def get_trend_analysis(
        self,
        benchmark_name: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Analyze performance trends for a benchmark"""
        end_time = datetime.now()
        start_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_time = datetime.fromtimestamp(start_time)
        
        # Get all benchmarks with this name in the time range
        all_benchmarks = await self.find_by_name(benchmark_name)
        
        relevant_benchmarks = []
        for benchmark in all_benchmarks:
            if (benchmark.status == BenchmarkStatus.COMPLETED and
                benchmark.completed_at and
                start_time <= benchmark.completed_at <= end_time):
                relevant_benchmarks.append(benchmark)
        
        # Sort by completion time
        relevant_benchmarks.sort(key=lambda b: b.completed_at)
        
        # Build trend data
        trends = []
        for benchmark in relevant_benchmarks:
            trend_point = {
                "timestamp": benchmark.completed_at.isoformat(),
                "benchmark_id": str(benchmark.id),
                "results": benchmark.results,
            }
            trends.append(trend_point)
        
        return trends


class JsonOptimizationStrategyRepository(JsonRepository, OptimizationStrategyRepository):
    """JSON-based implementation of OptimizationStrategyRepository"""
    
    def __init__(self, storage_path: str = "data/optimization_strategies"):
        super().__init__(storage_path, "optimization_strategy")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract optimization strategy data for indexing"""
        return {
            "name": data.get("name"),
            "target_metric": data.get("target_metric"),
            "is_active": data.get("is_active"),
            "effectiveness_score": data.get("effectiveness_score"),
            "created_at": data.get("created_at"),
        }
    
    async def save(self, strategy: OptimizationStrategy) -> None:
        """Save an optimization strategy"""
        await self.save_entity(strategy, strategy.id)
    
    async def find_by_id(self, strategy_id: UUID) -> Optional[OptimizationStrategy]:
        """Find an optimization strategy by ID"""
        return await self.load_entity(strategy_id, OptimizationStrategy)
    
    async def find_by_target_metric(self, metric_name: str) -> List[OptimizationStrategy]:
        """Find strategies targeting a specific metric"""
        all_strategies = await self.find_all(OptimizationStrategy)
        return [s for s in all_strategies if s.target_metric == metric_name]
    
    async def find_active(self) -> List[OptimizationStrategy]:
        """Find all active optimization strategies"""
        all_strategies = await self.find_all(OptimizationStrategy)
        return [s for s in all_strategies if s.is_active]
    
    async def find_effective_strategies(
        self,
        min_effectiveness: float = 0.7,
    ) -> List[OptimizationStrategy]:
        """Find strategies with high effectiveness"""
        all_strategies = await self.find_all(OptimizationStrategy)
        
        effective = []
        for strategy in all_strategies:
            if strategy.effectiveness_score and strategy.effectiveness_score >= min_effectiveness:
                effective.append(strategy)
        
        # Sort by effectiveness score descending
        effective.sort(key=lambda s: s.effectiveness_score or 0, reverse=True)
        
        return effective
    
    async def find_by_technique(self, technique: str) -> List[OptimizationStrategy]:
        """Find strategies using a specific technique"""
        all_strategies = await self.find_all(OptimizationStrategy)
        
        matching = []
        for strategy in all_strategies:
            for opt in strategy.optimizations:
                if technique.lower() in opt.technique.lower():
                    matching.append(strategy)
                    break
        
        return matching
    
    async def update(self, strategy: OptimizationStrategy) -> bool:
        """Update an optimization strategy"""
        if await self.exists(strategy.id):
            await self.save(strategy)
            return True
        return False
    
    async def delete(self, strategy_id: UUID) -> bool:
        """Delete an optimization strategy"""
        return await self.delete_entity(strategy_id)
    
    async def get_strategy_performance(
        self,
        strategy_id: UUID,
    ) -> Dict[str, Any]:
        """Get performance metrics for a strategy"""
        strategy = await self.find_by_id(strategy_id)
        
        if not strategy:
            return {}
        
        # Calculate performance based on optimizations
        total_impact = 0
        successful_optimizations = 0
        
        for optimization in strategy.optimizations:
            if optimization.expected_impact:
                # Parse impact percentage
                impact_str = optimization.expected_impact.replace("%", "")
                try:
                    impact = float(impact_str)
                    total_impact += impact
                    if impact > 0:
                        successful_optimizations += 1
                except ValueError:
                    pass
        
        optimization_count = len(strategy.optimizations)
        
        return {
            "strategy_name": strategy.name,
            "optimization_count": optimization_count,
            "successful_optimizations": successful_optimizations,
            "average_impact": total_impact / optimization_count if optimization_count > 0 else 0,
            "effectiveness_score": strategy.effectiveness_score,
            "is_active": strategy.is_active,
        }


class JsonPerformanceAlertRepository(JsonRepository, PerformanceAlertRepository):
    """JSON-based implementation of PerformanceAlertRepository"""
    
    def __init__(self, storage_path: str = "data/performance_alerts"):
        super().__init__(storage_path, "performance_alert")
    
    async def create_alert(
        self,
        metric_name: str,
        threshold: float,
        condition: str,
        severity: str,
    ) -> str:
        """Create a performance alert"""
        alert = {
            "id": str(UUID()),
            "metric_name": metric_name,
            "threshold": threshold,
            "condition": condition,
            "severity": severity,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
        }
        
        await self.save_entity(alert, UUID(alert["id"]))
        
        return alert["id"]
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        all_alerts = await self.find_all(dict)
        return [a for a in all_alerts if a.get("is_active", False)]
    
    async def trigger_alert(
        self,
        alert_id: str,
        current_value: float,
        timestamp: datetime,
    ) -> None:
        """Record an alert trigger"""
        trigger = {
            "id": str(UUID()),
            "alert_id": alert_id,
            "current_value": current_value,
            "timestamp": timestamp.isoformat(),
            "status": "triggered",
        }
        
        # Save trigger separately
        trigger_path = self.storage_path / "triggers"
        trigger_path.mkdir(exist_ok=True)
        
        await JsonRepository(str(trigger_path), "alert_trigger").save_entity(
            trigger,
            UUID(trigger["id"])
        )
    
    async def get_alert_history(
        self,
        alert_id: str,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Get alert trigger history"""
        trigger_repo = JsonRepository(str(self.storage_path / "triggers"), "alert_trigger")
        all_triggers = await trigger_repo.find_all(dict)
        
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        history = []
        for trigger in all_triggers:
            if trigger.get("alert_id") == alert_id:
                timestamp = datetime.fromisoformat(trigger["timestamp"])
                if timestamp.timestamp() >= cutoff_date:
                    history.append(trigger)
        
        # Sort by timestamp descending
        history.sort(key=lambda t: t["timestamp"], reverse=True)
        
        return history
    
    async def disable_alert(self, alert_id: str) -> bool:
        """Disable an alert"""
        alert = await self.load_entity(UUID(alert_id), dict)
        
        if alert:
            alert["is_active"] = False
            alert["disabled_at"] = datetime.now().isoformat()
            await self.save_entity(alert, UUID(alert_id))
            return True
        
        return False
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        all_alerts = await self.find_all(dict)
        trigger_repo = JsonRepository(str(self.storage_path / "triggers"), "alert_trigger")
        all_triggers = await trigger_repo.find_all(dict)
        
        active_count = sum(1 for a in all_alerts if a.get("is_active", False))
        
        # Count triggers by severity
        severity_counts = {}
        for alert in all_alerts:
            alert_id = alert["id"]
            severity = alert.get("severity", "medium")
            
            trigger_count = sum(1 for t in all_triggers if t.get("alert_id") == alert_id)
            
            if severity not in severity_counts:
                severity_counts[severity] = 0
            severity_counts[severity] += trigger_count
        
        return {
            "total_alerts": len(all_alerts),
            "active_alerts": active_count,
            "total_triggers": len(all_triggers),
            "triggers_by_severity": severity_counts,
        }