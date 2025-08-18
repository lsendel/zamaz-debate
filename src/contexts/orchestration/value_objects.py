"""
Orchestration Context Value Objects

Value objects for the orchestration domain representing concepts like
project phases, work estimates, dependencies, and orchestration plans.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID


class WorkItemType(Enum):
    """Type of work item in the hierarchy"""
    PROJECT = "project"
    EPIC = "epic"
    STORY = "story"
    TASK = "task"


class Priority(Enum):
    """Priority levels for work items"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkItemStatus(Enum):
    """Status of work items"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DependencyType(Enum):
    """Type of dependency between work items"""
    BLOCKS = "blocks"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"


@dataclass(frozen=True)
class WorkEstimate:
    """Estimate for work completion"""
    story_points: Optional[int] = None
    hours: Optional[float] = None
    confidence_level: str = "medium"  # low, medium, high
    basis: str = ""  # explanation of estimate basis
    created_by: str = ""
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now())


@dataclass(frozen=True)
class Dependency:
    """Dependency between work items"""
    from_item_id: UUID
    to_item_id: UUID
    dependency_type: DependencyType
    description: str = ""
    is_hard_dependency: bool = True


@dataclass(frozen=True)
class AcceptanceCriteria:
    """Acceptance criteria for a work item"""
    id: str
    description: str
    is_testable: bool = True
    test_approach: str = ""


@dataclass(frozen=True)
class ImplementationPhase:
    """A phase in the implementation process"""
    phase_name: str
    description: str
    prerequisites: List[str]
    deliverables: List[str]
    estimated_duration: Optional[float] = None  # in hours
    parallel_capable: bool = False
    risk_level: str = "medium"  # low, medium, high


@dataclass(frozen=True)
class OrchestrationPlan:
    """Plan for orchestrating implementation across multiple phases"""
    project_id: UUID
    phases: List[ImplementationPhase]
    overall_strategy: str
    risk_mitigation: List[str]
    resource_requirements: Dict[str, Any]
    success_metrics: List[str]
    created_by: str = "llm_orchestrator"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now())


@dataclass(frozen=True)
class ProjectMetrics:
    """Metrics for tracking project progress"""
    total_story_points: int
    completed_story_points: int
    total_work_items: int
    completed_work_items: int
    blocked_work_items: int
    average_cycle_time: Optional[float] = None  # in days
    velocity: Optional[float] = None  # story points per iteration
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage by story points"""
        if self.total_story_points == 0:
            return 0.0
        return (self.completed_story_points / self.total_story_points) * 100

    @property
    def work_items_completion_percentage(self) -> float:
        """Calculate completion percentage by work item count"""
        if self.total_work_items == 0:
            return 0.0
        return (self.completed_work_items / self.total_work_items) * 100


@dataclass(frozen=True)
class DecisionContext:
    """Context for LLM decision making"""
    complexity_score: float  # 0-10 scale
    domain_knowledge_required: List[str]
    stakeholders: List[str]
    business_impact: str  # low, medium, high, critical
    technical_risk: str  # low, medium, high, critical
    time_sensitivity: str  # low, medium, high, urgent
    
    def should_trigger_debate(self) -> bool:
        """Determine if this decision should trigger a debate"""
        return (
            self.complexity_score >= 7.0 or
            self.business_impact in ["high", "critical"] or
            self.technical_risk in ["high", "critical"]
        )


@dataclass(frozen=True)
class ResourceAllocation:
    """Resource allocation for work items"""
    assignee_type: str  # human, ai_agent, hybrid
    estimated_capacity: float  # percentage of time allocation
    required_skills: List[str]
    availability_window: Optional[tuple] = None  # (start_date, end_date)
    
    
@dataclass(frozen=True)
class QualityGate:
    """Quality gate that must be passed before proceeding"""
    gate_name: str
    criteria: List[AcceptanceCriteria]
    automated_checks: List[str]
    manual_review_required: bool = False
    approvers: List[str] = None

    def __post_init__(self):
        if self.approvers is None:
            object.__setattr__(self, 'approvers', [])