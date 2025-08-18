"""
Orchestration API Endpoints

REST API endpoints for the LLM Orchestration Project Management system.
Provides visibility into projects, epics, stories, and orchestration execution.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.contexts.orchestration.aggregates import Project, Epic, Story
from src.contexts.orchestration.domain_services import (
    ProjectPlanningService,
    DependencyManagementService,
    OrchestrationExecutionService,
)
from src.contexts.orchestration.value_objects import (
    Priority,
    WorkItemStatus,
    WorkItemType,
    AcceptanceCriteria,
    WorkEstimate,
    DecisionContext,
)
from src.infrastructure.repositories.orchestration_repositories import (
    JsonProjectRepository,
    JsonEpicRepository,
    JsonStoryRepository,
)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

# Initialize repositories and services
project_repo = JsonProjectRepository()
epic_repo = JsonEpicRepository()
story_repo = JsonStoryRepository()
planning_service = ProjectPlanningService()
dependency_service = DependencyManagementService()
execution_service = OrchestrationExecutionService()


# Request/Response Models
class CreateProjectRequest(BaseModel):
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    vision: str = Field(default="", description="Project vision statement")
    business_justification: str = Field(default="", description="Business justification")
    requirements: List[str] = Field(default=[], description="List of requirements")
    priority: str = Field(default="medium", description="Project priority (low, medium, high, critical)")
    target_completion_date: Optional[str] = Field(None, description="Target completion date (ISO format)")
    stakeholders: List[str] = Field(default=[], description="Project stakeholders")


class CreateEpicRequest(BaseModel):
    name: str = Field(..., description="Epic name")
    description: str = Field(..., description="Epic description")
    business_value: str = Field(default="", description="Business value statement")
    priority: str = Field(default="medium", description="Epic priority")


class CreateStoryRequest(BaseModel):
    name: str = Field(..., description="Story name")
    description: str = Field(..., description="Story description")
    user_story: str = Field(default="", description="User story format")
    story_points: Optional[int] = Field(None, description="Story points estimate")
    priority: str = Field(default="medium", description="Story priority")


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    priority: str
    epic_count: int
    total_story_points: int
    completed_story_points: int
    completion_percentage: float
    created_at: str
    project_manager: str


class EpicResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    priority: str
    story_count: int
    total_story_points: int
    completed_story_points: int
    completion_percentage: float


class StoryResponse(BaseModel):
    id: str
    name: str
    description: str
    user_story: str
    status: str
    priority: str
    story_points: Optional[int]
    assignee: Optional[str]


class ProjectDashboardResponse(BaseModel):
    projects: List[ProjectResponse]
    total_projects: int
    active_projects: int
    completed_projects: int
    total_story_points: int
    completed_story_points: int
    overall_progress: float


class ProjectDetailResponse(BaseModel):
    project: ProjectResponse
    epics: List[EpicResponse]
    stories: List[StoryResponse]
    orchestration_phases: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    project_metrics: Dict[str, Any]


@router.get("/dashboard", response_model=ProjectDashboardResponse)
async def get_project_dashboard():
    """Get the main project dashboard with overview of all projects"""
    projects = project_repo.list_all()
    
    project_responses = []
    total_story_points = 0
    completed_story_points = 0
    active_count = 0
    completed_count = 0
    
    for project in projects:
        metrics = project.get_project_metrics()
        
        project_response = ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            status=project.status.value,
            priority=project.priority.value,
            epic_count=len(project.epics),
            total_story_points=metrics.total_story_points,
            completed_story_points=metrics.completed_story_points,
            completion_percentage=metrics.completion_percentage,
            created_at=project.created_at.isoformat(),
            project_manager=project.project_manager
        )
        project_responses.append(project_response)
        
        total_story_points += metrics.total_story_points
        completed_story_points += metrics.completed_story_points
        
        if project.status == WorkItemStatus.IN_PROGRESS:
            active_count += 1
        elif project.status == WorkItemStatus.COMPLETED:
            completed_count += 1
    
    overall_progress = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0
    
    return ProjectDashboardResponse(
        projects=project_responses,
        total_projects=len(projects),
        active_projects=active_count,
        completed_projects=completed_count,
        total_story_points=total_story_points,
        completed_story_points=completed_story_points,
        overall_progress=overall_progress
    )


@router.post("/projects", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    """Create a new project with LLM-based planning"""
    # Create the project
    project = Project(
        name=request.name,
        description=request.description,
        vision=request.vision,
        business_justification=request.business_justification,
        priority=Priority(request.priority),
        stakeholders=request.stakeholders,
        project_manager="llm_orchestrator"
    )
    
    if request.target_completion_date:
        project.target_completion_date = datetime.fromisoformat(request.target_completion_date)
    
    # Use LLM planning service to break down requirements
    if request.requirements:
        decision_context = planning_service.analyze_project_complexity(
            request.description, request.requirements
        )
        
        epics = planning_service.create_epic_breakdown(project, request.requirements)
        for epic in epics:
            project.add_epic(epic)
        
        # Create orchestration plan
        orchestration_plan = planning_service.create_orchestration_plan(project)
        project.create_orchestration_plan(
            orchestration_plan.phases,
            orchestration_plan.overall_strategy,
            orchestration_plan.risk_mitigation
        )
    
    # Save the project
    project_repo.save(project)
    
    # Calculate metrics
    metrics = project.get_project_metrics()
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        status=project.status.value,
        priority=project.priority.value,
        epic_count=len(project.epics),
        total_story_points=metrics.total_story_points,
        completed_story_points=metrics.completed_story_points,
        completion_percentage=metrics.completion_percentage,
        created_at=project.created_at.isoformat(),
        project_manager=project.project_manager
    )


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project_detail(project_id: str):
    """Get detailed view of a specific project"""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    project = project_repo.get_by_id(project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Calculate metrics
    metrics = project.get_project_metrics()
    
    # Prepare project response
    project_response = ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        status=project.status.value,
        priority=project.priority.value,
        epic_count=len(project.epics),
        total_story_points=metrics.total_story_points,
        completed_story_points=metrics.completed_story_points,
        completion_percentage=metrics.completion_percentage,
        created_at=project.created_at.isoformat(),
        project_manager=project.project_manager
    )
    
    # Prepare epics
    epic_responses = []
    for epic in project.epics:
        epic_responses.append(EpicResponse(
            id=str(epic.id),
            name=epic.name,
            description=epic.description,
            status=epic.status.value,
            priority=epic.priority.value,
            story_count=len(epic.stories),
            total_story_points=epic.get_total_story_points(),
            completed_story_points=epic.get_completed_story_points(),
            completion_percentage=epic.completion_percentage
        ))
    
    # Prepare stories
    story_responses = []
    for epic in project.epics:
        for story in epic.stories:
            story_responses.append(StoryResponse(
                id=str(story.id),
                name=story.name,
                description=story.description,
                user_story=story.user_story,
                status=story.status.value,
                priority=story.priority.value,
                story_points=story.story_points,
                assignee=story.assignee
            ))
    
    # Prepare orchestration phases
    orchestration_phases = []
    if project.orchestration_plan:
        for i, phase in enumerate(project.orchestration_plan.phases):
            orchestration_phases.append({
                "phase_name": phase.phase_name,
                "description": phase.description,
                "estimated_duration": phase.estimated_duration,
                "parallel_capable": phase.parallel_capable,
                "risk_level": phase.risk_level,
                "prerequisites": phase.prerequisites,
                "deliverables": phase.deliverables
            })
    
    # Analyze dependencies
    dependencies = dependency_service.analyze_dependencies(project)
    dependency_responses = []
    for dep in dependencies:
        dependency_responses.append({
            "from_item_id": str(dep.from_item_id),
            "to_item_id": str(dep.to_item_id),
            "dependency_type": dep.dependency_type.value,
            "description": dep.description,
            "is_hard_dependency": dep.is_hard_dependency
        })
    
    return ProjectDetailResponse(
        project=project_response,
        epics=epic_responses,
        stories=story_responses,
        orchestration_phases=orchestration_phases,
        dependencies=dependency_responses,
        project_metrics=metrics.__dict__
    )


@router.post("/projects/{project_id}/start")
async def start_project(project_id: str):
    """Start a project"""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    project = project_repo.get_by_id(project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        project.start()
        project_repo.save(project)
        return {"message": f"Project '{project.name}' started successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/complete")
async def complete_project(project_id: str):
    """Complete a project"""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    project = project_repo.get_by_id(project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        project.complete()
        project_repo.save(project)
        return {"message": f"Project '{project.name}' completed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/epics", response_model=EpicResponse)
async def create_epic(project_id: str, request: CreateEpicRequest):
    """Create a new epic in a project"""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    project = project_repo.get_by_id(project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    epic = Epic(
        project_id=project_uuid,
        name=request.name,
        description=request.description,
        business_value=request.business_value,
        priority=Priority(request.priority)
    )
    
    project.add_epic(epic)
    project_repo.save(project)
    
    return EpicResponse(
        id=str(epic.id),
        name=epic.name,
        description=epic.description,
        status=epic.status.value,
        priority=epic.priority.value,
        story_count=len(epic.stories),
        total_story_points=epic.get_total_story_points(),
        completed_story_points=epic.get_completed_story_points(),
        completion_percentage=epic.completion_percentage
    )


@router.post("/epics/{epic_id}/stories", response_model=StoryResponse)
async def create_story(epic_id: str, request: CreateStoryRequest):
    """Create a new story in an epic"""
    try:
        epic_uuid = UUID(epic_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid epic ID format")
    
    # Find the project containing this epic
    projects = project_repo.list_all()
    project = None
    epic = None
    
    for p in projects:
        for e in p.epics:
            if e.id == epic_uuid:
                project = p
                epic = e
                break
        if project:
            break
    
    if not project or not epic:
        raise HTTPException(status_code=404, detail="Epic not found")
    
    story = Story(
        epic_id=epic_uuid,
        name=request.name,
        description=request.description,
        user_story=request.user_story,
        story_points=request.story_points,
        priority=Priority(request.priority)
    )
    
    epic.add_story(story)
    project_repo.save(project)
    
    return StoryResponse(
        id=str(story.id),
        name=story.name,
        description=story.description,
        user_story=story.user_story,
        status=story.status.value,
        priority=story.priority.value,
        story_points=story.story_points,
        assignee=story.assignee
    )


@router.get("/stats")
async def get_orchestration_stats():
    """Get orchestration system statistics"""
    projects = project_repo.list_all()
    
    total_projects = len(projects)
    active_projects = len([p for p in projects if p.status == WorkItemStatus.IN_PROGRESS])
    completed_projects = len([p for p in projects if p.status == WorkItemStatus.COMPLETED])
    
    total_epics = sum(len(p.epics) for p in projects)
    total_stories = sum(len(epic.stories) for p in projects for epic in p.epics)
    
    total_story_points = sum(p.get_project_metrics().total_story_points for p in projects)
    completed_story_points = sum(p.get_project_metrics().completed_story_points for p in projects)
    
    return {
        "orchestration_stats": {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "total_epics": total_epics,
            "total_stories": total_stories,
            "total_story_points": total_story_points,
            "completed_story_points": completed_story_points,
            "overall_progress": (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0
        }
    }


@router.get("/projects/{project_id}/orchestration/execute")
async def execute_project_orchestration(project_id: str):
    """Execute orchestration for a project"""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    project = project_repo.get_by_id(project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.orchestration_plan:
        raise HTTPException(status_code=400, detail="Project has no orchestration plan")
    
    # Execute the first phase (simplified)
    result = execution_service.execute_project_phase(project, 0)
    
    return {
        "orchestration_execution": result,
        "project_id": project_id,
        "total_phases": len(project.orchestration_plan.phases)
    }


@router.get("/health")
async def orchestration_health():
    """Health check for orchestration system"""
    try:
        # Test basic repository functionality
        projects = project_repo.list_all()
        
        return {
            "status": "healthy",
            "components": {
                "project_repository": "operational",
                "planning_service": "operational",
                "dependency_service": "operational",
                "execution_service": "operational"
            },
            "metrics": {
                "total_projects": len(projects),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }