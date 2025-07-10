"""
Implementation Context Value Objects

Value objects representing concepts within the implementation domain.
These are immutable objects that encapsulate implementation-related data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Assignment:
    """
    Represents task assignment details
    
    Value object containing information about who is assigned to a task.
    """
    
    assignee: str
    assignee_type: str = "human"  # "human", "ai", "automated"
    assigned_at: datetime = None
    skills: List[str] = None
    availability_hours: float = 40.0  # Weekly availability
    
    def __post_init__(self):
        """Initialize and validate assignment"""
        if not self.assignee:
            raise ValueError("Assignee cannot be empty")
        
        valid_types = ["human", "ai", "automated"]
        if self.assignee_type not in valid_types:
            raise ValueError(f"Assignee type must be one of {valid_types}")
        
        if self.assigned_at is None:
            object.__setattr__(self, "assigned_at", datetime.now())
        
        if self.skills is None:
            object.__setattr__(self, "skills", [])
        
        if self.availability_hours < 0:
            raise ValueError("Availability hours cannot be negative")
    
    def has_skill(self, skill: str) -> bool:
        """Check if assignee has a specific skill"""
        return skill.lower() in [s.lower() for s in self.skills]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "assignee": self.assignee,
            "assignee_type": self.assignee_type,
            "assigned_at": self.assigned_at.isoformat(),
            "skills": self.skills,
            "availability_hours": self.availability_hours,
        }


@dataclass(frozen=True)
class ImplementationPlan:
    """
    Implementation plan for a task
    
    Value object containing the detailed plan for implementing a feature or fix.
    """
    
    approach: str
    steps: List[str]
    estimated_hours: float
    required_skills: List[str] = None
    dependencies: List[str] = None
    risks: List[str] = None
    
    def __post_init__(self):
        """Initialize and validate plan"""
        if not self.approach:
            raise ValueError("Implementation approach cannot be empty")
        
        if not self.steps:
            raise ValueError("Implementation must have at least one step")
        
        if self.estimated_hours <= 0:
            raise ValueError("Estimated hours must be positive")
        
        if self.required_skills is None:
            object.__setattr__(self, "required_skills", [])
        if self.dependencies is None:
            object.__setattr__(self, "dependencies", [])
        if self.risks is None:
            object.__setattr__(self, "risks", [])
    
    @property
    def step_count(self) -> int:
        """Get the number of implementation steps"""
        return len(self.steps)
    
    @property
    def has_dependencies(self) -> bool:
        """Check if the plan has dependencies"""
        return len(self.dependencies) > 0
    
    @property
    def risk_level(self) -> str:
        """Assess risk level based on number of risks"""
        if not self.risks:
            return "low"
        elif len(self.risks) <= 2:
            return "medium"
        else:
            return "high"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "approach": self.approach,
            "steps": self.steps,
            "estimated_hours": self.estimated_hours,
            "required_skills": self.required_skills,
            "dependencies": self.dependencies,
            "risks": self.risks,
            "step_count": self.step_count,
            "risk_level": self.risk_level,
        }


@dataclass(frozen=True)
class CodeChange:
    """
    Represents a code change in a pull request
    
    Value object containing information about files changed and the nature of changes.
    """
    
    file_path: str
    change_type: str  # "added", "modified", "deleted", "renamed"
    additions: int = 0
    deletions: int = 0
    language: Optional[str] = None
    
    def __post_init__(self):
        """Validate code change data"""
        if not self.file_path:
            raise ValueError("File path cannot be empty")
        
        valid_types = ["added", "modified", "deleted", "renamed"]
        if self.change_type not in valid_types:
            raise ValueError(f"Change type must be one of {valid_types}")
        
        if self.additions < 0 or self.deletions < 0:
            raise ValueError("Additions and deletions cannot be negative")
    
    @property
    def total_changes(self) -> int:
        """Get total number of line changes"""
        return self.additions + self.deletions
    
    @property
    def is_new_file(self) -> bool:
        """Check if this is a new file"""
        return self.change_type == "added"
    
    @property
    def is_deletion(self) -> bool:
        """Check if this is a file deletion"""
        return self.change_type == "deleted"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "file_path": self.file_path,
            "change_type": self.change_type,
            "additions": self.additions,
            "deletions": self.deletions,
            "language": self.language,
            "total_changes": self.total_changes,
        }


@dataclass(frozen=True)
class ReviewComment:
    """
    Code review comment
    
    Value object representing a comment made during code review.
    """
    
    file_path: str
    line_number: int
    comment: str
    severity: str = "info"  # "info", "warning", "error", "suggestion"
    resolved: bool = False
    
    def __post_init__(self):
        """Validate review comment data"""
        if not self.comment:
            raise ValueError("Comment cannot be empty")
        
        valid_severities = ["info", "warning", "error", "suggestion"]
        if self.severity not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}")
        
        if self.line_number < 0:
            raise ValueError("Line number cannot be negative")
    
    @property
    def is_blocking(self) -> bool:
        """Check if this comment blocks PR approval"""
        return self.severity == "error" and not self.resolved
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "comment": self.comment,
            "severity": self.severity,
            "resolved": self.resolved,
            "is_blocking": self.is_blocking,
        }


@dataclass(frozen=True)
class DeploymentConfig:
    """
    Deployment configuration
    
    Value object containing deployment settings and parameters.
    """
    
    strategy: str = "rolling"  # "rolling", "blue_green", "canary"
    replicas: int = 1
    health_check_path: str = "/health"
    timeout_seconds: int = 300
    rollback_on_failure: bool = True
    environment_variables: Dict[str, str] = None
    
    def __post_init__(self):
        """Validate deployment configuration"""
        valid_strategies = ["rolling", "blue_green", "canary"]
        if self.strategy not in valid_strategies:
            raise ValueError(f"Strategy must be one of {valid_strategies}")
        
        if self.replicas < 1:
            raise ValueError("Replicas must be at least 1")
        
        if self.timeout_seconds < 1:
            raise ValueError("Timeout must be at least 1 second")
        
        if self.environment_variables is None:
            object.__setattr__(self, "environment_variables", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "strategy": self.strategy,
            "replicas": self.replicas,
            "health_check_path": self.health_check_path,
            "timeout_seconds": self.timeout_seconds,
            "rollback_on_failure": self.rollback_on_failure,
            "environment_variables": self.environment_variables,
        }


@dataclass(frozen=True)
class CommitInfo:
    """
    Git commit information
    
    Value object containing details about a git commit.
    """
    
    commit_hash: str
    author: str
    author_email: str
    message: str
    timestamp: datetime
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    
    def __post_init__(self):
        """Validate commit info"""
        if not self.commit_hash:
            raise ValueError("Commit hash cannot be empty")
        
        if not self.author:
            raise ValueError("Author cannot be empty")
        
        if not self.message:
            raise ValueError("Commit message cannot be empty")
        
        if len(self.commit_hash) < 7:
            raise ValueError("Commit hash must be at least 7 characters")
    
    @property
    def short_hash(self) -> str:
        """Get short version of commit hash"""
        return self.commit_hash[:7]
    
    @property
    def total_changes(self) -> int:
        """Get total line changes"""
        return self.insertions + self.deletions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "commit_hash": self.commit_hash,
            "short_hash": self.short_hash,
            "author": self.author,
            "author_email": self.author_email,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "total_changes": self.total_changes,
        }


@dataclass(frozen=True)
class BuildInfo:
    """
    Build information
    
    Value object containing build process details.
    """
    
    build_id: str
    build_number: int
    status: str  # "pending", "running", "success", "failed"
    started_at: datetime
    duration_seconds: Optional[int] = None
    artifacts: List[str] = None
    logs_url: Optional[str] = None
    
    def __post_init__(self):
        """Validate build info"""
        if not self.build_id:
            raise ValueError("Build ID cannot be empty")
        
        if self.build_number < 1:
            raise ValueError("Build number must be positive")
        
        valid_statuses = ["pending", "running", "success", "failed"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        
        if self.artifacts is None:
            object.__setattr__(self, "artifacts", [])
    
    @property
    def is_successful(self) -> bool:
        """Check if build was successful"""
        return self.status == "success"
    
    @property
    def is_complete(self) -> bool:
        """Check if build is complete"""
        return self.status in ["success", "failed"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "build_id": self.build_id,
            "build_number": self.build_number,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "artifacts": self.artifacts,
            "logs_url": self.logs_url,
            "is_successful": self.is_successful,
            "is_complete": self.is_complete,
        }