"""
Implementation Context Repository Implementations

JSON-based implementations of Implementation context repositories.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.contexts.implementation import (
    Deployment,
    DeploymentRepository,
    DeploymentStatus,
    ImplementationMetricsRepository,
    PullRequest,
    PullRequestRepository,
    PullRequestStatus,
    Task,
    TaskRepository,
    TaskStatus,
)

from .base import JsonRepository


class JsonTaskRepository(JsonRepository, TaskRepository):
    """JSON-based implementation of TaskRepository"""
    
    def __init__(self, storage_path: str = "data/tasks"):
        super().__init__(storage_path, "task")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract task data for indexing"""
        return {
            "status": data.get("status"),
            "priority": data.get("priority"),
            "assignee": data.get("assignment", {}).get("assignee") if data.get("assignment") else None,
            "decision_id": data.get("decision_id"),
            "created_at": data.get("created_at"),
        }
    
    async def save(self, task: Task) -> None:
        """Save a task"""
        await self.save_entity(task, task.id)
    
    async def find_by_id(self, task_id: UUID) -> Optional[Task]:
        """Find a task by ID"""
        return await self.load_entity(task_id, Task)
    
    async def find_by_decision_id(self, decision_id: UUID) -> List[Task]:
        """Find tasks by decision ID"""
        all_tasks = await self.find_all(Task)
        return [t for t in all_tasks if t.decision_id == decision_id]
    
    async def find_by_status(self, status: str) -> List[Task]:
        """Find tasks by status"""
        all_tasks = await self.find_all(Task)
        return [t for t in all_tasks if t.status.value == status]
    
    async def find_assigned_to(self, assignee: str) -> List[Task]:
        """Find tasks assigned to a person"""
        all_tasks = await self.find_all(Task)
        return [
            t for t in all_tasks
            if t.assignment and t.assignment.assignee == assignee
        ]
    
    async def find_blocked(self) -> List[Task]:
        """Find blocked tasks"""
        all_tasks = await self.find_all(Task)
        return [t for t in all_tasks if t.is_blocked]
    
    async def find_by_priority(self, priority: str) -> List[Task]:
        """Find tasks by priority"""
        all_tasks = await self.find_all(Task)
        return [t for t in all_tasks if t.priority == priority]
    
    async def find_overdue(self, expected_hours: float) -> List[Task]:
        """Find overdue tasks"""
        all_tasks = await self.find_all(Task)
        
        overdue = []
        current_time = datetime.now()
        
        for task in all_tasks:
            if (task.status in [TaskStatus.IN_PROGRESS, TaskStatus.ASSIGNED] and
                task.assigned_at):
                hours_elapsed = (current_time - task.assigned_at).total_seconds() / 3600
                if hours_elapsed > expected_hours:
                    overdue.append(task)
        
        return overdue
    
    async def update(self, task: Task) -> bool:
        """Update a task"""
        if await self.exists(task.id):
            await self.save(task)
            return True
        return False
    
    async def delete(self, task_id: UUID) -> bool:
        """Delete a task"""
        return await self.delete_entity(task_id)
    
    async def count_by_status(self) -> Dict[str, int]:
        """Count tasks by status"""
        all_tasks = await self.find_all(Task)
        
        counts = {}
        for task in all_tasks:
            status = task.status.value
            counts[status] = counts.get(status, 0) + 1
        
        return counts


class JsonPullRequestRepository(JsonRepository, PullRequestRepository):
    """JSON-based implementation of PullRequestRepository"""
    
    def __init__(self, storage_path: str = "data/pull_requests"):
        super().__init__(storage_path, "pull_request")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PR data for indexing"""
        return {
            "status": data.get("status"),
            "task_id": data.get("task_id"),
            "pr_number": data.get("pr_number"),
            "branch_name": data.get("branch_name"),
            "created_at": data.get("created_at"),
            "merged_at": data.get("merged_at"),
        }
    
    async def save(self, pull_request: PullRequest) -> None:
        """Save a pull request"""
        await self.save_entity(pull_request, pull_request.id)
    
    async def find_by_id(self, pr_id: UUID) -> Optional[PullRequest]:
        """Find a pull request by ID"""
        return await self.load_entity(pr_id, PullRequest)
    
    async def find_by_task_id(self, task_id: UUID) -> List[PullRequest]:
        """Find pull requests by task ID"""
        all_prs = await self.find_all(PullRequest)
        return [pr for pr in all_prs if pr.task_id == task_id]
    
    async def find_by_status(self, status: str) -> List[PullRequest]:
        """Find pull requests by status"""
        all_prs = await self.find_all(PullRequest)
        return [pr for pr in all_prs if pr.status.value == status]
    
    async def find_by_pr_number(self, pr_number: int) -> Optional[PullRequest]:
        """Find a pull request by PR number"""
        all_prs = await self.find_all(PullRequest)
        
        for pr in all_prs:
            if pr.pr_number == pr_number:
                return pr
        
        return None
    
    async def find_open_prs(self) -> List[PullRequest]:
        """Find all open pull requests"""
        open_statuses = [
            PullRequestStatus.DRAFT.value,
            PullRequestStatus.OPEN.value,
            PullRequestStatus.REVIEWING.value,
        ]
        
        all_prs = await self.find_all(PullRequest)
        return [pr for pr in all_prs if pr.status.value in open_statuses]
    
    async def find_awaiting_review(self) -> List[PullRequest]:
        """Find PRs awaiting review"""
        all_prs = await self.find_all(PullRequest)
        return [
            pr for pr in all_prs
            if pr.status == PullRequestStatus.OPEN and not pr.reviews
        ]
    
    async def find_by_branch(self, branch_name: str) -> Optional[PullRequest]:
        """Find a pull request by branch name"""
        all_prs = await self.find_all(PullRequest)
        
        for pr in all_prs:
            if pr.branch_name == branch_name:
                return pr
        
        return None
    
    async def find_merged_between(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[PullRequest]:
        """Find pull requests merged between dates"""
        all_prs = await self.find_all(PullRequest)
        
        merged = []
        for pr in all_prs:
            if (pr.status == PullRequestStatus.MERGED and
                pr.merged_at and
                start_date <= pr.merged_at <= end_date):
                merged.append(pr)
        
        return merged
    
    async def update(self, pull_request: PullRequest) -> bool:
        """Update a pull request"""
        if await self.exists(pull_request.id):
            await self.save(pull_request)
            return True
        return False
    
    async def delete(self, pr_id: UUID) -> bool:
        """Delete a pull request"""
        return await self.delete_entity(pr_id)
    
    async def get_review_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get pull request review statistics"""
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        recent_prs = await self.find_merged_between(start_date, end_date)
        
        if not recent_prs:
            return {
                "average_review_time_hours": 0,
                "average_reviews_per_pr": 0,
                "approval_rate": 0,
            }
        
        total_review_time = 0
        total_reviews = 0
        approved_count = 0
        
        for pr in recent_prs:
            # Calculate review time
            if pr.created_at and pr.merged_at:
                review_time = (pr.merged_at - pr.created_at).total_seconds() / 3600
                total_review_time += review_time
            
            # Count reviews
            total_reviews += len(pr.reviews)
            
            # Check if approved
            if pr.is_approved:
                approved_count += 1
        
        return {
            "average_review_time_hours": total_review_time / len(recent_prs),
            "average_reviews_per_pr": total_reviews / len(recent_prs),
            "approval_rate": (approved_count / len(recent_prs)) * 100,
        }


class JsonDeploymentRepository(JsonRepository, DeploymentRepository):
    """JSON-based implementation of DeploymentRepository"""
    
    def __init__(self, storage_path: str = "data/deployments"):
        super().__init__(storage_path, "deployment")
    
    def _extract_index_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract deployment data for indexing"""
        return {
            "status": data.get("status"),
            "environment": data.get("environment"),
            "pr_id": data.get("pr_id"),
            "started_at": data.get("started_at"),
            "completed_at": data.get("completed_at"),
        }
    
    async def save(self, deployment: Deployment) -> None:
        """Save a deployment"""
        await self.save_entity(deployment, deployment.id)
    
    async def find_by_id(self, deployment_id: UUID) -> Optional[Deployment]:
        """Find a deployment by ID"""
        return await self.load_entity(deployment_id, Deployment)
    
    async def find_by_pr_id(self, pr_id: UUID) -> List[Deployment]:
        """Find deployments by pull request ID"""
        all_deployments = await self.find_all(Deployment)
        return [d for d in all_deployments if d.pr_id == pr_id]
    
    async def find_by_environment(self, environment: str) -> List[Deployment]:
        """Find deployments by environment"""
        all_deployments = await self.find_all(Deployment)
        return [d for d in all_deployments if d.environment == environment]
    
    async def find_active_deployments(self) -> List[Deployment]:
        """Find all active deployments"""
        all_deployments = await self.find_all(Deployment)
        return [
            d for d in all_deployments
            if d.status == DeploymentStatus.IN_PROGRESS
        ]
    
    async def find_failed_deployments(self, since: datetime) -> List[Deployment]:
        """Find failed deployments since a date"""
        all_deployments = await self.find_all(Deployment)
        
        failed = []
        for deployment in all_deployments:
            if (deployment.status == DeploymentStatus.FAILED and
                deployment.started_at and
                deployment.started_at >= since):
                failed.append(deployment)
        
        return failed
    
    async def find_successful_deployments(
        self,
        environment: str,
        limit: int = 10,
    ) -> List[Deployment]:
        """Find recent successful deployments"""
        all_deployments = await self.find_all(Deployment)
        
        successful = [
            d for d in all_deployments
            if (d.environment == environment and
                d.status == DeploymentStatus.SUCCEEDED)
        ]
        
        # Sort by completion time (most recent first)
        successful.sort(
            key=lambda d: d.completed_at or d.started_at or d.created_at,
            reverse=True
        )
        
        return successful[:limit]
    
    async def get_deployment_metrics(
        self,
        environment: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get deployment metrics for an environment"""
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        all_deployments = await self.find_all(Deployment)
        
        # Filter deployments for environment and date range
        env_deployments = []
        for deployment in all_deployments:
            if (deployment.environment == environment and
                deployment.started_at and
                deployment.started_at >= start_date):
                env_deployments.append(deployment)
        
        if not env_deployments:
            return {
                "total_deployments": 0,
                "success_rate": 0,
                "average_duration_minutes": 0,
                "failure_count": 0,
            }
        
        # Calculate metrics
        total = len(env_deployments)
        successful = sum(1 for d in env_deployments if d.is_successful)
        failed = sum(1 for d in env_deployments if d.status == DeploymentStatus.FAILED)
        
        total_duration = 0
        duration_count = 0
        
        for deployment in env_deployments:
            if deployment.duration_minutes:
                total_duration += deployment.duration_minutes
                duration_count += 1
        
        return {
            "total_deployments": total,
            "success_rate": (successful / total) * 100,
            "average_duration_minutes": (
                total_duration / duration_count
                if duration_count > 0 else 0
            ),
            "failure_count": failed,
        }
    
    async def update(self, deployment: Deployment) -> bool:
        """Update a deployment"""
        if await self.exists(deployment.id):
            await self.save(deployment)
            return True
        return False


class JsonImplementationMetricsRepository(JsonRepository, ImplementationMetricsRepository):
    """JSON-based implementation of ImplementationMetricsRepository"""
    
    def __init__(self, storage_path: str = "data/implementation_metrics"):
        super().__init__(storage_path, "impl_metrics")
        self.task_repo = JsonTaskRepository()
        self.pr_repo = JsonPullRequestRepository()
        self.deployment_repo = JsonDeploymentRepository()
    
    async def get_velocity_metrics(
        self,
        team: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get team velocity metrics"""
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        all_tasks = await self.task_repo.find_all(Task)
        
        # Filter tasks
        completed_tasks = []
        for task in all_tasks:
            if (task.status == TaskStatus.COMPLETED and
                task.completed_at and
                task.completed_at >= start_date):
                
                if team and task.assignment and task.assignment.assignee != team:
                    continue
                
                completed_tasks.append(task)
        
        # Calculate metrics
        total_tasks = len(completed_tasks)
        total_hours = sum(t.actual_hours or t.estimated_hours or 0 for t in completed_tasks)
        
        weeks = days / 7
        
        return {
            "tasks_completed": total_tasks,
            "tasks_per_week": total_tasks / weeks if weeks > 0 else 0,
            "total_hours": total_hours,
            "hours_per_week": total_hours / weeks if weeks > 0 else 0,
            "average_task_hours": total_hours / total_tasks if total_tasks > 0 else 0,
        }
    
    async def get_cycle_time_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get cycle time metrics"""
        end_date = datetime.now()
        start_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_date)
        
        all_tasks = await self.task_repo.find_all(Task)
        
        # Filter completed tasks
        completed_tasks = []
        for task in all_tasks:
            if (task.status == TaskStatus.COMPLETED and
                task.completed_at and
                task.completed_at >= start_date and
                task.created_at):
                completed_tasks.append(task)
        
        if not completed_tasks:
            return {
                "average_cycle_time_hours": 0,
                "min_cycle_time_hours": 0,
                "max_cycle_time_hours": 0,
            }
        
        # Calculate cycle times
        cycle_times = []
        for task in completed_tasks:
            cycle_time = (task.completed_at - task.created_at).total_seconds() / 3600
            cycle_times.append(cycle_time)
        
        return {
            "average_cycle_time_hours": sum(cycle_times) / len(cycle_times),
            "min_cycle_time_hours": min(cycle_times),
            "max_cycle_time_hours": max(cycle_times),
        }
    
    async def get_pr_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get pull request metrics"""
        return await self.pr_repo.get_review_statistics(days)
    
    async def get_deployment_frequency(
        self,
        environment: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get deployment frequency metrics"""
        metrics = await self.deployment_repo.get_deployment_metrics(environment, days)
        
        weeks = days / 7
        deployments_per_week = metrics["total_deployments"] / weeks if weeks > 0 else 0
        
        return {
            "deployments_per_week": deployments_per_week,
            "total_deployments": metrics["total_deployments"],
            "success_rate": metrics["success_rate"],
        }
    
    async def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify bottlenecks in the implementation process"""
        bottlenecks = []
        
        # Check for tasks stuck in review
        all_tasks = await self.task_repo.find_all(Task)
        review_tasks = [t for t in all_tasks if t.status == TaskStatus.REVIEW]
        
        if len(review_tasks) > 5:
            bottlenecks.append({
                "type": "review_queue",
                "severity": "high",
                "count": len(review_tasks),
                "description": f"{len(review_tasks)} tasks waiting for review",
                "recommendation": "Allocate more reviewers or streamline review process",
            })
        
        # Check for blocked tasks
        blocked_tasks = await self.task_repo.find_blocked()
        if len(blocked_tasks) > 3:
            bottlenecks.append({
                "type": "blocked_tasks",
                "severity": "medium",
                "count": len(blocked_tasks),
                "description": f"{len(blocked_tasks)} tasks are blocked",
                "recommendation": "Resolve blockers to improve flow",
            })
        
        # Check for long-running deployments
        active_deployments = await self.deployment_repo.find_active_deployments()
        for deployment in active_deployments:
            if deployment.started_at:
                duration = (datetime.now() - deployment.started_at).total_seconds() / 60
                if duration > 60:  # More than 1 hour
                    bottlenecks.append({
                        "type": "long_deployment",
                        "severity": "high",
                        "deployment_id": str(deployment.id),
                        "duration_minutes": duration,
                        "description": f"Deployment running for {duration:.0f} minutes",
                        "recommendation": "Check deployment status and logs",
                    })
        
        return bottlenecks