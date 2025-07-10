"""
Implementation Context Domain Services

Domain services that orchestrate complex implementation workflows
and enforce business rules across multiple aggregates.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from .aggregates import (
    CodeReview,
    Deployment,
    ImplementationType,
    PullRequest,
    ReviewStatus,
    Task,
    TaskStatus,
)
from .repositories import (
    DeploymentRepository,
    PullRequestRepository,
    TaskRepository,
)
from .value_objects import (
    Assignment,
    CodeChange,
    DeploymentConfig,
    ImplementationPlan,
    ReviewComment,
)


class TaskAssignmentService:
    """
    Domain service for task assignment and workload management
    
    Handles complex task assignment logic including skill matching,
    workload balancing, and priority-based allocation.
    """
    
    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo
    
    async def assign_task(
        self,
        task: Task,
        available_assignees: List[Assignment],
    ) -> Assignment:
        """
        Assign a task to the most suitable assignee
        
        Args:
            task: The task to assign
            available_assignees: List of available assignees
            
        Returns:
            The selected assignment
        """
        if not available_assignees:
            raise ValueError("No available assignees")
        
        # Score each assignee based on various factors
        scores = []
        for assignee in available_assignees:
            score = await self._calculate_assignee_score(task, assignee)
            scores.append((assignee, score))
        
        # Sort by score (highest first)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select the best assignee
        best_assignee = scores[0][0]
        
        # Assign the task
        task.assign(best_assignee)
        await self.task_repo.save(task)
        
        return best_assignee
    
    async def _calculate_assignee_score(
        self,
        task: Task,
        assignee: Assignment,
    ) -> float:
        """Calculate assignment score based on multiple factors"""
        score = 0.0
        
        # Skill match (40% weight)
        if task.plan and task.plan.required_skills:
            matching_skills = sum(
                1 for skill in task.plan.required_skills
                if assignee.has_skill(skill)
            )
            skill_score = (matching_skills / len(task.plan.required_skills)) * 40
            score += skill_score
        
        # Workload (30% weight)
        current_tasks = await self.task_repo.find_assigned_to(assignee.assignee)
        active_tasks = [t for t in current_tasks if not t.is_completed]
        workload_score = max(0, 30 - (len(active_tasks) * 10))
        score += workload_score
        
        # Assignee type preference (20% weight)
        type_scores = {
            "ai": 20 if task.implementation_type == ImplementationType.FEATURE else 10,
            "human": 20 if task.implementation_type == ImplementationType.BUGFIX else 15,
            "automated": 20 if task.implementation_type == ImplementationType.INFRASTRUCTURE else 5,
        }
        score += type_scores.get(assignee.assignee_type, 10)
        
        # Availability (10% weight)
        if assignee.availability_hours >= (task.estimated_hours or 8):
            score += 10
        
        return score
    
    async def balance_workload(
        self,
        assignees: List[str],
    ) -> Dict[str, List[Task]]:
        """
        Balance workload across assignees
        
        Args:
            assignees: List of assignee names
            
        Returns:
            Recommended task redistributions
        """
        redistributions = {}
        
        # Get current workload for each assignee
        workloads = {}
        for assignee in assignees:
            tasks = await self.task_repo.find_assigned_to(assignee)
            active_tasks = [t for t in tasks if not t.is_completed]
            total_hours = sum(t.estimated_hours or 8 for t in active_tasks)
            workloads[assignee] = {
                "tasks": active_tasks,
                "total_hours": total_hours,
            }
        
        # Calculate average workload
        avg_hours = sum(w["total_hours"] for w in workloads.values()) / len(assignees)
        
        # Identify overloaded and underloaded assignees
        overloaded = [
            (a, w) for a, w in workloads.items()
            if w["total_hours"] > avg_hours * 1.2
        ]
        underloaded = [
            (a, w) for a, w in workloads.items()
            if w["total_hours"] < avg_hours * 0.8
        ]
        
        # Recommend redistributions
        for over_assignee, over_workload in overloaded:
            tasks_to_move = []
            
            # Find low-priority tasks that can be moved
            movable_tasks = [
                t for t in over_workload["tasks"]
                if t.priority in ["low", "medium"] and t.status == TaskStatus.ASSIGNED
            ]
            
            for task in movable_tasks:
                if underloaded:
                    # Move to underloaded assignee
                    target_assignee = underloaded[0][0]
                    tasks_to_move.append(task)
                    
                    # Update underloaded list
                    for i, (a, w) in enumerate(underloaded):
                        if a == target_assignee:
                            w["total_hours"] += task.estimated_hours or 8
                            if w["total_hours"] >= avg_hours * 0.8:
                                underloaded.pop(i)
                            break
            
            if tasks_to_move:
                redistributions[over_assignee] = tasks_to_move
        
        return redistributions


class PullRequestService:
    """
    Domain service for pull request management
    
    Handles PR creation, review orchestration, and merge coordination.
    """
    
    def __init__(
        self,
        pr_repo: PullRequestRepository,
        task_repo: TaskRepository,
    ):
        self.pr_repo = pr_repo
        self.task_repo = task_repo
    
    async def create_pull_request(
        self,
        task: Task,
        code_changes: List[CodeChange],
        branch_name: str,
    ) -> PullRequest:
        """
        Create a pull request for a task
        
        Args:
            task: The task being implemented
            code_changes: List of code changes
            branch_name: The feature branch name
            
        Returns:
            The created pull request
        """
        # Validate task is ready for PR
        if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.REVIEW]:
            raise ValueError("Task must be in progress or review to create PR")
        
        # Create PR
        pr = PullRequest(
            task_id=task.id,
            title=f"[{task.implementation_type.value}] {task.title}",
            description=self._generate_pr_description(task),
            branch_name=branch_name,
        )
        
        # Add code changes
        for change in code_changes:
            pr.add_code_change(change)
        
        # Save PR
        await self.pr_repo.save(pr)
        
        # Update task status
        task.submit_for_review()
        await self.task_repo.save(task)
        
        return pr
    
    def _generate_pr_description(self, task: Task) -> str:
        """Generate PR description from task details"""
        description = f"## Summary\n\n{task.description}\n\n"
        
        if task.plan:
            description += "## Implementation Approach\n\n"
            description += f"{task.plan.approach}\n\n"
            
            description += "### Steps\n"
            for i, step in enumerate(task.plan.steps, 1):
                description += f"{i}. {step}\n"
            description += "\n"
            
            if task.plan.risks:
                description += "### Risks\n"
                for risk in task.plan.risks:
                    description += f"- {risk}\n"
                description += "\n"
        
        description += f"## Related\n\n- Decision ID: {task.decision_id}\n"
        description += f"- Task ID: {task.id}\n"
        
        return description
    
    async def orchestrate_review(
        self,
        pr: PullRequest,
        reviewers: List[str],
    ) -> None:
        """
        Orchestrate the review process for a PR
        
        Args:
            pr: The pull request
            reviewers: List of reviewer names
        """
        if not reviewers:
            raise ValueError("At least one reviewer is required")
        
        # Request reviews
        pr.request_review(reviewers)
        await self.pr_repo.save(pr)
        
        # In a real implementation, this would trigger notifications
        # to reviewers and integrate with the code review system
    
    async def process_review_feedback(
        self,
        pr: PullRequest,
        reviewer: str,
        status: ReviewStatus,
        comments: List[ReviewComment],
    ) -> None:
        """
        Process review feedback
        
        Args:
            pr: The pull request
            reviewer: The reviewer name
            status: The review status
            comments: List of review comments
        """
        # Create or update review
        review = next(
            (r for r in pr.reviews if r.reviewer == reviewer),
            CodeReview(pull_request_id=pr.id, reviewer=reviewer)
        )
        
        # Add comments
        for comment in comments:
            review.add_comment(comment)
        
        # Update review status
        if status == ReviewStatus.APPROVED:
            review.approve()
        elif status == ReviewStatus.CHANGES_REQUESTED:
            review.request_changes()
        
        # Update PR with review
        pr.add_review(review)
        await self.pr_repo.save(pr)
        
        # Check if PR can be auto-merged
        if pr.is_approved:
            await self._check_auto_merge(pr)
    
    async def _check_auto_merge(self, pr: PullRequest) -> None:
        """Check if PR can be automatically merged"""
        # In a real implementation, this would check:
        # - CI/CD status
        # - Merge conflicts
        # - Branch protection rules
        # - Required approvals
        pass
    
    async def merge_pull_request(
        self,
        pr: PullRequest,
        merge_method: str = "squash",
    ) -> None:
        """
        Merge a pull request
        
        Args:
            pr: The pull request to merge
            merge_method: The merge method (squash, merge, rebase)
        """
        if not pr.is_approved:
            raise ValueError("PR must be approved before merging")
        
        # Merge the PR
        pr.merge()
        await self.pr_repo.save(pr)
        
        # Complete the associated task
        task = await self.task_repo.find_by_id(pr.task_id)
        if task and task.status == TaskStatus.REVIEW:
            task.complete()
            await self.task_repo.save(task)
    
    async def get_review_metrics(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get pull request review metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Review metrics including average review time, approval rate, etc.
        """
        return await self.pr_repo.get_review_statistics(days)


class DeploymentService:
    """
    Domain service for deployment management
    
    Handles deployment orchestration, environment management, and rollbacks.
    """
    
    def __init__(
        self,
        deployment_repo: DeploymentRepository,
        pr_repo: PullRequestRepository,
    ):
        self.deployment_repo = deployment_repo
        self.pr_repo = pr_repo
    
    async def deploy_pull_request(
        self,
        pr: PullRequest,
        environment: str,
        config: Optional[DeploymentConfig] = None,
    ) -> Deployment:
        """
        Deploy a merged pull request to an environment
        
        Args:
            pr: The pull request to deploy
            environment: Target environment
            config: Optional deployment configuration
            
        Returns:
            The deployment record
        """
        if not pr.is_merged:
            raise ValueError("Can only deploy merged pull requests")
        
        # Check for active deployments to the same environment
        active_deployments = await self.deployment_repo.find_active_deployments()
        env_deployments = [d for d in active_deployments if d.environment == environment]
        
        if env_deployments:
            raise ValueError(f"Active deployment already in progress for {environment}")
        
        # Create deployment
        deployment = Deployment(
            pr_id=pr.id,
            environment=environment,
            config=config or DeploymentConfig(),
        )
        
        # Start deployment
        deployment.start()
        await self.deployment_repo.save(deployment)
        
        # In a real implementation, this would trigger the actual deployment
        # process through CI/CD pipelines
        
        return deployment
    
    async def promote_deployment(
        self,
        deployment_id: UUID,
        target_environment: str,
    ) -> Deployment:
        """
        Promote a successful deployment to another environment
        
        Args:
            deployment_id: The deployment to promote
            target_environment: Target environment
            
        Returns:
            The new deployment record
        """
        source_deployment = await self.deployment_repo.find_by_id(deployment_id)
        if not source_deployment:
            raise ValueError("Source deployment not found")
        
        if not source_deployment.is_successful:
            raise ValueError("Can only promote successful deployments")
        
        # Create promotion deployment
        promotion = Deployment(
            pr_id=source_deployment.pr_id,
            environment=target_environment,
            config=source_deployment.config,
        )
        
        promotion.start()
        await self.deployment_repo.save(promotion)
        
        return promotion
    
    async def rollback_deployment(
        self,
        deployment_id: UUID,
    ) -> Deployment:
        """
        Rollback a deployment
        
        Args:
            deployment_id: The deployment to rollback
            
        Returns:
            The updated deployment record
        """
        deployment = await self.deployment_repo.find_by_id(deployment_id)
        if not deployment:
            raise ValueError("Deployment not found")
        
        # Perform rollback
        deployment.rollback()
        await self.deployment_repo.save(deployment)
        
        # Find the last successful deployment to this environment
        successful_deployments = await self.deployment_repo.find_successful_deployments(
            deployment.environment,
            limit=2  # Current + previous
        )
        
        if len(successful_deployments) > 1:
            # Deploy the previous version
            previous_deployment = successful_deployments[1]
            pr = await self.pr_repo.find_by_id(previous_deployment.pr_id)
            
            if pr:
                # Create rollback deployment
                rollback_deployment = await self.deploy_pull_request(
                    pr,
                    deployment.environment,
                    deployment.config,
                )
                return rollback_deployment
        
        return deployment
    
    async def get_deployment_status(
        self,
        environment: str,
    ) -> Dict[str, Any]:
        """
        Get current deployment status for an environment
        
        Args:
            environment: The environment to check
            
        Returns:
            Current deployment status and history
        """
        # Get active deployments
        active_deployments = await self.deployment_repo.find_active_deployments()
        env_active = [d for d in active_deployments if d.environment == environment]
        
        # Get recent successful deployments
        successful = await self.deployment_repo.find_successful_deployments(
            environment,
            limit=5
        )
        
        # Get deployment metrics
        metrics = await self.deployment_repo.get_deployment_metrics(
            environment,
            days=30
        )
        
        return {
            "environment": environment,
            "active_deployment": env_active[0] if env_active else None,
            "last_successful": successful[0] if successful else None,
            "recent_deployments": successful,
            "metrics": metrics,
        }


class ImplementationPlanningService:
    """
    Domain service for implementation planning
    
    Helps create detailed implementation plans based on decision requirements.
    """
    
    def create_implementation_plan(
        self,
        decision_type: str,
        requirements: Dict[str, Any],
    ) -> ImplementationPlan:
        """
        Create an implementation plan based on decision requirements
        
        Args:
            decision_type: Type of decision
            requirements: Decision requirements
            
        Returns:
            Implementation plan
        """
        # Analyze requirements to determine approach
        approach = self._determine_approach(decision_type, requirements)
        
        # Generate implementation steps
        steps = self._generate_steps(decision_type, requirements)
        
        # Estimate effort
        estimated_hours = self._estimate_effort(steps, requirements)
        
        # Identify required skills
        required_skills = self._identify_required_skills(decision_type, requirements)
        
        # Identify dependencies
        dependencies = self._identify_dependencies(requirements)
        
        # Assess risks
        risks = self._assess_risks(decision_type, requirements)
        
        return ImplementationPlan(
            approach=approach,
            steps=steps,
            estimated_hours=estimated_hours,
            required_skills=required_skills,
            dependencies=dependencies,
            risks=risks,
        )
    
    def _determine_approach(
        self,
        decision_type: str,
        requirements: Dict[str, Any],
    ) -> str:
        """Determine the implementation approach"""
        if decision_type == "architectural":
            return "Incremental refactoring with feature flags for safe rollout"
        elif decision_type == "feature":
            return "Test-driven development with continuous integration"
        elif decision_type == "bugfix":
            return "Root cause analysis followed by targeted fix with regression tests"
        else:
            return "Standard implementation with code review and testing"
    
    def _generate_steps(
        self,
        decision_type: str,
        requirements: Dict[str, Any],
    ) -> List[str]:
        """Generate implementation steps"""
        base_steps = [
            "Set up development environment",
            "Create feature branch",
            "Write unit tests",
            "Implement core functionality",
            "Add integration tests",
            "Update documentation",
            "Submit for code review",
        ]
        
        # Add type-specific steps
        if decision_type == "architectural":
            base_steps.insert(2, "Create architecture design document")
            base_steps.insert(3, "Implement proof of concept")
            base_steps.append("Update architecture documentation")
        elif decision_type == "feature":
            base_steps.insert(3, "Implement feature flag")
            base_steps.append("Create user documentation")
        elif decision_type == "bugfix":
            base_steps.insert(0, "Reproduce the bug")
            base_steps.insert(1, "Identify root cause")
            base_steps.append("Verify fix in staging")
        
        return base_steps
    
    def _estimate_effort(
        self,
        steps: List[str],
        requirements: Dict[str, Any],
    ) -> float:
        """Estimate implementation effort in hours"""
        # Base estimate per step
        base_hours_per_step = 2.0
        base_estimate = len(steps) * base_hours_per_step
        
        # Adjust based on complexity
        complexity = requirements.get("complexity", "medium")
        complexity_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 2.0,
            "very_high": 3.0,
        }
        
        multiplier = complexity_multipliers.get(complexity, 1.0)
        
        return base_estimate * multiplier
    
    def _identify_required_skills(
        self,
        decision_type: str,
        requirements: Dict[str, Any],
    ) -> List[str]:
        """Identify required skills for implementation"""
        base_skills = ["programming", "testing", "git"]
        
        # Add type-specific skills
        if decision_type == "architectural":
            base_skills.extend(["system_design", "architecture", "performance"])
        elif decision_type == "feature":
            base_skills.extend(["ui_development", "api_design"])
        elif decision_type == "infrastructure":
            base_skills.extend(["devops", "kubernetes", "cloud"])
        
        # Add technology-specific skills from requirements
        technologies = requirements.get("technologies", [])
        base_skills.extend(technologies)
        
        return list(set(base_skills))  # Remove duplicates
    
    def _identify_dependencies(
        self,
        requirements: Dict[str, Any],
    ) -> List[str]:
        """Identify implementation dependencies"""
        dependencies = []
        
        # Check for explicit dependencies
        if "dependencies" in requirements:
            dependencies.extend(requirements["dependencies"])
        
        # Check for service dependencies
        if "services" in requirements:
            for service in requirements["services"]:
                dependencies.append(f"Integration with {service}")
        
        # Check for data dependencies
        if "data_sources" in requirements:
            for source in requirements["data_sources"]:
                dependencies.append(f"Access to {source}")
        
        return dependencies
    
    def _assess_risks(
        self,
        decision_type: str,
        requirements: Dict[str, Any],
    ) -> List[str]:
        """Assess implementation risks"""
        risks = []
        
        # Type-specific risks
        if decision_type == "architectural":
            risks.append("Potential breaking changes to existing functionality")
            risks.append("Performance regression during migration")
        elif decision_type == "infrastructure":
            risks.append("Service downtime during deployment")
            risks.append("Configuration drift between environments")
        
        # Complexity-based risks
        complexity = requirements.get("complexity", "medium")
        if complexity in ["high", "very_high"]:
            risks.append("Estimation uncertainty due to high complexity")
            risks.append("Potential for unforeseen technical challenges")
        
        # Dependency risks
        if requirements.get("dependencies"):
            risks.append("Delays due to external dependencies")
        
        return risks