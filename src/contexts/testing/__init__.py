"""
Testing Context

This bounded context handles all testing-related domain logic including
test execution, coverage analysis, mock configuration, and test reporting.
"""

from .aggregates import MockConfiguration, TestCase, TestSuite
from .domain_services import (
    CoverageAnalysisService,
    TestDataGenerationService,
    TestExecutionService,
)
from .events import (
    CoverageAnalyzed,
    MockConfigured,
    TestExecuted,
    TestFailed,
    TestPassed,
    TestReportGenerated,
    TestSkipped,
    TestSuiteCompleted,
    TestSuiteCreated,
)
from .repositories import (
    MockConfigurationRepository,
    TestResultRepository,
    TestSuiteRepository,
)
from .value_objects import (
    Coverage,
    TestAssertion,
    TestConfiguration,
    TestResult,
    TestTag,
)

__all__ = [
    # Aggregates
    "TestSuite",
    "TestCase",
    "MockConfiguration",
    # Value Objects
    "TestAssertion",
    "TestConfiguration",
    "Coverage",
    "TestResult",
    "TestTag",
    # Events
    "TestSuiteCreated",
    "TestExecuted",
    "TestPassed",
    "TestFailed",
    "TestSkipped",
    "TestSuiteCompleted",
    "CoverageAnalyzed",
    "MockConfigured",
    "TestReportGenerated",
    # Repositories
    "TestSuiteRepository",
    "MockConfigurationRepository",
    "TestResultRepository",
    # Domain Services
    "TestExecutionService",
    "CoverageAnalysisService",
    "TestDataGenerationService",
]
