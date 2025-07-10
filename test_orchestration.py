#!/usr/bin/env python3
"""
Test script for the Orchestration System

This script tests the basic functionality of the orchestration implementation
to ensure everything is working correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

import asyncio
from datetime import datetime
from uuid import UUID

from src.contexts.orchestration.aggregates import Project, Epic, Story
from src.contexts.orchestration.domain_services import ProjectPlanningService
from src.contexts.orchestration.value_objects import Priority, WorkItemStatus
from src.infrastructure.repositories.orchestration_repositories import JsonProjectRepository
from src.integration.orchestration_integration import OrchestrationIntegrationService


async def test_orchestration_system():
    """Test the orchestration system functionality"""
    
    print("🚀 Testing Orchestration System Implementation")
    print("=" * 50)
    
    # Test 1: Create a project with LLM planning
    print("\n📋 Test 1: Creating Project with LLM Planning")
    try:
        planning_service = ProjectPlanningService()
        
        requirements = [
            "Implement user authentication system",
            "Create RESTful API endpoints",
            "Design user interface for dashboard",
            "Set up database schema and migrations",
            "Implement real-time notifications"
        ]
        
        project = Project(
            name="E-commerce Platform",
            description="Modern e-commerce platform with real-time features",
            vision="Create a scalable, user-friendly e-commerce solution",
            priority=Priority.HIGH,
            project_manager="llm_orchestrator"
        )
        
        # Use planning service to break down requirements
        epics = planning_service.create_epic_breakdown(project, requirements)
        for epic in epics:
            project.add_epic(epic)
        
        print(f"✅ Project created: {project.name}")
        print(f"   - Epics generated: {len(project.epics)}")
        for epic in project.epics:
            print(f"     • {epic.name} ({len(epic.stories)} stories)")
        
    except Exception as e:
        print(f"❌ Error in Test 1: {e}")
        return False
    
    # Test 2: Repository operations
    print("\n💾 Test 2: Testing Repository Operations")
    try:
        repo = JsonProjectRepository()
        
        # Save project
        repo.save(project)
        print("✅ Project saved to repository")
        
        # Retrieve project
        retrieved_project = repo.get_by_id(project.id)
        if retrieved_project:
            print(f"✅ Project retrieved: {retrieved_project.name}")
            print(f"   - Status: {retrieved_project.status.value}")
            print(f"   - Priority: {retrieved_project.priority.value}")
        else:
            print("❌ Failed to retrieve project")
            return False
        
        # List all projects
        all_projects = repo.list_all()
        print(f"✅ Total projects in repository: {len(all_projects)}")
        
    except Exception as e:
        print(f"❌ Error in Test 2: {e}")
        return False
    
    # Test 3: Project metrics and orchestration
    print("\n📊 Test 3: Testing Project Metrics and Orchestration")
    try:
        # Start the project
        project.start()
        print(f"✅ Project started: {project.status.value}")
        
        # Get project metrics
        metrics = project.get_project_metrics()
        print(f"✅ Project metrics calculated:")
        print(f"   - Total story points: {metrics.total_story_points}")
        print(f"   - Total work items: {metrics.total_work_items}")
        print(f"   - Completion: {metrics.completion_percentage:.1f}%")
        
        # Create orchestration plan
        orchestration_plan = planning_service.create_orchestration_plan(project)
        project.create_orchestration_plan(
            orchestration_plan.phases,
            orchestration_plan.overall_strategy,
            orchestration_plan.risk_mitigation
        )
        
        print(f"✅ Orchestration plan created:")
        print(f"   - Total phases: {len(orchestration_plan.phases)}")
        for i, phase in enumerate(orchestration_plan.phases):
            print(f"     {i+1}. {phase.phase_name} ({phase.estimated_duration}h)")
        
    except Exception as e:
        print(f"❌ Error in Test 3: {e}")
        return False
    
    # Test 4: Integration service
    print("\n🔗 Test 4: Testing Integration Service")
    try:
        integration_service = OrchestrationIntegrationService()
        
        # Test health check
        health = await integration_service.health_check()
        print(f"✅ Integration service health: {health['status']}")
        
        # Test project integration status
        status = await integration_service.get_project_integration_status(project.id)
        print(f"✅ Project integration status:")
        print(f"   - Epics: {status['integration_status']['total_epics']}")
        print(f"   - Stories: {status['integration_status']['total_stories']}")
        print(f"   - Has orchestration plan: {status['integration_status']['orchestration_plan_exists']}")
        
    except Exception as e:
        print(f"❌ Error in Test 4: {e}")
        return False
    
    # Test 5: Story and Epic operations
    print("\n📝 Test 5: Testing Story and Epic Operations")
    try:
        if project.epics:
            epic = project.epics[0]
            print(f"✅ Testing epic: {epic.name}")
            
            # Start epic
            epic.start()
            print(f"   - Epic started: {epic.status.value}")
            
            if epic.stories:
                story = epic.stories[0]
                print(f"✅ Testing story: {story.name}")
                
                # Start story
                story.start()
                print(f"   - Story started: {story.status.value}")
                print(f"   - Story points: {story.story_points}")
                
                # Complete story
                story.complete()
                print(f"   - Story completed: {story.status.value}")
                
                # Check epic completion percentage
                print(f"   - Epic completion: {epic.completion_percentage:.1f}%")
        
    except Exception as e:
        print(f"❌ Error in Test 5: {e}")
        return False
    
    # Final save
    print("\n💾 Saving final state...")
    try:
        repo.save(project)
        print("✅ Project saved with all updates")
    except Exception as e:
        print(f"❌ Error saving final state: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Orchestration system is working correctly.")
    print(f"📁 Project data saved in: data/orchestration/")
    print(f"🆔 Test project ID: {project.id}")
    
    return True


def main():
    """Run the orchestration tests"""
    success = asyncio.run(test_orchestration_system())
    if success:
        print("\n✅ Orchestration implementation test completed successfully!")
        return 0
    else:
        print("\n❌ Orchestration implementation test failed!")
        return 1


if __name__ == "__main__":
    exit(main())