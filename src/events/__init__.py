"""
Domain Events Infrastructure

This package provides the infrastructure for domain events across all bounded contexts.
It includes the event bus, event handlers, and event storage mechanisms.
"""

from .domain_event import DomainEvent
from .event_bus import EventBus

__all__ = [
    "EventBus",
    "DomainEvent",
]
