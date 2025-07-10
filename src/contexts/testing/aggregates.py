"""
Testing Context Aggregates

This module contains the aggregate roots for the testing context.
Aggregates enforce business invariants and manage test execution consistency.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .events import (
    CoverageAnalyzed,
    TestExecuted,
    TestFailed,
    TestPassed,
    TestSuiteCompleted,
    TestSuiteCreated,
)
from .value_objects import Coverage, TestAssertion, TestConfiguration


class TestStatus(Enum):
    """Status of a test"""
    
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestSuiteStatus(Enum):
    """Status of a test suite"""
    
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TestCase:
    """
    Represents a single test case
    
    This is not an aggregate root, but an entity within the TestSuite aggregate.
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    test_method: str = ""
    status: TestStatus = TestStatus.PENDING
    assertions: List[TestAssertion] = field(default_factory=list)
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def execute(self) -> None:
        """Start test execution"""
        if self.status != TestStatus.PENDING:
            raise ValueError("Test has already been executed")
        self.status = TestStatus.RUNNING
        self.started_at = datetime.now()
    
    def mark_passed(self, execution_time_ms: int) -> None:
        """Mark test as passed"""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Test must be running to mark as passed")
        self.status = TestStatus.PASSED
        self.execution_time_ms = execution_time_ms
        self.completed_at = datetime.now()
    
    def mark_failed(self, error_message: str, stack_trace: Optional[str] = None) -> None:
        """Mark test as failed"""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Test must be running to mark as failed")
        self.status = TestStatus.FAILED
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.completed_at = datetime.now()
    
    def mark_error(self, error_message: str, stack_trace: Optional[str] = None) -> None:
        """Mark test as error"""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Test must be running to mark as error")
        self.status = TestStatus.ERROR
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.completed_at = datetime.now()
    
    def skip(self, reason: str) -> None:
        """Skip test execution"""
        if self.status != TestStatus.PENDING:
            raise ValueError("Only pending tests can be skipped")
        self.status = TestStatus.SKIPPED
        self.error_message = reason
    
    def add_assertion(self, assertion: TestAssertion) -> None:
        """Add an assertion to the test"""
        self.assertions.append(assertion)
    
    @property
    def is_completed(self) -> bool:
        """Check if test execution is completed"""
        return self.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR, TestStatus.SKIPPED]
    
    @property
    def is_successful(self) -> bool:
        """Check if test passed"""
        return self.status == TestStatus.PASSED


@dataclass
class TestSuite:
    """
    Test Suite Aggregate Root
    
    Manages a collection of related test cases and their execution.
    Enforces business invariants around test execution order and dependencies.
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    test_cases: List[TestCase] = field(default_factory=list)
    configuration: TestConfiguration = field(default_factory=TestConfiguration)
    status: TestSuiteStatus = TestSuiteStatus.CREATED
    coverage: Optional[Coverage] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize the test suite and publish domain event"""
        if self.status == TestSuiteStatus.CREATED and not self._events:
            self._publish_event(
                TestSuiteCreated(
                    test_suite_id=self.id,
                    name=self.name,
                    test_count=len(self.test_cases),
                    configuration=self.configuration.to_dict(),
                    occurred_at=datetime.now(),
                )
            )
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case to the suite"""
        if self.status != TestSuiteStatus.CREATED:
            raise ValueError("Cannot add tests to suite that has started execution")
        if any(tc.id == test_case.id for tc in self.test_cases):
            raise ValueError(f"Test case {test_case.id} already in suite")
        self.test_cases.append(test_case)
    
    def start_execution(self) -> None:
        """Start test suite execution"""
        if self.status != TestSuiteStatus.CREATED:
            raise ValueError("Test suite has already been started")
        if not self.test_cases:
            raise ValueError("Cannot start empty test suite")
        
        self.status = TestSuiteStatus.RUNNING
        self.started_at = datetime.now()
    
    def execute_test(self, test_id: UUID) -> TestCase:
        """Execute a specific test case"""
        if self.status != TestSuiteStatus.RUNNING:
            raise ValueError("Test suite must be running to execute tests")
        
        test_case = next((tc for tc in self.test_cases if tc.id == test_id), None)
        if not test_case:
            raise ValueError(f"Test case {test_id} not found in suite")
        
        test_case.execute()
        
        self._publish_event(
            TestExecuted(
                test_suite_id=self.id,
                test_case_id=test_case.id,
                test_name=test_case.name,
                occurred_at=datetime.now(),
            )
        )
        
        return test_case
    
    def mark_test_passed(self, test_id: UUID, execution_time_ms: int) -> None:
        """Mark a test as passed"""
        test_case = self._get_running_test(test_id)
        test_case.mark_passed(execution_time_ms)
        
        self._publish_event(
            TestPassed(
                test_suite_id=self.id,
                test_case_id=test_case.id,
                test_name=test_case.name,
                execution_time_ms=execution_time_ms,
                occurred_at=datetime.now(),
            )
        )
    
    def mark_test_failed(self, test_id: UUID, error_message: str, stack_trace: Optional[str] = None) -> None:
        """Mark a test as failed"""
        test_case = self._get_running_test(test_id)
        test_case.mark_failed(error_message, stack_trace)
        
        self._publish_event(
            TestFailed(
                test_suite_id=self.id,
                test_case_id=test_case.id,
                test_name=test_case.name,
                error_message=error_message,
                stack_trace=stack_trace,
                occurred_at=datetime.now(),
            )
        )
    
    def complete_execution(self) -> None:
        """Complete test suite execution"""
        if self.status != TestSuiteStatus.RUNNING:
            raise ValueError("Test suite must be running to complete")
        
        # Ensure all tests are completed
        incomplete_tests = [tc for tc in self.test_cases if not tc.is_completed]
        if incomplete_tests:
            raise ValueError(f"{len(incomplete_tests)} tests are still running")
        
        self.status = TestSuiteStatus.COMPLETED
        self.completed_at = datetime.now()
        
        # Calculate execution statistics
        total_tests = len(self.test_cases)
        passed_tests = sum(1 for tc in self.test_cases if tc.status == TestStatus.PASSED)
        failed_tests = sum(1 for tc in self.test_cases if tc.status == TestStatus.FAILED)
        error_tests = sum(1 for tc in self.test_cases if tc.status == TestStatus.ERROR)
        skipped_tests = sum(1 for tc in self.test_cases if tc.status == TestStatus.SKIPPED)
        
        total_execution_time = sum(
            tc.execution_time_ms or 0
            for tc in self.test_cases
            if tc.execution_time_ms is not None
        )
        
        self._publish_event(
            TestSuiteCompleted(
                test_suite_id=self.id,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                error_tests=error_tests,
                skipped_tests=skipped_tests,
                total_execution_time_ms=total_execution_time,
                occurred_at=datetime.now(),
            )
        )
    
    def analyze_coverage(self, coverage: Coverage) -> None:
        """Analyze and set code coverage"""
        if self.status != TestSuiteStatus.COMPLETED:
            raise ValueError("Test suite must be completed to analyze coverage")
        
        self.coverage = coverage
        
        self._publish_event(
            CoverageAnalyzed(
                test_suite_id=self.id,
                line_coverage=coverage.line_coverage,
                branch_coverage=coverage.branch_coverage,
                function_coverage=coverage.function_coverage,
                total_lines=coverage.total_lines,
                covered_lines=coverage.covered_lines,
                occurred_at=datetime.now(),
            )
        )
    
    def cancel(self) -> None:
        """Cancel test suite execution"""
        if self.status in [TestSuiteStatus.COMPLETED, TestSuiteStatus.CANCELLED]:
            raise ValueError("Cannot cancel completed or already cancelled test suite")
        
        self.status = TestSuiteStatus.CANCELLED
        self.completed_at = datetime.now()
    
    def _get_running_test(self, test_id: UUID) -> TestCase:
        """Get a running test case by ID"""
        test_case = next((tc for tc in self.test_cases if tc.id == test_id), None)
        if not test_case:
            raise ValueError(f"Test case {test_id} not found in suite")
        if test_case.status != TestStatus.RUNNING:
            raise ValueError(f"Test case {test_id} is not running")
        return test_case
    
    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def is_completed(self) -> bool:
        """Check if test suite execution is completed"""
        return self.status == TestSuiteStatus.COMPLETED
    
    @property
    def has_failures(self) -> bool:
        """Check if any tests failed"""
        return any(tc.status in [TestStatus.FAILED, TestStatus.ERROR] for tc in self.test_cases)
    
    @property
    def success_rate(self) -> float:
        """Calculate test success rate"""
        if not self.test_cases:
            return 0.0
        successful_tests = sum(1 for tc in self.test_cases if tc.is_successful)
        return successful_tests / len(self.test_cases)


@dataclass
class MockConfiguration:
    """
    Mock Configuration Aggregate Root
    
    Manages mock configurations for test environments.
    Ensures consistency in mock behavior across test runs.
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    target_service: str = ""
    mock_responses: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    
    def add_response(self, endpoint: str, response: Dict[str, Any]) -> None:
        """Add a mock response for an endpoint"""
        self.mock_responses[endpoint] = response
        self.updated_at = datetime.now()
    
    def remove_response(self, endpoint: str) -> None:
        """Remove a mock response for an endpoint"""
        if endpoint not in self.mock_responses:
            raise ValueError(f"No mock response found for endpoint: {endpoint}")
        del self.mock_responses[endpoint]
        self.updated_at = datetime.now()
    
    def activate(self) -> None:
        """Activate the mock configuration"""
        if self.active:
            raise ValueError("Mock configuration is already active")
        self.active = True
        self.updated_at = datetime.now()
    
    def deactivate(self) -> None:
        """Deactivate the mock configuration"""
        if not self.active:
            raise ValueError("Mock configuration is already inactive")
        self.active = False
        self.updated_at = datetime.now()
    
    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events