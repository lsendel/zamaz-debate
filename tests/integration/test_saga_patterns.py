"""
Integration tests for saga patterns.

Tests long-running processes that span multiple contexts with compensation.
"""

import asyncio
import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.contexts.evolution import (
    Evolution,
    EvolutionStatus,
    EvolutionTrigger,
)
from src.contexts.implementation import (
    Task,
    TaskStatus,
    PullRequest,
    PullRequestStatus,
    Deployment,
    DeploymentStatus,
)
from src.events import get_event_bus, subscribe
from src.events.cross_context_handlers import EvolutionSaga
from src.infrastructure.repositories import (
    JsonEvolutionRepository,
    JsonTaskRepository,
    JsonPullRequestRepository,
    JsonDeploymentRepository,
)


class DeploymentSaga:
    """
    Orchestrates deployment workflow from PR merge to production.
    
    Steps:
    1. PR Merged
    2. Run Tests
    3. Build Application
    4. Deploy to Staging
    5. Validate Staging
    6. Deploy to Production
    7. Validate Production
    """
    
    def __init__(self, pr_repo, deployment_repo):
        self.saga_id = uuid4()
        self.pr_repo = pr_repo
        self.deployment_repo = deployment_repo
        self.state = "initialized"
        self.completed_steps = []
        self.pr_id = None
        self.staging_deployment_id = None
        self.production_deployment_id = None
    
    async def execute(self, pr_id: UUID) -> Dict[str, Any]:
        """Execute the deployment saga"""
        self.pr_id = pr_id
        
        try:
            # Step 1: Verify PR is merged
            self.state = "verifying_pr"
            pr = await self._verify_pr_merged(pr_id)
            self.completed_steps.append("verify_pr")
            
            # Step 2: Run tests
            self.state = "running_tests"
            test_results = await self._run_tests(pr)
            self.completed_steps.append("run_tests")
            
            # Step 3: Build application
            self.state = "building"
            build_info = await self._build_application(pr)
            self.completed_steps.append("build")
            
            # Step 4: Deploy to staging
            self.state = "deploying_staging"
            self.staging_deployment_id = await self._deploy_to_staging(pr, build_info)
            self.completed_steps.append("deploy_staging")
            
            # Step 5: Validate staging
            self.state = "validating_staging"
            staging_validation = await self._validate_staging(self.staging_deployment_id)
            self.completed_steps.append("validate_staging")
            
            # Step 6: Deploy to production
            self.state = "deploying_production"
            self.production_deployment_id = await self._deploy_to_production(pr, build_info)
            self.completed_steps.append("deploy_production")
            
            # Step 7: Validate production
            self.state = "validating_production"
            prod_validation = await self._validate_production(self.production_deployment_id)
            self.completed_steps.append("validate_production")
            
            self.state = "completed"
            
            return {
                "saga_id": str(self.saga_id),
                "pr_id": str(pr_id),
                "staging_deployment_id": str(self.staging_deployment_id),
                "production_deployment_id": str(self.production_deployment_id),
                "status": "success",
                "completed_steps": self.completed_steps,
            }
            
        except Exception as e:
            self.state = "failed"
            await self._compensate()
            raise
    
    async def _verify_pr_merged(self, pr_id: UUID) -> PullRequest:
        """Verify PR is merged"""
        pr = await self.pr_repo.find_by_id(pr_id)
        if not pr:
            raise ValueError(f"PR {pr_id} not found")
        if pr.status != PullRequestStatus.MERGED:
            raise ValueError(f"PR {pr_id} is not merged")
        return pr
    
    async def _run_tests(self, pr: PullRequest) -> Dict[str, Any]:
        """Run tests (simulated)"""
        # In real implementation, would trigger test suite
        await asyncio.sleep(0.1)  # Simulate test execution
        
        # Simulate test failure for testing compensation
        if "fail_tests" in pr.title.lower():
            raise ValueError("Tests failed")
        
        return {
            "tests_passed": 150,
            "tests_failed": 0,
            "coverage": 92.5,
        }
    
    async def _build_application(self, pr: PullRequest) -> Dict[str, Any]:
        """Build application (simulated)"""
        await asyncio.sleep(0.1)  # Simulate build
        
        return {
            "build_id": str(uuid4()),
            "version": f"1.0.{pr.pr_number}",
            "artifacts": ["app.jar", "config.yml"],
        }
    
    async def _deploy_to_staging(self, pr: PullRequest, build_info: Dict[str, Any]) -> UUID:
        """Deploy to staging environment"""
        deployment = Deployment(
            pr_id=pr.id,
            environment="staging",
        )
        deployment.start()
        
        # Simulate deployment
        await asyncio.sleep(0.1)
        
        # Simulate deployment failure for testing compensation
        if "fail_staging" in pr.title.lower():
            deployment.fail("Staging deployment failed")
            await self.deployment_repo.save(deployment)
            raise ValueError("Staging deployment failed")
        
        deployment.complete()
        await self.deployment_repo.save(deployment)
        
        return deployment.id
    
    async def _validate_staging(self, deployment_id: UUID) -> Dict[str, Any]:
        """Validate staging deployment"""
        await asyncio.sleep(0.1)  # Simulate validation
        
        return {
            "health_check": "passed",
            "smoke_tests": "passed",
            "performance": "acceptable",
        }
    
    async def _deploy_to_production(self, pr: PullRequest, build_info: Dict[str, Any]) -> UUID:
        """Deploy to production environment"""
        deployment = Deployment(
            pr_id=pr.id,
            environment="production",
        )
        deployment.start()
        
        # Simulate deployment
        await asyncio.sleep(0.1)
        
        # Simulate deployment failure for testing compensation
        if "fail_production" in pr.title.lower():
            deployment.fail("Production deployment failed")
            await self.deployment_repo.save(deployment)
            raise ValueError("Production deployment failed")
        
        deployment.complete()
        await self.deployment_repo.save(deployment)
        
        return deployment.id
    
    async def _validate_production(self, deployment_id: UUID) -> Dict[str, Any]:
        """Validate production deployment"""
        await asyncio.sleep(0.1)  # Simulate validation
        
        return {
            "health_check": "passed",
            "monitoring": "configured",
            "alerts": "active",
        }
    
    async def _compensate(self) -> None:
        """Compensate for failed saga"""
        print(f"Compensating deployment saga {self.saga_id}")
        
        # Reverse completed steps
        for step in reversed(self.completed_steps):
            if step == "deploy_production" and self.production_deployment_id:
                # Rollback production
                deployment = await self.deployment_repo.find_by_id(self.production_deployment_id)
                if deployment:
                    deployment.rollback()
                    await self.deployment_repo.save(deployment)
                    
            elif step == "deploy_staging" and self.staging_deployment_id:
                # Rollback staging
                deployment = await self.deployment_repo.find_by_id(self.staging_deployment_id)
                if deployment:
                    deployment.rollback()
                    await self.deployment_repo.save(deployment)


@pytest.fixture
async def setup_saga_repositories():
    """Set up repositories for saga testing"""
    # Create repositories
    evolution_repo = JsonEvolutionRepository(storage_path="tests/data/evolutions")
    task_repo = JsonTaskRepository(storage_path="tests/data/tasks")
    pr_repo = JsonPullRequestRepository(storage_path="tests/data/pull_requests")
    deployment_repo = JsonDeploymentRepository(storage_path="tests/data/deployments")
    
    # Clean up any existing test data
    import shutil
    paths = [
        "tests/data/evolutions",
        "tests/data/tasks",
        "tests/data/pull_requests",
        "tests/data/deployments",
    ]
    for path in paths:
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass
    
    yield {
        "evolution": evolution_repo,
        "task": task_repo,
        "pr": pr_repo,
        "deployment": deployment_repo,
    }
    
    # Cleanup after tests
    for path in paths:
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass


@pytest.fixture
def setup_saga_event_bus():
    """Set up event bus for saga testing"""
    bus = get_event_bus(record_events=True)
    bus.clear_history()
    bus._handlers.clear()
    bus._context_handlers.clear()
    
    yield bus
    
    # Cleanup
    bus.clear_history()
    bus._handlers.clear()
    bus._context_handlers.clear()


class TestEvolutionSaga:
    """Test evolution saga pattern"""
    
    @pytest.mark.asyncio
    async def test_evolution_saga_happy_path(self, setup_saga_repositories, setup_saga_event_bus):
        """Test successful evolution saga execution"""
        repos = setup_saga_repositories
        bus = setup_saga_event_bus
        
        # Mock the saga steps
        saga = EvolutionSaga()
        saga._trigger_evolution = async_mock_return(uuid4())
        saga._analyze_system = async_mock_return(None)
        saga._create_plan = async_mock_return(None)
        saga._implement_improvements = async_mock_return(None)
        saga._validate_evolution = async_mock_return(None)
        
        # Execute saga
        await saga.execute(EvolutionTrigger.PERFORMANCE, {"reason": "Test"})
        
        # Verify all steps completed
        assert saga.state == "completed"
        assert len(saga.completed_steps) == 5
        assert saga.completed_steps == [
            "trigger",
            "analysis",
            "planning",
            "implementation",
            "validation",
        ]
    
    @pytest.mark.asyncio
    async def test_evolution_saga_compensation(self, setup_saga_repositories, setup_saga_event_bus):
        """Test evolution saga compensation on failure"""
        repos = setup_saga_repositories
        bus = setup_saga_event_bus
        
        # Mock saga to fail at implementation
        saga = EvolutionSaga()
        saga._trigger_evolution = async_mock_return(uuid4())
        saga._analyze_system = async_mock_return(None)
        saga._create_plan = async_mock_return(None)
        saga._implement_improvements = async_mock_raise(ValueError("Implementation failed"))
        
        compensated = []
        saga._compensate = async_mock_track(compensated)
        
        # Execute saga and expect failure
        with pytest.raises(ValueError, match="Implementation failed"):
            await saga.execute(EvolutionTrigger.PERFORMANCE, {"reason": "Test"})
        
        # Verify compensation was called
        assert saga.state == "failed"
        assert len(compensated) == 1
        assert saga.completed_steps == ["trigger", "analysis", "planning"]


class TestDeploymentSaga:
    """Test deployment saga pattern"""
    
    @pytest.mark.asyncio
    async def test_deployment_saga_success(self, setup_saga_repositories):
        """Test successful deployment saga"""
        repos = setup_saga_repositories
        
        # Create a merged PR
        pr = PullRequest(
            task_id=uuid4(),
            title="Feature: Add new API endpoint",
            description="Implements new endpoint",
            branch_name="feature/new-api",
        )
        pr.merge()
        await repos["pr"].save(pr)
        
        # Execute deployment saga
        saga = DeploymentSaga(repos["pr"], repos["deployment"])
        result = await saga.execute(pr.id)
        
        # Verify success
        assert result["status"] == "success"
        assert len(result["completed_steps"]) == 7
        assert saga.state == "completed"
        
        # Verify deployments were created
        staging_deployment = await repos["deployment"].find_by_id(
            UUID(result["staging_deployment_id"])
        )
        assert staging_deployment is not None
        assert staging_deployment.status == DeploymentStatus.SUCCEEDED
        
        prod_deployment = await repos["deployment"].find_by_id(
            UUID(result["production_deployment_id"])
        )
        assert prod_deployment is not None
        assert prod_deployment.status == DeploymentStatus.SUCCEEDED
    
    @pytest.mark.asyncio
    async def test_deployment_saga_test_failure(self, setup_saga_repositories):
        """Test deployment saga compensation on test failure"""
        repos = setup_saga_repositories
        
        # Create PR that will fail tests
        pr = PullRequest(
            task_id=uuid4(),
            title="Feature: fail_tests",  # Trigger test failure
            description="Will fail tests",
            branch_name="feature/bad",
        )
        pr.merge()
        await repos["pr"].save(pr)
        
        # Execute saga and expect failure
        saga = DeploymentSaga(repos["pr"], repos["deployment"])
        
        with pytest.raises(ValueError, match="Tests failed"):
            await saga.execute(pr.id)
        
        # Verify saga failed early
        assert saga.state == "failed"
        assert saga.completed_steps == ["verify_pr"]
        assert saga.staging_deployment_id is None
        assert saga.production_deployment_id is None
    
    @pytest.mark.asyncio
    async def test_deployment_saga_staging_failure(self, setup_saga_repositories):
        """Test deployment saga compensation on staging failure"""
        repos = setup_saga_repositories
        
        # Create PR that will fail staging deployment
        pr = PullRequest(
            task_id=uuid4(),
            title="Feature: fail_staging",  # Trigger staging failure
            description="Will fail staging",
            branch_name="feature/staging-fail",
        )
        pr.merge()
        await repos["pr"].save(pr)
        
        # Execute saga and expect failure
        saga = DeploymentSaga(repos["pr"], repos["deployment"])
        
        with pytest.raises(ValueError, match="Staging deployment failed"):
            await saga.execute(pr.id)
        
        # Verify partial completion
        assert saga.state == "failed"
        assert "deploy_staging" not in saga.completed_steps
        assert saga.staging_deployment_id is not None
        
        # Verify staging deployment was marked as failed
        staging = await repos["deployment"].find_by_id(saga.staging_deployment_id)
        assert staging.status == DeploymentStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_deployment_saga_production_rollback(self, setup_saga_repositories):
        """Test deployment saga compensation with production rollback"""
        repos = setup_saga_repositories
        
        # Create PR that will fail production deployment
        pr = PullRequest(
            task_id=uuid4(),
            title="Feature: fail_production",  # Trigger production failure
            description="Will fail production",
            branch_name="feature/prod-fail",
        )
        pr.merge()
        await repos["pr"].save(pr)
        
        # Execute saga and expect failure
        saga = DeploymentSaga(repos["pr"], repos["deployment"])
        
        with pytest.raises(ValueError, match="Production deployment failed"):
            await saga.execute(pr.id)
        
        # Verify staging succeeded but production failed
        assert saga.state == "failed"
        assert "validate_staging" in saga.completed_steps
        assert "deploy_production" not in saga.completed_steps
        
        # Verify staging deployment succeeded
        staging = await repos["deployment"].find_by_id(saga.staging_deployment_id)
        assert staging.status == DeploymentStatus.SUCCEEDED
        
        # Verify production deployment was marked as failed
        production = await repos["deployment"].find_by_id(saga.production_deployment_id)
        assert production.status == DeploymentStatus.FAILED


class TestSagaOrchestration:
    """Test saga orchestration patterns"""
    
    @pytest.mark.asyncio
    async def test_parallel_saga_execution(self, setup_saga_repositories):
        """Test running multiple sagas in parallel"""
        repos = setup_saga_repositories
        
        # Create multiple PRs
        prs = []
        for i in range(3):
            pr = PullRequest(
                task_id=uuid4(),
                title=f"Feature: parallel-{i}",
                description=f"Parallel deployment {i}",
                branch_name=f"feature/parallel-{i}",
            )
            pr.merge()
            await repos["pr"].save(pr)
            prs.append(pr)
        
        # Execute sagas in parallel
        sagas = [DeploymentSaga(repos["pr"], repos["deployment"]) for _ in prs]
        
        results = await asyncio.gather(*[
            saga.execute(pr.id) for saga, pr in zip(sagas, prs)
        ])
        
        # Verify all succeeded
        assert all(r["status"] == "success" for r in results)
        assert all(saga.state == "completed" for saga in sagas)
        
        # Verify all deployments were created
        all_deployments = await repos["deployment"].find_all(Deployment)
        assert len(all_deployments) == 6  # 3 staging + 3 production
    
    @pytest.mark.asyncio
    async def test_saga_state_persistence(self, setup_saga_repositories):
        """Test saga state can be persisted and resumed"""
        repos = setup_saga_repositories
        
        # Create PR
        pr = PullRequest(
            task_id=uuid4(),
            title="Feature: persistent",
            description="Test persistence",
            branch_name="feature/persistent",
        )
        pr.merge()
        await repos["pr"].save(pr)
        
        # Start saga
        saga = DeploymentSaga(repos["pr"], repos["deployment"])
        
        # Simulate saving saga state after each step
        saga_states = []
        
        original_methods = {}
        for method_name in ["_verify_pr_merged", "_run_tests", "_build_application"]:
            original_method = getattr(saga, method_name)
            
            async def wrapped_method(*args, **kwargs):
                result = await original_method(*args, **kwargs)
                # Save state
                saga_states.append({
                    "saga_id": saga.saga_id,
                    "state": saga.state,
                    "completed_steps": saga.completed_steps.copy(),
                })
                return result
            
            setattr(saga, method_name, wrapped_method)
        
        # Execute partially
        result = await saga.execute(pr.id)
        
        # Verify states were captured
        assert len(saga_states) >= 3
        assert saga_states[0]["state"] == "verifying_pr"
        assert saga_states[1]["state"] == "running_tests"
        assert saga_states[2]["state"] == "building"


# Helper functions for mocking
def async_mock_return(value):
    """Create an async function that returns a value"""
    async def mock(*args, **kwargs):
        return value
    return mock


def async_mock_raise(exception):
    """Create an async function that raises an exception"""
    async def mock(*args, **kwargs):
        raise exception
    return mock


def async_mock_track(track_list):
    """Create an async function that tracks calls"""
    async def mock(*args, **kwargs):
        track_list.append((args, kwargs))
    return mock