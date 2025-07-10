"""
Domain Events Infrastructure

This package provides the infrastructure for domain events across all bounded contexts.
It includes the event bus, event handlers, and event storage mechanisms.
"""

from .domain_event import DomainEvent
from .event_bus import EventBus, get_event_bus, publish, publish_sync, subscribe
from .cross_context_handlers import initialize_cross_context_handlers

__all__ = [
    "DomainEvent",
    "EventBus",
    "get_event_bus",
    "publish",
    "publish_sync",
    "subscribe",
    "initialize_cross_context_handlers",
]
