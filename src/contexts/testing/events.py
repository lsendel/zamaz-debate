"""
Testing Context Domain Events

Domain events that occur within the testing context, including test execution,
test results, coverage analysis, and mock configuration.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from src.events.domain_event import DomainEvent


@dataclass(frozen=True)
class TestSuiteCreated(DomainEvent):
    """Event published when a test suite is created"""
    
    test_suite_id: UUID
    name: str
    test_count: int
    configuration: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestSuiteCreated")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "name": self.name,
            "test_count": self.test_count,
            "configuration": self.configuration,
        })
        return data


@dataclass(frozen=True)
class TestExecuted(DomainEvent):
    """Event published when a test is executed"""
    
    test_suite_id: UUID
    test_case_id: UUID
    test_name: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestExecuted")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "test_case_id": str(self.test_case_id),
            "test_name": self.test_name,
        })
        return data


@dataclass(frozen=True)
class TestPassed(DomainEvent):
    """Event published when a test passes"""
    
    test_suite_id: UUID
    test_case_id: UUID
    test_name: str
    execution_time_ms: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestPassed")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "test_case_id": str(self.test_case_id),
            "test_name": self.test_name,
            "execution_time_ms": self.execution_time_ms,
        })
        return data


@dataclass(frozen=True)
class TestFailed(DomainEvent):
    """Event published when a test fails"""
    
    test_suite_id: UUID
    test_case_id: UUID
    test_name: str
    error_message: str
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestFailed")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "test_case_id": str(self.test_case_id),
            "test_name": self.test_name,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
        })
        return data


@dataclass(frozen=True)
class TestSkipped(DomainEvent):
    """Event published when a test is skipped"""
    
    test_suite_id: UUID
    test_case_id: UUID
    test_name: str
    reason: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestSkipped")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "test_case_id": str(self.test_case_id),
            "test_name": self.test_name,
            "reason": self.reason,
        })
        return data


@dataclass(frozen=True)
class TestSuiteCompleted(DomainEvent):
    """Event published when a test suite execution is completed"""
    
    test_suite_id: UUID
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    total_execution_time_ms: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestSuiteCompleted")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_tests": self.error_tests,
            "skipped_tests": self.skipped_tests,
            "total_execution_time_ms": self.total_execution_time_ms,
        })
        return data


@dataclass(frozen=True)
class CoverageAnalyzed(DomainEvent):
    """Event published when code coverage is analyzed"""
    
    test_suite_id: UUID
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    total_lines: int
    covered_lines: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "CoverageAnalyzed")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "line_coverage": self.line_coverage,
            "branch_coverage": self.branch_coverage,
            "function_coverage": self.function_coverage,
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
        })
        return data


@dataclass(frozen=True)
class MockConfigured(DomainEvent):
    """Event published when a mock is configured"""
    
    mock_config_id: UUID
    target_service: str
    endpoint: str
    response_configured: bool
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "MockConfigured")
        object.__setattr__(self, "aggregate_id", self.mock_config_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "mock_config_id": str(self.mock_config_id),
            "target_service": self.target_service,
            "endpoint": self.endpoint,
            "response_configured": self.response_configured,
        })
        return data


@dataclass(frozen=True)
class TestEnvironmentSetup(DomainEvent):
    """Event published when test environment is set up"""
    
    test_suite_id: UUID
    environment_name: str
    configuration: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestEnvironmentSetup")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "environment_name": self.environment_name,
            "configuration": self.configuration,
        })
        return data


@dataclass(frozen=True)
class TestReportGenerated(DomainEvent):
    """Event published when a test report is generated"""
    
    test_suite_id: UUID
    report_type: str
    report_format: str
    report_path: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestReportGenerated")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "report_type": self.report_type,
            "report_format": self.report_format,
            "report_path": self.report_path,
        })
        return data


@dataclass(frozen=True)
class TestDataGenerated(DomainEvent):
    """Event published when test data is generated"""
    
    test_suite_id: UUID
    data_type: str
    record_count: int
    schema: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestDataGenerated")
        object.__setattr__(self, "aggregate_id", self.test_suite_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "test_suite_id": str(self.test_suite_id),
            "data_type": self.data_type,
            "record_count": self.record_count,
            "schema": self.schema,
        })
        return data