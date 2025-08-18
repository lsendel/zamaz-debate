"""
Orchestration Context Aggregates

This module contains the aggregate roots for the orchestration context.
Aggregates enforce business rules around project management, work breakdown,
and orchestration of complex implementations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .events import (
    DebateTriggeredForWorkItem,
    DependencyCreated,
    DependencyResolved,
    EpicCreated,
    OrchestrationPlanCreated,
    PhaseCompleted,
    PhaseStarted,
    ProjectCompleted,
    ProjectCreated,
    ProjectMetricsUpdated,
    ProjectRiskAssessed,
    QualityGateCheckTriggered,
    QualityGateFailed,
    QualityGatePassed,
    ResourcesAllocated,
    StoryCreated,
    TaskGeneratedFromStory,
    WorkItemBlocked,
    WorkItemStatusChanged,
    WorkItemUnblocked,
)
from .value_objects import (
    AcceptanceCriteria,
    DecisionContext,
    Dependency,
    ImplementationPhase,
    OrchestrationPlan,
    Priority,
    ProjectMetrics,
    QualityGate,
    ResourceAllocation,
    WorkEstimate,
    WorkItemStatus,
    WorkItemType,
)


@dataclass
class Project:
    """
    Project Aggregate Root
    
    Manages the lifecycle of a project from conception to completion.
    Enforces business rules around project planning, orchestration, and delivery.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    vision: str = ""
    business_justification: str = ""
    success_criteria: List[AcceptanceCriteria] = field(default_factory=list)
    epics: List["Epic"] = field(default_factory=list)
    orchestration_plan: Optional[OrchestrationPlan] = None
    status: WorkItemStatus = WorkItemStatus.PLANNED
    priority: Priority = Priority.MEDIUM
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    project_manager: str = "llm_orchestrator"
    stakeholders: List[str] = field(default_factory=list)
    budget_estimate: Optional[float] = None
    actual_cost: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Initialize project and publish domain event"""
        if self.status == WorkItemStatus.PLANNED and not self._events:
            self._publish_event(
                ProjectCreated(
                    project_id=self.id,
                    name=self.name,
                    description=self.description,
                    created_by=self.project_manager,
                    occurred_at=datetime.now(),
                )
            )

    def add_epic(self, epic: "Epic") -> None:
        """Add an epic to the project"""
        if self.status == WorkItemStatus.COMPLETED:
            raise ValueError("Cannot add epics to completed projects")
        
        epic.project_id = self.id
        self.epics.append(epic)
        
        self._publish_event(
            EpicCreated(
                epic_id=epic.id,
                project_id=self.id,
                name=epic.name,
                description=epic.description,
                priority=epic.priority,
                occurred_at=datetime.now(),
            )
        )

    def create_orchestration_plan(self, phases: List[ImplementationPhase], 
                                 strategy: str, risk_mitigation: List[str]) -> None:
        """Create an orchestration plan for the project"""
        if self.orchestration_plan is not None:
            raise ValueError("Project already has an orchestration plan")
        
        self.orchestration_plan = OrchestrationPlan(
            project_id=self.id,
            phases=phases,
            overall_strategy=strategy,
            risk_mitigation=risk_mitigation,
            resource_requirements={},
            success_metrics=[]
        )
        
        self._publish_event(
            OrchestrationPlanCreated(
                plan_id=uuid4(),
                project_id=self.id,
                phase_count=len(phases),
                created_by=self.project_manager,
                occurred_at=datetime.now(),
            )
        )

    def start(self) -> None:
        """Start the project"""
        if self.status != WorkItemStatus.PLANNED:
            raise ValueError("Can only start planned projects")
        
        self.status = WorkItemStatus.IN_PROGRESS
        self.start_date = datetime.now()
        
        self._publish_event(
            WorkItemStatusChanged(
                work_item_id=self.id,
                work_item_type=WorkItemType.PROJECT,
                old_status=WorkItemStatus.PLANNED,
                new_status=WorkItemStatus.IN_PROGRESS,
                changed_by=self.project_manager,
                occurred_at=datetime.now(),
            )
        )

    def complete(self) -> None:
        """Complete the project"""
        if self.status != WorkItemStatus.IN_PROGRESS:
            raise ValueError("Can only complete in-progress projects")
        
        # Check if all epics are completed
        incomplete_epics = [epic for epic in self.epics if not epic.is_completed]
        if incomplete_epics:
            raise ValueError(f"Cannot complete project with {len(incomplete_epics)} incomplete epics")
        
        self.status = WorkItemStatus.COMPLETED
        self.actual_completion_date = datetime.now()
        
        metrics = self.get_project_metrics()
        duration_days = None
        if self.start_date and self.actual_completion_date:
            duration = self.actual_completion_date - self.start_date
            duration_days = duration.total_seconds() / 86400  # seconds to days
        
        self._publish_event(
            ProjectCompleted(
                project_id=self.id,
                total_duration_days=duration_days,
                final_metrics=metrics.__dict__,
                completed_by=self.project_manager,
                occurred_at=datetime.now(),
            )
        )

    def assess_risks(self, risk_factors: List[str], mitigation_strategies: List[str]) -> float:
        """Assess project risks and return overall risk score"""
        # Simple risk scoring algorithm
        base_risk_score = len(risk_factors) * 0.5
        complexity_factor = len(self.epics) * 0.2
        timeline_factor = 0.5 if self.target_completion_date else 0.0
        
        overall_risk_score = min(10.0, base_risk_score + complexity_factor + timeline_factor)
        
        self._publish_event(
            ProjectRiskAssessed(
                project_id=self.id,
                risk_factors=risk_factors,
                overall_risk_score=overall_risk_score,
                mitigation_strategies=mitigation_strategies,
                assessed_by=self.project_manager,
                occurred_at=datetime.now(),
            )
        )
        
        return overall_risk_score

    def get_project_metrics(self) -> ProjectMetrics:
        """Calculate current project metrics"""
        total_story_points = sum(epic.get_total_story_points() for epic in self.epics)
        completed_story_points = sum(epic.get_completed_story_points() for epic in self.epics)
        total_work_items = len(self.epics) + sum(len(epic.stories) for epic in self.epics)
        completed_work_items = sum(1 for epic in self.epics if epic.is_completed) + \
                              sum(sum(1 for story in epic.stories if story.is_completed) for epic in self.epics)
        blocked_work_items = sum(1 for epic in self.epics if epic.is_blocked) + \
                            sum(sum(1 for story in epic.stories if story.is_blocked) for epic in self.epics)
        
        metrics = ProjectMetrics(
            total_story_points=total_story_points,
            completed_story_points=completed_story_points,
            total_work_items=total_work_items,
            completed_work_items=completed_work_items,
            blocked_work_items=blocked_work_items
        )
        
        self._publish_event(
            ProjectMetricsUpdated(
                project_id=self.id,
                metrics=metrics.__dict__,
                previous_completion_percentage=0.0,  # Would need to track previous state
                new_completion_percentage=metrics.completion_percentage,
                occurred_at=datetime.now(),
            )
        )
        
        return metrics

    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events

    @property
    def is_completed(self) -> bool:
        """Check if project is completed"""
        return self.status == WorkItemStatus.COMPLETED

    @property
    def is_in_progress(self) -> bool:
        """Check if project is in progress"""
        return self.status == WorkItemStatus.IN_PROGRESS

    @property
    def duration_days(self) -> Optional[float]:
        """Calculate project duration in days"""
        if self.start_date and self.actual_completion_date:
            duration = self.actual_completion_date - self.start_date
            return duration.total_seconds() / 86400
        return None


@dataclass
class Epic:
    """
    Epic Entity
    
    Part of the Project aggregate.
    Represents a large feature or capability that spans multiple stories.
    """

    id: UUID = field(default_factory=uuid4)
    project_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    business_value: str = ""
    acceptance_criteria: List[AcceptanceCriteria] = field(default_factory=list)
    stories: List["Story"] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    status: WorkItemStatus = WorkItemStatus.PLANNED
    priority: Priority = Priority.MEDIUM
    estimate: Optional[WorkEstimate] = None
    resource_allocation: Optional[ResourceAllocation] = None
    quality_gates: List[QualityGate] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None

    def add_story(self, story: "Story") -> None:
        """Add a story to the epic"""
        if self.status == WorkItemStatus.COMPLETED:
            raise ValueError("Cannot add stories to completed epics")
        
        story.epic_id = self.id
        self.stories.append(story)

    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency for this epic"""
        self.dependencies.append(dependency)

    def start(self) -> None:
        """Start the epic"""
        if self.status != WorkItemStatus.PLANNED:
            raise ValueError("Can only start planned epics")
        
        self.status = WorkItemStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def complete(self) -> None:
        """Complete the epic"""
        if self.status != WorkItemStatus.IN_PROGRESS:
            raise ValueError("Can only complete in-progress epics")
        
        # Check if all stories are completed
        incomplete_stories = [story for story in self.stories if not story.is_completed]
        if incomplete_stories:
            raise ValueError(f"Cannot complete epic with {len(incomplete_stories)} incomplete stories")
        
        self.status = WorkItemStatus.COMPLETED
        self.completed_at = datetime.now()

    def block(self, reason: str) -> None:
        """Block the epic"""
        if self.status in [WorkItemStatus.COMPLETED]:
            raise ValueError("Cannot block completed epics")
        
        self.status = WorkItemStatus.BLOCKED
        self.blocked_reason = reason

    def unblock(self) -> None:
        """Unblock the epic"""
        if self.status != WorkItemStatus.BLOCKED:
            raise ValueError("Can only unblock blocked epics")
        
        self.status = WorkItemStatus.IN_PROGRESS if self.started_at else WorkItemStatus.PLANNED
        self.blocked_reason = None

    def get_total_story_points(self) -> int:
        """Calculate total story points for this epic"""
        return sum(story.story_points or 0 for story in self.stories)

    def get_completed_story_points(self) -> int:
        """Calculate completed story points for this epic"""
        return sum(story.story_points or 0 for story in self.stories if story.is_completed)

    @property
    def is_completed(self) -> bool:
        """Check if epic is completed"""
        return self.status == WorkItemStatus.COMPLETED

    @property
    def is_blocked(self) -> bool:
        """Check if epic is blocked"""
        return self.status == WorkItemStatus.BLOCKED

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage by story points"""
        total_points = self.get_total_story_points()
        if total_points == 0:
            return 0.0
        return (self.get_completed_story_points() / total_points) * 100


@dataclass
class Story:
    """
    Story Entity
    
    Part of the Epic entity.
    Represents a specific user-facing functionality within an epic.
    """

    id: UUID = field(default_factory=uuid4)
    epic_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    user_story: str = ""  # "As a ... I want ... so that ..."
    acceptance_criteria: List[AcceptanceCriteria] = field(default_factory=list)
    story_points: Optional[int] = None
    dependencies: List[Dependency] = field(default_factory=list)
    status: WorkItemStatus = WorkItemStatus.PLANNED
    priority: Priority = Priority.MEDIUM
    assignee: Optional[str] = None
    generated_task_ids: List[UUID] = field(default_factory=list)
    quality_gates: List[QualityGate] = field(default_factory=list)
    decision_context: Optional[DecisionContext] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None

    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency for this story"""
        self.dependencies.append(dependency)

    def assign(self, assignee: str, assignee_type: str = "human") -> None:
        """Assign the story to someone"""
        if self.status == WorkItemStatus.COMPLETED:
            raise ValueError("Cannot assign completed stories")
        
        self.assignee = assignee

    def start(self) -> None:
        """Start the story"""
        if self.status != WorkItemStatus.PLANNED:
            raise ValueError("Can only start planned stories")
        
        self.status = WorkItemStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def complete(self) -> None:
        """Complete the story"""
        if self.status != WorkItemStatus.IN_PROGRESS:
            raise ValueError("Can only complete in-progress stories")
        
        self.status = WorkItemStatus.COMPLETED
        self.completed_at = datetime.now()

    def block(self, reason: str) -> None:
        """Block the story"""
        if self.status in [WorkItemStatus.COMPLETED]:
            raise ValueError("Cannot block completed stories")
        
        self.status = WorkItemStatus.BLOCKED
        self.blocked_reason = reason

    def unblock(self) -> None:
        """Unblock the story"""
        if self.status != WorkItemStatus.BLOCKED:
            raise ValueError("Can only unblock blocked stories")
        
        self.status = WorkItemStatus.IN_PROGRESS if self.started_at else WorkItemStatus.PLANNED
        self.blocked_reason = None

    def trigger_debate_if_needed(self) -> bool:
        """Check if story should trigger a debate and trigger it if needed"""
        if self.decision_context and self.decision_context.should_trigger_debate():
            # This would integrate with the debate context
            return True
        return False

    def generate_tasks(self, strategy: str = "llm_breakdown") -> List[UUID]:
        """Generate implementation tasks from this story"""
        # This would integrate with the implementation context
        # For now, return empty list - actual implementation would create tasks
        task_ids = []
        self.generated_task_ids = task_ids
        return task_ids

    @property
    def is_completed(self) -> bool:
        """Check if story is completed"""
        return self.status == WorkItemStatus.COMPLETED

    @property
    def is_blocked(self) -> bool:
        """Check if story is blocked"""
        return self.status == WorkItemStatus.BLOCKED

    @property
    def duration_hours(self) -> Optional[float]:
        """Calculate story duration in hours"""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return duration.total_seconds() / 3600
        return None