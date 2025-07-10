"""
Integration tests for the Event Bus infrastructure.

Tests event publishing, subscription, and cross-context communication.
"""

import asyncio
import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.events import (
    DomainEvent,
    EventBus,
    get_event_bus,
    publish,
    subscribe,
)


class TestEvent(DomainEvent):
    """Test event for integration tests"""
    
    def __init__(self, message: str):
        super().__init__(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TestEvent",
            aggregate_id=uuid4(),
            version=1,
        )
        self.message = message


class AnotherTestEvent(DomainEvent):
    """Another test event type"""
    
    def __init__(self, value: int):
        super().__init__(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="AnotherTestEvent",
            aggregate_id=uuid4(),
            version=1,
        )
        self.value = value


@pytest.fixture
def event_bus():
    """Create a fresh event bus for testing"""
    bus = EventBus(record_events=True)
    yield bus
    bus.clear_history()


@pytest.fixture
def clean_global_bus():
    """Clean the global event bus before and after tests"""
    bus = get_event_bus(record_events=True)
    bus.clear_history()
    # Clear all handlers
    bus._handlers.clear()
    bus._context_handlers.clear()
    yield bus
    bus.clear_history()
    bus._handlers.clear()
    bus._context_handlers.clear()


class TestEventBusBasics:
    """Test basic event bus functionality"""
    
    @pytest.mark.asyncio
    async def test_publish_subscribe(self, event_bus):
        """Test basic publish/subscribe functionality"""
        received_events = []
        
        async def handler(event: TestEvent):
            received_events.append(event)
        
        # Subscribe handler
        event_bus.subscribe(TestEvent, handler, "test_context")
        
        # Publish event
        test_event = TestEvent("Hello, World!")
        await event_bus.publish(test_event)
        
        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].message == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_bus):
        """Test multiple handlers for same event"""
        handler1_events = []
        handler2_events = []
        
        async def handler1(event: TestEvent):
            handler1_events.append(event)
        
        async def handler2(event: TestEvent):
            handler2_events.append(event)
        
        # Subscribe both handlers
        event_bus.subscribe(TestEvent, handler1, "context1")
        event_bus.subscribe(TestEvent, handler2, "context2")
        
        # Publish event
        test_event = TestEvent("Broadcast")
        await event_bus.publish(test_event)
        
        # Both handlers should receive the event
        assert len(handler1_events) == 1
        assert len(handler2_events) == 1
        assert handler1_events[0].message == "Broadcast"
        assert handler2_events[0].message == "Broadcast"
    
    @pytest.mark.asyncio
    async def test_handler_priority(self, event_bus):
        """Test handler execution order by priority"""
        execution_order = []
        
        async def low_priority_handler(event: TestEvent):
            execution_order.append("low")
        
        async def high_priority_handler(event: TestEvent):
            execution_order.append("high")
        
        async def normal_priority_handler(event: TestEvent):
            execution_order.append("normal")
        
        # Subscribe with different priorities
        event_bus.subscribe(TestEvent, low_priority_handler, "context1", priority=-1)
        event_bus.subscribe(TestEvent, high_priority_handler, "context2", priority=10)
        event_bus.subscribe(TestEvent, normal_priority_handler, "context3", priority=0)
        
        # Publish event
        await event_bus.publish(TestEvent("Priority test"))
        
        # Check execution order (high -> normal -> low)
        assert execution_order == ["high", "normal", "low"]
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """Test unsubscribing handlers"""
        received_events = []
        
        async def handler(event: TestEvent):
            received_events.append(event)
        
        # Subscribe and publish
        event_bus.subscribe(TestEvent, handler, "test_context")
        await event_bus.publish(TestEvent("First"))
        assert len(received_events) == 1
        
        # Unsubscribe and publish again
        event_bus.unsubscribe(TestEvent, handler, "test_context")
        await event_bus.publish(TestEvent("Second"))
        assert len(received_events) == 1  # Should not receive second event
    
    @pytest.mark.asyncio
    async def test_event_history(self, event_bus):
        """Test event history recording"""
        # Publish several events
        event1 = TestEvent("First")
        event2 = TestEvent("Second")
        event3 = AnotherTestEvent(42)
        
        await event_bus.publish(event1)
        await event_bus.publish(event2)
        await event_bus.publish(event3)
        
        # Check history
        history = event_bus.get_event_history()
        assert len(history) == 3
        assert history[0].message == "First"
        assert history[1].message == "Second"
        assert history[2].value == 42
    
    @pytest.mark.asyncio
    async def test_sync_handler(self, event_bus):
        """Test synchronous event handlers"""
        received_events = []
        
        def sync_handler(event: TestEvent):
            received_events.append(event)
        
        # Subscribe sync handler
        event_bus.subscribe(TestEvent, sync_handler, "test_context")
        
        # Publish event
        await event_bus.publish(TestEvent("Sync test"))
        
        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].message == "Sync test"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, event_bus):
        """Test error handling in event handlers"""
        successful_events = []
        
        async def failing_handler(event: TestEvent):
            raise ValueError("Handler error")
        
        async def successful_handler(event: TestEvent):
            successful_events.append(event)
        
        # Subscribe both handlers
        event_bus.subscribe(TestEvent, failing_handler, "context1")
        event_bus.subscribe(TestEvent, successful_handler, "context2")
        
        # Publish event
        await event_bus.publish(TestEvent("Error test"))
        
        # Successful handler should still execute
        assert len(successful_events) == 1
        
        # Check failed events
        failed = event_bus.get_failed_events()
        assert len(failed) == 1
        assert "Handler error" in failed[0]["error"]
    
    def test_sync_publish(self, event_bus):
        """Test synchronous event publishing"""
        received_events = []
        
        def handler(event: TestEvent):
            received_events.append(event)
        
        # Subscribe handler
        event_bus.subscribe(TestEvent, handler, "test_context")
        
        # Publish synchronously
        event_bus.publish_sync(TestEvent("Sync publish"))
        
        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].message == "Sync publish"


class TestGlobalEventBus:
    """Test global event bus functionality"""
    
    @pytest.mark.asyncio
    async def test_decorator_subscription(self, clean_global_bus):
        """Test @subscribe decorator"""
        received_events = []
        
        @subscribe(TestEvent, context="test_context")
        async def decorated_handler(event: TestEvent):
            received_events.append(event)
        
        # Publish event
        await publish(TestEvent("Decorator test"))
        
        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].message == "Decorator test"
    
    @pytest.mark.asyncio
    async def test_global_publish(self, clean_global_bus):
        """Test global publish function"""
        received_events = []
        
        # Subscribe using global bus
        bus = get_event_bus()
        
        async def handler(event: TestEvent):
            received_events.append(event)
        
        bus.subscribe(TestEvent, handler, "test_context")
        
        # Publish using global function
        await publish(TestEvent("Global publish"))
        
        # Verify
        assert len(received_events) == 1
        assert received_events[0].message == "Global publish"
    
    @pytest.mark.asyncio
    async def test_event_metrics(self, clean_global_bus):
        """Test event metrics collection"""
        bus = get_event_bus()
        
        # Publish various events
        await publish(TestEvent("First"))
        await publish(TestEvent("Second"))
        await publish(AnotherTestEvent(100))
        await publish(AnotherTestEvent(200))
        await publish(AnotherTestEvent(300))
        
        # Check metrics
        metrics = bus.get_event_metrics()
        assert metrics["TestEvent"] == 2
        assert metrics["AnotherTestEvent"] == 3


class TestEventReplay:
    """Test event replay functionality"""
    
    @pytest.mark.asyncio
    async def test_replay_events(self, event_bus):
        """Test replaying historical events"""
        replayed_events = []
        
        async def replay_handler(event: TestEvent):
            replayed_events.append(event)
        
        # Create historical events
        events = [
            TestEvent("Event 1"),
            TestEvent("Event 2"),
            TestEvent("Event 3"),
        ]
        
        # Subscribe handler
        event_bus.subscribe(TestEvent, replay_handler, "replay_context")
        
        # Replay events
        event_bus.replay_events(events)
        
        # Wait for async handlers to complete
        await asyncio.sleep(0.1)
        
        # Verify all events were replayed
        assert len(replayed_events) == 3
        assert [e.message for e in replayed_events] == ["Event 1", "Event 2", "Event 3"]
    
    @pytest.mark.asyncio
    async def test_filtered_replay(self, event_bus):
        """Test replaying events to specific context"""
        context1_events = []
        context2_events = []
        
        async def handler1(event: TestEvent):
            context1_events.append(event)
        
        async def handler2(event: TestEvent):
            context2_events.append(event)
        
        # Subscribe handlers from different contexts
        event_bus.subscribe(TestEvent, handler1, "context1")
        event_bus.subscribe(TestEvent, handler2, "context2")
        
        # Create events
        events = [TestEvent("Replay 1"), TestEvent("Replay 2")]
        
        # Replay only to context1
        event_bus.replay_events(events, filter_context="context1")
        
        # Wait for async handlers
        await asyncio.sleep(0.1)
        
        # Only context1 should receive events
        assert len(context1_events) == 2
        assert len(context2_events) == 0


class TestCrossContextIntegration:
    """Test cross-context communication patterns"""
    
    @pytest.mark.asyncio
    async def test_event_chain(self, clean_global_bus):
        """Test event chain across contexts"""
        execution_chain = []
        
        @subscribe(TestEvent, context="context1", priority=10)
        async def initial_handler(event: TestEvent):
            execution_chain.append(f"context1: {event.message}")
            # Trigger another event
            await publish(AnotherTestEvent(42))
        
        @subscribe(AnotherTestEvent, context="context2", priority=5)
        async def secondary_handler(event: AnotherTestEvent):
            execution_chain.append(f"context2: {event.value}")
        
        # Start the chain
        await publish(TestEvent("Start chain"))
        
        # Allow async execution to complete
        await asyncio.sleep(0.1)
        
        # Verify chain executed
        assert len(execution_chain) == 2
        assert execution_chain[0] == "context1: Start chain"
        assert execution_chain[1] == "context2: 42"
    
    @pytest.mark.asyncio
    async def test_fan_out_pattern(self, clean_global_bus):
        """Test fan-out pattern (one event, multiple contexts)"""
        responses = []
        
        @subscribe(TestEvent, context="analytics")
        async def analytics_handler(event: TestEvent):
            responses.append(f"analytics: analyzing {event.message}")
        
        @subscribe(TestEvent, context="logging")
        async def logging_handler(event: TestEvent):
            responses.append(f"logging: logged {event.message}")
        
        @subscribe(TestEvent, context="monitoring")
        async def monitoring_handler(event: TestEvent):
            responses.append(f"monitoring: tracking {event.message}")
        
        # Publish event that fans out
        await publish(TestEvent("user_action"))
        
        # Allow async execution
        await asyncio.sleep(0.1)
        
        # All contexts should respond
        assert len(responses) == 3
        assert any("analytics" in r for r in responses)
        assert any("logging" in r for r in responses)
        assert any("monitoring" in r for r in responses)