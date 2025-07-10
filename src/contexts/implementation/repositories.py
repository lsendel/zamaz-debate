"""
Implementation Context Repository Interfaces

Repository interfaces for the implementation context following DDD patterns.
These abstractions hide persistence details from the domain layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from .aggregates import Deployment, PullRequest, Task


class TaskRepository(ABC):
    """
    Repository interface for Task aggregate
    
    Provides persistence operations for implementation tasks.
    """
    
    @abstractmethod
    async def save(self, task: Task) -> None:
        """
        Save a task
        
        Args:
            task: The task to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, task_id: UUID) -> Optional[Task]:
        """
        Find a task by ID
        
        Args:
            task_id: The ID of the task
            
        Returns:
            The task if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_decision_id(self, decision_id: UUID) -> List[Task]:
        """
        Find tasks by decision ID
        
        Args:
            decision_id: The ID of the decision
            
        Returns:
            List of tasks for the decision
        """
        pass
    
    @abstractmethod
    async def find_by_status(self, status: str) -> List[Task]:
        """
        Find tasks by status
        
        Args:
            status: The task status
            
        Returns:
            List of tasks with the given status
        """
        pass
    
    @abstractmethod
    async def find_assigned_to(self, assignee: str) -> List[Task]:
        """
        Find tasks assigned to a specific person/entity
        
        Args:
            assignee: The assignee name
            
        Returns:
            List of tasks assigned to the assignee
        """
        pass
    
    @abstractmethod
    async def find_blocked(self) -> List[Task]:
        """
        Find all blocked tasks
        
        Returns:
            List of blocked tasks
        """
        pass
    
    @abstractmethod
    async def find_by_priority(self, priority: str) -> List[Task]:
        """
        Find tasks by priority
        
        Args:
            priority: The priority level (low, medium, high, critical)
            
        Returns:
            List of tasks with the given priority
        """
        pass
    
    @abstractmethod
    async def find_overdue(self, expected_hours: float) -> List[Task]:
        """
        Find tasks that are overdue based on estimated hours
        
        Args:
            expected_hours: Expected hours for completion
            
        Returns:
            List of overdue tasks
        """
        pass
    
    @abstractmethod
    async def update(self, task: Task) -> bool:
        """
        Update a task
        
        Args:
            task: The task to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, task_id: UUID) -> bool:
        """
        Delete a task
        
        Args:
            task_id: The ID of the task to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def count_by_status(self) -> Dict[str, int]:
        """
        Count tasks by status
        
        Returns:
            Dictionary with status as key and count as value
        """
        pass
    
    @abstractmethod
    async def exists(self, task_id: UUID) -> bool:
        """
        Check if a task exists
        
        Args:
            task_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class PullRequestRepository(ABC):
    """
    Repository interface for PullRequest aggregate
    
    Provides persistence operations for pull requests.
    """
    
    @abstractmethod
    async def save(self, pull_request: PullRequest) -> None:
        """
        Save a pull request
        
        Args:
            pull_request: The pull request to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, pr_id: UUID) -> Optional[PullRequest]:
        """
        Find a pull request by ID
        
        Args:
            pr_id: The ID of the pull request
            
        Returns:
            The pull request if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_task_id(self, task_id: UUID) -> List[PullRequest]:
        """
        Find pull requests by task ID
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List of pull requests for the task
        """
        pass
    
    @abstractmethod
    async def find_by_status(self, status: str) -> List[PullRequest]:
        """
        Find pull requests by status
        
        Args:
            status: The PR status
            
        Returns:
            List of pull requests with the given status
        """
        pass
    
    @abstractmethod
    async def find_by_pr_number(self, pr_number: int) -> Optional[PullRequest]:
        """
        Find a pull request by its GitHub PR number
        
        Args:
            pr_number: The GitHub PR number
            
        Returns:
            The pull request if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_open_prs(self) -> List[PullRequest]:
        """
        Find all open pull requests
        
        Returns:
            List of open pull requests
        """
        pass
    
    @abstractmethod
    async def find_awaiting_review(self) -> List[PullRequest]:
        """
        Find pull requests awaiting review
        
        Returns:
            List of PRs needing review
        """
        pass
    
    @abstractmethod
    async def find_by_branch(self, branch_name: str) -> Optional[PullRequest]:
        """
        Find a pull request by branch name
        
        Args:
            branch_name: The branch name
            
        Returns:
            The pull request if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_merged_between(self, start_date: datetime, end_date: datetime) -> List[PullRequest]:
        """
        Find pull requests merged between dates
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of merged pull requests
        """
        pass
    
    @abstractmethod
    async def update(self, pull_request: PullRequest) -> bool:
        """
        Update a pull request
        
        Args:
            pull_request: The pull request to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, pr_id: UUID) -> bool:
        """
        Delete a pull request
        
        Args:
            pr_id: The ID of the pull request to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def get_review_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get pull request review statistics
        
        Args:
            days: Number of days to look back
            
        Returns:
            Statistics about PR reviews
        """
        pass


class DeploymentRepository(ABC):
    """
    Repository interface for Deployment aggregate
    
    Provides persistence operations for deployments.
    """
    
    @abstractmethod
    async def save(self, deployment: Deployment) -> None:
        """
        Save a deployment
        
        Args:
            deployment: The deployment to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, deployment_id: UUID) -> Optional[Deployment]:
        """
        Find a deployment by ID
        
        Args:
            deployment_id: The ID of the deployment
            
        Returns:
            The deployment if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_pr_id(self, pr_id: UUID) -> List[Deployment]:
        """
        Find deployments by pull request ID
        
        Args:
            pr_id: The ID of the pull request
            
        Returns:
            List of deployments for the PR
        """
        pass
    
    @abstractmethod
    async def find_by_environment(self, environment: str) -> List[Deployment]:
        """
        Find deployments by environment
        
        Args:
            environment: The deployment environment
            
        Returns:
            List of deployments to the environment
        """
        pass
    
    @abstractmethod
    async def find_active_deployments(self) -> List[Deployment]:
        """
        Find all active (in-progress) deployments
        
        Returns:
            List of active deployments
        """
        pass
    
    @abstractmethod
    async def find_failed_deployments(self, since: datetime) -> List[Deployment]:
        """
        Find failed deployments since a date
        
        Args:
            since: Date to search from
            
        Returns:
            List of failed deployments
        """
        pass
    
    @abstractmethod
    async def find_successful_deployments(self, environment: str, limit: int = 10) -> List[Deployment]:
        """
        Find recent successful deployments to an environment
        
        Args:
            environment: The deployment environment
            limit: Maximum number of results
            
        Returns:
            List of successful deployments
        """
        pass
    
    @abstractmethod
    async def get_deployment_metrics(self, environment: str, days: int = 30) -> Dict[str, Any]:
        """
        Get deployment metrics for an environment
        
        Args:
            environment: The deployment environment
            days: Number of days to analyze
            
        Returns:
            Deployment metrics including success rate, average duration, etc.
        """
        pass
    
    @abstractmethod
    async def update(self, deployment: Deployment) -> bool:
        """
        Update a deployment
        
        Args:
            deployment: The deployment to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, deployment_id: UUID) -> bool:
        """
        Check if a deployment exists
        
        Args:
            deployment_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class ImplementationMetricsRepository(ABC):
    """
    Repository interface for implementation metrics and analytics
    
    Provides aggregated metrics across the implementation context.
    """
    
    @abstractmethod
    async def get_velocity_metrics(self, team: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get team velocity metrics
        
        Args:
            team: Optional team name to filter by
            days: Number of days to analyze
            
        Returns:
            Velocity metrics including tasks completed, story points, etc.
        """
        pass
    
    @abstractmethod
    async def get_cycle_time_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cycle time metrics from task creation to completion
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Cycle time statistics
        """
        pass
    
    @abstractmethod
    async def get_pr_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get pull request metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            PR metrics including time to merge, review time, etc.
        """
        pass
    
    @abstractmethod
    async def get_deployment_frequency(self, environment: str, days: int = 30) -> Dict[str, Any]:
        """
        Get deployment frequency metrics
        
        Args:
            environment: The deployment environment
            days: Number of days to analyze
            
        Returns:
            Deployment frequency statistics
        """
        pass
    
    @abstractmethod
    async def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Identify bottlenecks in the implementation process
        
        Returns:
            List of identified bottlenecks with details
        """
        pass