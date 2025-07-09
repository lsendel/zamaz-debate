"""
Implementation Context Aggregates

This module contains the aggregate roots for the implementation context.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4, UUID
from enum import Enum


class TaskStatus(Enum):
    """Status of an implementation task"""
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PullRequestStatus(Enum):
    """Status of a pull request"""
    DRAFT = "draft"
    OPEN = "open"
    REVIEW_REQUESTED = "review_requested"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"


@dataclass
class ImplementationTask:
    """Implementation Task Aggregate Root"""
    id: UUID = field(default_factory=uuid4)
    decision_id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.CREATED
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)


@dataclass
class PullRequest:
    """Pull Request Aggregate Root"""
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    status: PullRequestStatus = PullRequestStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)


@dataclass
class CodeReview:
    """Code Review Aggregate Root"""
    id: UUID = field(default_factory=uuid4)
    pull_request_id: UUID = field(default_factory=uuid4)
    reviewer: str = ""
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
