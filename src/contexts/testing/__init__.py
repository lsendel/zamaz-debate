"""
Testing Context

This bounded context handles test execution, reporting, and mock management.
"""

from .aggregates import TestCase, TestResult, TestSuite
from .domain_services import MockManagement, TestExecution
from .events import TestExecuted, TestFailed, TestPassed, TestSuiteCompleted
from .repositories import TestRepository, TestResultRepository
from .value_objects import MockConfiguration, TestData

__all__ = [
    "TestSuite",
    "TestCase",
    "TestResult",
    "TestExecution",
    "MockManagement",
    "TestData",
    "MockConfiguration",
    "TestRepository",
    "TestResultRepository",
    "TestExecuted",
    "TestPassed",
    "TestFailed",
    "TestSuiteCompleted",
]
