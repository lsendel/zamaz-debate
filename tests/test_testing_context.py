"""
Unit tests for the Testing Context domain logic

Tests aggregates, value objects, domain services, and business rules.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.contexts.testing.aggregates import (
    MockConfiguration,
    TestCase,
    TestStatus,
    TestSuite,
    TestSuiteStatus,
)
from src.contexts.testing.value_objects import (
    Coverage,
    TestAssertion,
    TestConfiguration,
    TestResult,
    TestTag,
)
from src.contexts.testing.events import (
    CoverageAnalyzed,
    TestExecuted,
    TestFailed,
    TestPassed,
    TestSuiteCompleted,
    TestSuiteCreated,
)


class TestTestConfiguration:
    """Test cases for TestConfiguration value object"""
    
    def test_create_default_configuration(self):
        """Test creating a test configuration with defaults"""
        config = TestConfiguration()
        
        assert config.parallel_execution is False
        assert config.max_parallel_tests == 1
        assert config.timeout_seconds == 300
        assert config.retry_count == 0
        assert config.environment == "test"
        assert config.tags == []
        assert config.skip_patterns == []
    
    def test_create_custom_configuration(self):
        """Test creating a test configuration with custom values"""
        config = TestConfiguration(
            parallel_execution=True,
            max_parallel_tests=4,
            timeout_seconds=600,
            retry_count=2,
            environment="staging",
            tags=["integration", "slow"],
            skip_patterns=["*.skip", "test_experimental_*"]
        )
        
        assert config.parallel_execution is True
        assert config.max_parallel_tests == 4
        assert config.timeout_seconds == 600
        assert config.retry_count == 2
        assert config.environment == "staging"
        assert config.tags == ["integration", "slow"]
        assert config.skip_patterns == ["*.skip", "test_experimental_*"]
    
    def test_invalid_configuration_values(self):
        """Test that invalid values raise appropriate errors"""
        with pytest.raises(ValueError, match="Max parallel tests must be at least 1"):
            TestConfiguration(max_parallel_tests=0)
        
        with pytest.raises(ValueError, match="Timeout must be at least 1 second"):
            TestConfiguration(timeout_seconds=0)
        
        with pytest.raises(ValueError, match="Retry count cannot be negative"):
            TestConfiguration(retry_count=-1)


class TestTestAssertion:
    """Test cases for TestAssertion value object"""
    
    def test_create_assertion(self):
        """Test creating a test assertion"""
        assertion = TestAssertion(
            assertion_type="equals",
            expected_value="foo",
            actual_value="foo",
            passed=True
        )
        
        assert assertion.assertion_type == "equals"
        assert assertion.expected_value == "foo"
        assert assertion.actual_value == "foo"
        assert assertion.passed is True
        assert assertion.message is None
    
    def test_failed_assertion_with_message(self):
        """Test creating a failed assertion with message"""
        assertion = TestAssertion(
            assertion_type="contains",
            expected_value="hello",
            actual_value="goodbye",
            passed=False,
            message="Expected string to contain 'hello'"
        )
        
        assert assertion.passed is False
        assert assertion.message == "Expected string to contain 'hello'"
    
    def test_assertion_type_required(self):
        """Test that assertion type is required"""
        with pytest.raises(ValueError, match="Assertion type cannot be empty"):
            TestAssertion(assertion_type="", expected_value=1)


class TestCoverage:
    """Test cases for Coverage value object"""
    
    def test_create_coverage(self):
        """Test creating coverage metrics"""
        coverage = Coverage(
            line_coverage=85.5,
            branch_coverage=78.0,
            function_coverage=92.0,
            total_lines=1000,
            covered_lines=855,
            total_branches=200,
            covered_branches=156,
            total_functions=50,
            covered_functions=46
        )
        
        assert coverage.line_coverage == 85.5
        assert coverage.branch_coverage == 78.0
        assert coverage.function_coverage == 92.0
        assert coverage.overall_coverage == pytest.approx(85.16666666666667)
        assert coverage.is_complete is False
    
    def test_complete_coverage(self):
        """Test coverage that is 100% complete"""
        coverage = Coverage(
            line_coverage=100.0,
            branch_coverage=100.0,
            function_coverage=100.0,
            total_lines=100,
            covered_lines=100
        )
        
        assert coverage.is_complete is True
        assert coverage.overall_coverage == 100.0
    
    def test_coverage_meets_threshold(self):
        """Test checking if coverage meets threshold"""
        coverage = Coverage(
            line_coverage=85.0,
            branch_coverage=80.0,
            function_coverage=90.0,
            total_lines=100,
            covered_lines=85
        )
        
        assert coverage.meets_threshold(80.0) is True
        assert coverage.meets_threshold(85.0) is True
        assert coverage.meets_threshold(90.0) is False
    
    def test_invalid_coverage_values(self):
        """Test that invalid coverage values raise errors"""
        with pytest.raises(ValueError, match="Line coverage must be between 0 and 100"):
            Coverage(line_coverage=101.0, branch_coverage=80.0, function_coverage=90.0,
                    total_lines=100, covered_lines=100)
        
        with pytest.raises(ValueError, match="Covered lines cannot exceed total lines"):
            Coverage(line_coverage=80.0, branch_coverage=80.0, function_coverage=90.0,
                    total_lines=100, covered_lines=101)


class TestTestCase:
    """Test cases for TestCase entity"""
    
    def test_create_test_case(self):
        """Test creating a test case"""
        test_case = TestCase(
            name="test_user_login",
            description="Test user login functionality",
            test_method="test_user_login"
        )
        
        assert test_case.name == "test_user_login"
        assert test_case.description == "Test user login functionality"
        assert test_case.test_method == "test_user_login"
        assert test_case.status == TestStatus.PENDING
        assert test_case.assertions == []
        assert test_case.execution_time_ms is None
        assert test_case.error_message is None
        assert test_case.is_completed is False
        assert test_case.is_successful is False
    
    def test_execute_test(self):
        """Test executing a test case"""
        test_case = TestCase(name="test_example")
        
        test_case.execute()
        
        assert test_case.status == TestStatus.RUNNING
        assert test_case.started_at is not None
        
        # Cannot execute already running test
        with pytest.raises(ValueError, match="Test has already been executed"):
            test_case.execute()
    
    def test_mark_test_passed(self):
        """Test marking a test as passed"""
        test_case = TestCase(name="test_example")
        test_case.execute()
        
        test_case.mark_passed(execution_time_ms=150)
        
        assert test_case.status == TestStatus.PASSED
        assert test_case.execution_time_ms == 150
        assert test_case.completed_at is not None
        assert test_case.is_completed is True
        assert test_case.is_successful is True
    
    def test_mark_test_failed(self):
        """Test marking a test as failed"""
        test_case = TestCase(name="test_example")
        test_case.execute()
        
        test_case.mark_failed(
            error_message="Assertion failed",
            stack_trace="File test.py, line 10..."
        )
        
        assert test_case.status == TestStatus.FAILED
        assert test_case.error_message == "Assertion failed"
        assert test_case.stack_trace == "File test.py, line 10..."
        assert test_case.is_completed is True
        assert test_case.is_successful is False
    
    def test_skip_test(self):
        """Test skipping a test"""
        test_case = TestCase(name="test_example")
        
        test_case.skip(reason="Not applicable in this environment")
        
        assert test_case.status == TestStatus.SKIPPED
        assert test_case.error_message == "Not applicable in this environment"
        assert test_case.is_completed is True
        assert test_case.is_successful is False
    
    def test_add_assertions(self):
        """Test adding assertions to a test case"""
        test_case = TestCase(name="test_example")
        
        assertion1 = TestAssertion(
            assertion_type="equals",
            expected_value=1,
            actual_value=1,
            passed=True
        )
        assertion2 = TestAssertion(
            assertion_type="greater_than",
            expected_value=0,
            actual_value=5,
            passed=True
        )
        
        test_case.add_assertion(assertion1)
        test_case.add_assertion(assertion2)
        
        assert len(test_case.assertions) == 2
        assert test_case.assertions[0] == assertion1
        assert test_case.assertions[1] == assertion2


class TestTestSuite:
    """Test cases for TestSuite aggregate root"""
    
    def test_create_test_suite(self):
        """Test creating a test suite"""
        suite = TestSuite(
            name="Unit Tests",
            description="Unit test suite for the application"
        )
        
        assert suite.name == "Unit Tests"
        assert suite.description == "Unit test suite for the application"
        assert suite.test_cases == []
        assert suite.status == TestSuiteStatus.CREATED
        assert suite.coverage is None
        assert len(suite.get_events()) == 1
        
        # Check TestSuiteCreated event
        event = suite.get_events()[0]
        assert isinstance(event, TestSuiteCreated)
        assert event.name == "Unit Tests"
        assert event.test_count == 0
    
    def test_add_test_cases(self):
        """Test adding test cases to a suite"""
        suite = TestSuite(name="Test Suite")
        test_case1 = TestCase(name="test_1")
        test_case2 = TestCase(name="test_2")
        
        suite.add_test_case(test_case1)
        suite.add_test_case(test_case2)
        
        assert len(suite.test_cases) == 2
        assert suite.test_cases[0] == test_case1
        assert suite.test_cases[1] == test_case2
    
    def test_cannot_add_duplicate_test_case(self):
        """Test that duplicate test cases cannot be added"""
        suite = TestSuite(name="Test Suite")
        test_case = TestCase(name="test_1")
        
        suite.add_test_case(test_case)
        
        with pytest.raises(ValueError, match=f"Test case {test_case.id} already in suite"):
            suite.add_test_case(test_case)
    
    def test_start_execution(self):
        """Test starting test suite execution"""
        suite = TestSuite(name="Test Suite")
        test_case = TestCase(name="test_1")
        suite.add_test_case(test_case)
        
        suite.start_execution()
        
        assert suite.status == TestSuiteStatus.RUNNING
        assert suite.started_at is not None
        
        # Cannot start already running suite
        with pytest.raises(ValueError, match="Test suite has already been started"):
            suite.start_execution()
    
    def test_execute_test_in_suite(self):
        """Test executing a specific test in the suite"""
        suite = TestSuite(name="Test Suite")
        test_case = TestCase(name="test_1")
        suite.add_test_case(test_case)
        suite.start_execution()
        
        executed_test = suite.execute_test(test_case.id)
        
        assert executed_test == test_case
        assert test_case.status == TestStatus.RUNNING
        
        # Check TestExecuted event
        events = suite.get_events()
        test_executed_event = next(e for e in events if isinstance(e, TestExecuted))
        assert test_executed_event.test_case_id == test_case.id
        assert test_executed_event.test_name == "test_1"
    
    def test_mark_test_results(self):
        """Test marking test results in a suite"""
        suite = TestSuite(name="Test Suite")
        test_case = TestCase(name="test_1")
        suite.add_test_case(test_case)
        suite.start_execution()
        suite.execute_test(test_case.id)
        
        # Mark test as passed
        suite.mark_test_passed(test_case.id, execution_time_ms=100)
        
        assert test_case.status == TestStatus.PASSED
        assert test_case.execution_time_ms == 100
        
        # Check TestPassed event
        events = suite.get_events()
        test_passed_event = next(e for e in events if isinstance(e, TestPassed))
        assert test_passed_event.test_case_id == test_case.id
        assert test_passed_event.execution_time_ms == 100
    
    def test_complete_suite_execution(self):
        """Test completing test suite execution"""
        suite = TestSuite(name="Test Suite")
        test1 = TestCase(name="test_1")
        test2 = TestCase(name="test_2")
        suite.add_test_case(test1)
        suite.add_test_case(test2)
        
        suite.start_execution()
        suite.execute_test(test1.id)
        suite.mark_test_passed(test1.id, 100)
        suite.execute_test(test2.id)
        suite.mark_test_failed(test2.id, "Assertion error")
        
        suite.complete_execution()
        
        assert suite.status == TestSuiteStatus.COMPLETED
        assert suite.completed_at is not None
        assert suite.is_completed is True
        assert suite.has_failures is True
        assert suite.success_rate == 0.5
        
        # Check TestSuiteCompleted event
        events = suite.get_events()
        completed_event = next(e for e in events if isinstance(e, TestSuiteCompleted))
        assert completed_event.total_tests == 2
        assert completed_event.passed_tests == 1
        assert completed_event.failed_tests == 1
    
    def test_analyze_coverage(self):
        """Test analyzing coverage for a completed suite"""
        suite = TestSuite(name="Test Suite")
        test_case = TestCase(name="test_1")
        suite.add_test_case(test_case)
        
        suite.start_execution()
        suite.execute_test(test_case.id)
        suite.mark_test_passed(test_case.id, 100)
        suite.complete_execution()
        
        coverage = Coverage(
            line_coverage=85.0,
            branch_coverage=80.0,
            function_coverage=90.0,
            total_lines=100,
            covered_lines=85
        )
        
        suite.analyze_coverage(coverage)
        
        assert suite.coverage == coverage
        
        # Check CoverageAnalyzed event
        events = suite.get_events()
        coverage_event = next(e for e in events if isinstance(e, CoverageAnalyzed))
        assert coverage_event.line_coverage == 85.0
        assert coverage_event.branch_coverage == 80.0
    
    def test_cannot_analyze_coverage_before_completion(self):
        """Test that coverage cannot be analyzed before suite completion"""
        suite = TestSuite(name="Test Suite")
        coverage = Coverage(
            line_coverage=85.0,
            branch_coverage=80.0,
            function_coverage=90.0,
            total_lines=100,
            covered_lines=85
        )
        
        with pytest.raises(ValueError, match="Test suite must be completed to analyze coverage"):
            suite.analyze_coverage(coverage)


class TestMockConfiguration:
    """Test cases for MockConfiguration aggregate"""
    
    def test_create_mock_configuration(self):
        """Test creating a mock configuration"""
        mock_config = MockConfiguration(
            name="API Mock",
            target_service="external-api"
        )
        
        assert mock_config.name == "API Mock"
        assert mock_config.target_service == "external-api"
        assert mock_config.mock_responses == {}
        assert mock_config.active is True
    
    def test_add_mock_response(self):
        """Test adding mock responses"""
        mock_config = MockConfiguration(
            name="API Mock",
            target_service="external-api"
        )
        
        mock_config.add_response(
            "/api/users",
            {"users": [{"id": 1, "name": "Test User"}]}
        )
        
        assert "/api/users" in mock_config.mock_responses
        assert mock_config.mock_responses["/api/users"]["users"][0]["name"] == "Test User"
        assert mock_config.updated_at > mock_config.created_at
    
    def test_remove_mock_response(self):
        """Test removing mock responses"""
        mock_config = MockConfiguration(
            name="API Mock",
            target_service="external-api"
        )
        
        mock_config.add_response("/api/users", {"users": []})
        mock_config.remove_response("/api/users")
        
        assert "/api/users" not in mock_config.mock_responses
    
    def test_activate_deactivate_mock(self):
        """Test activating and deactivating mock configuration"""
        mock_config = MockConfiguration(
            name="API Mock",
            target_service="external-api",
            active=False
        )
        
        assert mock_config.active is False
        
        mock_config.activate()
        assert mock_config.active is True
        
        mock_config.deactivate()
        assert mock_config.active is False
        
        # Cannot activate already active mock
        mock_config.activate()
        with pytest.raises(ValueError, match="Mock configuration is already active"):
            mock_config.activate()


class TestTestResult:
    """Test cases for TestResult value object"""
    
    def test_create_test_result(self):
        """Test creating a test result"""
        result = TestResult(
            status="passed",
            execution_time_ms=150,
            assertions_passed=5,
            assertions_failed=0
        )
        
        assert result.status == "passed"
        assert result.execution_time_ms == 150
        assert result.is_successful is True
        assert result.total_assertions == 5
    
    def test_failed_test_result(self):
        """Test creating a failed test result"""
        result = TestResult(
            status="failed",
            execution_time_ms=200,
            error_message="Assertion failed: expected 5 but got 3",
            stack_trace="File test.py, line 42...",
            assertions_passed=3,
            assertions_failed=1
        )
        
        assert result.status == "failed"
        assert result.is_successful is False
        assert result.total_assertions == 4
        assert result.error_message == "Assertion failed: expected 5 but got 3"
    
    def test_invalid_test_result(self):
        """Test that invalid test results raise errors"""
        with pytest.raises(ValueError, match="Invalid status"):
            TestResult(status="unknown", execution_time_ms=100)
        
        with pytest.raises(ValueError, match="Execution time cannot be negative"):
            TestResult(status="passed", execution_time_ms=-1)
        
        with pytest.raises(ValueError, match="Assertion counts cannot be negative"):
            TestResult(status="passed", execution_time_ms=100, assertions_passed=-1)


if __name__ == "__main__":
    pytest.main([__file__])