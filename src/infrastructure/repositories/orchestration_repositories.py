"""
Orchestration Context Repository Implementations

Concrete implementations of orchestration repositories using JSON storage.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.contexts.orchestration.aggregates import Project, Epic, Story
from src.contexts.orchestration.repositories import (
    ProjectRepository,
    EpicRepository,
    StoryRepository,
)
from src.contexts.orchestration.value_objects import WorkItemStatus, Priority
from .base import JsonRepository


class JsonProjectRepository(ProjectRepository, JsonRepository):
    """JSON-based repository for Project aggregates"""

    def __init__(self, storage_path: str = "data/orchestration"):
        super().__init__(storage_path, "project")

    def save(self, project: Project) -> None:
        """Save a project"""
        file_path = self._get_file_path(project.id)
        data = self._serialize(project)
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        # Update index
        self._update_index_sync(project.id, data)

    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        """Get a project by ID"""
        file_path = self._get_file_path(project_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            return self._deserialize_project(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading project {project_id}: {e}")
            return None

    def list_all(self) -> List[Project]:
        """List all projects"""
        projects = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                project = self._deserialize_project(data)
                projects.append(project)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error loading project from {file_path}: {e}")
                continue
        
        return projects

    def list_by_status(self, status: str) -> List[Project]:
        """List projects by status"""
        return [p for p in self.list_all() if p.status.value == status]

    def list_by_priority(self, priority: str) -> List[Project]:
        """List projects by priority"""
        return [p for p in self.list_all() if p.priority.value == priority]

    def search_by_name(self, name_pattern: str) -> List[Project]:
        """Search projects by name pattern"""
        pattern_lower = name_pattern.lower()
        return [p for p in self.list_all() if pattern_lower in p.name.lower()]

    def delete(self, project_id: UUID) -> None:
        """Delete a project"""
        file_path = self._get_file_path(project_id)
        
        if file_path.exists():
            file_path.unlink()
            self._remove_from_index_sync(project_id)

    def _deserialize_project(self, data: Dict[str, Any]) -> Project:
        """Deserialize project data"""
        # Convert string UUIDs back to UUID objects
        if isinstance(data["id"], str):
            data["id"] = UUID(data["id"])
        
        # Convert datetime strings back to datetime objects
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("start_date") and isinstance(data["start_date"], str):
            data["start_date"] = datetime.fromisoformat(data["start_date"])
        if data.get("target_completion_date") and isinstance(data["target_completion_date"], str):
            data["target_completion_date"] = datetime.fromisoformat(data["target_completion_date"])
        if data.get("actual_completion_date") and isinstance(data["actual_completion_date"], str):
            data["actual_completion_date"] = datetime.fromisoformat(data["actual_completion_date"])
        
        # Convert enum strings back to enums
        if isinstance(data["status"], str):
            data["status"] = WorkItemStatus(data["status"])
        if isinstance(data["priority"], str):
            data["priority"] = Priority(data["priority"])
        
        # Handle nested objects (epics, orchestration_plan, etc.)
        if "epics" in data:
            data["epics"] = [self._deserialize_epic(epic_data) for epic_data in data["epics"]]
        else:
            data["epics"] = []
        
        if "orchestration_plan" in data and data["orchestration_plan"]:
            # Simplified orchestration plan deserialization
            data["orchestration_plan"] = None  # Would need proper deserialization
        
        # Handle lists that might be missing
        data.setdefault("success_criteria", [])
        data.setdefault("stakeholders", [])
        
        # Remove private attributes if present
        data = {k: v for k, v in data.items() if not k.startswith("_")}
        
        return Project(**data)

    def _deserialize_epic(self, data: Dict[str, Any]) -> Epic:
        """Deserialize epic data"""
        # Convert string UUIDs back to UUID objects
        if isinstance(data["id"], str):
            data["id"] = UUID(data["id"])
        if isinstance(data["project_id"], str):
            data["project_id"] = UUID(data["project_id"])
        
        # Convert datetime strings back to datetime objects
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("started_at") and isinstance(data["started_at"], str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        
        # Convert enum strings back to enums
        if isinstance(data["status"], str):
            data["status"] = WorkItemStatus(data["status"])
        if isinstance(data["priority"], str):
            data["priority"] = Priority(data["priority"])
        
        # Handle nested objects
        if "stories" in data:
            data["stories"] = [self._deserialize_story(story_data) for story_data in data["stories"]]
        else:
            data["stories"] = []
        
        # Handle lists that might be missing
        data.setdefault("acceptance_criteria", [])
        data.setdefault("dependencies", [])
        data.setdefault("quality_gates", [])
        
        # Remove private attributes if present
        data = {k: v for k, v in data.items() if not k.startswith("_")}
        
        return Epic(**data)

    def _deserialize_story(self, data: Dict[str, Any]) -> Story:
        """Deserialize story data"""
        # Convert string UUIDs back to UUID objects
        if isinstance(data["id"], str):
            data["id"] = UUID(data["id"])
        if isinstance(data["epic_id"], str):
            data["epic_id"] = UUID(data["epic_id"])
        
        # Convert datetime strings back to datetime objects
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("started_at") and isinstance(data["started_at"], str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        
        # Convert enum strings back to enums
        if isinstance(data["status"], str):
            data["status"] = WorkItemStatus(data["status"])
        if isinstance(data["priority"], str):
            data["priority"] = Priority(data["priority"])
        
        # Handle lists that might be missing
        data.setdefault("acceptance_criteria", [])
        data.setdefault("dependencies", [])
        data.setdefault("generated_task_ids", [])
        data.setdefault("quality_gates", [])
        
        # Convert generated_task_ids from strings to UUIDs
        if "generated_task_ids" in data:
            data["generated_task_ids"] = [UUID(task_id) if isinstance(task_id, str) else task_id 
                                         for task_id in data["generated_task_ids"]]
        
        # Remove private attributes if present
        data = {k: v for k, v in data.items() if not k.startswith("_")}
        
        return Story(**data)

    def _update_index_sync(self, entity_id: UUID, data: Dict[str, Any]) -> None:
        """Synchronous version of index update"""
        index = self._load_index_sync()
        
        # Store basic info in index for faster queries
        index[str(entity_id)] = {
            "id": str(entity_id),
            "updated_at": datetime.now().isoformat(),
            "name": data.get("name", ""),
            "status": data.get("status", ""),
            "priority": data.get("priority", ""),
            "project_manager": data.get("project_manager", ""),
        }
        
        self._save_index_sync(index)

    def _remove_from_index_sync(self, entity_id: UUID) -> None:
        """Synchronous version of index removal"""
        index = self._load_index_sync()
        index.pop(str(entity_id), None)
        self._save_index_sync(index)

    def _load_index_sync(self) -> Dict[str, Any]:
        """Synchronous version of index loading"""
        index_path = self._get_index_file_path()
        
        if not index_path.exists():
            return {}
        
        with open(index_path, "r") as f:
            return json.load(f)

    def _save_index_sync(self, index: Dict[str, Any]) -> None:
        """Synchronous version of index saving"""
        index_path = self._get_index_file_path()
        
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)


class JsonEpicRepository(EpicRepository, JsonRepository):
    """JSON-based repository for Epic entities"""

    def __init__(self, storage_path: str = "data/orchestration"):
        super().__init__(storage_path, "epic")

    def save(self, epic: Epic) -> None:
        """Save an epic"""
        file_path = self._get_file_path(epic.id)
        data = self._serialize(epic)
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_by_id(self, epic_id: UUID) -> Optional[Epic]:
        """Get an epic by ID"""
        file_path = self._get_file_path(epic_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            return self._deserialize_epic(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading epic {epic_id}: {e}")
            return None

    def list_by_project(self, project_id: UUID) -> List[Epic]:
        """List epics for a project"""
        epics = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                if data.get("project_id") == str(project_id):
                    epic = self._deserialize_epic(data)
                    epics.append(epic)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        return epics

    def list_by_status(self, status: str) -> List[Epic]:
        """List epics by status"""
        epics = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                if data.get("status") == status:
                    epic = self._deserialize_epic(data)
                    epics.append(epic)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        return epics

    def list_blocked(self) -> List[Epic]:
        """List all blocked epics"""
        return self.list_by_status("blocked")

    def delete(self, epic_id: UUID) -> None:
        """Delete an epic"""
        file_path = self._get_file_path(epic_id)
        
        if file_path.exists():
            file_path.unlink()

    def _deserialize_epic(self, data: Dict[str, Any]) -> Epic:
        """Deserialize epic data - reuse from project repository"""
        project_repo = JsonProjectRepository()
        return project_repo._deserialize_epic(data)


class JsonStoryRepository(StoryRepository, JsonRepository):
    """JSON-based repository for Story entities"""

    def __init__(self, storage_path: str = "data/orchestration"):
        super().__init__(storage_path, "story")

    def save(self, story: Story) -> None:
        """Save a story"""
        file_path = self._get_file_path(story.id)
        data = self._serialize(story)
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_by_id(self, story_id: UUID) -> Optional[Story]:
        """Get a story by ID"""
        file_path = self._get_file_path(story_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            return self._deserialize_story(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading story {story_id}: {e}")
            return None

    def list_by_epic(self, epic_id: UUID) -> List[Story]:
        """List stories for an epic"""
        stories = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                if data.get("epic_id") == str(epic_id):
                    story = self._deserialize_story(data)
                    stories.append(story)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        return stories

    def list_by_assignee(self, assignee: str) -> List[Story]:
        """List stories assigned to someone"""
        stories = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                if data.get("assignee") == assignee:
                    story = self._deserialize_story(data)
                    stories.append(story)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        return stories

    def list_by_status(self, status: str) -> List[Story]:
        """List stories by status"""
        stories = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                if data.get("status") == status:
                    story = self._deserialize_story(data)
                    stories.append(story)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        return stories

    def list_ready_for_implementation(self) -> List[Story]:
        """List stories ready for implementation (no blocking dependencies)"""
        # For now, return stories that are planned and have no dependencies
        all_stories = []
        
        for file_path in self.storage_path.glob(f"{self.entity_name}_*.json"):
            if file_path.name == f"{self.entity_name}_index.json":
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                if (data.get("status") == "planned" and 
                    (not data.get("dependencies") or len(data.get("dependencies", [])) == 0)):
                    story = self._deserialize_story(data)
                    all_stories.append(story)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        return all_stories

    def delete(self, story_id: UUID) -> None:
        """Delete a story"""
        file_path = self._get_file_path(story_id)
        
        if file_path.exists():
            file_path.unlink()

    def _deserialize_story(self, data: Dict[str, Any]) -> Story:
        """Deserialize story data - reuse from project repository"""
        project_repo = JsonProjectRepository()
        return project_repo._deserialize_story(data)