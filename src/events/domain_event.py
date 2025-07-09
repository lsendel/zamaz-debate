"""
Domain Event Base Classes

This module provides the base classes and interfaces for domain events.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class EventMetadata:
    """Metadata for domain events"""

    event_id: UUID
    occurred_at: datetime
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    user_id: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "user_id": self.user_id,
            "source": self.source,
        }


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    Base class for all domain events

    All domain events must inherit from this class and implement the required methods.
    """

    metadata: EventMetadata = field(default_factory=lambda: EventMetadata(event_id=uuid4(), occurred_at=datetime.now()))

    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the event type identifier"""
        pass

    @property
    @abstractmethod
    def aggregate_id(self) -> UUID:
        """Return the ID of the aggregate that produced this event"""
        pass

    @property
    @abstractmethod
    def aggregate_type(self) -> str:
        """Return the type of the aggregate that produced this event"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Create event from dictionary"""
        pass

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "DomainEvent":
        """Create event from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @property
    def event_id(self) -> UUID:
        """Get the event ID"""
        return self.metadata.event_id

    @property
    def occurred_at(self) -> datetime:
        """Get the event occurrence time"""
        return self.metadata.occurred_at

    @property
    def correlation_id(self) -> Optional[UUID]:
        """Get the correlation ID"""
        return self.metadata.correlation_id

    @property
    def causation_id(self) -> Optional[UUID]:
        """Get the causation ID"""
        return self.metadata.causation_id


class EventSerializationError(Exception):
    """Exception raised when event serialization fails"""

    pass


class EventDeserializationError(Exception):
    """Exception raised when event deserialization fails"""

    pass
