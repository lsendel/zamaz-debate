"""
Implementation Context

This bounded context handles the implementation of decisions made through debates.
It manages tasks, pull requests, code reviews, and deployment processes.
"""

from .aggregates import CodeReview, Deployment, PullRequest, Task
from .domain_services import (
    DeploymentService,
    ImplementationPlanningService,
    PullRequestService,
    TaskAssignmentService,
)
from .events import (
    BranchCreated,
    BuildCompleted,
    CodeReviewCompleted,
    CodeReviewRequested,
    CommitMade,
    DeploymentCompleted,
    DeploymentTriggered,
    ImplementationCompleted,
    ImplementationRequested,
    PullRequestCreated,
    PullRequestDrafted,
    PullRequestMerged,
    QualityGatesPassed,
    TaskAssigned,
    TaskCreated,
    TestsRun,
)
from .repositories import (
    DeploymentRepository,
    ImplementationMetricsRepository,
    PullRequestRepository,
    TaskRepository,
)
from .value_objects import (
    Assignment,
    BuildInfo,
    CodeChange,
    CommitInfo,
    DeploymentConfig,
    ImplementationPlan,
    ReviewComment,
)


class ImplementationContext:
    """Main context class for Implementation"""
    pass


__all__ = [
    "ImplementationContext",
    # Aggregates
    "Task",
    "PullRequest",
    "CodeReview",
    "Deployment",
    # Value Objects
    "Assignment",
    "ImplementationPlan",
    "CodeChange",
    "ReviewComment",
    "DeploymentConfig",
    "CommitInfo",
    "BuildInfo",
    # Events
    "ImplementationRequested",
    "TaskCreated",
    "TaskAssigned",
    "PullRequestDrafted",
    "PullRequestCreated",
    "CodeReviewRequested",
    "CodeReviewCompleted",
    "PullRequestMerged",
    "ImplementationCompleted",
    "DeploymentTriggered",
    "DeploymentCompleted",
    "BranchCreated",
    "CommitMade",
    "TestsRun",
    "BuildCompleted",
    "QualityGatesPassed",
    # Repositories
    "TaskRepository",
    "PullRequestRepository",
    "DeploymentRepository",
    "ImplementationMetricsRepository",
    # Domain Services
    "TaskAssignmentService",
    "PullRequestService",
    "DeploymentService",
    "ImplementationPlanningService",
]
