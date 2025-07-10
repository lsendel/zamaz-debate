"""
Testing Context Repository Implementations

JSON-based implementations of Testing context repositories.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.contexts.testing import (
    MockConfiguration,
    MockConfigurationRepository,
    TestCase,
    TestExecutionRepository,
    TestMetricsRepository,
    TestStatus,
    TestSuite,
    TestSuiteRepository,
)

from .base import JsonRepository


class JsonTestSuiteRepository(JsonRepository, TestSuiteRepository):
    """JSON-based implementation of TestSuiteRepository"""
    
    def __init__(self, storage_path: str = "data/test_suites"):
        super().__init__(storage_path, "test_suite")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract test suite data for indexing"""
        return {
            "name": data.get("name"),
            "context": data.get("context"),
            "test_count": len(data.get("test_cases", [])),
            "created_at": data.get("created_at"),
        }
    
    async def save(self, test_suite: TestSuite) -> None:
        """Save a test suite"""
        await self.save_entity(test_suite, test_suite.id)
    
    async def find_by_id(self, suite_id: UUID) -> Optional[TestSuite]:
        """Find a test suite by ID"""
        return await self.load_entity(suite_id, TestSuite)
    
    async def find_by_name(self, name: str) -> Optional[TestSuite]:
        """Find a test suite by name"""
        all_suites = await self.find_all(TestSuite)
        
        for suite in all_suites:
            if suite.name == name:
                return suite
        
        return None
    
    async def find_by_context(self, context: str) -> List[TestSuite]:
        """Find test suites by context"""
        all_suites = await self.find_all(TestSuite)
        return [s for s in all_suites if s.context == context]
    
    async def find_all_active(self) -> List[TestSuite]:
        """Find all active test suites"""
        all_suites = await self.find_all(TestSuite)
        return [s for s in all_suites if s.is_active]
    
    async def find_suites_with_failing_tests(self) -> List[TestSuite]:
        """Find test suites with failing tests"""
        all_suites = await self.find_all(TestSuite)
        
        failing_suites = []
        for suite in all_suites:
            if any(tc.status == TestStatus.FAILED for tc in suite.test_cases):
                failing_suites.append(suite)
        
        return failing_suites
    
    async def update(self, test_suite: TestSuite) -> bool:
        """Update a test suite"""
        if await self.exists(test_suite.id):
            await self.save(test_suite)
            return True
        return False
    
    async def delete(self, suite_id: UUID) -> bool:
        """Delete a test suite"""
        return await self.delete_entity(suite_id)
    
    async def get_suite_statistics(self, suite_id: UUID) -> Dict[str, Any]:
        """Get statistics for a test suite"""
        suite = await self.find_by_id(suite_id)
        
        if not suite:
            return {}
        
        total_tests = len(suite.test_cases)
        passed = sum(1 for tc in suite.test_cases if tc.status == TestStatus.PASSED)
        failed = sum(1 for tc in suite.test_cases if tc.status == TestStatus.FAILED)
        skipped = sum(1 for tc in suite.test_cases if tc.status == TestStatus.SKIPPED)
        pending = sum(1 for tc in suite.test_cases if tc.status == TestStatus.PENDING)
        
        total_duration = sum(tc.duration_ms or 0 for tc in suite.test_cases)
        
        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pending": pending,
            "pass_rate": (passed / total_tests) * 100 if total_tests > 0 else 0,
            "total_duration_ms": total_duration,
            "average_duration_ms": total_duration / total_tests if total_tests > 0 else 0,
        }


class JsonMockConfigurationRepository(JsonRepository, MockConfigurationRepository):
    """JSON-based implementation of MockConfigurationRepository"""
    
    def __init__(self, storage_path: str = "data/mock_configs"):
        super().__init__(storage_path, "mock_config")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract mock configuration data for indexing"""
        return {
            "name": data.get("name"),
            "service": data.get("service"),
            "is_active": data.get("is_active"),
            "created_at": data.get("created_at"),
        }
    
    async def save(self, mock_config: MockConfiguration) -> None:
        """Save a mock configuration"""
        await self.save_entity(mock_config, mock_config.id)
    
    async def find_by_id(self, config_id: UUID) -> Optional[MockConfiguration]:
        """Find a mock configuration by ID"""
        return await self.load_entity(config_id, MockConfiguration)
    
    async def find_by_name(self, name: str) -> Optional[MockConfiguration]:
        """Find a mock configuration by name"""
        all_configs = await self.find_all(MockConfiguration)
        
        for config in all_configs:
            if config.name == name:
                return config
        
        return None
    
    async def find_by_service(self, service: str) -> List[MockConfiguration]:
        """Find mock configurations by service"""
        all_configs = await self.find_all(MockConfiguration)
        return [c for c in all_configs if c.service == service]
    
    async def find_active_configs(self) -> List[MockConfiguration]:
        """Find all active mock configurations"""
        all_configs = await self.find_all(MockConfiguration)
        return [c for c in all_configs if c.is_active]
    
    async def find_by_scenario(self, scenario: str) -> List[MockConfiguration]:
        """Find mock configurations by scenario"""
        all_configs = await self.find_all(MockConfiguration)
        
        matching = []
        for config in all_configs:
            if scenario in config.scenarios:
                matching.append(config)
        
        return matching
    
    async def update(self, mock_config: MockConfiguration) -> bool:
        """Update a mock configuration"""
        if await self.exists(mock_config.id):
            await self.save(mock_config)
            return True
        return False
    
    async def delete(self, config_id: UUID) -> bool:
        """Delete a mock configuration"""
        return await self.delete_entity(config_id)


class JsonTestExecutionRepository(JsonRepository, TestExecutionRepository):
    """JSON-based implementation of TestExecutionRepository"""
    
    def __init__(self, storage_path: str = "data/test_executions"):
        super().__init__(storage_path, "test_execution")
        self.test_suite_repo = JsonTestSuiteRepository()
    
    async def save_test_execution(
        self,
        suite_id: UUID,
        test_case_id: UUID,
        result: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Save a test execution result"""
        execution = {
            "id": str(UUID()),
            "suite_id": str(suite_id),
            "test_case_id": str(test_case_id),
            "result": result,
            "timestamp": timestamp.isoformat(),
        }
        
        await self.save_entity(execution, UUID(execution["id"]))
    
    async def get_test_history(
        self,
        test_case_id: UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get execution history for a test case"""
        all_executions = await self.find_all(dict)
        
        # Filter by test case ID
        test_history = [
            e for e in all_executions
            if e.get("test_case_id") == str(test_case_id)
        ]
        
        # Sort by timestamp (most recent first)
        test_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return test_history[:limit]
    
    async def get_suite_execution_history(
        self,
        suite_id: UUID,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get execution history for a test suite"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        all_executions = await self.find_all(dict)
        
        # Filter by suite ID and date
        suite_history = []
        for execution in all_executions:
            if execution.get("suite_id") == str(suite_id):
                timestamp = datetime.fromisoformat(execution["timestamp"])
                if timestamp.timestamp() >= cutoff_date:
                    suite_history.append(execution)
        
        # Sort by timestamp
        suite_history.sort(key=lambda x: x["timestamp"])
        
        return suite_history
    
    async def get_failure_trends(
        self,
        days: int = 7,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get failure trends over time"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        all_executions = await self.find_all(dict)
        
        # Group failures by test case
        failure_trends = {}
        
        for execution in all_executions:
            timestamp = datetime.fromisoformat(execution["timestamp"])
            if timestamp.timestamp() >= cutoff_date:
                result = execution.get("result", {})
                if result.get("status") == "failed":
                    test_case_id = execution["test_case_id"]
                    
                    if test_case_id not in failure_trends:
                        failure_trends[test_case_id] = []
                    
                    failure_trends[test_case_id].append({
                        "timestamp": execution["timestamp"],
                        "error": result.get("error"),
                    })
        
        return failure_trends
    
    async def get_flaky_tests(
        self,
        threshold: float = 0.2,
        min_runs: int = 5,
    ) -> List[Dict[str, Any]]:
        """Identify flaky tests"""
        all_executions = await self.find_all(dict)
        
        # Group executions by test case
        test_results = {}
        
        for execution in all_executions:
            test_case_id = execution["test_case_id"]
            if test_case_id not in test_results:
                test_results[test_case_id] = {"passed": 0, "failed": 0}
            
            result = execution.get("result", {})
            if result.get("status") == "passed":
                test_results[test_case_id]["passed"] += 1
            elif result.get("status") == "failed":
                test_results[test_case_id]["failed"] += 1
        
        # Identify flaky tests
        flaky_tests = []
        
        for test_case_id, results in test_results.items():
            total_runs = results["passed"] + results["failed"]
            
            if total_runs >= min_runs:
                failure_rate = results["failed"] / total_runs
                
                # Flaky if failure rate is between threshold and (1 - threshold)
                if threshold <= failure_rate <= (1 - threshold):
                    flaky_tests.append({
                        "test_case_id": test_case_id,
                        "failure_rate": failure_rate,
                        "total_runs": total_runs,
                        "passed": results["passed"],
                        "failed": results["failed"],
                    })
        
        # Sort by failure rate
        flaky_tests.sort(key=lambda x: x["failure_rate"], reverse=True)
        
        return flaky_tests


class JsonTestMetricsRepository(JsonRepository, TestMetricsRepository):
    """JSON-based implementation of TestMetricsRepository"""
    
    def __init__(self, storage_path: str = "data/test_metrics"):
        super().__init__(storage_path, "test_metrics")
        self.test_suite_repo = JsonTestSuiteRepository()
        self.test_execution_repo = JsonTestExecutionRepository()
    
    async def get_coverage_trends(
        self,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get test coverage trends over time"""
        # In a real implementation, this would track actual coverage data
        # For now, we'll generate sample data
        trends = []
        
        for i in range(days):
            date = datetime.now().timestamp() - (i * 24 * 60 * 60)
            date = datetime.fromtimestamp(date)
            
            # Simulate coverage improvement over time
            base_coverage = 70
            daily_improvement = 0.3
            coverage = min(95, base_coverage + (days - i) * daily_improvement)
            
            trends.append({
                "date": date.isoformat(),
                "line_coverage": coverage,
                "branch_coverage": coverage - 5,
                "function_coverage": coverage + 2,
            })
        
        return trends
    
    async def get_test_performance_metrics(
        self,
        suite_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get test performance metrics"""
        if suite_id:
            suites = [await self.test_suite_repo.find_by_id(suite_id)]
        else:
            suites = await self.test_suite_repo.find_all(TestSuite)
        
        total_tests = 0
        total_duration = 0
        slowest_tests = []
        
        for suite in suites:
            if not suite:
                continue
                
            for test_case in suite.test_cases:
                total_tests += 1
                duration = test_case.duration_ms or 0
                total_duration += duration
                
                slowest_tests.append({
                    "test_name": test_case.name,
                    "suite_name": suite.name,
                    "duration_ms": duration,
                })
        
        # Sort by duration
        slowest_tests.sort(key=lambda x: x["duration_ms"], reverse=True)
        
        return {
            "total_tests": total_tests,
            "total_duration_ms": total_duration,
            "average_duration_ms": total_duration / total_tests if total_tests > 0 else 0,
            "slowest_tests": slowest_tests[:10],
        }
    
    async def get_reliability_score(
        self,
        suite_id: Optional[UUID] = None,
        days: int = 7,
    ) -> float:
        """Calculate test reliability score"""
        flaky_tests = await self.test_execution_repo.get_flaky_tests()
        
        if suite_id:
            # Filter flaky tests for specific suite
            suite = await self.test_suite_repo.find_by_id(suite_id)
            if suite:
                suite_test_ids = {str(tc.id) for tc in suite.test_cases}
                flaky_tests = [
                    ft for ft in flaky_tests
                    if ft["test_case_id"] in suite_test_ids
                ]
        
        # Calculate reliability score
        if not flaky_tests:
            return 100.0
        
        # Penalize based on flaky test count and failure rates
        total_penalty = 0
        for flaky_test in flaky_tests:
            # Higher penalty for tests with failure rates closer to 50%
            failure_rate = flaky_test["failure_rate"]
            penalty = 10 * (1 - abs(0.5 - failure_rate) * 2)
            total_penalty += penalty
        
        reliability_score = max(0, 100 - total_penalty)
        
        return reliability_score
    
    async def get_test_impact_analysis(
        self,
        changed_files: List[str],
    ) -> List[Dict[str, Any]]:
        """Analyze which tests are impacted by file changes"""
        # In a real implementation, this would use dependency analysis
        # For now, we'll use a simple mapping
        
        impacted_tests = []
        all_suites = await self.test_suite_repo.find_all(TestSuite)
        
        for suite in all_suites:
            for test_case in suite.test_cases:
                # Simple heuristic: tests are impacted if they're in the same context
                # as the changed files
                for changed_file in changed_files:
                    if suite.context.lower() in changed_file.lower():
                        impacted_tests.append({
                            "test_id": str(test_case.id),
                            "test_name": test_case.name,
                            "suite_name": suite.name,
                            "reason": f"Related to {changed_file}",
                            "priority": "high" if test_case.is_critical else "medium",
                        })
                        break
        
        return impacted_tests