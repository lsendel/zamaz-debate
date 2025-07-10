"""
Performance Context Value Objects

Value objects representing concepts within the performance domain.
These are immutable objects that encapsulate performance-related data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MetricValue:
    """
    Represents a single metric measurement
    
    Value object that captures a performance metric at a point in time.
    """
    
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize and validate metric value"""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PerformanceThreshold:
    """
    Performance threshold configuration
    
    Value object defining when a metric exceeds acceptable bounds.
    """
    
    name: str
    value: float
    type: str  # "min" or "max"
    severity: str = "warning"  # "warning" or "critical"
    
    def __post_init__(self):
        """Validate threshold data"""
        if not self.name:
            raise ValueError("Threshold name cannot be empty")
        if self.type not in ["min", "max"]:
            raise ValueError("Threshold type must be 'min' or 'max'")
        if self.severity not in ["warning", "critical"]:
            raise ValueError("Severity must be 'warning' or 'critical'")
    
    def is_exceeded(self, metric_value: float) -> bool:
        """Check if a metric value exceeds this threshold"""
        if self.type == "max":
            return metric_value > self.value
        else:  # min
            return metric_value < self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.type,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class ResourceUsage:
    """
    System resource usage snapshot
    
    Value object capturing resource utilization at a point in time.
    """
    
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_io_sent_mb: float = 0.0
    network_io_recv_mb: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided"""
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now())
        
        # Validate percentages
        if not (0 <= self.cpu_percent <= 100):
            raise ValueError("CPU percent must be between 0 and 100")
        if not (0 <= self.memory_percent <= 100):
            raise ValueError("Memory percent must be between 0 and 100")
    
    @property
    def total_disk_io_mb(self) -> float:
        """Total disk I/O in MB"""
        return self.disk_io_read_mb + self.disk_io_write_mb
    
    @property
    def total_network_io_mb(self) -> float:
        """Total network I/O in MB"""
        return self.network_io_sent_mb + self.network_io_recv_mb
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_mb": self.memory_mb,
            "disk_io_read_mb": self.disk_io_read_mb,
            "disk_io_write_mb": self.disk_io_write_mb,
            "network_io_sent_mb": self.network_io_sent_mb,
            "network_io_recv_mb": self.network_io_recv_mb,
            "total_disk_io_mb": self.total_disk_io_mb,
            "total_network_io_mb": self.total_network_io_mb,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class Optimization:
    """
    Performance optimization configuration
    
    Value object describing a performance optimization strategy.
    """
    
    type: str = "general"  # "cache", "query", "algorithm", "infrastructure", "general"
    target_area: str = ""  # e.g., "database", "api", "frontend"
    technique: str = ""  # e.g., "indexing", "caching", "parallelization"
    implementation_details: Dict[str, Any] = None
    risk_level: str = "low"  # "low", "medium", "high"
    
    def __post_init__(self):
        """Initialize and validate optimization data"""
        valid_types = ["cache", "query", "algorithm", "infrastructure", "general"]
        if self.type not in valid_types:
            raise ValueError(f"Optimization type must be one of {valid_types}")
        
        valid_risks = ["low", "medium", "high"]
        if self.risk_level not in valid_risks:
            raise ValueError(f"Risk level must be one of {valid_risks}")
        
        if self.implementation_details is None:
            object.__setattr__(self, "implementation_details", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "type": self.type,
            "target_area": self.target_area,
            "technique": self.technique,
            "implementation_details": self.implementation_details,
            "risk_level": self.risk_level,
        }


@dataclass(frozen=True)
class PerformanceProfile:
    """
    Performance profile for a system or component
    
    Value object containing performance characteristics and expectations.
    """
    
    name: str
    expected_response_time_ms: float
    expected_throughput_rps: float  # requests per second
    max_concurrent_users: int
    resource_limits: Dict[str, float] = None  # e.g., {"cpu": 80, "memory": 90}
    sla_targets: Dict[str, float] = None  # e.g., {"uptime": 99.9, "p99_latency": 500}
    
    def __post_init__(self):
        """Initialize and validate profile data"""
        if not self.name:
            raise ValueError("Profile name cannot be empty")
        if self.expected_response_time_ms < 0:
            raise ValueError("Expected response time cannot be negative")
        if self.expected_throughput_rps < 0:
            raise ValueError("Expected throughput cannot be negative")
        if self.max_concurrent_users < 1:
            raise ValueError("Max concurrent users must be at least 1")
        
        if self.resource_limits is None:
            object.__setattr__(self, "resource_limits", {})
        if self.sla_targets is None:
            object.__setattr__(self, "sla_targets", {})
    
    def meets_sla(self, metric_name: str, value: float) -> bool:
        """Check if a metric value meets SLA target"""
        if metric_name not in self.sla_targets:
            return True  # No SLA defined
        
        target = self.sla_targets[metric_name]
        
        # For uptime and success rate, value should be >= target
        if metric_name in ["uptime", "success_rate"]:
            return value >= target
        
        # For latency and response time, value should be <= target
        if "latency" in metric_name or "response_time" in metric_name:
            return value <= target
        
        # Default comparison
        return value <= target
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "expected_response_time_ms": self.expected_response_time_ms,
            "expected_throughput_rps": self.expected_throughput_rps,
            "max_concurrent_users": self.max_concurrent_users,
            "resource_limits": self.resource_limits,
            "sla_targets": self.sla_targets,
        }


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Result of a benchmark run
    
    Value object containing benchmark execution results.
    """
    
    metric_name: str
    value: float
    unit: str
    percentiles: Dict[str, float] = None  # e.g., {"p50": 100, "p95": 200, "p99": 500}
    
    def __post_init__(self):
        """Initialize percentiles if not provided"""
        if self.percentiles is None:
            object.__setattr__(self, "percentiles", {})
    
    @property
    def p50(self) -> Optional[float]:
        """Get 50th percentile (median)"""
        return self.percentiles.get("p50")
    
    @property
    def p95(self) -> Optional[float]:
        """Get 95th percentile"""
        return self.percentiles.get("p95")
    
    @property
    def p99(self) -> Optional[float]:
        """Get 99th percentile"""
        return self.percentiles.get("p99")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "percentiles": self.percentiles,
        }