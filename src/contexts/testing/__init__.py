"""
Testing Context

This bounded context handles test execution, reporting, and mock management.
"""

from .aggregates import TestSuite, TestCase, TestResult
from .domain_services import TestExecution, MockManagement
from .value_objects import TestData, MockConfiguration
from .repositories import TestRepository, TestResultRepository
from .events import TestExecuted, TestPassed, TestFailed, TestSuiteCompleted

__all__ = [
    'TestSuite',
    'TestCase', 
    'TestResult',
    'TestExecution',
    'MockManagement',
    'TestData',
    'MockConfiguration',
    'TestRepository',
    'TestResultRepository',
    'TestExecuted',
    'TestPassed',
    'TestFailed',
    'TestSuiteCompleted'
]