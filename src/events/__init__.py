"""
Domain Events Infrastructure

This package provides the infrastructure for domain events across all bounded contexts.
It includes the event bus, event handlers, and event storage mechanisms.
"""

from .domain_event import DomainEvent, EventMetadata
from .event_bus import EventBus, InMemoryEventBus
from .event_handler import EventHandler, EventHandlerRegistry
from .event_store import EventStore, InMemoryEventStore

__all__ = [
    "EventBus",
    "InMemoryEventBus",
    "EventHandler",
    "EventHandlerRegistry",
    "EventStore",
    "InMemoryEventStore",
    "DomainEvent",
    "EventMetadata",
]
