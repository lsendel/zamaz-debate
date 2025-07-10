"""
Domain Event Base Classes

This module provides the base classes and interfaces for domain events.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """
    Base class for all domain events
    
    This is a simplified base class that provides common fields for all domain events.
    Each bounded context extends this with their specific event data.
    """
    
    event_id: UUID
    occurred_at: datetime
    event_type: str
    aggregate_id: UUID
    version: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.event_type,
            "aggregate_id": str(self.aggregate_id),
            "version": self.version,
        }


class EventSerializationError(Exception):
    """Exception raised when event serialization fails"""
    pass


class EventDeserializationError(Exception):
    """Exception raised when event deserialization fails"""
    pass
