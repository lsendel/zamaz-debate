"""
Evolution Context Value Objects

Immutable domain concepts that represent key aspects of system evolution
including improvement suggestions, evolution plans, and validation results.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ImprovementArea(Enum):
    """Areas where improvements can be made"""
    
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    CODE_QUALITY = "code_quality"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    SCALABILITY = "scalability"
    MAINTAINABILITY = "maintainability"
    USER_EXPERIENCE = "user_experience"
    USABILITY = "usability"
    INFRASTRUCTURE = "infrastructure"
    MONITORING = "monitoring"
    DEPLOYMENT = "deployment"


class RiskLevel(Enum):
    """Risk levels for evolution plans"""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ImprovementSuggestion:
    """
    Value object representing an improvement suggestion
    
    Contains details about a potential improvement including
    the area, expected impact, and implementation approach.
    """
    
    area: ImprovementArea
    title: str
    description: str
    rationale: str
    expected_benefits: List[str]
    estimated_impact: str  # "low", "medium", "high"
    implementation_approach: str
    complexity: str  # "simple", "moderate", "complex"
    prerequisites: List[str] = None
    
    def __post_init__(self):
        """Validate improvement suggestion"""
        if not self.title:
            raise ValueError("Improvement title cannot be empty")
        
        if not self.description:
            raise ValueError("Improvement description cannot be empty")
        
        if self.estimated_impact not in ["low", "medium", "high"]:
            raise ValueError("Impact must be low, medium, or high")
        
        if self.complexity not in ["simple", "moderate", "complex"]:
            raise ValueError("Complexity must be simple, moderate, or complex")
        
        # Set default for prerequisites if None
        if self.prerequisites is None:
            object.__setattr__(self, "prerequisites", [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "area": self.area.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "expected_benefits": self.expected_benefits,
            "estimated_impact": self.estimated_impact,
            "implementation_approach": self.implementation_approach,
            "complexity": self.complexity,
            "prerequisites": self.prerequisites,
        }


@dataclass(frozen=True)
class EvolutionStep:
    """A single step in an evolution plan"""
    
    order: int
    action: str
    description: str
    estimated_duration_hours: float
    dependencies: List[int] = None  # Order numbers of dependent steps
    validation_criteria: List[str] = None
    
    def __post_init__(self):
        """Validate evolution step"""
        if self.order < 1:
            raise ValueError("Step order must be positive")
        
        if not self.action:
            raise ValueError("Step action cannot be empty")
        
        if self.estimated_duration_hours <= 0:
            raise ValueError("Duration must be positive")
        
        # Set defaults
        if self.dependencies is None:
            object.__setattr__(self, "dependencies", [])
        if self.validation_criteria is None:
            object.__setattr__(self, "validation_criteria", [])


@dataclass(frozen=True)
class EvolutionPlan:
    """
    Value object representing a plan for system evolution
    
    Contains the steps, timeline, and risks associated with
    implementing a set of improvements.
    """
    
    steps: List[EvolutionStep]
    estimated_duration_hours: float
    risk_level: RiskLevel
    rollback_strategy: str
    success_criteria: List[str]
    monitoring_plan: str
    
    def __post_init__(self):
        """Validate evolution plan"""
        if not self.steps:
            raise ValueError("Evolution plan must have at least one step")
        
        if self.estimated_duration_hours <= 0:
            raise ValueError("Duration must be positive")
        
        if not self.rollback_strategy:
            raise ValueError("Rollback strategy is required")
        
        if not self.success_criteria:
            raise ValueError("Success criteria are required")
        
        # Validate step order uniqueness
        orders = [step.order for step in self.steps]
        if len(orders) != len(set(orders)):
            raise ValueError("Step orders must be unique")
        
        # Validate dependencies
        for step in self.steps:
            for dep in step.dependencies:
                if dep not in orders:
                    raise ValueError(f"Invalid dependency: step {dep} does not exist")
                if dep >= step.order:
                    raise ValueError(f"Step {step.order} cannot depend on later step {dep}")
    
    def get_critical_path(self) -> List[EvolutionStep]:
        """Calculate the critical path through the plan"""
        # Simple implementation - in reality would use graph algorithms
        return sorted(self.steps, key=lambda s: s.order)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "steps": [
                {
                    "order": step.order,
                    "action": step.action,
                    "description": step.description,
                    "estimated_duration_hours": step.estimated_duration_hours,
                    "dependencies": step.dependencies,
                    "validation_criteria": step.validation_criteria,
                }
                for step in self.steps
            ],
            "estimated_duration_hours": self.estimated_duration_hours,
            "risk_level": self.risk_level.value,
            "rollback_strategy": self.rollback_strategy,
            "success_criteria": self.success_criteria,
            "monitoring_plan": self.monitoring_plan,
        }


@dataclass(frozen=True)
class ValidationResult:
    """
    Value object representing the result of evolution validation
    
    Contains the outcome of validating that an evolution was
    successful and met its objectives.
    """
    
    is_successful: bool
    validation_timestamp: datetime
    tests_passed: int
    tests_failed: int
    performance_impact: Dict[str, float]  # Metric name -> percentage change
    issues_found: List[str]
    rollback_required: bool
    validator: str  # Who/what performed the validation
    
    def __post_init__(self):
        """Validate validation result"""
        if self.tests_passed < 0 or self.tests_failed < 0:
            raise ValueError("Test counts cannot be negative")
        
        if self.is_successful and self.rollback_required:
            raise ValueError("Successful validation cannot require rollback")
    
    @property
    def test_pass_rate(self) -> float:
        """Calculate test pass rate"""
        total_tests = self.tests_passed + self.tests_failed
        if total_tests == 0:
            return 100.0
        return (self.tests_passed / total_tests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "is_successful": self.is_successful,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "test_pass_rate": self.test_pass_rate,
            "performance_impact": self.performance_impact,
            "issues_found": self.issues_found,
            "rollback_required": self.rollback_required,
            "validator": self.validator,
        }


@dataclass(frozen=True)
class EvolutionMetrics:
    """
    Value object representing system metrics used in evolution
    
    Captures key performance indicators before and after evolution
    to measure the impact of changes.
    """
    
    performance_score: float  # 0-100
    reliability_score: float  # 0-100
    maintainability_score: float  # 0-100
    security_score: float  # 0-100
    test_coverage: float  # 0-100
    code_complexity: float  # Average cyclomatic complexity
    technical_debt_hours: float
    error_rate: float  # Errors per hour
    response_time_ms: float  # Average response time
    memory_usage_mb: float  # Average memory usage
    cpu_usage_percent: float  # Average CPU usage
    measured_at: datetime
    
    def __post_init__(self):
        """Validate metrics"""
        # Validate score ranges
        scores = [
            ("performance_score", self.performance_score),
            ("reliability_score", self.reliability_score),
            ("maintainability_score", self.maintainability_score),
            ("security_score", self.security_score),
            ("test_coverage", self.test_coverage),
        ]
        
        for name, value in scores:
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        
        # Validate non-negative values
        if self.code_complexity < 0:
            raise ValueError("Code complexity cannot be negative")
        
        if self.technical_debt_hours < 0:
            raise ValueError("Technical debt cannot be negative")
        
        if self.error_rate < 0:
            raise ValueError("Error rate cannot be negative")
        
        if self.response_time_ms < 0:
            raise ValueError("Response time cannot be negative")
        
        if self.memory_usage_mb < 0:
            raise ValueError("Memory usage cannot be negative")
        
        if not 0 <= self.cpu_usage_percent <= 100:
            raise ValueError("CPU usage must be between 0 and 100")
    
    def calculate_overall_health(self) -> float:
        """Calculate overall system health score"""
        # Weighted average of key metrics
        weights = {
            "performance": 0.25,
            "reliability": 0.25,
            "maintainability": 0.20,
            "security": 0.20,
            "test_coverage": 0.10,
        }
        
        score = (
            self.performance_score * weights["performance"] +
            self.reliability_score * weights["reliability"] +
            self.maintainability_score * weights["maintainability"] +
            self.security_score * weights["security"] +
            self.test_coverage * weights["test_coverage"]
        )
        
        return round(score, 2)
    
    def compare_to(self, other: "EvolutionMetrics") -> Dict[str, float]:
        """Compare metrics to another set of metrics"""
        return {
            "performance_score_change": self.performance_score - other.performance_score,
            "reliability_score_change": self.reliability_score - other.reliability_score,
            "maintainability_score_change": self.maintainability_score - other.maintainability_score,
            "security_score_change": self.security_score - other.security_score,
            "test_coverage_change": self.test_coverage - other.test_coverage,
            "code_complexity_change": self.code_complexity - other.code_complexity,
            "technical_debt_change": self.technical_debt_hours - other.technical_debt_hours,
            "error_rate_change": self.error_rate - other.error_rate,
            "response_time_change": self.response_time_ms - other.response_time_ms,
            "memory_usage_change": self.memory_usage_mb - other.memory_usage_mb,
            "cpu_usage_change": self.cpu_usage_percent - other.cpu_usage_percent,
            "overall_health_change": self.calculate_overall_health() - other.calculate_overall_health(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "performance_score": self.performance_score,
            "reliability_score": self.reliability_score,
            "maintainability_score": self.maintainability_score,
            "security_score": self.security_score,
            "test_coverage": self.test_coverage,
            "code_complexity": self.code_complexity,
            "technical_debt_hours": self.technical_debt_hours,
            "error_rate": self.error_rate,
            "response_time_ms": self.response_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "overall_health": self.calculate_overall_health(),
            "measured_at": self.measured_at.isoformat(),
        }


@dataclass(frozen=True)
class EvolutionImpact:
    """
    Value object representing the impact of an evolution
    
    Captures both positive and negative impacts of system changes.
    """
    
    improvements_applied: int
    performance_improvement_percent: float
    reliability_improvement_percent: float
    new_capabilities_added: List[str]
    technical_debt_reduced_hours: float
    breaking_changes: List[str]
    migration_required: bool
    downtime_minutes: float
    rollback_count: int
    
    def __post_init__(self):
        """Validate impact"""
        if self.improvements_applied < 0:
            raise ValueError("Improvements applied cannot be negative")
        
        if self.technical_debt_reduced_hours < 0:
            raise ValueError("Technical debt reduction cannot be negative")
        
        if self.downtime_minutes < 0:
            raise ValueError("Downtime cannot be negative")
        
        if self.rollback_count < 0:
            raise ValueError("Rollback count cannot be negative")
    
    @property
    def is_positive_impact(self) -> bool:
        """Check if overall impact is positive"""
        return (
            self.performance_improvement_percent > 0 or
            self.reliability_improvement_percent > 0 or
            self.technical_debt_reduced_hours > 0 or
            len(self.new_capabilities_added) > 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "improvements_applied": self.improvements_applied,
            "performance_improvement_percent": self.performance_improvement_percent,
            "reliability_improvement_percent": self.reliability_improvement_percent,
            "new_capabilities_added": self.new_capabilities_added,
            "technical_debt_reduced_hours": self.technical_debt_reduced_hours,
            "breaking_changes": self.breaking_changes,
            "migration_required": self.migration_required,
            "downtime_minutes": self.downtime_minutes,
            "rollback_count": self.rollback_count,
            "is_positive_impact": self.is_positive_impact,
        }