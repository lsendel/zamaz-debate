"""
Tests for Kafka Integration

This module contains comprehensive tests for the Kafka event-driven architecture.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.events.kafka.config import KafkaConfig
from src.events.kafka.client import KafkaClient
from src.events.kafka.producer import KafkaProducer
from src.events.kafka.consumer import KafkaConsumer
from src.events.kafka.event_bridge import KafkaEventBridge
from src.events.kafka.service import KafkaService
from src.events.kafka.processors import DebateEventProcessor, DecisionEventProcessor
from src.events.kafka.serializers import JSONEventSerializer, AvroEventSerializer
from src.events.event_bus import EventBus
from src.events.domain_event import DomainEvent, EventMetadata


class TestKafkaConfig:
    """Test Kafka configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = KafkaConfig()
        assert config.bootstrap_servers == "localhost:9092"
        assert config.group_id == "zamaz-debate-group"
        assert config.topic_prefix == "zamaz-debate"
        assert config.num_partitions == 3
        assert config.replication_factor == 1
    
    def test_from_env(self):
        """Test configuration from environment variables"""
        with patch.dict('os.environ', {
            'KAFKA_BOOTSTRAP_SERVERS': 'kafka1:9092,kafka2:9092',
            'KAFKA_GROUP_ID': 'test-group',
            'KAFKA_TOPIC_PREFIX': 'test-prefix',
            'KAFKA_NUM_PARTITIONS': '6',
            'KAFKA_REPLICATION_FACTOR': '3'
        }):
            config = KafkaConfig.from_env()
            assert config.bootstrap_servers == "kafka1:9092,kafka2:9092"
            assert config.group_id == "test-group"
            assert config.topic_prefix == "test-prefix"
            assert config.num_partitions == 6
            assert config.replication_factor == 3
    
    def test_topic_name_generation(self):
        """Test topic name generation"""
        config = KafkaConfig(topic_prefix="test")
        assert config.get_topic_name("debate-events") == "test.debate-events"
        assert config.get_dead_letter_topic_name("debate-events") == "test.debate-events.dead-letter"
    
    def test_producer_config(self):
        """Test producer configuration conversion"""
        config = KafkaConfig()
        producer_config = config.to_producer_config()
        
        assert producer_config["bootstrap.servers"] == "localhost:9092"
        assert producer_config["acks"] == "all"
        assert producer_config["retries"] == 3
        assert producer_config["compression.type"] == "snappy"
    
    def test_consumer_config(self):
        """Test consumer configuration conversion"""
        config = KafkaConfig()
        consumer_config = config.to_consumer_config()
        
        assert consumer_config["bootstrap.servers"] == "localhost:9092"
        assert consumer_config["group.id"] == "zamaz-debate-group"
        assert consumer_config["auto.offset.reset"] == "latest"
        assert consumer_config["enable.auto.commit"] == True


class TestEventSerializers:
    """Test event serializers"""
    
    def test_json_serializer(self):
        """Test JSON event serializer"""
        serializer = JSONEventSerializer()
        
        # Test data
        event_data = {
            "event_type": "test_event",
            "timestamp": "2023-01-01T00:00:00Z",
            "data": {"key": "value"}
        }
        
        # Serialize
        serialized = serializer.serialize(event_data)
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = serializer.deserialize(serialized)
        assert deserialized == event_data
    
    def test_json_serializer_with_datetime(self):
        """Test JSON serializer with datetime objects"""
        from datetime import datetime
        
        serializer = JSONEventSerializer()
        
        # Test data with datetime
        event_data = {
            "event_type": "test_event",
            "timestamp": datetime(2023, 1, 1, 0, 0, 0),
            "data": {"key": "value"}
        }
        
        # Serialize
        serialized = serializer.serialize(event_data)
        
        # Deserialize
        deserialized = serializer.deserialize(serialized)
        assert deserialized["timestamp"] == "2023-01-01T00:00:00"
    
    @pytest.mark.skipif(not hasattr(AvroEventSerializer, '__init__'), reason="Avro not available")
    def test_avro_serializer(self):
        """Test Avro event serializer"""
        schema = """
        {
            "type": "record",
            "name": "TestEvent",
            "fields": [
                {"name": "event_type", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "data", "type": {"type": "map", "values": "string"}}
            ]
        }
        """
        
        serializer = AvroEventSerializer(schema)
        
        # Test data
        event_data = {
            "event_type": "test_event",
            "timestamp": 1672531200000,  # 2023-01-01 in milliseconds
            "data": {"key": "value"}
        }
        
        # Serialize
        serialized = serializer.serialize(event_data)
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = serializer.deserialize(serialized)
        assert deserialized == event_data


class TestKafkaProducer:
    """Test Kafka producer"""
    
    @pytest.fixture
    def mock_producer(self):
        """Create mock Kafka producer"""
        with patch('src.events.kafka.producer.Producer') as mock_producer_class:
            mock_producer = MagicMock()
            mock_producer_class.return_value = mock_producer
            yield mock_producer
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return KafkaConfig(bootstrap_servers="localhost:9092")
    
    @pytest.mark.asyncio
    async def test_producer_start_stop(self, mock_producer, config):
        """Test producer start and stop"""
        producer = KafkaProducer(config)
        
        # Start
        await producer.start()
        assert producer.is_ready()
        
        # Stop
        await producer.stop()
        assert not producer.is_ready()
    
    @pytest.mark.asyncio
    async def test_producer_produce_message(self, mock_producer, config):
        """Test message production"""
        producer = KafkaProducer(config)
        await producer.start()
        
        # Mock successful delivery
        def mock_produce(topic, key, value, callback, headers):
            callback(None, MagicMock(topic=lambda: topic, partition=lambda: 0, offset=lambda: 1))
        
        mock_producer.produce.side_effect = mock_produce
        
        # Produce message
        success = await producer.produce("test-topic", {"key": "value"}, wait_for_delivery=False)
        assert success
        
        # Verify produce was called
        mock_producer.produce.assert_called_once()
        
        await producer.stop()
    
    @pytest.mark.asyncio
    async def test_producer_batch_produce(self, mock_producer, config):
        """Test batch message production"""
        producer = KafkaProducer(config)
        await producer.start()
        
        # Mock successful delivery
        def mock_produce(topic, key, value, callback, headers):
            callback(None, MagicMock(topic=lambda: topic, partition=lambda: 0, offset=lambda: 1))
        
        mock_producer.produce.side_effect = mock_produce
        
        # Produce batch
        events = [{"key": f"value{i}"} for i in range(5)]
        success_count = await producer.produce_batch("test-topic", events)
        assert success_count == 5
        
        await producer.stop()


class TestKafkaConsumer:
    """Test Kafka consumer"""
    
    @pytest.fixture
    def mock_consumer(self):
        """Create mock Kafka consumer"""
        with patch('src.events.kafka.consumer.Consumer') as mock_consumer_class:
            mock_consumer = MagicMock()
            mock_consumer_class.return_value = mock_consumer
            yield mock_consumer
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return KafkaConfig(bootstrap_servers="localhost:9092")
    
    @pytest.fixture
    def handler_callback(self):
        """Create test handler callback"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_consumer_start_stop(self, mock_consumer, config, handler_callback):
        """Test consumer start and stop"""
        consumer = KafkaConsumer(config, "test-consumer", ["test-topic"], handler_callback)
        
        # Start
        await consumer.start()
        assert consumer._running
        
        # Stop
        await consumer.stop()
        assert not consumer._running
    
    @pytest.mark.asyncio
    async def test_consumer_message_processing(self, mock_consumer, config, handler_callback):
        """Test message processing"""
        consumer = KafkaConsumer(config, "test-consumer", ["test-topic"], handler_callback)
        
        # Mock message
        mock_message = MagicMock()
        mock_message.error.return_value = None
        mock_message.value.return_value = b'{"key": "value"}'
        mock_message.topic.return_value = "test-topic"
        mock_message.partition.return_value = 0
        mock_message.offset.return_value = 1
        mock_message.timestamp.return_value = (1, 1672531200000)
        mock_message.key.return_value = None
        mock_message.headers.return_value = []
        
        # Process message directly
        await consumer._process_message(mock_message)
        
        # Verify handler was called
        handler_callback.assert_called_once()
        
        # Verify message data
        call_args = handler_callback.call_args[0][0]
        assert call_args["key"] == "value"
        assert "kafka_metadata" in call_args


class TestKafkaEventBridge:
    """Test Kafka event bridge"""
    
    @pytest.fixture
    def event_bus(self):
        """Create test event bus"""
        return EventBus()
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return KafkaConfig(bootstrap_servers="localhost:9092")
    
    @pytest.fixture
    def mock_kafka_client(self):
        """Create mock Kafka client"""
        with patch('src.events.kafka.event_bridge.KafkaClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_event_bridge_start_stop(self, event_bus, config, mock_kafka_client):
        """Test event bridge start and stop"""
        bridge = KafkaEventBridge(event_bus, config)
        
        # Start
        await bridge.start()
        assert bridge._running
        
        # Stop
        await bridge.stop()
        assert not bridge._running
    
    @pytest.mark.asyncio
    async def test_event_bridge_routing(self, event_bus, config, mock_kafka_client):
        """Test event routing to Kafka"""
        bridge = KafkaEventBridge(event_bus, config)
        
        # Mock domain event
        class TestEvent(DomainEvent):
            def __init__(self):
                super().__init__()
                self.test_data = "test_value"
            
            @property
            def event_type(self) -> str:
                return "debate_initiated"
            
            @property
            def aggregate_id(self):
                from uuid import uuid4
                return uuid4()
            
            @property
            def aggregate_type(self) -> str:
                return "debate"
            
            def to_dict(self) -> Dict[str, Any]:
                return {"test_data": self.test_data}
            
            @classmethod
            def from_dict(cls, data: Dict[str, Any]) -> "TestEvent":
                event = cls()
                event.test_data = data["test_data"]
                return event
        
        # Start bridge
        await bridge.start()
        
        # Create and handle event
        event = TestEvent()
        await bridge._handle_domain_event(event)
        
        # Verify Kafka client was called
        mock_kafka_client.produce_event.assert_called_once()
        
        await bridge.stop()


class TestEventProcessors:
    """Test event processors"""
    
    @pytest.fixture
    def mock_kafka_client(self):
        """Create mock Kafka client"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_debate_event_processor(self, mock_kafka_client):
        """Test debate event processor"""
        processor = DebateEventProcessor(mock_kafka_client)
        
        # Test event data
        event_data = {
            "event_type": "debate_initiated",
            "event_data": {
                "debate_id": "test-debate-123",
                "question": "Test question",
                "context": "Test context"
            }
        }
        
        # Process event
        success = await processor.process_event(event_data)
        assert success
        
        # Verify debate tracking
        assert "test-debate-123" in processor.active_debates
        assert processor.debate_metrics["test-debate-123"]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_decision_event_processor(self, mock_kafka_client):
        """Test decision event processor"""
        processor = DecisionEventProcessor(mock_kafka_client)
        
        # Test event data
        event_data = {
            "event_type": "decision_made",
            "event_data": {
                "decision_id": "test-decision-123",
                "decision_type": "complex",
                "method": "debate",
                "question": "Test question"
            }
        }
        
        # Process event
        success = await processor.process_event(event_data)
        assert success
        
        # Verify decision tracking
        assert "test-decision-123" in processor.decision_tracking
        assert processor.decision_tracking["test-decision-123"]["status"] == "pending"
        assert processor.decision_tracking["test-decision-123"]["decision_type"] == "complex"


class TestKafkaService:
    """Test Kafka service integration"""
    
    @pytest.fixture
    def event_bus(self):
        """Create test event bus"""
        return EventBus()
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return KafkaConfig(bootstrap_servers="localhost:9092")
    
    @pytest.fixture
    def mock_kafka_client(self):
        """Create mock Kafka client"""
        with patch('src.events.kafka.service.KafkaClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_kafka_service_start_stop(self, event_bus, config, mock_kafka_client):
        """Test Kafka service start and stop"""
        service = KafkaService(event_bus, config)
        
        # Start
        await service.start()
        assert service.is_running()
        
        # Stop
        await service.stop()
        assert not service.is_running()
    
    @pytest.mark.asyncio
    async def test_kafka_service_publish_event(self, event_bus, config, mock_kafka_client):
        """Test event publishing through service"""
        service = KafkaService(event_bus, config)
        await service.start()
        
        # Mock successful publish
        mock_kafka_client.produce_event.return_value = True
        
        # Publish event
        success = await service.publish_event("test-event", {"key": "value"})
        assert success
        
        # Verify client was called
        mock_kafka_client.produce_event.assert_called_once_with("test-event", {"key": "value"}, None)
        
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_kafka_service_health_check(self, event_bus, config, mock_kafka_client):
        """Test service health check"""
        service = KafkaService(event_bus, config)
        await service.start()
        
        # Mock health check
        mock_kafka_client.health_check.return_value = {"status": "healthy"}
        
        # Perform health check
        health = await service.health_check()
        assert health["service_running"] == True
        assert "kafka_client" in health
        
        await service.stop()


class TestKafkaIntegration:
    """Integration tests for Kafka system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_event_flow(self):
        """Test complete event flow from domain event to Kafka and back"""
        # This would require actual Kafka instance for full integration test
        # For now, we'll test with mocks
        
        event_bus = EventBus()
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        
        with patch('src.events.kafka.client.KafkaClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Create service
            service = KafkaService(event_bus, config)
            await service.start()
            
            # Test event publishing
            event_data = {
                "event_type": "debate_initiated",
                "debate_id": "test-debate-123",
                "question": "Test question"
            }
            
            success = await service.publish_event("debate-events", event_data)
            assert success
            
            # Verify integration
            mock_client.produce_event.assert_called_once()
            
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery scenarios"""
        event_bus = EventBus()
        config = KafkaConfig(bootstrap_servers="localhost:9092")
        
        with patch('src.events.kafka.client.KafkaClient') as mock_client_class:
            # Mock client that fails on start
            mock_client = AsyncMock()
            mock_client.start.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client
            
            service = KafkaService(event_bus, config)
            
            # Service should handle startup failure gracefully
            with pytest.raises(Exception):
                await service.start()
            
            # Service should be in stopped state
            assert not service.is_running()
    
    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test configuration validation"""
        # Test invalid bootstrap servers
        with pytest.raises(Exception):
            config = KafkaConfig(bootstrap_servers="")
            # This would fail in real implementation
        
        # Test valid configuration
        config = KafkaConfig(
            bootstrap_servers="localhost:9092",
            group_id="test-group",
            topic_prefix="test"
        )
        
        assert config.bootstrap_servers == "localhost:9092"
        assert config.group_id == "test-group"
        assert config.topic_prefix == "test"


if __name__ == "__main__":
    pytest.main([__file__])