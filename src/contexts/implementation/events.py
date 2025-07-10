"""
Implementation Context Domain Events

Domain events that occur within the implementation context, including task management,
pull requests, code reviews, and deployments.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.events.domain_event import DomainEvent


@dataclass(frozen=True)
class ImplementationRequested(DomainEvent):
    """Event published when implementation is requested for a decision"""
    
    decision_id: UUID
    decision_type: str
    question: str
    recommendation: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "ImplementationRequested")
        object.__setattr__(self, "aggregate_id", self.decision_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "decision_id": str(self.decision_id),
            "decision_type": self.decision_type,
            "question": self.question,
            "recommendation": self.recommendation,
        })
        return data


@dataclass(frozen=True)
class TaskCreated(DomainEvent):
    """Event published when an implementation task is created"""
    
    task_id: UUID
    decision_id: UUID
    title: str
    implementation_type: str
    priority: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TaskCreated")
        object.__setattr__(self, "aggregate_id", self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "task_id": str(self.task_id),
            "decision_id": str(self.decision_id),
            "title": self.title,
            "implementation_type": self.implementation_type,
            "priority": self.priority,
        })
        return data


@dataclass(frozen=True)
class TaskAssigned(DomainEvent):
    """Event published when a task is assigned to an implementer"""
    
    task_id: UUID
    assignee: str
    assignee_type: str  # "human", "ai", "automated"
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TaskAssigned")
        object.__setattr__(self, "aggregate_id", self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "task_id": str(self.task_id),
            "assignee": self.assignee,
            "assignee_type": self.assignee_type,
        })
        return data


@dataclass(frozen=True)
class PullRequestDrafted(DomainEvent):
    """Event published when a pull request is drafted"""
    
    pr_id: UUID
    task_id: UUID
    title: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "PullRequestDrafted")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "task_id": str(self.task_id),
            "title": self.title,
        })
        return data


@dataclass(frozen=True)
class PullRequestCreated(DomainEvent):
    """Event published when a pull request is created in the repository"""
    
    pr_id: UUID
    task_id: UUID
    pr_number: int
    pr_url: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "PullRequestCreated")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "task_id": str(self.task_id),
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
        })
        return data


@dataclass(frozen=True)
class CodeReviewRequested(DomainEvent):
    """Event published when code review is requested"""
    
    pr_id: UUID
    reviewers: List[str]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "CodeReviewRequested")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "reviewers": self.reviewers,
        })
        return data


@dataclass(frozen=True)
class CodeReviewCompleted(DomainEvent):
    """Event published when a code review is completed"""
    
    pr_id: UUID
    reviewer: str
    review_status: str  # "approved", "changes_requested", "dismissed"
    comments_count: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "CodeReviewCompleted")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "reviewer": self.reviewer,
            "review_status": self.review_status,
            "comments_count": self.comments_count,
        })
        return data


@dataclass(frozen=True)
class PullRequestMerged(DomainEvent):
    """Event published when a pull request is merged"""
    
    pr_id: UUID
    task_id: UUID
    pr_number: Optional[int]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "PullRequestMerged")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "task_id": str(self.task_id),
            "pr_number": self.pr_number,
        })
        return data


@dataclass(frozen=True)
class ImplementationCompleted(DomainEvent):
    """Event published when an implementation task is completed"""
    
    task_id: UUID
    decision_id: UUID
    actual_hours: Optional[float]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "ImplementationCompleted")
        object.__setattr__(self, "aggregate_id", self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "task_id": str(self.task_id),
            "decision_id": str(self.decision_id),
            "actual_hours": self.actual_hours,
        })
        return data


@dataclass(frozen=True)
class DeploymentTriggered(DomainEvent):
    """Event published when a deployment is triggered"""
    
    deployment_id: UUID
    pr_id: UUID
    environment: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "DeploymentTriggered")
        object.__setattr__(self, "aggregate_id", self.deployment_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "deployment_id": str(self.deployment_id),
            "pr_id": str(self.pr_id),
            "environment": self.environment,
        })
        return data


@dataclass(frozen=True)
class DeploymentCompleted(DomainEvent):
    """Event published when a deployment completes"""
    
    deployment_id: UUID
    environment: str
    status: str  # "success", "failed"
    duration_minutes: float
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "DeploymentCompleted")
        object.__setattr__(self, "aggregate_id", self.deployment_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "deployment_id": str(self.deployment_id),
            "environment": self.environment,
            "status": self.status,
            "duration_minutes": self.duration_minutes,
        })
        return data


@dataclass(frozen=True)
class BranchCreated(DomainEvent):
    """Event published when a new branch is created"""
    
    task_id: UUID
    branch_name: str
    base_branch: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "BranchCreated")
        object.__setattr__(self, "aggregate_id", self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "task_id": str(self.task_id),
            "branch_name": self.branch_name,
            "base_branch": self.base_branch,
        })
        return data


@dataclass(frozen=True)
class CommitMade(DomainEvent):
    """Event published when code is committed"""
    
    task_id: UUID
    commit_hash: str
    commit_message: str
    files_changed: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "CommitMade")
        object.__setattr__(self, "aggregate_id", self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "task_id": str(self.task_id),
            "commit_hash": self.commit_hash,
            "commit_message": self.commit_message,
            "files_changed": self.files_changed,
        })
        return data


@dataclass(frozen=True)
class TestsRun(DomainEvent):
    """Event published when tests are executed for a PR"""
    
    pr_id: UUID
    test_suite: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "TestsRun")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "test_suite": self.test_suite,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
        })
        return data


@dataclass(frozen=True)
class BuildCompleted(DomainEvent):
    """Event published when a build process completes"""
    
    pr_id: UUID
    build_id: str
    status: str  # "success", "failed"
    duration_seconds: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "BuildCompleted")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "build_id": self.build_id,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
        })
        return data


@dataclass(frozen=True)
class QualityGatesPassed(DomainEvent):
    """Event published when quality checks pass"""
    
    pr_id: UUID
    checks_passed: List[str]
    coverage_percent: float
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "QualityGatesPassed")
        object.__setattr__(self, "aggregate_id", self.pr_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "pr_id": str(self.pr_id),
            "checks_passed": self.checks_passed,
            "coverage_percent": self.coverage_percent,
        })
        return data