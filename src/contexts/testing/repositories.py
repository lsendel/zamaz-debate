"""
Testing Context Repository Interfaces

Repository interfaces for the testing context following DDD patterns.
These are abstractions that hide persistence details from the domain layer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .aggregates import MockConfiguration, TestSuite


class TestSuiteRepository(ABC):
    """
    Repository interface for TestSuite aggregate
    
    Provides persistence operations for test suites while hiding
    implementation details from the domain layer.
    """
    
    @abstractmethod
    async def save(self, test_suite: TestSuite) -> None:
        """
        Save a test suite
        
        Args:
            test_suite: The test suite to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, test_suite_id: UUID) -> Optional[TestSuite]:
        """
        Find a test suite by ID
        
        Args:
            test_suite_id: The ID of the test suite
            
        Returns:
            The test suite if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> List[TestSuite]:
        """
        Find test suites by name
        
        Args:
            name: The name to search for
            
        Returns:
            List of matching test suites
        """
        pass
    
    @abstractmethod
    async def find_running(self) -> List[TestSuite]:
        """
        Find all currently running test suites
        
        Returns:
            List of running test suites
        """
        pass
    
    @abstractmethod
    async def find_by_status(self, status: str) -> List[TestSuite]:
        """
        Find test suites by status
        
        Args:
            status: The status to filter by
            
        Returns:
            List of test suites with the given status
        """
        pass
    
    @abstractmethod
    async def find_with_failures(self) -> List[TestSuite]:
        """
        Find test suites that have test failures
        
        Returns:
            List of test suites with failures
        """
        pass
    
    @abstractmethod
    async def find_by_date_range(self, start_date: str, end_date: str) -> List[TestSuite]:
        """
        Find test suites within a date range
        
        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format
            
        Returns:
            List of test suites within the date range
        """
        pass
    
    @abstractmethod
    async def delete(self, test_suite_id: UUID) -> bool:
        """
        Delete a test suite
        
        Args:
            test_suite_id: The ID of the test suite to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """
        Count total number of test suites
        
        Returns:
            Total count of test suites
        """
        pass
    
    @abstractmethod
    async def exists(self, test_suite_id: UUID) -> bool:
        """
        Check if a test suite exists
        
        Args:
            test_suite_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class MockConfigurationRepository(ABC):
    """
    Repository interface for MockConfiguration aggregate
    
    Provides persistence operations for mock configurations.
    """
    
    @abstractmethod
    async def save(self, mock_config: MockConfiguration) -> None:
        """
        Save a mock configuration
        
        Args:
            mock_config: The mock configuration to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, config_id: UUID) -> Optional[MockConfiguration]:
        """
        Find a mock configuration by ID
        
        Args:
            config_id: The ID of the configuration
            
        Returns:
            The configuration if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_service(self, service_name: str) -> List[MockConfiguration]:
        """
        Find mock configurations by target service
        
        Args:
            service_name: The name of the target service
            
        Returns:
            List of configurations for the service
        """
        pass
    
    @abstractmethod
    async def find_active(self) -> List[MockConfiguration]:
        """
        Find all active mock configurations
        
        Returns:
            List of active configurations
        """
        pass
    
    @abstractmethod
    async def find_by_endpoint(self, service: str, endpoint: str) -> Optional[MockConfiguration]:
        """
        Find a mock configuration by service and endpoint
        
        Args:
            service: The target service name
            endpoint: The endpoint path
            
        Returns:
            The configuration if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update(self, mock_config: MockConfiguration) -> bool:
        """
        Update a mock configuration
        
        Args:
            mock_config: The configuration to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, config_id: UUID) -> bool:
        """
        Delete a mock configuration
        
        Args:
            config_id: The ID of the configuration to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def deactivate_all(self) -> int:
        """
        Deactivate all mock configurations
        
        Returns:
            Number of configurations deactivated
        """
        pass
    
    @abstractmethod
    async def exists(self, config_id: UUID) -> bool:
        """
        Check if a mock configuration exists
        
        Args:
            config_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class TestResultRepository(ABC):
    """
    Repository interface for test results
    
    Provides query operations for test results across multiple test suites.
    """
    
    @abstractmethod
    async def find_by_test_suite(self, test_suite_id: UUID) -> List[dict]:
        """
        Find all test results for a test suite
        
        Args:
            test_suite_id: The test suite ID
            
        Returns:
            List of test results
        """
        pass
    
    @abstractmethod
    async def find_failures_by_date(self, date: str) -> List[dict]:
        """
        Find all test failures for a specific date
        
        Args:
            date: The date in ISO format
            
        Returns:
            List of failed test results
        """
        pass
    
    @abstractmethod
    async def get_success_rate(self, days: int = 7) -> float:
        """
        Calculate test success rate over a period
        
        Args:
            days: Number of days to look back
            
        Returns:
            Success rate as a percentage
        """
        pass
    
    @abstractmethod
    async def get_flaky_tests(self, threshold: float = 0.8) -> List[dict]:
        """
        Find tests that fail intermittently
        
        Args:
            threshold: Success rate threshold (tests below this are considered flaky)
            
        Returns:
            List of flaky tests with their success rates
        """
        pass
    
    @abstractmethod
    async def get_slowest_tests(self, limit: int = 10) -> List[dict]:
        """
        Find the slowest running tests
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of slowest tests with execution times
        """
        pass