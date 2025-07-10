"""
Testing Context Domain Services

Domain services that contain business logic that doesn't naturally fit
within a single aggregate. These services orchestrate operations across
multiple aggregates or provide specialized domain functionality.
"""

from typing import Dict, List, Optional, Tuple
from uuid import UUID

from .aggregates import MockConfiguration, TestCase, TestSuite
from .repositories import MockConfigurationRepository, TestSuiteRepository
from .value_objects import Coverage, TestConfiguration, TestResult


class TestExecutionService:
    """
    Domain service for orchestrating test execution
    
    Handles complex test execution scenarios that span multiple aggregates
    or require coordination with external systems.
    """
    
    def __init__(
        self,
        test_suite_repo: TestSuiteRepository,
        mock_config_repo: MockConfigurationRepository,
    ):
        self.test_suite_repo = test_suite_repo
        self.mock_config_repo = mock_config_repo
    
    async def execute_test_suite(
        self,
        test_suite: TestSuite,
        configuration: Optional[TestConfiguration] = None,
    ) -> TestResult:
        """
        Execute a complete test suite with proper setup and teardown
        
        Args:
            test_suite: The test suite to execute
            configuration: Optional test configuration override
            
        Returns:
            Aggregated test result
        """
        # Apply configuration if provided
        if configuration:
            test_suite.configuration = configuration
        
        # Set up mocks for the test suite
        mocks = await self._setup_mocks(test_suite.configuration.environment)
        
        try:
            # Start test suite execution
            test_suite.start_execution()
            
            # Execute tests based on configuration
            if test_suite.configuration.parallel_execution:
                results = await self._execute_parallel(test_suite)
            else:
                results = await self._execute_sequential(test_suite)
            
            # Complete the suite
            test_suite.complete_execution()
            
            # Save the updated test suite
            await self.test_suite_repo.save(test_suite)
            
            return self._aggregate_results(results)
            
        finally:
            # Always clean up mocks
            await self._cleanup_mocks(mocks)
    
    async def _execute_sequential(self, test_suite: TestSuite) -> List[TestResult]:
        """Execute tests sequentially"""
        results = []
        
        for test_case in test_suite.test_cases:
            result = await self._execute_single_test(test_suite, test_case)
            results.append(result)
            
            # Stop on first failure if configured
            if not result.is_successful and not test_suite.configuration.retry_count:
                break
        
        return results
    
    async def _execute_parallel(self, test_suite: TestSuite) -> List[TestResult]:
        """Execute tests in parallel"""
        # This is a simplified version - real implementation would use asyncio
        # or multiprocessing for true parallel execution
        import asyncio
        
        tasks = []
        for test_case in test_suite.test_cases:
            task = self._execute_single_test(test_suite, test_case)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _execute_single_test(
        self,
        test_suite: TestSuite,
        test_case: TestCase,
    ) -> TestResult:
        """Execute a single test case"""
        # This would integrate with actual test runners
        # For now, we'll simulate test execution
        
        test_suite.execute_test(test_case.id)
        
        # Simulate test execution result
        # In real implementation, this would run the actual test
        import random
        import time
        
        execution_time = random.randint(10, 1000)
        time.sleep(execution_time / 1000)  # Simulate execution time
        
        if random.random() > 0.1:  # 90% success rate
            test_suite.mark_test_passed(test_case.id, execution_time)
            return TestResult(
                status="passed",
                execution_time_ms=execution_time,
                assertions_passed=len(test_case.assertions),
                assertions_failed=0,
            )
        else:
            error_msg = "Simulated test failure"
            test_suite.mark_test_failed(test_case.id, error_msg)
            return TestResult(
                status="failed",
                execution_time_ms=execution_time,
                error_message=error_msg,
                assertions_passed=0,
                assertions_failed=1,
            )
    
    async def _setup_mocks(self, environment: str) -> List[MockConfiguration]:
        """Set up mock configurations for the test environment"""
        mocks = await self.mock_config_repo.find_active()
        # Filter mocks for the specific environment
        return [m for m in mocks if environment in m.name]
    
    async def _cleanup_mocks(self, mocks: List[MockConfiguration]) -> None:
        """Clean up mock configurations after test execution"""
        # In a real implementation, this might reset mock states
        # or remove temporary mock configurations
        pass
    
    def _aggregate_results(self, results: List[TestResult]) -> TestResult:
        """Aggregate individual test results into a suite result"""
        total_time = sum(r.execution_time_ms for r in results)
        passed = sum(1 for r in results if r.is_successful)
        failed = len(results) - passed
        
        status = "passed" if failed == 0 else "failed"
        
        return TestResult(
            status=status,
            execution_time_ms=total_time,
            assertions_passed=sum(r.assertions_passed for r in results),
            assertions_failed=sum(r.assertions_failed for r in results),
        )


class CoverageAnalysisService:
    """
    Domain service for analyzing test coverage
    
    Provides sophisticated coverage analysis beyond what a single
    aggregate can handle.
    """
    
    def analyze_coverage(
        self,
        test_suite: TestSuite,
        coverage_data: Dict[str, any],
    ) -> Coverage:
        """
        Analyze test coverage data and create coverage metrics
        
        Args:
            test_suite: The test suite that was executed
            coverage_data: Raw coverage data from test execution
            
        Returns:
            Coverage value object with calculated metrics
        """
        # Calculate coverage metrics
        total_lines = coverage_data.get("total_lines", 0)
        covered_lines = coverage_data.get("covered_lines", 0)
        total_branches = coverage_data.get("total_branches", 0)
        covered_branches = coverage_data.get("covered_branches", 0)
        total_functions = coverage_data.get("total_functions", 0)
        covered_functions = coverage_data.get("covered_functions", 0)
        
        line_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0
        branch_coverage = (covered_branches / total_branches * 100) if total_branches > 0 else 0.0
        function_coverage = (covered_functions / total_functions * 100) if total_functions > 0 else 0.0
        
        coverage = Coverage(
            line_coverage=line_coverage,
            branch_coverage=branch_coverage,
            function_coverage=function_coverage,
            total_lines=total_lines,
            covered_lines=covered_lines,
            total_branches=total_branches,
            covered_branches=covered_branches,
            total_functions=total_functions,
            covered_functions=covered_functions,
        )
        
        # Update the test suite with coverage data
        test_suite.analyze_coverage(coverage)
        
        return coverage
    
    def identify_uncovered_code(
        self,
        coverage: Coverage,
        source_files: List[str],
    ) -> List[Tuple[str, List[int]]]:
        """
        Identify specific lines of code that are not covered by tests
        
        Args:
            coverage: The coverage metrics
            source_files: List of source files analyzed
            
        Returns:
            List of tuples (filename, uncovered_lines)
        """
        # This would integrate with actual coverage tools
        # For now, return empty list
        return []
    
    def suggest_test_improvements(
        self,
        coverage: Coverage,
        test_suite: TestSuite,
    ) -> List[str]:
        """
        Suggest improvements to increase test coverage
        
        Args:
            coverage: Current coverage metrics
            test_suite: The test suite analyzed
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        if coverage.line_coverage < 80:
            suggestions.append(
                f"Line coverage is {coverage.line_coverage:.1f}%. "
                "Consider adding tests for uncovered code paths."
            )
        
        if coverage.branch_coverage < 70:
            suggestions.append(
                f"Branch coverage is {coverage.branch_coverage:.1f}%. "
                "Add tests for conditional logic and edge cases."
            )
        
        if coverage.function_coverage < 90:
            suggestions.append(
                f"Function coverage is {coverage.function_coverage:.1f}%. "
                "Ensure all public functions have at least one test."
            )
        
        if test_suite.has_failures:
            suggestions.append(
                "Fix failing tests before focusing on coverage improvements."
            )
        
        return suggestions


class TestDataGenerationService:
    """
    Domain service for generating test data
    
    Provides sophisticated test data generation capabilities for various
    testing scenarios.
    """
    
    def generate_test_data(
        self,
        schema: Dict[str, any],
        count: int = 10,
        strategy: str = "random",
    ) -> List[Dict[str, any]]:
        """
        Generate test data based on a schema
        
        Args:
            schema: Data schema definition
            count: Number of records to generate
            strategy: Generation strategy (random, sequential, edge_cases)
            
        Returns:
            List of generated test data records
        """
        records = []
        
        for i in range(count):
            if strategy == "random":
                record = self._generate_random_record(schema)
            elif strategy == "sequential":
                record = self._generate_sequential_record(schema, i)
            elif strategy == "edge_cases":
                record = self._generate_edge_case_record(schema, i)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
            
            records.append(record)
        
        return records
    
    def _generate_random_record(self, schema: Dict[str, any]) -> Dict[str, any]:
        """Generate a random record based on schema"""
        import random
        import string
        
        record = {}
        for field, field_type in schema.items():
            if field_type == "string":
                record[field] = ''.join(random.choices(string.ascii_letters, k=10))
            elif field_type == "int":
                record[field] = random.randint(1, 1000)
            elif field_type == "float":
                record[field] = random.uniform(0.0, 1000.0)
            elif field_type == "bool":
                record[field] = random.choice([True, False])
            else:
                record[field] = None
        
        return record
    
    def _generate_sequential_record(
        self,
        schema: Dict[str, any],
        index: int,
    ) -> Dict[str, any]:
        """Generate a sequential record based on schema and index"""
        record = {}
        for field, field_type in schema.items():
            if field_type == "string":
                record[field] = f"{field}_{index}"
            elif field_type == "int":
                record[field] = index
            elif field_type == "float":
                record[field] = float(index)
            elif field_type == "bool":
                record[field] = index % 2 == 0
            else:
                record[field] = None
        
        return record
    
    def _generate_edge_case_record(
        self,
        schema: Dict[str, any],
        index: int,
    ) -> Dict[str, any]:
        """Generate edge case records for boundary testing"""
        edge_cases = {
            "string": ["", "null", "undefined", "very_long_" * 100],
            "int": [0, -1, 2147483647, -2147483648],
            "float": [0.0, -0.0, float('inf'), float('-inf')],
            "bool": [True, False, None, 0],
        }
        
        record = {}
        for field, field_type in schema.items():
            if field_type in edge_cases:
                cases = edge_cases[field_type]
                record[field] = cases[index % len(cases)]
            else:
                record[field] = None
        
        return record