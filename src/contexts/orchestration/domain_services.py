"""
Orchestration Context Domain Services

Domain services that handle complex orchestration workflows,
LLM-based project management, and cross-context coordination.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4

from .aggregates import Epic, Project, Story
from .value_objects import (
    AcceptanceCriteria,
    DecisionContext,
    Dependency,
    DependencyType,
    ImplementationPhase,
    OrchestrationPlan,
    Priority,
    ProjectMetrics,
    QualityGate,
    ResourceAllocation,
    WorkEstimate,
    WorkItemStatus,
    WorkItemType,
)


class ProjectPlanningService:
    """
    Domain service for LLM-based project planning and breakdown.
    
    This service acts as the "LLM Project Manager" that can analyze
    requirements and break them down into manageable work items.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def analyze_project_complexity(self, description: str, requirements: List[str]) -> DecisionContext:
        """Analyze project complexity and create decision context"""
        # Simplified complexity scoring - real implementation would use LLM
        complexity_score = min(10.0, len(requirements) * 0.5 + len(description.split()) * 0.01)
        
        # Extract domain knowledge from requirements (simplified)
        domain_knowledge = []
        if any("api" in req.lower() for req in requirements):
            domain_knowledge.append("API Development")
        if any("database" in req.lower() or "db" in req.lower() for req in requirements):
            domain_knowledge.append("Database Design")
        if any("ui" in req.lower() or "interface" in req.lower() for req in requirements):
            domain_knowledge.append("User Interface Design")
        
        # Determine business impact and technical risk
        business_impact = "high" if complexity_score >= 7.0 else "medium" if complexity_score >= 4.0 else "low"
        technical_risk = "high" if complexity_score >= 8.0 else "medium" if complexity_score >= 5.0 else "low"
        
        return DecisionContext(
            complexity_score=complexity_score,
            domain_knowledge_required=domain_knowledge,
            stakeholders=["product_owner", "development_team"],
            business_impact=business_impact,
            technical_risk=technical_risk,
            time_sensitivity="medium"
        )

    def create_epic_breakdown(self, project: Project, requirements: List[str]) -> List[Epic]:
        """Break down project requirements into epics"""
        epics = []
        
        # Group related requirements into epics (simplified logic)
        epic_groups = self._group_requirements_into_epics(requirements)
        
        for group_name, group_requirements in epic_groups.items():
            epic = Epic(
                name=group_name,
                description=f"Epic covering: {', '.join(group_requirements)}",
                business_value=f"Delivers functionality for {group_name.lower()}",
                priority=self._determine_epic_priority(group_requirements),
                estimate=WorkEstimate(
                    story_points=len(group_requirements) * 5,  # Rough estimate
                    hours=len(group_requirements) * 20.0,
                    confidence_level="medium",
                    basis="Initial breakdown by LLM project manager"
                )
            )
            
            # Create stories for each requirement in the epic
            for req in group_requirements:
                story = self._create_story_from_requirement(req)
                epic.add_story(story)
            
            epics.append(epic)
        
        return epics

    def create_orchestration_plan(self, project: Project) -> OrchestrationPlan:
        """Create an orchestration plan for project execution"""
        phases = self._analyze_implementation_phases(project)
        strategy = self._determine_orchestration_strategy(project)
        risk_mitigation = self._identify_risk_mitigation_strategies(project)
        
        return OrchestrationPlan(
            project_id=project.id,
            phases=phases,
            overall_strategy=strategy,
            risk_mitigation=risk_mitigation,
            resource_requirements=self._calculate_resource_requirements(project),
            success_metrics=self._define_success_metrics(project)
        )

    def _group_requirements_into_epics(self, requirements: List[str]) -> Dict[str, List[str]]:
        """Group requirements into logical epics"""
        # Simplified grouping logic - real implementation would use LLM
        groups = {}
        
        for req in requirements:
            req_lower = req.lower()
            if "auth" in req_lower or "login" in req_lower or "user" in req_lower:
                groups.setdefault("User Management", []).append(req)
            elif "data" in req_lower or "database" in req_lower or "storage" in req_lower:
                groups.setdefault("Data Management", []).append(req)
            elif "api" in req_lower or "service" in req_lower or "endpoint" in req_lower:
                groups.setdefault("API Services", []).append(req)
            elif "ui" in req_lower or "interface" in req_lower or "frontend" in req_lower:
                groups.setdefault("User Interface", []).append(req)
            else:
                groups.setdefault("Core Features", []).append(req)
        
        return groups

    def _determine_epic_priority(self, requirements: List[str]) -> Priority:
        """Determine priority based on requirements"""
        # Simplified priority logic
        if any("critical" in req.lower() or "security" in req.lower() for req in requirements):
            return Priority.HIGH
        elif any("auth" in req.lower() or "core" in req.lower() for req in requirements):
            return Priority.HIGH
        else:
            return Priority.MEDIUM

    def _create_story_from_requirement(self, requirement: str) -> Story:
        """Create a story from a requirement"""
        # Extract user story format from requirement (simplified)
        user_story = f"As a user, I want {requirement.lower()}"
        
        # Create basic acceptance criteria
        criteria = [
            AcceptanceCriteria(
                id="ac_1",
                description=f"Requirement '{requirement}' is implemented",
                is_testable=True,
                test_approach="Integration testing"
            )
        ]
        
        return Story(
            name=requirement,
            description=f"Implement {requirement}",
            user_story=user_story,
            acceptance_criteria=criteria,
            story_points=3,  # Default estimate
            priority=Priority.MEDIUM
        )

    def _analyze_implementation_phases(self, project: Project) -> List[ImplementationPhase]:
        """Analyze project and create implementation phases"""
        phases = []
        
        # Standard phases for most projects
        phases.append(ImplementationPhase(
            phase_name="Foundation",
            description="Set up infrastructure, core services, and basic architecture",
            prerequisites=[],
            deliverables=["Infrastructure setup", "Core services", "Basic authentication"],
            estimated_duration=40.0,
            parallel_capable=False,
            risk_level="medium"
        ))
        
        phases.append(ImplementationPhase(
            phase_name="Core Features",
            description="Implement main business functionality",
            prerequisites=["Foundation"],
            deliverables=["Main features", "Business logic", "Data models"],
            estimated_duration=80.0,
            parallel_capable=True,
            risk_level="high"
        ))
        
        phases.append(ImplementationPhase(
            phase_name="Integration",
            description="Integrate components and external services",
            prerequisites=["Core Features"],
            deliverables=["API integrations", "Component integration", "End-to-end workflows"],
            estimated_duration=30.0,
            parallel_capable=False,
            risk_level="medium"
        ))
        
        phases.append(ImplementationPhase(
            phase_name="Polish & Deploy",
            description="Final testing, optimization, and deployment",
            prerequisites=["Integration"],
            deliverables=["Performance optimization", "Final testing", "Production deployment"],
            estimated_duration=20.0,
            parallel_capable=False,
            risk_level="low"
        ))
        
        return phases

    def _determine_orchestration_strategy(self, project: Project) -> str:
        """Determine the best orchestration strategy for the project"""
        epic_count = len(project.epics)
        total_stories = sum(len(epic.stories) for epic in project.epics)
        
        if epic_count <= 2 and total_stories <= 10:
            return "Sequential execution with single team"
        elif epic_count <= 4 and total_stories <= 25:
            return "Parallel epic development with feature team coordination"
        else:
            return "Multi-team parallel execution with epic-based team assignments"

    def _identify_risk_mitigation_strategies(self, project: Project) -> List[str]:
        """Identify risk mitigation strategies for the project"""
        strategies = [
            "Regular progress reviews and milestone checkpoints",
            "Automated testing and continuous integration",
            "Incremental delivery with stakeholder feedback loops"
        ]
        
        # Add specific strategies based on project characteristics
        if len(project.epics) > 3:
            strategies.append("Cross-team communication protocols and dependency management")
        
        if any(epic.priority == Priority.HIGH for epic in project.epics):
            strategies.append("Priority epic fast-tracking with dedicated resources")
        
        return strategies

    def _calculate_resource_requirements(self, project: Project) -> Dict[str, Any]:
        """Calculate resource requirements for the project"""
        total_story_points = sum(epic.get_total_story_points() for epic in project.epics)
        
        return {
            "estimated_developer_weeks": total_story_points / 10,  # Assume 10 story points per week
            "required_skill_areas": ["Software Development", "Testing", "DevOps"],
            "peak_team_size": min(8, max(2, len(project.epics))),
            "recommended_team_composition": {
                "senior_developers": 2,
                "mid_developers": 3,
                "qa_engineers": 1,
                "devops_engineer": 1
            }
        }

    def _define_success_metrics(self, project: Project) -> List[str]:
        """Define success metrics for the project"""
        return [
            "All acceptance criteria met for 100% of stories",
            "Zero critical defects in production",
            "Project delivered within 110% of estimated timeline",
            "Stakeholder satisfaction score >= 8/10",
            "System performance meets defined SLAs"
        ]


class DependencyManagementService:
    """
    Domain service for managing dependencies between work items.
    
    Handles dependency analysis, resolution planning, and blocking issue identification.
    """

    def analyze_dependencies(self, project: Project) -> List[Dependency]:
        """Analyze and identify dependencies across the project"""
        dependencies = []
        
        # Analyze epic-level dependencies
        for i, epic in enumerate(project.epics):
            for j, other_epic in enumerate(project.epics[i+1:], start=i+1):
                if self._has_dependency(epic, other_epic):
                    dependencies.append(Dependency(
                        from_item_id=epic.id,
                        to_item_id=other_epic.id,
                        dependency_type=DependencyType.BLOCKS,
                        description=f"Epic '{epic.name}' must complete before '{other_epic.name}'"
                    ))
        
        # Analyze story-level dependencies within epics
        for epic in project.epics:
            story_dependencies = self._analyze_story_dependencies(epic.stories)
            dependencies.extend(story_dependencies)
        
        return dependencies

    def create_dependency_resolution_plan(self, dependencies: List[Dependency]) -> Dict[str, Any]:
        """Create a plan for resolving dependencies"""
        # Group dependencies by type and analyze critical path
        blocking_deps = [d for d in dependencies if d.dependency_type == DependencyType.BLOCKS]
        
        return {
            "critical_path_items": self._identify_critical_path(blocking_deps),
            "parallel_workstreams": self._identify_parallel_workstreams(dependencies),
            "dependency_resolution_order": self._calculate_resolution_order(blocking_deps),
            "risk_factors": self._identify_dependency_risks(dependencies)
        }

    def _has_dependency(self, epic1: Epic, epic2: Epic) -> bool:
        """Check if epic1 has a dependency on epic2"""
        # Simplified dependency detection logic
        epic1_lower = epic1.name.lower()
        epic2_lower = epic2.name.lower()
        
        # Infrastructure dependencies
        if "user" in epic1_lower and "auth" in epic2_lower:
            return True
        if "api" in epic1_lower and "data" in epic2_lower:
            return True
        
        return False

    def _analyze_story_dependencies(self, stories: List[Story]) -> List[Dependency]:
        """Analyze dependencies between stories within an epic"""
        dependencies = []
        
        # Simple heuristic: stories with setup/infrastructure come first
        infrastructure_stories = [s for s in stories if any(word in s.name.lower() 
                                 for word in ["setup", "infrastructure", "config", "auth"])]
        feature_stories = [s for s in stories if s not in infrastructure_stories]
        
        # Infrastructure stories block feature stories
        for infra_story in infrastructure_stories:
            for feature_story in feature_stories:
                dependencies.append(Dependency(
                    from_item_id=infra_story.id,
                    to_item_id=feature_story.id,
                    dependency_type=DependencyType.BLOCKS,
                    description=f"Infrastructure story must complete before feature story"
                ))
        
        return dependencies

    def _identify_critical_path(self, blocking_dependencies: List[Dependency]) -> List[UUID]:
        """Identify work items on the critical path"""
        # Simplified critical path calculation
        critical_items = set()
        for dep in blocking_dependencies:
            critical_items.add(dep.from_item_id)
        
        return list(critical_items)

    def _identify_parallel_workstreams(self, dependencies: List[Dependency]) -> List[List[UUID]]:
        """Identify work items that can be executed in parallel"""
        # Simplified parallel workstream identification
        dependent_items = {dep.to_item_id for dep in dependencies}
        independent_items = {dep.from_item_id for dep in dependencies} - dependent_items
        
        # Group independent items into potential parallel streams
        return [list(independent_items)] if independent_items else []

    def _calculate_resolution_order(self, blocking_dependencies: List[Dependency]) -> List[UUID]:
        """Calculate the order for resolving dependencies"""
        # Topological sort would be ideal here, simplified for now
        ordered_items = []
        
        # Start with items that don't depend on anything
        remaining_deps = blocking_dependencies.copy()
        processed_items = set()
        
        while remaining_deps:
            # Find items with no unresolved dependencies
            ready_items = set()
            for dep in remaining_deps:
                if dep.from_item_id not in processed_items:
                    ready_items.add(dep.from_item_id)
            
            if not ready_items:
                # Circular dependency or all items processed
                break
            
            # Process one ready item
            next_item = ready_items.pop()
            ordered_items.append(next_item)
            processed_items.add(next_item)
            
            # Remove dependencies for this item
            remaining_deps = [dep for dep in remaining_deps if dep.from_item_id != next_item]
        
        return ordered_items

    def _identify_dependency_risks(self, dependencies: List[Dependency]) -> List[str]:
        """Identify risks related to dependencies"""
        risks = []
        
        if len(dependencies) > 10:
            risks.append("High number of dependencies may cause coordination overhead")
        
        blocking_count = len([d for d in dependencies if d.dependency_type == DependencyType.BLOCKS])
        if blocking_count > 5:
            risks.append("Multiple blocking dependencies may cause delays")
        
        return risks


class OrchestrationExecutionService:
    """
    Domain service for executing orchestration plans.
    
    Coordinates the execution of projects across multiple phases and teams.
    """

    def __init__(self, task_assignment_service=None, debate_service=None):
        self.task_assignment_service = task_assignment_service
        self.debate_service = debate_service

    def execute_project_phase(self, project: Project, phase_index: int) -> Dict[str, Any]:
        """Execute a specific phase of the project orchestration plan"""
        if not project.orchestration_plan:
            raise ValueError("Project must have an orchestration plan")
        
        if phase_index >= len(project.orchestration_plan.phases):
            raise ValueError("Invalid phase index")
        
        phase = project.orchestration_plan.phases[phase_index]
        
        # Check prerequisites
        if not self._prerequisites_met(project, phase):
            return {
                "status": "blocked",
                "reason": "Prerequisites not met",
                "missing_prerequisites": phase.prerequisites
            }
        
        # Execute phase
        execution_result = self._execute_phase_work(project, phase)
        
        return {
            "status": "completed",
            "phase_name": phase.phase_name,
            "execution_result": execution_result,
            "next_phases": self._identify_next_phases(project, phase_index)
        }

    def coordinate_cross_epic_work(self, project: Project) -> Dict[str, Any]:
        """Coordinate work across multiple epics"""
        coordination_plan = {
            "parallel_epics": [],
            "sequential_epics": [],
            "shared_dependencies": [],
            "resource_conflicts": []
        }
        
        # Analyze epic interdependencies
        for epic in project.epics:
            if epic.dependencies:
                coordination_plan["sequential_epics"].append(epic.id)
            else:
                coordination_plan["parallel_epics"].append(epic.id)
        
        return coordination_plan

    def _prerequisites_met(self, project: Project, phase: ImplementationPhase) -> bool:
        """Check if phase prerequisites are met"""
        if not phase.prerequisites:
            return True
        
        # Check if previous phases are completed
        # Simplified check - real implementation would track phase completion
        return True

    def _execute_phase_work(self, project: Project, phase: ImplementationPhase) -> Dict[str, Any]:
        """Execute the work for a specific phase"""
        # This would coordinate with implementation context to create and assign tasks
        return {
            "phase_duration": phase.estimated_duration,
            "deliverables_completed": phase.deliverables,
            "work_items_assigned": len(phase.deliverables),
            "parallel_execution": phase.parallel_capable
        }

    def _identify_next_phases(self, project: Project, current_phase_index: int) -> List[str]:
        """Identify which phases can be started next"""
        if not project.orchestration_plan:
            return []
        
        phases = project.orchestration_plan.phases
        next_phases = []
        
        # Check subsequent phases
        for i in range(current_phase_index + 1, len(phases)):
            next_phase = phases[i]
            if self._prerequisites_met(project, next_phase):
                next_phases.append(next_phase.phase_name)
        
        return next_phases