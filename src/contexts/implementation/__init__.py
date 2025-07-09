"""
Implementation Context

This bounded context handles the implementation of decisions made through debates.
It manages tasks, pull requests, code reviews, and deployment processes.

Key Aggregates:
- ImplementationTask: Manages the implementation process
- PullRequest: Manages pull request lifecycle
- CodeReview: Manages code review process

Key Domain Services:
- TaskAssignment: Assigns tasks to appropriate agents
- ProgressTracking: Tracks implementation progress
- QualityAssurance: Ensures code quality standards
"""

from .aggregates import CodeReview, ImplementationTask, PullRequest
from .domain_services import ProgressTracking, QualityAssurance, TaskAssignment
from .events import (
    CodeReviewCompleted,
    ImplementationCompleted,
    PullRequestDrafted,
    TaskCreated,
)
from .repositories import ImplementationRepository, PullRequestRepository
from .value_objects import ReviewComment, Task, TestResult

__all__ = [
    # Aggregates
    "ImplementationTask",
    "PullRequest",
    "CodeReview",
    # Domain Services
    "TaskAssignment",
    "ProgressTracking",
    "QualityAssurance",
    # Value Objects
    "Task",
    "ReviewComment",
    "TestResult",
    # Repositories
    "ImplementationRepository",
    "PullRequestRepository",
    # Events
    "TaskCreated",
    "PullRequestDrafted",
    "CodeReviewCompleted",
    "ImplementationCompleted",
]
