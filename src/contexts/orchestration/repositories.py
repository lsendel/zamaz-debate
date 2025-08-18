"""
Orchestration Context Repository Interfaces

Repository interfaces for the orchestration bounded context.
These define contracts for persisting and retrieving orchestration aggregates.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .aggregates import Project, Epic, Story


class ProjectRepository(ABC):
    """Repository interface for Project aggregates"""

    @abstractmethod
    def save(self, project: Project) -> None:
        """Save a project"""
        pass

    @abstractmethod
    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        """Get a project by ID"""
        pass

    @abstractmethod
    def list_all(self) -> List[Project]:
        """List all projects"""
        pass

    @abstractmethod
    def list_by_status(self, status: str) -> List[Project]:
        """List projects by status"""
        pass

    @abstractmethod
    def list_by_priority(self, priority: str) -> List[Project]:
        """List projects by priority"""
        pass

    @abstractmethod
    def search_by_name(self, name_pattern: str) -> List[Project]:
        """Search projects by name pattern"""
        pass

    @abstractmethod
    def delete(self, project_id: UUID) -> None:
        """Delete a project"""
        pass


class EpicRepository(ABC):
    """Repository interface for Epic entities"""

    @abstractmethod
    def save(self, epic: Epic) -> None:
        """Save an epic"""
        pass

    @abstractmethod
    def get_by_id(self, epic_id: UUID) -> Optional[Epic]:
        """Get an epic by ID"""
        pass

    @abstractmethod
    def list_by_project(self, project_id: UUID) -> List[Epic]:
        """List epics for a project"""
        pass

    @abstractmethod
    def list_by_status(self, status: str) -> List[Epic]:
        """List epics by status"""
        pass

    @abstractmethod
    def list_blocked(self) -> List[Epic]:
        """List all blocked epics"""
        pass

    @abstractmethod
    def delete(self, epic_id: UUID) -> None:
        """Delete an epic"""
        pass


class StoryRepository(ABC):
    """Repository interface for Story entities"""

    @abstractmethod
    def save(self, story: Story) -> None:
        """Save a story"""
        pass

    @abstractmethod
    def get_by_id(self, story_id: UUID) -> Optional[Story]:
        """Get a story by ID"""
        pass

    @abstractmethod
    def list_by_epic(self, epic_id: UUID) -> List[Story]:
        """List stories for an epic"""
        pass

    @abstractmethod
    def list_by_assignee(self, assignee: str) -> List[Story]:
        """List stories assigned to someone"""
        pass

    @abstractmethod
    def list_by_status(self, status: str) -> List[Story]:
        """List stories by status"""
        pass

    @abstractmethod
    def list_ready_for_implementation(self) -> List[Story]:
        """List stories ready for implementation (no blocking dependencies)"""
        pass

    @abstractmethod
    def delete(self, story_id: UUID) -> None:
        """Delete a story"""
        pass