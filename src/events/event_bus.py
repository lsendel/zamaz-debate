"""
Event Bus Implementation

This module implements an asynchronous event bus for domain event distribution.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, Optional, Set

from src.events.domain_event import DomainEvent

logger = logging.getLogger(__name__)


class EventBus:
    """
    Asynchronous event bus for publishing and subscribing to domain events

    This implementation uses asyncio queues for event distribution and supports
    multiple subscribers per event type.
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the event bus

        Args:
            max_queue_size: Maximum number of events that can be queued
        """
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers: Dict[str, Set[Callable]] = defaultdict(set)
        self._running: bool = False
        self._processor_task: Optional[asyncio.Task] = None
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "subscribers_count": 0,
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
            self._stats["events_published"] += 1
            logger.debug(f"Published event: {event.event_type} (ID: {event.event_id})")
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            raise

    async def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """
        Subscribe to events of a specific type

        Args:
            event_type: The type of events to subscribe to
            handler: The handler function to call when events are received
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()

        self._subscribers[event_type].add(handler)
        self._stats["subscribers_count"] = sum(len(handlers) for handlers in self._subscribers.values())

        logger.debug(f"Subscribed to {event_type} events")

    async def unsubscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """
        Unsubscribe from events of a specific type

        Args:
            event_type: The type of events to unsubscribe from
            handler: The handler function to unsubscribe
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(handler)

            # Clean up empty sets
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

        self._stats["subscribers_count"] = sum(len(handlers) for handlers in self._subscribers.values())
        logger.debug(f"Unsubscribed from {event_type} events")

    async def start(self) -> None:
        """Start the event bus"""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop the event bus"""
        if not self._running:
            return

        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Event bus stopped")

    async def _process_events(self) -> None:
        """Process events from the queue"""
        while self._running:
            try:
                # Wait for an event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
                self._stats["events_processed"] += 1

            except asyncio.TimeoutError:
                # No event received, continue
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self._stats["events_failed"] += 1

    async def _handle_event(self, event: DomainEvent) -> None:
        """Handle a single event by notifying all subscribers"""
        event_type = event.event_type

        if event_type not in self._subscribers:
            logger.debug(f"No subscribers for event type: {event_type}")
            return

        handlers = self._subscribers[event_type].copy()  # Copy to avoid modification during iteration

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)

            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
                self._stats["events_failed"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            **self._stats,
            "queue_size": self._event_queue.qsize(),
            "is_running": self._running,
            "subscriber_types": list(self._subscribers.keys()),
        }

    def clear_stats(self) -> None:
        """Clear event bus statistics"""
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "subscribers_count": len(self._subscribers),
        }


class EventBusError(Exception):
    """Exception raised by event bus operations"""

    pass


class EventPublishError(EventBusError):
    """Exception raised when event publishing fails"""

    pass


class EventSubscriptionError(EventBusError):
    """Exception raised when event subscription fails"""

    pass
