"""
Orchestration Context Domain Events

Events that occur within the orchestration domain, enabling
communication with other bounded contexts.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from .value_objects import WorkItemType, Priority, WorkItemStatus, DependencyType


@dataclass
class ProjectCreated:
    """Event published when a new project is created"""
    project_id: UUID
    name: str
    description: str
    created_by: str
    occurred_at: datetime


@dataclass
class EpicCreated:
    """Event published when a new epic is created"""
    epic_id: UUID
    project_id: UUID
    name: str
    description: str
    priority: Priority
    occurred_at: datetime


@dataclass
class StoryCreated:
    """Event published when a new story is created"""
    story_id: UUID
    epic_id: UUID
    name: str
    description: str
    story_points: Optional[int]
    occurred_at: datetime


@dataclass
class WorkItemStatusChanged:
    """Event published when a work item status changes"""
    work_item_id: UUID
    work_item_type: WorkItemType
    old_status: WorkItemStatus
    new_status: WorkItemStatus
    changed_by: str
    occurred_at: datetime


@dataclass
class DependencyCreated:
    """Event published when a dependency is established"""
    from_item_id: UUID
    to_item_id: UUID
    dependency_type: DependencyType
    description: str
    occurred_at: datetime


@dataclass
class DependencyResolved:
    """Event published when a dependency is resolved"""
    from_item_id: UUID
    to_item_id: UUID
    dependency_type: DependencyType
    occurred_at: datetime


@dataclass
class OrchestrationPlanCreated:
    """Event published when an orchestration plan is created"""
    plan_id: UUID
    project_id: UUID
    phase_count: int
    created_by: str
    occurred_at: datetime


@dataclass
class PhaseStarted:
    """Event published when an implementation phase starts"""
    project_id: UUID
    phase_name: str
    phase_index: int
    started_by: str
    occurred_at: datetime


@dataclass
class PhaseCompleted:
    """Event published when an implementation phase is completed"""
    project_id: UUID
    phase_name: str
    phase_index: int
    duration_hours: Optional[float]
    completed_by: str
    occurred_at: datetime


@dataclass
class ProjectCompleted:
    """Event published when a project is completed"""
    project_id: UUID
    total_duration_days: Optional[float]
    final_metrics: Dict[str, Any]
    completed_by: str
    occurred_at: datetime


@dataclass
class WorkItemBlocked:
    """Event published when a work item becomes blocked"""
    work_item_id: UUID
    work_item_type: WorkItemType
    blocking_reason: str
    blocking_dependencies: List[UUID]
    occurred_at: datetime


@dataclass
class WorkItemUnblocked:
    """Event published when a work item is unblocked"""
    work_item_id: UUID
    work_item_type: WorkItemType
    unblocking_reason: str
    occurred_at: datetime


@dataclass
class DebateTriggeredForWorkItem:
    """Event published when a work item triggers a debate"""
    work_item_id: UUID
    work_item_type: WorkItemType
    debate_topic: str
    complexity_score: float
    participants: List[str]
    occurred_at: datetime


@dataclass
class TaskGeneratedFromStory:
    """Event published when tasks are generated from a story"""
    story_id: UUID
    generated_task_ids: List[UUID]
    generation_strategy: str
    occurred_at: datetime


@dataclass
class ProjectRiskAssessed:
    """Event published when project risks are assessed"""
    project_id: UUID
    risk_factors: List[str]
    overall_risk_score: float
    mitigation_strategies: List[str]
    assessed_by: str
    occurred_at: datetime


@dataclass
class ResourcesAllocated:
    """Event published when resources are allocated to work items"""
    work_item_id: UUID
    work_item_type: WorkItemType
    assignee: str
    assignee_type: str  # human, ai_agent, hybrid
    estimated_capacity: float
    occurred_at: datetime


@dataclass
class ProjectMetricsUpdated:
    """Event published when project metrics are updated"""
    project_id: UUID
    metrics: Dict[str, Any]
    previous_completion_percentage: float
    new_completion_percentage: float
    occurred_at: datetime


@dataclass
class QualityGateCheckTriggered:
    """Event published when a quality gate check is triggered"""
    work_item_id: UUID
    work_item_type: WorkItemType
    gate_name: str
    automated_checks: List[str]
    manual_review_required: bool
    occurred_at: datetime


@dataclass
class QualityGatePassed:
    """Event published when a work item passes a quality gate"""
    work_item_id: UUID
    work_item_type: WorkItemType
    gate_name: str
    passed_checks: List[str]
    approved_by: List[str]
    occurred_at: datetime


@dataclass
class QualityGateFailed:
    """Event published when a work item fails a quality gate"""
    work_item_id: UUID
    work_item_type: WorkItemType
    gate_name: str
    failed_checks: List[str]
    failure_reasons: List[str]
    occurred_at: datetime