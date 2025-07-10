"""
Implementation Context Aggregates

This module contains the aggregate roots for the implementation context.
Aggregates enforce business rules around task management, pull requests, and code reviews.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .events import (
    BuildCompleted,
    CodeReviewCompleted,
    CodeReviewRequested,
    DeploymentTriggered,
    ImplementationCompleted,
    ImplementationRequested,
    PullRequestCreated,
    PullRequestDrafted,
    PullRequestMerged,
    TaskAssigned,
    TaskCreated,
)
from .value_objects import (
    Assignment,
    CodeChange,
    DeploymentConfig,
    ImplementationPlan,
    ReviewComment,
)


class TaskStatus(Enum):
    """Status of an implementation task"""

    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class PullRequestStatus(Enum):
    """Status of a pull request"""

    DRAFT = "draft"
    OPEN = "open"
    REVIEW_REQUESTED = "review_requested"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"


class ReviewStatus(Enum):
    """Status of a code review"""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    DISMISSED = "dismissed"


class ImplementationType(Enum):
    """Type of implementation required"""
    
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"


@dataclass
class Task:
    """
    Task Aggregate Root
    
    Manages the lifecycle of an implementation task from creation to completion.
    Enforces business rules around task assignment and progress tracking.
    """

    id: UUID = field(default_factory=uuid4)
    decision_id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    implementation_type: ImplementationType = ImplementationType.FEATURE
    plan: Optional[ImplementationPlan] = None
    assignment: Optional[Assignment] = None
    status: TaskStatus = TaskStatus.CREATED
    priority: str = "medium"  # low, medium, high, critical
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None

    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Initialize task and publish domain event"""
        if self.status == TaskStatus.CREATED and not self._events:
            self._publish_event(
                TaskCreated(
                    task_id=self.id,
                    decision_id=self.decision_id,
                    title=self.title,
                    implementation_type=self.implementation_type.value,
                    priority=self.priority,
                    occurred_at=datetime.now(),
                )
            )

    def assign(self, assignment: Assignment) -> None:
        """Assign the task to an implementer"""
        if self.status not in [TaskStatus.CREATED, TaskStatus.BLOCKED]:
            raise ValueError("Can only assign created or blocked tasks")
        
        self.assignment = assignment
        self.status = TaskStatus.ASSIGNED
        
        self._publish_event(
            TaskAssigned(
                task_id=self.id,
                assignee=assignment.assignee,
                assignee_type=assignment.assignee_type,
                occurred_at=datetime.now(),
            )
        )

    def start(self) -> None:
        """Start working on the task"""
        if self.status != TaskStatus.ASSIGNED:
            raise ValueError("Can only start assigned tasks")
        
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def submit_for_review(self) -> None:
        """Submit task for review"""
        if self.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Can only submit in-progress tasks for review")
        
        self.status = TaskStatus.REVIEW

    def complete(self, actual_hours: Optional[float] = None) -> None:
        """Complete the task"""
        if self.status != TaskStatus.REVIEW:
            raise ValueError("Can only complete tasks that have been reviewed")
        
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.actual_hours = actual_hours
        
        self._publish_event(
            ImplementationCompleted(
                task_id=self.id,
                decision_id=self.decision_id,
                actual_hours=actual_hours,
                occurred_at=datetime.now(),
            )
        )

    def fail(self, reason: str) -> None:
        """Mark task as failed"""
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("Cannot fail completed tasks")
        
        self.status = TaskStatus.FAILED
        self.blocked_reason = reason
        self.completed_at = datetime.now()

    def block(self, reason: str) -> None:
        """Block the task"""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            raise ValueError("Cannot block completed or failed tasks")
        
        self.status = TaskStatus.BLOCKED
        self.blocked_reason = reason

    def unblock(self) -> None:
        """Unblock the task"""
        if self.status != TaskStatus.BLOCKED:
            raise ValueError("Can only unblock blocked tasks")
        
        self.status = TaskStatus.ASSIGNED if self.assignment else TaskStatus.CREATED
        self.blocked_reason = None

    def update_plan(self, plan: ImplementationPlan) -> None:
        """Update the implementation plan"""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            raise ValueError("Cannot update plan for completed or failed tasks")
        
        self.plan = plan

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
        """Check if task is completed"""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked"""
        return self.status == TaskStatus.BLOCKED

    @property
    def duration_hours(self) -> Optional[float]:
        """Calculate task duration in hours"""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return duration.total_seconds() / 3600
        return None


@dataclass
class PullRequest:
    """
    Pull Request Aggregate Root
    
    Manages the lifecycle of a pull request from draft to merge.
    Enforces rules around code review and merge requirements.
    """

    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    branch_name: str = ""
    base_branch: str = "main"
    status: PullRequestStatus = PullRequestStatus.DRAFT
    code_changes: List[CodeChange] = field(default_factory=list)
    reviews: List["CodeReview"] = field(default_factory=list)
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Initialize PR and publish domain event"""
        if self.status == PullRequestStatus.DRAFT and not self._events:
            self._publish_event(
                PullRequestDrafted(
                    pr_id=self.id,
                    task_id=self.task_id,
                    title=self.title,
                    occurred_at=datetime.now(),
                )
            )

    def add_code_change(self, change: CodeChange) -> None:
        """Add a code change to the PR"""
        if self.status in [PullRequestStatus.MERGED, PullRequestStatus.CLOSED]:
            raise ValueError("Cannot add changes to merged or closed PRs")
        
        self.code_changes.append(change)

    def open(self, pr_number: int, pr_url: str) -> None:
        """Open the pull request"""
        if self.status != PullRequestStatus.DRAFT:
            raise ValueError("Can only open draft PRs")
        
        self.status = PullRequestStatus.OPEN
        self.pr_number = pr_number
        self.pr_url = pr_url
        
        self._publish_event(
            PullRequestCreated(
                pr_id=self.id,
                task_id=self.task_id,
                pr_number=pr_number,
                pr_url=pr_url,
                occurred_at=datetime.now(),
            )
        )

    def request_review(self, reviewers: List[str]) -> None:
        """Request code review"""
        if self.status != PullRequestStatus.OPEN:
            raise ValueError("Can only request review for open PRs")
        
        self.status = PullRequestStatus.REVIEW_REQUESTED
        
        for reviewer in reviewers:
            review = CodeReview(
                pull_request_id=self.id,
                reviewer=reviewer
            )
            self.reviews.append(review)
        
        self._publish_event(
            CodeReviewRequested(
                pr_id=self.id,
                reviewers=reviewers,
                occurred_at=datetime.now(),
            )
        )

    def add_review(self, review: "CodeReview") -> None:
        """Add a code review"""
        if self.status not in [PullRequestStatus.REVIEW_REQUESTED, PullRequestStatus.CHANGES_REQUESTED]:
            raise ValueError("PR must be in review to add reviews")
        
        # Update existing review or add new one
        existing_review = next((r for r in self.reviews if r.reviewer == review.reviewer), None)
        if existing_review:
            existing_review.status = review.status
            existing_review.comments = review.comments
        else:
            self.reviews.append(review)
        
        # Update PR status based on review
        if review.status == ReviewStatus.APPROVED:
            if all(r.status == ReviewStatus.APPROVED for r in self.reviews):
                self.status = PullRequestStatus.APPROVED
        elif review.status == ReviewStatus.CHANGES_REQUESTED:
            self.status = PullRequestStatus.CHANGES_REQUESTED

    def merge(self) -> None:
        """Merge the pull request"""
        if self.status != PullRequestStatus.APPROVED:
            raise ValueError("Can only merge approved PRs")
        
        self.status = PullRequestStatus.MERGED
        self.merged_at = datetime.now()
        
        self._publish_event(
            PullRequestMerged(
                pr_id=self.id,
                task_id=self.task_id,
                pr_number=self.pr_number,
                occurred_at=datetime.now(),
            )
        )

    def close(self) -> None:
        """Close the pull request without merging"""
        if self.status in [PullRequestStatus.MERGED, PullRequestStatus.CLOSED]:
            raise ValueError("PR is already merged or closed")
        
        self.status = PullRequestStatus.CLOSED
        self.closed_at = datetime.now()

    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events

    @property
    def is_merged(self) -> bool:
        """Check if PR is merged"""
        return self.status == PullRequestStatus.MERGED

    @property
    def is_approved(self) -> bool:
        """Check if PR is approved"""
        return self.status == PullRequestStatus.APPROVED

    @property
    def needs_changes(self) -> bool:
        """Check if PR needs changes"""
        return self.status == PullRequestStatus.CHANGES_REQUESTED


@dataclass
class CodeReview:
    """
    Code Review Entity
    
    Part of the PullRequest aggregate.
    Represents a single review on a pull request.
    """

    id: UUID = field(default_factory=uuid4)
    pull_request_id: UUID = field(default_factory=uuid4)
    reviewer: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    comments: List[ReviewComment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def start_review(self) -> None:
        """Start the review process"""
        if self.status != ReviewStatus.PENDING:
            raise ValueError("Review has already been started")
        
        self.status = ReviewStatus.IN_PROGRESS

    def add_comment(self, comment: ReviewComment) -> None:
        """Add a review comment"""
        if self.status not in [ReviewStatus.IN_PROGRESS, ReviewStatus.PENDING]:
            raise ValueError("Cannot add comments to completed reviews")
        
        self.comments.append(comment)
        if self.status == ReviewStatus.PENDING:
            self.status = ReviewStatus.IN_PROGRESS

    def approve(self) -> None:
        """Approve the PR"""
        if self.status not in [ReviewStatus.IN_PROGRESS, ReviewStatus.CHANGES_REQUESTED]:
            raise ValueError("Can only approve in-progress reviews")
        
        self.status = ReviewStatus.APPROVED
        self.completed_at = datetime.now()

    def request_changes(self) -> None:
        """Request changes to the PR"""
        if self.status != ReviewStatus.IN_PROGRESS:
            raise ValueError("Can only request changes for in-progress reviews")
        
        self.status = ReviewStatus.CHANGES_REQUESTED
        self.completed_at = datetime.now()

    def dismiss(self, reason: str) -> None:
        """Dismiss the review"""
        self.status = ReviewStatus.DISMISSED
        self.completed_at = datetime.now()
        self.comments.append(
            ReviewComment(
                file_path="",
                line_number=0,
                comment=f"Review dismissed: {reason}",
                severity="info"
            )
        )

    @property
    def is_approved(self) -> bool:
        """Check if review is approved"""
        return self.status == ReviewStatus.APPROVED

    @property
    def is_completed(self) -> bool:
        """Check if review is completed"""
        return self.status in [
            ReviewStatus.APPROVED,
            ReviewStatus.CHANGES_REQUESTED,
            ReviewStatus.DISMISSED
        ]


@dataclass
class Deployment:
    """
    Deployment Aggregate Root
    
    Manages deployment of implemented changes to various environments.
    Tracks deployment status and rollback capabilities.
    """

    id: UUID = field(default_factory=uuid4)
    pr_id: UUID = field(default_factory=uuid4)
    environment: str = "staging"  # staging, production, development
    config: DeploymentConfig = field(default_factory=DeploymentConfig)
    status: str = "pending"  # pending, in_progress, success, failed, rolled_back
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def start(self) -> None:
        """Start the deployment"""
        if self.status != "pending":
            raise ValueError("Deployment has already been started")
        
        self.status = "in_progress"
        self.started_at = datetime.now()
        
        self._publish_event(
            DeploymentTriggered(
                deployment_id=self.id,
                pr_id=self.pr_id,
                environment=self.environment,
                occurred_at=datetime.now(),
            )
        )

    def complete_successfully(self) -> None:
        """Mark deployment as successful"""
        if self.status != "in_progress":
            raise ValueError("Can only complete in-progress deployments")
        
        self.status = "success"
        self.completed_at = datetime.now()

    def fail(self, error_message: str) -> None:
        """Mark deployment as failed"""
        if self.status != "in_progress":
            raise ValueError("Can only fail in-progress deployments")
        
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = datetime.now()

    def rollback(self) -> None:
        """Rollback the deployment"""
        if self.status != "success":
            raise ValueError("Can only rollback successful deployments")
        
        self.status = "rolled_back"

    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events

    @property
    def is_successful(self) -> bool:
        """Check if deployment was successful"""
        return self.status == "success"

    @property
    def duration_minutes(self) -> Optional[float]:
        """Calculate deployment duration in minutes"""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return duration.total_seconds() / 60
        return None
