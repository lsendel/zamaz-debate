"""
Event Bus Infrastructure

This module provides the event bus for publishing and subscribing to domain events.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Set
from asyncio import Queue
import asyncio
import logging
from datetime import datetime
from uuid import UUID

from .domain_event import DomainEvent


logger = logging.getLogger(__name__)


class EventBus(ABC):
    """
    Abstract base class for event buses
    """
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to the bus
        
        Args:
            event: The domain event to publish
        """
        pass
    
    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """
        Subscribe to events of a specific type
        
        Args:
            event_type: The type of events to subscribe to
            handler: The handler function to call when events are received
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """
        Unsubscribe from events of a specific type
        
        Args:
            event_type: The type of events to unsubscribe from
            handler: The handler function to unsubscribe
        """
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the event bus"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus"""
        pass


class InMemoryEventBus(EventBus):
    """
    In-memory implementation of the event bus
    
    This implementation is suitable for development and testing.
    For production, consider using a message broker like RabbitMQ or Apache Kafka.
    """
    
    def __init__(self, max_queue_size: int = 1000):
        self._subscribers: Dict[str, Set[Callable[[DomainEvent], None]]] = {}
        self._event_queue: Queue = Queue(maxsize=max_queue_size)
        self._running = False
        self._processor_task = None
        self._stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'subscribers_count': 0
        }
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to the bus
        
        Args:
            event: The domain event to publish
        """
        if not self._running:
            raise RuntimeError("Event bus is not running")
        
        try:
            await self._event_queue.put(event)
            self._stats['events_published'] += 1
            logger.debug(f\"Published event: {event.event_type} (ID: {event.event_id})\")\n        except Exception as e:\n            logger.error(f\"Failed to publish event {event.event_type}: {e}\")\n            raise\n    \n    async def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:\n        \"\"\"\n        Subscribe to events of a specific type\n        \n        Args:\n            event_type: The type of events to subscribe to\n            handler: The handler function to call when events are received\n        \"\"\"\n        if event_type not in self._subscribers:\n            self._subscribers[event_type] = set()\n        \n        self._subscribers[event_type].add(handler)\n        self._stats['subscribers_count'] = sum(len(handlers) for handlers in self._subscribers.values())\n        \n        logger.debug(f\"Subscribed to {event_type} events\")\n    \n    async def unsubscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:\n        \"\"\"\n        Unsubscribe from events of a specific type\n        \n        Args:\n            event_type: The type of events to unsubscribe from\n            handler: The handler function to unsubscribe\n        \"\"\"\n        if event_type in self._subscribers:\n            self._subscribers[event_type].discard(handler)\n            \n            # Clean up empty sets\n            if not self._subscribers[event_type]:\n                del self._subscribers[event_type]\n        \n        self._stats['subscribers_count'] = sum(len(handlers) for handlers in self._subscribers.values())\n        logger.debug(f\"Unsubscribed from {event_type} events\")\n    \n    async def start(self) -> None:\n        \"\"\"Start the event bus\"\"\"\n        if self._running:\n            return\n        \n        self._running = True\n        self._processor_task = asyncio.create_task(self._process_events())\n        logger.info(\"Event bus started\")\n    \n    async def stop(self) -> None:\n        \"\"\"Stop the event bus\"\"\"\n        if not self._running:\n            return\n        \n        self._running = False\n        \n        if self._processor_task:\n            self._processor_task.cancel()\n            try:\n                await self._processor_task\n            except asyncio.CancelledError:\n                pass\n        \n        logger.info(\"Event bus stopped\")\n    \n    async def _process_events(self) -> None:\n        \"\"\"Process events from the queue\"\"\"\n        while self._running:\n            try:\n                # Wait for an event with timeout\n                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)\n                await self._handle_event(event)\n                self._stats['events_processed'] += 1\n                \n            except asyncio.TimeoutError:\n                # No event received, continue\n                continue\n            except Exception as e:\n                logger.error(f\"Error processing event: {e}\")\n                self._stats['events_failed'] += 1\n    \n    async def _handle_event(self, event: DomainEvent) -> None:\n        \"\"\"Handle a single event by notifying all subscribers\"\"\"\n        event_type = event.event_type\n        \n        if event_type not in self._subscribers:\n            logger.debug(f\"No subscribers for event type: {event_type}\")\n            return\n        \n        handlers = self._subscribers[event_type].copy()  # Copy to avoid modification during iteration\n        \n        for handler in handlers:\n            try:\n                if asyncio.iscoroutinefunction(handler):\n                    await handler(event)\n                else:\n                    handler(event)\n                    \n            except Exception as e:\n                logger.error(f\"Error in event handler for {event_type}: {e}\")\n                self._stats['events_failed'] += 1\n    \n    def get_stats(self) -> Dict[str, Any]:\n        \"\"\"Get event bus statistics\"\"\"\n        return {\n            **self._stats,\n            'queue_size': self._event_queue.qsize(),\n            'is_running': self._running,\n            'subscriber_types': list(self._subscribers.keys())\n        }\n    \n    def clear_stats(self) -> None:\n        \"\"\"Clear event bus statistics\"\"\"\n        self._stats = {\n            'events_published': 0,\n            'events_processed': 0,\n            'events_failed': 0,\n            'subscribers_count': len(self._subscribers)\n        }\n\n\nclass EventBusError(Exception):\n    \"\"\"Exception raised by event bus operations\"\"\"\n    pass\n\n\nclass EventPublishError(EventBusError):\n    \"\"\"Exception raised when event publishing fails\"\"\"\n    pass\n\n\nclass EventSubscriptionError(EventBusError):\n    \"\"\"Exception raised when event subscription fails\"\"\"\n    pass"