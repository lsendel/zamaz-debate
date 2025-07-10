"""
Testing Context Value Objects

Value objects representing concepts within the testing domain that have no identity.
These are immutable objects that are defined by their attributes.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TestAssertion:
    """
    Represents a test assertion
    
    Value object that captures the expected vs actual comparison in a test.
    """
    
    assertion_type: str  # e.g., "equals", "contains", "greater_than"
    expected_value: Any
    actual_value: Optional[Any] = None
    passed: bool = False
    message: Optional[str] = None
    
    def __post_init__(self):
        """Validate assertion data"""
        if not self.assertion_type:
            raise ValueError("Assertion type cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "assertion_type": self.assertion_type,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "passed": self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class TestConfiguration:
    """
    Test execution configuration
    
    Value object containing settings for test execution.
    """
    
    parallel_execution: bool = False
    max_parallel_tests: int = 1
    timeout_seconds: int = 300
    retry_count: int = 0
    environment: str = "test"
    tags: List[str] = None
    skip_patterns: List[str] = None
    
    def __post_init__(self):
        """Initialize and validate configuration"""
        if self.max_parallel_tests < 1:
            raise ValueError("Max parallel tests must be at least 1")
        if self.timeout_seconds < 1:
            raise ValueError("Timeout must be at least 1 second")
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")
        
        # Set default values for mutable fields
        if self.tags is None:
            object.__setattr__(self, "tags", [])
        if self.skip_patterns is None:
            object.__setattr__(self, "skip_patterns", [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "parallel_execution": self.parallel_execution,
            "max_parallel_tests": self.max_parallel_tests,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "environment": self.environment,
            "tags": self.tags,
            "skip_patterns": self.skip_patterns,
        }


@dataclass(frozen=True)
class Coverage:
    """
    Code coverage metrics
    
    Value object representing test coverage statistics.
    """
    
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    total_lines: int
    covered_lines: int
    total_branches: int = 0
    covered_branches: int = 0
    total_functions: int = 0
    covered_functions: int = 0
    
    def __post_init__(self):
        """Validate coverage data"""
        if not (0.0 <= self.line_coverage <= 100.0):
            raise ValueError("Line coverage must be between 0 and 100")
        if not (0.0 <= self.branch_coverage <= 100.0):
            raise ValueError("Branch coverage must be between 0 and 100")
        if not (0.0 <= self.function_coverage <= 100.0):
            raise ValueError("Function coverage must be between 0 and 100")
        if self.covered_lines > self.total_lines:
            raise ValueError("Covered lines cannot exceed total lines")
        if self.covered_branches > self.total_branches:
            raise ValueError("Covered branches cannot exceed total branches")
        if self.covered_functions > self.total_functions:
            raise ValueError("Covered functions cannot exceed total functions")
    
    @property
    def is_complete(self) -> bool:
        """Check if coverage is 100%"""
        return (
            self.line_coverage == 100.0
            and self.branch_coverage == 100.0
            and self.function_coverage == 100.0
        )
    
    @property
    def overall_coverage(self) -> float:
        """Calculate overall coverage percentage"""
        return (self.line_coverage + self.branch_coverage + self.function_coverage) / 3
    
    def meets_threshold(self, threshold: float) -> bool:
        """Check if coverage meets a threshold"""
        return self.overall_coverage >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "line_coverage": self.line_coverage,
            "branch_coverage": self.branch_coverage,
            "function_coverage": self.function_coverage,
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "total_branches": self.total_branches,
            "covered_branches": self.covered_branches,
            "total_functions": self.total_functions,
            "covered_functions": self.covered_functions,
            "overall_coverage": self.overall_coverage,
            "is_complete": self.is_complete,
        }


@dataclass(frozen=True)
class TestResult:
    """
    Result of a test execution
    
    Value object containing the outcome of a test run.
    """
    
    status: str  # "passed", "failed", "error", "skipped"
    execution_time_ms: int
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    assertions_passed: int = 0
    assertions_failed: int = 0
    
    def __post_init__(self):
        """Validate test result data"""
        valid_statuses = ["passed", "failed", "error", "skipped"]
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
        if self.execution_time_ms < 0:
            raise ValueError("Execution time cannot be negative")
        if self.assertions_passed < 0 or self.assertions_failed < 0:
            raise ValueError("Assertion counts cannot be negative")
    
    @property
    def is_successful(self) -> bool:
        """Check if test was successful"""
        return self.status == "passed"
    
    @property
    def total_assertions(self) -> int:
        """Get total number of assertions"""
        return self.assertions_passed + self.assertions_failed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
            "is_successful": self.is_successful,
            "total_assertions": self.total_assertions,
        }


@dataclass(frozen=True)
class TestTag:
    """
    Tag for categorizing tests
    
    Value object for test categorization and filtering.
    """
    
    name: str
    category: str = "general"
    
    def __post_init__(self):
        """Validate tag data"""
        if not self.name.strip():
            raise ValueError("Tag name cannot be empty")
        if not self.category.strip():
            raise ValueError("Tag category cannot be empty")
    
    def matches(self, pattern: str) -> bool:
        """Check if tag matches a pattern"""
        return pattern.lower() in self.name.lower() or pattern.lower() in self.category.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "category": self.category,
        }