"""Event Bus implementation for the Zamaz Debate System.

This module provides a centralized event bus for publishing and subscribing to
domain events throughout the system.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import inspect
from functools import wraps

from ..domain.models import DomainEvent

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Priority levels for event handlers."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class EventHandler:
    """Wrapper for event handlers with metadata."""
    handler: Callable
    event_type: Type[DomainEvent]
    priority: EventPriority = EventPriority.NORMAL
    name: Optional[str] = None
    
    def __post_init__(self):
        if self.name is None:
            self.name = self.handler.__name__


class EventBus:
    """Centralized event bus for the Zamaz Debate System.
    
    Supports:
    - Type-safe event publishing and subscription
    - Async and sync handlers
    - Priority-based handler execution
    - Error handling and logging
    - Event history tracking
    """
    
    def __init__(self, max_history: int = 1000):
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}
        self._event_history: List[DomainEvent] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        
    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        name: Optional[str] = None
    ) -> None:
        """Subscribe a handler to an event type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The handler function (can be async or sync)
            priority: Priority for handler execution order
            name: Optional name for the handler
        """
        event_handler = EventHandler(
            handler=handler,
            event_type=event_type,
            priority=priority,
            name=name
        )
        
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            
        self._handlers[event_type].append(event_handler)
        
        # Sort handlers by priority (highest first)
        self._handlers[event_type].sort(
            key=lambda h: h.priority.value,
            reverse=True
        )
        
        logger.info(
            f"Subscribed handler '{event_handler.name}' to {event_type.__name__} "
            f"with priority {priority.name}"
        )
        
    def unsubscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable
    ) -> bool:
        """Unsubscribe a handler from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler function to remove
            
        Returns:
            True if handler was found and removed, False otherwise
        """
        if event_type not in self._handlers:
            return False
            
        handlers = self._handlers[event_type]
        initial_count = len(handlers)
        
        self._handlers[event_type] = [
            h for h in handlers if h.handler != handler
        ]
        
        removed = len(self._handlers[event_type]) < initial_count
        
        if removed:
            logger.info(f"Unsubscribed handler from {event_type.__name__}")
            
        # Clean up empty handler lists
        if not self._handlers[event_type]:
            del self._handlers[event_type]
            
        return removed
        
    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribed handlers.
        
        Args:
            event: The event to publish
        """
        async with self._lock:
            # Add to history
            self._event_history.append(event)
            
            # Trim history if needed
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
                
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            logger.debug(f"No handlers for event type {event_type.__name__}")
            return
            
        logger.info(
            f"Publishing {event_type.__name__} to {len(handlers)} handler(s)"
        )
        
        # Execute handlers concurrently by priority group
        for priority in EventPriority:
            priority_handlers = [
                h for h in handlers if h.priority == priority
            ]
            
            if priority_handlers:
                await self._execute_handlers(priority_handlers, event)
                
    async def _execute_handlers(
        self,
        handlers: List[EventHandler],
        event: DomainEvent
    ) -> None:
        """Execute a group of handlers concurrently.
        
        Args:
            handlers: List of handlers to execute
            event: The event to pass to handlers
        """
        tasks = []
        
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler.handler):
                    task = handler.handler(event)
                else:
                    # Wrap sync handlers to run in executor
                    task = asyncio.get_event_loop().run_in_executor(
                        None,
                        handler.handler,
                        event
                    )
                    
                tasks.append(
                    self._handle_with_logging(handler, task)
                )
            except Exception as e:
                logger.error(
                    f"Error preparing handler '{handler.name}': {e}",
                    exc_info=True
                )
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def _handle_with_logging(
        self,
        handler: EventHandler,
        task: asyncio.Task
    ) -> None:
        """Execute a handler task with error logging.
        
        Args:
            handler: The handler metadata
            task: The task to execute
        """
        try:
            await task
        except Exception as e:
            logger.error(
                f"Error in handler '{handler.name}' for "
                f"{handler.event_type.__name__}: {e}",
                exc_info=True
            )
            
    def get_handlers(
        self,
        event_type: Type[DomainEvent]
    ) -> List[EventHandler]:
        """Get all handlers for an event type.
        
        Args:
            event_type: The event type to query
            
        Returns:
            List of handlers subscribed to the event type
        """
        return self._handlers.get(event_type, []).copy()
        
    def get_event_history(
        self,
        event_type: Optional[Type[DomainEvent]] = None,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Get event history, optionally filtered by type.
        
        Args:
            event_type: Optional event type to filter by
            limit: Optional limit on number of events to return
            
        Returns:
            List of historical events
        """
        history = self._event_history.copy()
        
        if event_type:
            history = [e for e in history if isinstance(e, event_type)]
            
        if limit:
            history = history[-limit:]
            
        return history
        
    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
        
    def clear_handlers(
        self,
        event_type: Optional[Type[DomainEvent]] = None
    ) -> None:
        """Clear handlers, optionally for a specific event type.
        
        Args:
            event_type: Optional event type to clear handlers for.
                       If None, clears all handlers.
        """
        if event_type:
            if event_type in self._handlers:
                del self._handlers[event_type]
                logger.info(f"Cleared handlers for {event_type.__name__}")
        else:
            self._handlers.clear()
            logger.info("Cleared all event handlers")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance.
    
    Returns:
        The global EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def subscribe(
    event_type: Type[DomainEvent],
    priority: EventPriority = EventPriority.NORMAL,
    name: Optional[str] = None
):
    """Decorator to subscribe a function as an event handler.
    
    Args:
        event_type: The type of event to subscribe to
        priority: Priority for handler execution order
        name: Optional name for the handler
        
    Example:
        @subscribe(DecisionCreatedEvent)
        async def on_decision_created(event: DecisionCreatedEvent):
            print(f"Decision created: {event.decision.question}")
    """
    def decorator(func: Callable) -> Callable:
        get_event_bus().subscribe(
            event_type=event_type,
            handler=func,
            priority=priority,
            name=name or func.__name__
        )
        return func
        
    return decorator


async def publish(event: DomainEvent) -> None:
    """Publish an event to the global event bus.
    
    Args:
        event: The event to publish
    """
    await get_event_bus().publish(event)