"""
Cross-Context Event Handlers

Implements event handlers that enable communication between bounded contexts.
These handlers orchestrate workflows that span multiple contexts.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.contexts.debate import (
    DebateCompleted,
    DebateRepository,
)
from src.contexts.evolution import (
    Evolution,
    EvolutionAnalysisService,
    EvolutionCompleted,
    EvolutionRepository,
    EvolutionTrigger,
    EvolutionTriggered,
)
from src.contexts.implementation import (
    ImplementationRequested,
    Task,
    TaskCreated,
    TaskRepository,
)
from src.contexts.performance import (
    BenchmarkTriggered,
    MetricThresholdBreached,
    PerformanceAnalysisRequested,
)
from src.contexts.testing import (
    CoverageDecreased,
    TestFailed,
    TestSuiteCompleted,
)

from .event_bus import get_event_bus, subscribe

logger = logging.getLogger(__name__)


# Debate → Implementation Flow
@subscribe(DebateCompleted, context="implementation", priority=10)
async def create_implementation_tasks_from_debate(event: DebateCompleted) -> None:
    """
    When a debate completes with a complex decision, create implementation tasks.
    """
    logger.info(f"Processing debate completion for implementation: {event.debate_id}")
    
    # Only process complex decisions
    if event.decision_type not in ["COMPLEX", "EVOLUTION"]:
        logger.debug(f"Skipping non-complex decision type: {event.decision_type}")
        return
    
    # Get repositories (in real implementation, would use dependency injection)
    from src.infrastructure.repositories import JsonTaskRepository, JsonDebateRepository
    
    task_repo = JsonTaskRepository()
    debate_repo = JsonDebateRepository()
    
    # Get debate details
    debate = await debate_repo.find_by_id(event.debate_id)
    if not debate:
        logger.error(f"Debate not found: {event.debate_id}")
        return
    
    # Create implementation task
    task = Task(
        decision_id=event.decision_id,
        title=f"Implement: {event.topic}",
        description=f"Implementation task for debate: {event.summary}",
        priority="high" if event.decision_type == "EVOLUTION" else "medium",
    )
    
    # Assign based on debate winner
    if event.winner:
        from src.contexts.implementation import Assignment
        assignment = Assignment(
            assignee=event.winner.lower(),
            assignee_type="ai",
        )
        task.assign(assignment)
    
    # Save task
    await task_repo.save(task)
    
    # Publish task created event
    bus = get_event_bus()
    await bus.publish(TaskCreated(
        task_id=task.id,
        decision_id=event.decision_id,
        title=task.title,
        priority=task.priority,
        event_id=uuid4(),
        occurred_at=datetime.now(),
        event_type="TaskCreated",
        aggregate_id=task.id,
        version=1,
    ))
    
    logger.info(f"Created implementation task {task.id} for debate {event.debate_id}")


# Evolution → All Contexts Flow
@subscribe(EvolutionTriggered, context="all", priority=15)
async def analyze_all_contexts_for_evolution(event: EvolutionTriggered) -> None:
    """
    When evolution is triggered, analyze all contexts for improvements.
    """
    logger.info(f"Analyzing all contexts for evolution: {event.evolution_id}")
    
    # Get repositories
    from src.infrastructure.repositories import (
        JsonEvolutionRepository,
        JsonEvolutionMetricsRepository,
    )
    
    evolution_repo = JsonEvolutionRepository()
    metrics_repo = JsonEvolutionMetricsRepository()
    
    # Create analysis service
    from src.infrastructure.repositories import JsonEvolutionHistoryRepository
    history_repo = JsonEvolutionHistoryRepository()
    
    analysis_service = EvolutionAnalysisService(
        evolution_repo,
        history_repo,
        metrics_repo,
    )
    
    # Collect current metrics from all contexts
    from src.contexts.evolution import EvolutionMetrics
    
    # In real implementation, would collect actual metrics
    current_metrics = EvolutionMetrics(
        performance_score=75.0,
        reliability_score=82.0,
        maintainability_score=70.0,
        security_score=88.0,
        test_coverage=78.0,
        code_complexity=12.5,
        technical_debt_hours=150.0,
        error_rate=0.05,
        response_time_ms=450.0,
        memory_usage_mb=512.0,
        cpu_usage_percent=65.0,
        measured_at=datetime.now(),
    )
    
    # Analyze system
    suggestions = await analysis_service.analyze_system(current_metrics)
    
    logger.info(f"Evolution analysis found {len(suggestions)} improvement suggestions")
    
    # The evolution aggregate will handle creating improvements from suggestions


@subscribe(EvolutionCompleted, context="implementation", priority=10)
async def create_tasks_from_evolution(event: EvolutionCompleted) -> None:
    """
    When evolution completes, create implementation tasks for improvements.
    """
    logger.info(f"Creating tasks from completed evolution: {event.evolution_id}")
    
    # Get repositories
    from src.infrastructure.repositories import (
        JsonEvolutionRepository,
        JsonTaskRepository,
    )
    
    evolution_repo = JsonEvolutionRepository()
    task_repo = JsonTaskRepository()
    
    # Get evolution details
    evolution = await evolution_repo.find_by_id(event.evolution_id)
    if not evolution:
        logger.error(f"Evolution not found: {event.evolution_id}")
        return
    
    # Create tasks for successful improvements
    created_tasks = 0
    for improvement in evolution.improvements:
        if improvement.is_approved and not improvement.implementation_task_id:
            # Create implementation task
            task = Task(
                decision_id=evolution.id,  # Use evolution ID as decision ID
                title=f"Evolution: {improvement.suggestion.title}",
                description=improvement.suggestion.implementation_approach,
                priority="high",  # Evolution tasks are high priority
                implementation_type="evolution",
            )
            
            # Assign to appropriate implementer based on area
            from src.contexts.implementation import Assignment
            
            # Simple assignment logic (in reality would be more sophisticated)
            assignee = "claude" if improvement.suggestion.complexity == "complex" else "gemini"
            
            assignment = Assignment(
                assignee=assignee,
                assignee_type="ai",
            )
            task.assign(assignment)
            
            # Save task
            await task_repo.save(task)
            
            # Update improvement with task ID
            improvement.mark_implemented(task.id)
            
            created_tasks += 1
    
    # Update evolution if tasks were created
    if created_tasks > 0:
        await evolution_repo.update(evolution)
    
    logger.info(f"Created {created_tasks} implementation tasks from evolution {event.evolution_id}")


# Testing → Performance Flow
@subscribe(TestFailed, context="performance", priority=5)
async def analyze_performance_on_test_failure(event: TestFailed) -> None:
    """
    When a performance test fails, trigger performance analysis.
    """
    logger.info(f"Analyzing performance due to test failure: {event.test_case_id}")
    
    # Check if it's a performance-related test
    if "performance" not in event.test_name.lower() and "benchmark" not in event.test_name.lower():
        logger.debug("Test is not performance-related, skipping analysis")
        return
    
    # Publish performance analysis request
    bus = get_event_bus()
    await bus.publish(PerformanceAnalysisRequested(
        reason=f"Performance test failed: {event.test_name}",
        test_case_id=event.test_case_id,
        error_details=event.error_message,
        event_id=uuid4(),
        occurred_at=datetime.now(),
        event_type="PerformanceAnalysisRequested",
        aggregate_id=event.test_case_id,
        version=1,
    ))


@subscribe(CoverageDecreased, context="evolution", priority=10)
async def suggest_test_improvements(event: CoverageDecreased) -> None:
    """
    When test coverage decreases, suggest improvements through evolution.
    """
    logger.info(f"Coverage decreased from {event.previous_coverage}% to {event.current_coverage}%")
    
    # Only trigger if decrease is significant
    decrease = event.previous_coverage - event.current_coverage
    if decrease < 5.0:
        logger.debug("Coverage decrease is minor, not triggering evolution")
        return
    
    # Trigger evolution analysis focused on testing
    bus = get_event_bus()
    await bus.publish(EvolutionTriggered(
        evolution_id=uuid4(),
        trigger_type="testing",
        trigger_details={
            "reason": "Significant coverage decrease",
            "previous_coverage": event.previous_coverage,
            "current_coverage": event.current_coverage,
            "decrease": decrease,
            "affected_areas": event.affected_modules,
        },
        event_id=uuid4(),
        occurred_at=datetime.now(),
        event_type="EvolutionTriggered",
        aggregate_id=uuid4(),
        version=1,
    ))


@subscribe(TestSuiteCompleted, context="performance", priority=5)
async def update_performance_baselines(event: TestSuiteCompleted) -> None:
    """
    When a test suite completes, update performance baselines if needed.
    """
    logger.info(f"Test suite completed: {event.suite_name}")
    
    # Check if it's a benchmark suite
    if "benchmark" not in event.suite_name.lower():
        return
    
    # Trigger benchmark update
    bus = get_event_bus()
    await bus.publish(BenchmarkTriggered(
        benchmark_name=event.suite_name,
        triggered_by="test_suite_completion",
        environment="test",
        event_id=uuid4(),
        occurred_at=datetime.now(),
        event_type="BenchmarkTriggered",
        aggregate_id=uuid4(),
        version=1,
    ))


# Implementation → Evolution Flow
@subscribe(TaskCreated, context="evolution", priority=5)
async def track_implementation_velocity(event: TaskCreated) -> None:
    """
    Track task creation for evolution metrics.
    """
    # In a real implementation, would update evolution metrics
    logger.debug(f"Tracking task creation for evolution metrics: {event.task_id}")


# Performance → Implementation Flow
@subscribe(MetricThresholdBreached, context="implementation", priority=15)
async def create_urgent_task_for_threshold_breach(event: MetricThresholdBreached) -> None:
    """
    When a critical metric threshold is breached, create urgent task.
    """
    logger.warning(
        f"Metric threshold breached: {event.metric_name} = {event.current_value} "
        f"(threshold: {event.threshold})"
    )
    
    # Only create task for critical severity
    if event.severity != "critical":
        logger.debug(f"Severity is {event.severity}, not creating urgent task")
        return
    
    # Get repository
    from src.infrastructure.repositories import JsonTaskRepository
    task_repo = JsonTaskRepository()
    
    # Create urgent task
    task = Task(
        decision_id=uuid4(),  # No specific decision, metric-driven
        title=f"URGENT: Fix {event.metric_name} threshold breach",
        description=(
            f"Critical metric {event.metric_name} has reached {event.current_value}, "
            f"exceeding the threshold of {event.threshold}. Immediate action required."
        ),
        priority="critical",
        implementation_type="bugfix",
    )
    
    # Assign to senior implementer
    from src.contexts.implementation import Assignment
    assignment = Assignment(
        assignee="claude",  # Claude handles critical issues
        assignee_type="ai",
        skills=["performance", "critical-issues"],
    )
    task.assign(assignment)
    
    # Save task
    await task_repo.save(task)
    
    logger.info(f"Created urgent task {task.id} for metric threshold breach")


# Saga Orchestrations
class EvolutionSaga:
    """
    Orchestrates the complete evolution workflow from trigger to validation.
    """
    
    def __init__(self):
        self.saga_id = uuid4()
        self.state = "initialized"
        self.completed_steps = []
        
    async def execute(self, trigger: EvolutionTrigger, trigger_details: Dict[str, Any]) -> None:
        """Execute the evolution saga."""
        logger.info(f"Starting evolution saga {self.saga_id}")
        
        try:
            # Step 1: Trigger evolution
            self.state = "triggering"
            evolution_id = await self._trigger_evolution(trigger, trigger_details)
            self.completed_steps.append("trigger")
            
            # Step 2: Analyze system
            self.state = "analyzing"
            await self._analyze_system(evolution_id)
            self.completed_steps.append("analysis")
            
            # Step 3: Create plan
            self.state = "planning"
            await self._create_plan(evolution_id)
            self.completed_steps.append("planning")
            
            # Step 4: Implement improvements
            self.state = "implementing"
            await self._implement_improvements(evolution_id)
            self.completed_steps.append("implementation")
            
            # Step 5: Validate evolution
            self.state = "validating"
            await self._validate_evolution(evolution_id)
            self.completed_steps.append("validation")
            
            self.state = "completed"
            logger.info(f"Evolution saga {self.saga_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Evolution saga {self.saga_id} failed at {self.state}: {str(e)}")
            self.state = "failed"
            await self._compensate()
            raise
    
    async def _trigger_evolution(self, trigger: EvolutionTrigger, trigger_details: Dict[str, Any]) -> UUID:
        """Trigger evolution and return evolution ID."""
        # Implementation would trigger evolution
        return uuid4()
    
    async def _analyze_system(self, evolution_id: UUID) -> None:
        """Analyze system for improvements."""
        # Implementation would perform analysis
        pass
    
    async def _create_plan(self, evolution_id: UUID) -> None:
        """Create evolution plan."""
        # Implementation would create plan
        pass
    
    async def _implement_improvements(self, evolution_id: UUID) -> None:
        """Implement approved improvements."""
        # Implementation would create tasks
        pass
    
    async def _validate_evolution(self, evolution_id: UUID) -> None:
        """Validate evolution results."""
        # Implementation would validate
        pass
    
    async def _compensate(self) -> None:
        """Compensate for failed saga."""
        logger.info(f"Compensating evolution saga {self.saga_id}")
        
        # Reverse completed steps
        for step in reversed(self.completed_steps):
            logger.info(f"Reversing step: {step}")
            # Implementation would reverse each step


def initialize_cross_context_handlers() -> None:
    """
    Initialize all cross-context event handlers.
    
    This should be called during application startup.
    """
    logger.info("Cross-context event handlers initialized")
    
    # The @subscribe decorators automatically register handlers
    # This function serves as a marker that handlers are loaded