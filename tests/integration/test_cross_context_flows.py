"""
Integration tests for cross-context communication flows.

Tests the actual event flows between bounded contexts.
"""

import asyncio
import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.contexts.debate import (
    Debate,
    DebateCompleted,
    DebateResult,
    DebateStatus,
)
from src.contexts.evolution import (
    Evolution,
    EvolutionCompleted,
    EvolutionStatus,
    EvolutionTrigger,
    EvolutionTriggered,
    Improvement,
    ImprovementStatus,
)
from src.contexts.implementation import (
    Task,
    TaskCreated,
    TaskStatus,
)
from src.contexts.performance import (
    MetricThresholdBreached,
)
from src.contexts.testing import (
    CoverageDecreased,
    TestFailed,
    TestStatus,
    TestSuiteCompleted,
)
from src.events import get_event_bus, initialize_cross_context_handlers
from src.infrastructure.repositories import (
    JsonDebateRepository,
    JsonEvolutionRepository,
    JsonTaskRepository,
)


@pytest.fixture
async def setup_repositories():
    """Set up test repositories"""
    # Create repositories
    debate_repo = JsonDebateRepository(storage_path="tests/data/debates")
    evolution_repo = JsonEvolutionRepository(storage_path="tests/data/evolutions")
    task_repo = JsonTaskRepository(storage_path="tests/data/tasks")
    
    # Clean up any existing test data
    import shutil
    for path in ["tests/data/debates", "tests/data/evolutions", "tests/data/tasks"]:
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass
    
    yield {
        "debate": debate_repo,
        "evolution": evolution_repo,
        "task": task_repo,
    }
    
    # Cleanup after tests
    for path in ["tests/data/debates", "tests/data/evolutions", "tests/data/tasks"]:
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass


@pytest.fixture
def setup_event_bus():
    """Set up event bus with cross-context handlers"""
    bus = get_event_bus(record_events=True)
    bus.clear_history()
    bus._handlers.clear()
    bus._context_handlers.clear()
    
    # Initialize cross-context handlers
    initialize_cross_context_handlers()
    
    yield bus
    
    # Cleanup
    bus.clear_history()
    bus._handlers.clear()
    bus._context_handlers.clear()


class TestDebateToImplementationFlow:
    """Test Debate → Implementation context flow"""
    
    @pytest.mark.asyncio
    async def test_complex_debate_creates_task(self, setup_repositories, setup_event_bus):
        """Test that completing a complex debate creates implementation task"""
        repos = setup_repositories
        bus = setup_event_bus
        
        # Create and save a debate
        debate = Debate(
            topic="Implement new caching strategy",
            context="Performance optimization required",
        )
        debate.status = DebateStatus.COMPLETED
        debate.result = DebateResult(
            debate_id=debate.id,
            winner="Claude",
            consensus=True,
            summary="Implement Redis caching for API responses",
            decision_rationale="Caching will improve response times by 50%",
        )
        await repos["debate"].save(debate)
        
        # Publish debate completed event
        event = DebateCompleted(
            debate_id=debate.id,
            topic=debate.topic,
            winner="Claude",
            consensus=True,
            decision_type="COMPLEX",
            decision_id=uuid4(),
            summary="Implement Redis caching for API responses",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateCompleted",
            aggregate_id=debate.id,
            version=1,
        )
        
        await bus.publish(event)
        
        # Allow async handlers to complete
        await asyncio.sleep(0.5)
        
        # Verify task was created
        all_tasks = await repos["task"].find_all(Task)
        assert len(all_tasks) == 1
        
        task = all_tasks[0]
        assert "Implement: Implement new caching strategy" in task.title
        assert task.priority == "high"
        assert task.assignment is not None
        assert task.assignment.assignee == "claude"
        
        # Verify task created event was published
        history = bus.get_event_history()
        task_created_events = [e for e in history if isinstance(e, TaskCreated)]
        assert len(task_created_events) == 1
    
    @pytest.mark.asyncio
    async def test_simple_debate_no_task(self, setup_repositories, setup_event_bus):
        """Test that simple debates don't create tasks"""
        repos = setup_repositories
        bus = setup_event_bus
        
        # Create simple debate
        debate = Debate(
            topic="Fix typo in documentation",
            context="Minor documentation update",
        )
        await repos["debate"].save(debate)
        
        # Publish simple debate completion
        event = DebateCompleted(
            debate_id=debate.id,
            topic=debate.topic,
            winner="Gemini",
            consensus=True,
            decision_type="SIMPLE",
            decision_id=uuid4(),
            summary="Fix typo in README",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateCompleted",
            aggregate_id=debate.id,
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.2)
        
        # No task should be created
        all_tasks = await repos["task"].find_all(Task)
        assert len(all_tasks) == 0


class TestEvolutionToAllContextsFlow:
    """Test Evolution → All Contexts flow"""
    
    @pytest.mark.asyncio
    async def test_evolution_triggers_analysis(self, setup_repositories, setup_event_bus):
        """Test that evolution trigger causes system-wide analysis"""
        repos = setup_repositories
        bus = setup_event_bus
        
        # Track handler execution
        analysis_executed = []
        
        # Add custom handler to verify analysis
        async def track_analysis(event: EvolutionTriggered):
            analysis_executed.append(event)
        
        bus.subscribe(EvolutionTriggered, track_analysis, "test_tracker", priority=20)
        
        # Trigger evolution
        event = EvolutionTriggered(
            evolution_id=uuid4(),
            trigger_type="performance",
            trigger_details={
                "reason": "Response time degradation",
                "metric": "api_response_time",
                "current": 850,
                "threshold": 500,
            },
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="EvolutionTriggered",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.2)
        
        # Verify analysis was triggered
        assert len(analysis_executed) == 1
        assert analysis_executed[0].trigger_details["reason"] == "Response time degradation"
    
    @pytest.mark.asyncio
    async def test_evolution_completion_creates_tasks(self, setup_repositories, setup_event_bus):
        """Test that completed evolution creates implementation tasks"""
        repos = setup_repositories
        bus = setup_event_bus
        
        # Create an evolution with approved improvements
        evolution = Evolution(
            trigger=EvolutionTrigger.PERFORMANCE,
            trigger_details={"reason": "Performance degradation"},
        )
        evolution.status = EvolutionStatus.COMPLETED
        
        # Add improvements
        from src.contexts.evolution import ImprovementSuggestion, ImprovementArea
        
        improvement1 = Improvement(
            evolution_id=evolution.id,
            suggestion=ImprovementSuggestion(
                area=ImprovementArea.PERFORMANCE,
                title="Optimize database queries",
                description="Add database indexes",
                rationale="Reduce query time by 70%",
                expected_benefits=["Faster response times"],
                estimated_impact="high",
                implementation_approach="Add indexes to frequently queried columns",
                complexity="moderate",
            ),
        )
        improvement1.approve("system")
        
        improvement2 = Improvement(
            evolution_id=evolution.id,
            suggestion=ImprovementSuggestion(
                area=ImprovementArea.ARCHITECTURE,
                title="Implement caching layer",
                description="Add Redis caching",
                rationale="Reduce database load",
                expected_benefits=["Better scalability"],
                estimated_impact="high",
                implementation_approach="Implement Redis with cache-aside pattern",
                complexity="complex",
            ),
        )
        improvement2.approve("system")
        
        evolution.improvements = [improvement1, improvement2]
        await repos["evolution"].save(evolution)
        
        # Publish evolution completed event
        event = EvolutionCompleted(
            evolution_id=evolution.id,
            total_improvements=2,
            successful_improvements=2,
            metrics_improvement=15.5,
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="EvolutionCompleted",
            aggregate_id=evolution.id,
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.5)
        
        # Verify tasks were created
        all_tasks = await repos["task"].find_all(Task)
        assert len(all_tasks) == 2
        
        # Check task details
        task_titles = [t.title for t in all_tasks]
        assert any("Optimize database queries" in title for title in task_titles)
        assert any("Implement caching layer" in title for title in task_titles)
        
        # Verify assignments
        complex_tasks = [t for t in all_tasks if "caching" in t.title.lower()]
        assert complex_tasks[0].assignment.assignee == "claude"  # Complex task to Claude
        
        moderate_tasks = [t for t in all_tasks if "database" in t.title.lower()]
        assert moderate_tasks[0].assignment.assignee == "gemini"  # Moderate task to Gemini


class TestTestingToPerformanceFlow:
    """Test Testing → Performance context flow"""
    
    @pytest.mark.asyncio
    async def test_performance_test_failure_triggers_analysis(self, setup_event_bus):
        """Test that performance test failures trigger analysis"""
        bus = setup_event_bus
        
        # Track performance analysis requests
        analysis_requests = []
        
        from src.contexts.performance import PerformanceAnalysisRequested
        
        async def track_analysis_request(event: PerformanceAnalysisRequested):
            analysis_requests.append(event)
        
        bus.subscribe(PerformanceAnalysisRequested, track_analysis_request, "test_tracker")
        
        # Publish performance test failure
        event = TestFailed(
            test_case_id=uuid4(),
            test_name="test_api_response_performance",
            error_message="Response time 850ms exceeded threshold of 500ms",
            stack_trace="...",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TestFailed",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.2)
        
        # Verify analysis was requested
        assert len(analysis_requests) == 1
        assert "Response time" in analysis_requests[0].error_details
    
    @pytest.mark.asyncio
    async def test_coverage_decrease_triggers_evolution(self, setup_event_bus):
        """Test that significant coverage decrease triggers evolution"""
        bus = setup_event_bus
        
        # Track evolution triggers
        evolution_triggers = []
        
        async def track_evolution(event: EvolutionTriggered):
            evolution_triggers.append(event)
        
        bus.subscribe(EvolutionTriggered, track_evolution, "test_tracker")
        
        # Publish significant coverage decrease
        event = CoverageDecreased(
            suite_id=uuid4(),
            previous_coverage=85.0,
            current_coverage=75.0,  # 10% decrease
            affected_modules=["src/core", "src/services"],
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="CoverageDecreased",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.2)
        
        # Verify evolution was triggered
        assert len(evolution_triggers) == 1
        assert evolution_triggers[0].trigger_details["reason"] == "Significant coverage decrease"
        assert evolution_triggers[0].trigger_details["decrease"] == 10.0
    
    @pytest.mark.asyncio
    async def test_minor_coverage_decrease_no_evolution(self, setup_event_bus):
        """Test that minor coverage decrease doesn't trigger evolution"""
        bus = setup_event_bus
        
        evolution_triggers = []
        
        async def track_evolution(event: EvolutionTriggered):
            evolution_triggers.append(event)
        
        bus.subscribe(EvolutionTriggered, track_evolution, "test_tracker")
        
        # Publish minor coverage decrease
        event = CoverageDecreased(
            suite_id=uuid4(),
            previous_coverage=85.0,
            current_coverage=82.0,  # Only 3% decrease
            affected_modules=["src/utils"],
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="CoverageDecreased",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.2)
        
        # No evolution should be triggered
        assert len(evolution_triggers) == 0


class TestPerformanceToImplementationFlow:
    """Test Performance → Implementation context flow"""
    
    @pytest.mark.asyncio
    async def test_critical_threshold_creates_urgent_task(self, setup_repositories, setup_event_bus):
        """Test that critical metric threshold breach creates urgent task"""
        repos = setup_repositories
        bus = setup_event_bus
        
        # Publish critical threshold breach
        event = MetricThresholdBreached(
            metric_name="error_rate",
            current_value=0.15,
            threshold=0.05,
            severity="critical",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="MetricThresholdBreached",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.5)
        
        # Verify urgent task was created
        all_tasks = await repos["task"].find_all(Task)
        assert len(all_tasks) == 1
        
        task = all_tasks[0]
        assert "URGENT" in task.title
        assert "error_rate" in task.title
        assert task.priority == "critical"
        assert task.assignment.assignee == "claude"  # Critical tasks go to Claude
    
    @pytest.mark.asyncio
    async def test_non_critical_threshold_no_task(self, setup_repositories, setup_event_bus):
        """Test that non-critical thresholds don't create urgent tasks"""
        repos = setup_repositories
        bus = setup_event_bus
        
        # Publish non-critical threshold breach
        event = MetricThresholdBreached(
            metric_name="cpu_usage",
            current_value=75.0,
            threshold=70.0,
            severity="warning",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="MetricThresholdBreached",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.2)
        
        # No task should be created
        all_tasks = await repos["task"].find_all(Task)
        assert len(all_tasks) == 0


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_evolution_cycle(self, setup_repositories, setup_event_bus):
        """Test complete evolution cycle from trigger to task creation"""
        repos = setup_repositories
        bus = setup_event_bus
        
        # Step 1: Coverage decrease triggers evolution
        coverage_event = CoverageDecreased(
            suite_id=uuid4(),
            previous_coverage=90.0,
            current_coverage=70.0,  # 20% decrease
            affected_modules=["src/core", "src/services", "src/web"],
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="CoverageDecreased",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(coverage_event)
        await asyncio.sleep(0.2)
        
        # Verify evolution was triggered
        history = bus.get_event_history()
        evolution_triggers = [e for e in history if isinstance(e, EvolutionTriggered)]
        assert len(evolution_triggers) == 1
        
        # Step 2: Create and complete evolution
        evolution = Evolution(
            trigger=EvolutionTrigger.MANUAL,
            trigger_details={"reason": "Test coverage restoration"},
        )
        
        from src.contexts.evolution import ImprovementSuggestion, ImprovementArea
        
        improvement = Improvement(
            evolution_id=evolution.id,
            suggestion=ImprovementSuggestion(
                area=ImprovementArea.TESTING,
                title="Add missing unit tests",
                description="Restore test coverage to 90%",
                rationale="Maintain code quality",
                expected_benefits=["Better reliability", "Safer refactoring"],
                estimated_impact="high",
                implementation_approach="Write tests for uncovered code paths",
                complexity="simple",
            ),
        )
        improvement.approve("system")
        evolution.improvements = [improvement]
        evolution.status = EvolutionStatus.COMPLETED
        
        await repos["evolution"].save(evolution)
        
        # Step 3: Publish evolution completed
        evolution_completed = EvolutionCompleted(
            evolution_id=evolution.id,
            total_improvements=1,
            successful_improvements=1,
            metrics_improvement=20.0,
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="EvolutionCompleted",
            aggregate_id=evolution.id,
            version=1,
        )
        
        await bus.publish(evolution_completed)
        await asyncio.sleep(0.5)
        
        # Step 4: Verify task was created
        all_tasks = await repos["task"].find_all(Task)
        assert len(all_tasks) == 1
        
        task = all_tasks[0]
        assert "Add missing unit tests" in task.title
        assert task.priority == "high"
        assert task.assignment is not None
        
        # Verify complete event chain
        final_history = bus.get_event_history()
        assert any(isinstance(e, CoverageDecreased) for e in final_history)
        assert any(isinstance(e, EvolutionTriggered) for e in final_history)
        assert any(isinstance(e, EvolutionCompleted) for e in final_history)
        assert any(isinstance(e, TaskCreated) for e in final_history)