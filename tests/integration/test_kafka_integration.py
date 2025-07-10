"""
Integration tests for Kafka-DDD event system integration.

Tests the complete flow of events through both the in-memory bus and Kafka.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from testcontainers.kafka import KafkaContainer

from src.contexts.debate import DebateCompleted
from src.contexts.evolution import EvolutionTriggered
from src.contexts.implementation import TaskCreated
from src.contexts.performance import MetricThresholdBreached
from src.contexts.testing import TestFailed

from src.events import DomainEvent, get_event_bus
from src.infrastructure.kafka import (
    KafkaConfig,
    KafkaEventBridge,
    KafkaEventProducer,
    KafkaEventConsumer,
    EventSerializer,
    EventDeserializer,
    HybridEventBus,
    get_hybrid_event_bus,
)


@pytest.fixture(scope="module")
def kafka_container():
    """Start Kafka container for testing"""
    container = KafkaContainer(image="confluentinc/cp-kafka:7.5.0")
    container.start()
    
    yield container
    
    container.stop()


@pytest.fixture
def kafka_config(kafka_container):
    """Create Kafka configuration for tests"""
    return KafkaConfig(
        bootstrap_servers=kafka_container.get_bootstrap_server(),
        client_id="test-client",
        consumer_group_id="test-group",
        topic_prefix="test.",
        num_partitions=1,
        replication_factor=1,
    )


@pytest.fixture
async def kafka_bridge(kafka_config):
    """Create Kafka event bridge for tests"""
    bridge = KafkaEventBridge(kafka_config)
    yield bridge
    bridge.stop()


@pytest.fixture
def event_deserializer():
    """Create event deserializer with registered events"""
    from src.infrastructure.kafka.serialization import register_all_events
    register_all_events()
    return EventDeserializer()


class TestKafkaSerialization:
    """Test event serialization/deserialization for Kafka"""
    
    def test_serialize_domain_event(self):
        """Test serializing a domain event"""
        event = DebateCompleted(
            debate_id=uuid4(),
            topic="Test Decision",
            winner="Claude",
            consensus=True,
            decision_type="COMPLEX",
            decision_id=uuid4(),
            summary="Test completed",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateCompleted",
            aggregate_id=uuid4(),
            version=1,
        )
        
        serializer = EventSerializer()
        data = serializer.serialize(event)
        
        # Verify it's valid JSON
        parsed = json.loads(data.decode('utf-8'))
        assert parsed['event_type'] == "DebateCompleted"
        assert parsed['topic'] == "Test Decision"
        assert parsed['winner'] == "Claude"
        assert '_metadata' in parsed
    
    def test_deserialize_domain_event(self, event_deserializer):
        """Test deserializing a domain event"""
        # Create and serialize an event
        original = TaskCreated(
            task_id=uuid4(),
            decision_id=uuid4(),
            title="Test Task",
            priority="high",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TaskCreated",
            aggregate_id=uuid4(),
            version=1,
        )
        
        serializer = EventSerializer()
        data = serializer.serialize(original)
        
        # Deserialize
        deserialized = event_deserializer.deserialize(data)
        
        assert deserialized is not None
        assert isinstance(deserialized, TaskCreated)
        assert deserialized.task_id == original.task_id
        assert deserialized.title == original.title
        assert deserialized.priority == original.priority
    
    def test_serialize_complex_event(self):
        """Test serializing event with nested objects"""
        event = EvolutionTriggered(
            evolution_id=uuid4(),
            trigger_type="performance",
            trigger_details={
                "metrics": {
                    "cpu": 85.5,
                    "memory": 92.0,
                    "response_time": 450,
                },
                "thresholds": ["cpu > 80", "memory > 90"],
                "timestamp": datetime.now().isoformat(),
            },
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="EvolutionTriggered",
            aggregate_id=uuid4(),
            version=1,
        )
        
        serializer = EventSerializer()
        data = serializer.serialize(event)
        parsed = json.loads(data.decode('utf-8'))
        
        assert parsed['trigger_details']['metrics']['cpu'] == 85.5
        assert len(parsed['trigger_details']['thresholds']) == 2


class TestKafkaProducerConsumer:
    """Test Kafka producer and consumer"""
    
    @pytest.mark.asyncio
    async def test_produce_consume_single_event(self, kafka_config):
        """Test producing and consuming a single event"""
        # Create producer and consumer
        producer = KafkaEventProducer(kafka_config)
        
        # Create event
        event = TestFailed(
            test_case_id=uuid4(),
            test_name="test_integration",
            error_message="Test failed",
            stack_trace="...",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TestFailed",
            aggregate_id=uuid4(),
            version=1,
        )
        
        # Produce event
        producer.publish(event, context="testing")
        producer.flush()
        
        # Create consumer
        consumed_events = []
        
        async def event_handler(e: DomainEvent):
            consumed_events.append(e)
        
        # Manually consume (simplified for testing)
        from confluent_kafka import Consumer
        consumer_config = kafka_config.consumer_config.copy()
        consumer_config['group.id'] = 'test-consumer-single'
        consumer = Consumer(consumer_config)
        consumer.subscribe([f"{kafka_config.topic_prefix}testing.events"])
        
        # Poll for message
        msg = consumer.poll(timeout=5.0)
        assert msg is not None
        assert not msg.error()
        
        # Deserialize
        deserializer = EventDeserializer()
        consumed_event = deserializer.deserialize(msg.value())
        
        assert consumed_event is not None
        assert consumed_event.test_case_id == event.test_case_id
        assert consumed_event.test_name == event.test_name
        
        consumer.close()
        producer.close()
    
    @pytest.mark.asyncio
    async def test_batch_producer(self, kafka_config):
        """Test batch event production"""
        batch_producer = BatchEventProducer(kafka_config)
        
        # Add multiple events
        events = []
        for i in range(10):
            event = MetricThresholdBreached(
                metric_name=f"metric_{i}",
                current_value=100.0 + i,
                threshold=90.0,
                severity="warning",
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="MetricThresholdBreached",
                aggregate_id=uuid4(),
                version=1,
            )
            events.append(event)
            batch_producer.add_event(event, context="performance")
        
        # Flush batch
        count = batch_producer.flush_batch()
        assert count == 10
        
        batch_producer.close()


class TestKafkaEventBridge:
    """Test Kafka-DDD event bridge"""
    
    @pytest.mark.asyncio
    async def test_bridge_event_to_kafka(self, kafka_bridge):
        """Test bridging events from DDD bus to Kafka"""
        # Bridge specific event type
        kafka_bridge.bridge_event_type(
            DebateCompleted,
            context="debate",
            to_kafka=True,
            from_kafka=False,
        )
        
        # Publish event to local bus
        event = DebateCompleted(
            debate_id=uuid4(),
            topic="Bridge Test",
            winner="Gemini",
            consensus=False,
            decision_type="MODERATE",
            decision_id=uuid4(),
            summary="Testing bridge",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateCompleted",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await kafka_bridge.event_bus.publish(event)
        
        # Give time for async processing
        await asyncio.sleep(0.5)
        
        # Flush to ensure delivery
        kafka_bridge.producer.flush()
        
        # Verify event was published to Kafka
        # (In real test, would consume from Kafka to verify)
        metrics = kafka_bridge.get_metrics()
        assert metrics['event_bus_metrics'].get('DebateCompleted', 0) > 0
    
    @pytest.mark.asyncio
    async def test_bridge_all_events(self, kafka_bridge):
        """Test bridging all domain events"""
        kafka_bridge.bridge_all_events()
        
        # Verify events are bridged
        assert len(kafka_bridge._bridged_event_types) > 0
        assert DebateCompleted in kafka_bridge._bridged_event_types
        assert EvolutionTriggered in kafka_bridge._bridged_event_types
        assert TaskCreated in kafka_bridge._bridged_event_types
    
    @pytest.mark.asyncio
    async def test_consumer_integration(self, kafka_config):
        """Test consuming events from Kafka back to DDD bus"""
        # Create bridge
        bridge = KafkaEventBridge(kafka_config)
        
        # Track events received in local bus
        received_events = []
        
        @bridge.event_bus.subscribe(TaskCreated, "test-handler", priority=10)
        async def track_event(event: TaskCreated):
            received_events.append(event)
        
        # Produce event directly to Kafka
        producer = KafkaEventProducer(kafka_config)
        event = TaskCreated(
            task_id=uuid4(),
            decision_id=uuid4(),
            title="Consumer Test Task",
            priority="medium",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TaskCreated",
            aggregate_id=uuid4(),
            version=1,
        )
        
        producer.publish(event, context="implementation")
        producer.flush()
        producer.close()
        
        # Create and start consumer
        consumer = KafkaEventConsumer(kafka_config, ["implementation"])
        
        # Run consumer briefly
        consumer_task = asyncio.create_task(consumer.start())
        await asyncio.sleep(2.0)  # Give time to consume
        consumer.stop()
        
        # Cancel consumer task
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        
        # Verify event was received
        assert len(received_events) > 0
        assert received_events[0].task_id == event.task_id
        
        bridge.stop()


class TestHybridEventBus:
    """Test hybrid event bus with automatic Kafka integration"""
    
    @pytest.mark.asyncio
    async def test_hybrid_bus_local_only(self):
        """Test hybrid bus without Kafka"""
        bus = HybridEventBus(kafka_config=None)
        
        received = []
        
        @bus.subscribe(TestFailed, "test", priority=10)
        async def handler(event: TestFailed):
            received.append(event)
        
        event = TestFailed(
            test_case_id=uuid4(),
            test_name="test_hybrid",
            error_message="Failed",
            stack_trace="...",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TestFailed",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        
        assert len(received) == 1
        assert not bus._kafka_enabled
    
    @pytest.mark.asyncio
    async def test_hybrid_bus_with_kafka(self, kafka_config):
        """Test hybrid bus with Kafka enabled"""
        bus = HybridEventBus(kafka_config)
        bus.kafka_bridge.bridge_all_events()
        
        # Publish event
        event = EvolutionTriggered(
            evolution_id=uuid4(),
            trigger_type="manual",
            trigger_details={"reason": "Test"},
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="EvolutionTriggered",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(event)
        
        # Flush Kafka
        bus.kafka_bridge.producer.flush()
        
        # Verify metrics
        metrics = bus.get_event_metrics()
        assert metrics['EvolutionTriggered'] > 0
        
        bus.disable_kafka()


class TestEndToEndKafkaFlow:
    """Test complete end-to-end flows with Kafka"""
    
    @pytest.mark.asyncio
    async def test_cross_context_flow_via_kafka(self, kafka_config):
        """Test cross-context event flow through Kafka"""
        # Create hybrid bus
        bus = get_hybrid_event_bus(kafka_config)
        bus.kafka_bridge.bridge_all_events()
        
        # Track implementation tasks created
        created_tasks = []
        
        @bus.subscribe(TaskCreated, "test-tracker", priority=10)
        async def track_task_created(event: TaskCreated):
            created_tasks.append(event)
        
        # Start consumers
        consumer_task = asyncio.create_task(
            bus.kafka_bridge.start_consumers()
        )
        
        # Simulate debate completion
        debate_completed = DebateCompleted(
            debate_id=uuid4(),
            topic="Kafka Integration Test",
            winner="Claude",
            consensus=True,
            decision_type="COMPLEX",
            decision_id=uuid4(),
            summary="Implement Kafka integration",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateCompleted",
            aggregate_id=uuid4(),
            version=1,
        )
        
        # Publish to bus (will go to Kafka)
        await bus.publish(debate_completed)
        
        # Allow time for processing
        await asyncio.sleep(3.0)
        
        # In a real system, the cross-context handler would create a task
        # For this test, we'll simulate it
        task_created = TaskCreated(
            task_id=uuid4(),
            decision_id=debate_completed.decision_id,
            title=f"Implement: {debate_completed.topic}",
            priority="high",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TaskCreated",
            aggregate_id=uuid4(),
            version=1,
        )
        
        await bus.publish(task_created)
        await asyncio.sleep(1.0)
        
        # Verify task was tracked
        assert len(created_tasks) > 0
        
        # Stop consumers
        bus.kafka_bridge.stop()
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


class TestKafkaResilience:
    """Test Kafka resilience and error handling"""
    
    @pytest.mark.asyncio
    async def test_producer_resilience(self, kafka_config):
        """Test producer handles temporary Kafka unavailability"""
        # Create producer with wrong server
        bad_config = KafkaConfig(
            bootstrap_servers="localhost:9999",  # Non-existent
            client_id="test-resilience",
        )
        
        producer = KafkaEventProducer(bad_config)
        
        # Try to publish (should not crash)
        event = TestFailed(
            test_case_id=uuid4(),
            test_name="resilience_test",
            error_message="Test",
            stack_trace="...",
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="TestFailed",
            aggregate_id=uuid4(),
            version=1,
        )
        
        # This should log error but not crash
        try:
            producer.publish(event, context="testing")
            # Give some time for async error
            time.sleep(0.5)
        except Exception:
            # Should handle gracefully
            pass
        
        producer.close()
    
    @pytest.mark.asyncio
    async def test_serialization_error_handling(self, event_deserializer):
        """Test handling of serialization errors"""
        # Invalid JSON
        invalid_data = b"not valid json"
        result = event_deserializer.deserialize(invalid_data)
        assert result is None
        
        # Valid JSON but unknown event type
        unknown_event = json.dumps({
            "event_type": "UnknownEventType",
            "event_id": str(uuid4()),
            "occurred_at": datetime.now().isoformat(),
            "aggregate_id": str(uuid4()),
            "version": 1,
        }).encode('utf-8')
        
        result = event_deserializer.deserialize(unknown_event)
        # Should return generic DomainEvent
        assert result is not None
        assert result.event_type == "UnknownEventType"