"""
Orchestration Integration Service

Integrates the orchestration system with the existing debate and implementation systems.
Handles cross-context communication and workflow coordination.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.contexts.orchestration.aggregates import Project, Epic, Story
from src.contexts.orchestration.domain_services import ProjectPlanningService
from src.contexts.orchestration.value_objects import DecisionContext, WorkItemType
from src.infrastructure.repositories.orchestration_repositories import (
    JsonProjectRepository,
    JsonEpicRepository,
    JsonStoryRepository,
)


class OrchestrationIntegrationService:
    """
    Service that integrates orchestration with other bounded contexts.
    
    This service handles:
    - Creating orchestration projects from debate decisions
    - Triggering debates for complex orchestration decisions
    - Converting stories to implementation tasks
    - Coordinating cross-context workflows
    """

    def __init__(self, debate_nucleus=None, event_bus=None):
        self.debate_nucleus = debate_nucleus
        self.event_bus = event_bus
        self.project_repo = JsonProjectRepository()
        self.epic_repo = JsonEpicRepository()
        self.story_repo = JsonStoryRepository()
        self.planning_service = ProjectPlanningService()

    async def create_project_from_debate_decision(
        self, 
        decision_id: str,
        decision_text: str,
        complexity: str,
        context: str = ""
    ) -> Optional[Project]:
        """
        Create an orchestration project from a complex debate decision.
        
        This is triggered when a debate results in a decision that requires
        complex implementation with multiple phases or coordination.
        """
        
        # Only create projects for complex decisions
        if complexity.lower() not in ["complex", "very_complex"]:
            return None
        
        # Extract requirements from decision and context
        requirements = self._extract_requirements_from_decision(decision_text, context)
        
        if not requirements:
            return None
        
        # Create project
        project = Project(
            name=f"Implementation: {decision_text[:50]}...",
            description=f"Project created from debate decision {decision_id}",
            vision=decision_text,
            business_justification=f"Decision made through AI debate: {decision_text}",
            project_manager="llm_orchestrator"
        )
        
        # Use planning service to break down into epics and stories
        decision_context = self.planning_service.analyze_project_complexity(
            decision_text, requirements
        )
        
        epics = self.planning_service.create_epic_breakdown(project, requirements)
        for epic in epics:
            project.add_epic(epic)
        
        # Create orchestration plan
        orchestration_plan = self.planning_service.create_orchestration_plan(project)
        project.create_orchestration_plan(
            orchestration_plan.phases,
            orchestration_plan.overall_strategy,
            orchestration_plan.risk_mitigation
        )
        
        # Save project
        self.project_repo.save(project)
        
        # Publish integration event
        if self.event_bus:
            await self.event_bus.publish({
                "event_type": "orchestration.project_created_from_debate",
                "project_id": str(project.id),
                "decision_id": decision_id,
                "timestamp": datetime.now().isoformat()
            })
        
        return project

    async def trigger_debate_for_story(self, story: Story) -> Optional[Dict[str, Any]]:
        """
        Trigger a debate for a complex story that needs decision-making.
        
        This is called when a story has high complexity or risk that requires
        debate to determine the best implementation approach.
        """
        
        if not story.decision_context or not story.decision_context.should_trigger_debate():
            return None
        
        if not self.debate_nucleus:
            return None
        
        # Formulate debate question
        debate_question = f"How should we implement the story: {story.name}?"
        debate_context = f"""
        Story Description: {story.description}
        User Story: {story.user_story}
        Acceptance Criteria: {[ac.description for ac in story.acceptance_criteria]}
        Complexity Score: {story.decision_context.complexity_score}
        Business Impact: {story.decision_context.business_impact}
        Technical Risk: {story.decision_context.technical_risk}
        """
        
        # Trigger debate
        debate_result = await self.debate_nucleus.decide(debate_question, debate_context)
        
        # Update story with debate outcome
        story.description += f"\n\nDebate Decision: {debate_result.get('decision', '')}"
        
        # Publish integration event
        if self.event_bus:
            await self.event_bus.publish({
                "event_type": "orchestration.debate_triggered_for_story",
                "story_id": str(story.id),
                "debate_result": debate_result,
                "timestamp": datetime.now().isoformat()
            })
        
        return debate_result

    async def convert_stories_to_tasks(self, epic: Epic) -> List[Dict[str, Any]]:
        """
        Convert stories in an epic to implementation tasks.
        
        This integrates with the implementation context to create concrete
        tasks that can be assigned and tracked.
        """
        
        tasks = []
        
        for story in epic.stories:
            if story.status.value != "planned":
                continue
            
            # Create implementation tasks based on story
            task_data = {
                "id": str(UUID()),
                "story_id": str(story.id),
                "epic_id": str(epic.id),
                "title": f"Implement: {story.name}",
                "description": story.description,
                "user_story": story.user_story,
                "acceptance_criteria": [ac.description for ac in story.acceptance_criteria],
                "estimated_hours": story.story_points * 4 if story.story_points else 16,  # 4 hours per story point
                "priority": story.priority.value,
                "assignee": story.assignee,
                "created_at": datetime.now().isoformat()
            }
            
            tasks.append(task_data)
            
            # Update story to track generated task
            story.generated_task_ids.append(UUID(task_data["id"]))
        
        # Save epic with updated stories
        # Note: In real implementation, this would save to the project containing the epic
        
        # Publish integration event
        if self.event_bus:
            await self.event_bus.publish({
                "event_type": "orchestration.tasks_generated_from_epic",
                "epic_id": str(epic.id),
                "task_count": len(tasks),
                "task_ids": [task["id"] for task in tasks],
                "timestamp": datetime.now().isoformat()
            })
        
        return tasks

    async def get_project_integration_status(self, project_id: UUID) -> Dict[str, Any]:
        """
        Get integration status for a project, showing connections to
        debates, tasks, and other contexts.
        """
        
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {"error": "Project not found"}
        
        # Count related items across contexts
        total_stories = sum(len(epic.stories) for epic in project.epics)
        total_tasks = sum(len(story.generated_task_ids) for epic in project.epics for story in epic.stories)
        
        # Stories that might need debates
        debate_eligible_stories = []
        for epic in project.epics:
            for story in epic.stories:
                if story.decision_context and story.decision_context.should_trigger_debate():
                    debate_eligible_stories.append({
                        "story_id": str(story.id),
                        "story_name": story.name,
                        "complexity_score": story.decision_context.complexity_score
                    })
        
        return {
            "project_id": str(project_id),
            "project_name": project.name,
            "integration_status": {
                "total_epics": len(project.epics),
                "total_stories": total_stories,
                "generated_tasks": total_tasks,
                "debate_eligible_stories": len(debate_eligible_stories),
                "orchestration_plan_exists": project.orchestration_plan is not None
            },
            "debate_candidates": debate_eligible_stories,
            "cross_context_health": "operational"
        }

    def _extract_requirements_from_decision(
        self, 
        decision_text: str, 
        context: str
    ) -> List[str]:
        """
        Extract actionable requirements from a debate decision.
        
        This is a simplified extraction - a real implementation would
        use more sophisticated NLP or LLM analysis.
        """
        
        requirements = []
        text_to_analyze = f"{decision_text} {context}".lower()
        
        # Look for action keywords that suggest requirements
        action_keywords = [
            "implement", "create", "develop", "build", "design",
            "integrate", "configure", "setup", "establish", "add"
        ]
        
        # Look for technical keywords that suggest components
        technical_keywords = [
            "api", "database", "interface", "service", "system",
            "component", "module", "framework", "library", "tool"
        ]
        
        # Simple requirement extraction
        sentences = decision_text.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if not sentence_lower:
                continue
                
            # Check if sentence contains action + technical keywords
            has_action = any(keyword in sentence_lower for keyword in action_keywords)
            has_technical = any(keyword in sentence_lower for keyword in technical_keywords)
            
            if has_action and has_technical and len(sentence.strip()) > 10:
                requirements.append(sentence.strip())
        
        # If no requirements found, create generic ones based on decision
        if not requirements and len(decision_text.strip()) > 20:
            requirements = [
                f"Implement core functionality for: {decision_text[:100]}",
                "Set up necessary infrastructure and dependencies",
                "Create comprehensive tests and documentation",
                "Establish monitoring and deployment processes"
            ]
        
        return requirements[:10]  # Limit to 10 requirements max

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the integration service"""
        
        try:
            # Test repository connections
            projects = self.project_repo.list_all()
            
            # Test debate nucleus connection
            debate_connection = "connected" if self.debate_nucleus else "not_connected"
            
            # Test event bus connection
            event_bus_connection = "connected" if self.event_bus else "not_connected"
            
            return {
                "status": "healthy",
                "components": {
                    "project_repository": "operational",
                    "debate_nucleus": debate_connection,
                    "event_bus": event_bus_connection,
                    "planning_service": "operational"
                },
                "metrics": {
                    "total_projects": len(projects),
                    "integration_endpoints": 4
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }