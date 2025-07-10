"""
Performance Context Repository Interfaces

Repository interfaces for the performance context following DDD patterns.
These abstractions hide persistence details from the domain layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .aggregates import Benchmark, Metric, OptimizationStrategy


class MetricRepository(ABC):
    """
    Repository interface for Metric aggregate
    
    Provides persistence operations for performance metrics.
    """
    
    @abstractmethod
    async def save(self, metric: Metric) -> None:
        """
        Save a metric
        
        Args:
            metric: The metric to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, metric_id: UUID) -> Optional[Metric]:
        """
        Find a metric by ID
        
        Args:
            metric_id: The ID of the metric
            
        Returns:
            The metric if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Metric]:
        """
        Find a metric by name
        
        Args:
            name: The metric name
            
        Returns:
            The metric if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_type(self, metric_type: str) -> List[Metric]:
        """
        Find metrics by type
        
        Args:
            metric_type: The type of metrics to find
            
        Returns:
            List of metrics of the given type
        """
        pass
    
    @abstractmethod
    async def find_by_tags(self, tags: Dict[str, str]) -> List[Metric]:
        """
        Find metrics by tags
        
        Args:
            tags: Dictionary of tags to match
            
        Returns:
            List of metrics matching all tags
        """
        pass
    
    @abstractmethod
    async def find_with_threshold_violations(self) -> List[Metric]:
        """
        Find metrics that have exceeded thresholds
        
        Returns:
            List of metrics with threshold violations
        """
        pass
    
    @abstractmethod
    async def find_active_metrics(self) -> List[Metric]:
        """
        Find metrics that have recent values
        
        Returns:
            List of active metrics
        """
        pass
    
    @abstractmethod
    async def delete(self, metric_id: UUID) -> bool:
        """
        Delete a metric
        
        Args:
            metric_id: The ID of the metric to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def delete_old_values(self, before_date: datetime) -> int:
        """
        Delete metric values older than a specific date
        
        Args:
            before_date: Delete values before this date
            
        Returns:
            Number of values deleted
        """
        pass
    
    @abstractmethod
    async def exists(self, metric_id: UUID) -> bool:
        """
        Check if a metric exists
        
        Args:
            metric_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class BenchmarkRepository(ABC):
    """
    Repository interface for Benchmark aggregate
    
    Provides persistence operations for performance benchmarks.
    """
    
    @abstractmethod
    async def save(self, benchmark: Benchmark) -> None:
        """
        Save a benchmark
        
        Args:
            benchmark: The benchmark to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, benchmark_id: UUID) -> Optional[Benchmark]:
        """
        Find a benchmark by ID
        
        Args:
            benchmark_id: The ID of the benchmark
            
        Returns:
            The benchmark if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> List[Benchmark]:
        """
        Find benchmarks by name
        
        Args:
            name: The benchmark name
            
        Returns:
            List of benchmarks with matching name
        """
        pass
    
    @abstractmethod
    async def find_running(self) -> List[Benchmark]:
        """
        Find all currently running benchmarks
        
        Returns:
            List of running benchmarks
        """
        pass
    
    @abstractmethod
    async def find_completed(self, limit: int = 10) -> List[Benchmark]:
        """
        Find recently completed benchmarks
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of completed benchmarks
        """
        pass
    
    @abstractmethod
    async def find_by_scenario(self, scenario_name: str) -> List[Benchmark]:
        """
        Find benchmarks by scenario
        
        Args:
            scenario_name: Name of the scenario
            
        Returns:
            List of benchmarks for the scenario
        """
        pass
    
    @abstractmethod
    async def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Benchmark]:
        """
        Find benchmarks within a date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of benchmarks within the range
        """
        pass
    
    @abstractmethod
    async def get_comparison(self, benchmark_ids: List[UUID]) -> Dict[str, Any]:
        """
        Get comparison data for multiple benchmarks
        
        Args:
            benchmark_ids: List of benchmark IDs to compare
            
        Returns:
            Comparison data dictionary
        """
        pass
    
    @abstractmethod
    async def delete(self, benchmark_id: UUID) -> bool:
        """
        Delete a benchmark
        
        Args:
            benchmark_id: The ID of the benchmark to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, benchmark_id: UUID) -> bool:
        """
        Check if a benchmark exists
        
        Args:
            benchmark_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class OptimizationStrategyRepository(ABC):
    """
    Repository interface for OptimizationStrategy aggregate
    
    Provides persistence operations for performance optimization strategies.
    """
    
    @abstractmethod
    async def save(self, optimization: OptimizationStrategy) -> None:
        """
        Save an optimization strategy
        
        Args:
            optimization: The optimization strategy to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, optimization_id: UUID) -> Optional[OptimizationStrategy]:
        """
        Find an optimization strategy by ID
        
        Args:
            optimization_id: The ID of the optimization
            
        Returns:
            The optimization if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_pending(self) -> List[OptimizationStrategy]:
        """
        Find optimization strategies pending approval
        
        Returns:
            List of pending optimizations
        """
        pass
    
    @abstractmethod
    async def find_approved(self) -> List[OptimizationStrategy]:
        """
        Find approved optimization strategies
        
        Returns:
            List of approved optimizations
        """
        pass
    
    @abstractmethod
    async def find_applied(self) -> List[OptimizationStrategy]:
        """
        Find applied optimization strategies
        
        Returns:
            List of applied optimizations
        """
        pass
    
    @abstractmethod
    async def find_successful(self) -> List[OptimizationStrategy]:
        """
        Find successful optimization strategies
        
        Returns:
            List of successful optimizations
        """
        pass
    
    @abstractmethod
    async def find_by_target_area(self, target_area: str) -> List[OptimizationStrategy]:
        """
        Find optimizations by target area
        
        Args:
            target_area: The target area (e.g., "database", "api")
            
        Returns:
            List of optimizations for the target area
        """
        pass
    
    @abstractmethod
    async def find_by_type(self, optimization_type: str) -> List[OptimizationStrategy]:
        """
        Find optimizations by type
        
        Args:
            optimization_type: The type of optimization
            
        Returns:
            List of optimizations of the given type
        """
        pass
    
    @abstractmethod
    async def update(self, optimization: OptimizationStrategy) -> bool:
        """
        Update an optimization strategy
        
        Args:
            optimization: The optimization to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, optimization_id: UUID) -> bool:
        """
        Delete an optimization strategy
        
        Args:
            optimization_id: The ID of the optimization to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, optimization_id: UUID) -> bool:
        """
        Check if an optimization exists
        
        Args:
            optimization_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class PerformanceReportRepository(ABC):
    """
    Repository interface for performance reports
    
    Provides query operations for performance reports across the system.
    """
    
    @abstractmethod
    async def save_report(self, report: Dict[str, Any]) -> str:
        """
        Save a performance report
        
        Args:
            report: The report data
            
        Returns:
            Report ID
        """
        pass
    
    @abstractmethod
    async def find_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a report by ID
        
        Args:
            report_id: The report ID
            
        Returns:
            The report if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_reports_by_type(self, report_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find reports by type
        
        Args:
            report_type: Type of report (e.g., "benchmark", "optimization")
            limit: Maximum number of results
            
        Returns:
            List of reports
        """
        pass
    
    @abstractmethod
    async def find_reports_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Find reports within a date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of reports within the range
        """
        pass
    
    @abstractmethod
    async def generate_summary_report(self, period_days: int = 7) -> Dict[str, Any]:
        """
        Generate a summary report for a period
        
        Args:
            period_days: Number of days to include
            
        Returns:
            Summary report data
        """
        pass