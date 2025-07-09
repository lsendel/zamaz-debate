# Kafka Integration Documentation

## Overview

The Zamaz Debate System now includes comprehensive Apache Kafka integration for high-throughput, event-driven data processing. This integration complements the existing in-memory event bus with persistent, scalable event streaming capabilities.

## Architecture

### Core Components

#### 1. KafkaClient (`src/events/kafka/client.py`)
- High-level interface for Kafka operations
- Manages producers, consumers, and topic operations
- Provides health checking and statistics

#### 2. KafkaProducer (`src/events/kafka/producer.py`)
- Asynchronous message production
- Delivery confirmation tracking
- Batch processing support
- Error handling and retry logic

#### 3. KafkaConsumer (`src/events/kafka/consumer.py`)
- Asynchronous message consumption
- Dead letter queue handling
- Offset management
- Error recovery mechanisms

#### 4. KafkaEventBridge (`src/events/kafka/event_bridge.py`)
- Bridges domain events between EventBus and Kafka
- Automatic event routing
- Bidirectional event flow
- Consumer handler registration

#### 5. Event Processors (`src/events/kafka/processors.py`)
- DebateEventProcessor: Handles debate lifecycle events
- DecisionEventProcessor: Processes decision events
- EvolutionEventProcessor: Manages evolution events
- MetricsEventProcessor: Collects and aggregates metrics

#### 6. KafkaService (`src/events/kafka/service.py`)
- Main service coordinating all Kafka components
- Health monitoring
- Statistics collection
- Configuration management

### Event Flow

```
Domain Event → EventBus → KafkaEventBridge → KafkaProducer → Kafka Topic
                                                                    ↓
Kafka Topic → KafkaConsumer → EventProcessor → Business Logic
```

## Configuration

### Environment Variables

```bash
# Kafka Connection
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=your_username
KAFKA_SASL_PASSWORD=your_password

# Topics
KAFKA_TOPIC_PREFIX=zamaz-debate
KAFKA_NUM_PARTITIONS=3
KAFKA_REPLICATION_FACTOR=1

# Consumer
KAFKA_GROUP_ID=zamaz-debate-group
KAFKA_AUTO_OFFSET_RESET=latest
KAFKA_ENABLE_AUTO_COMMIT=true
KAFKA_MAX_POLL_RECORDS=500

# Producer
KAFKA_ACKS=all
KAFKA_RETRIES=3
KAFKA_BATCH_SIZE=16384
KAFKA_LINGER_MS=5
KAFKA_COMPRESSION_TYPE=snappy

# Service
KAFKA_ENABLED=true
KAFKA_SCHEMA_REGISTRY_URL=http://localhost:8081
```

### Configuration Class

```python
from src.events.kafka.config import KafkaConfig

# Load from environment
config = KafkaConfig.from_env()

# Or create manually
config = KafkaConfig(
    bootstrap_servers="localhost:9092",
    group_id="my-consumer-group",
    topic_prefix="my-app"
)
```

## Topics

### Default Topics

The system creates the following topics automatically:

1. **zamaz-debate.debate-events**
   - Debate lifecycle events
   - Partitions: 3
   - Retention: 7 days

2. **zamaz-debate.decision-events**
   - Decision-making events
   - Partitions: 3
   - Retention: 30 days

3. **zamaz-debate.evolution-events**
   - System evolution events
   - Partitions: 3
   - Retention: 90 days

4. **zamaz-debate.webhook-events**
   - Webhook notification events
   - Partitions: 3
   - Retention: 7 days

5. **zamaz-debate.metrics-events**
   - System metrics and monitoring
   - Partitions: 3
   - Retention: 7 days

### Dead Letter Topics

For each main topic, a corresponding dead letter topic is created:
- `zamaz-debate.debate-events.dead-letter`
- `zamaz-debate.decision-events.dead-letter`
- etc.

## Usage

### Starting the Kafka Service

```python
from src.events.kafka.service import KafkaService
from src.events.event_bus import EventBus

event_bus = EventBus()
await event_bus.start()

kafka_service = KafkaService(event_bus)
await kafka_service.start()
```

### Publishing Events

```python
# Direct event publishing
await kafka_service.publish_event(
    event_type="debate-events",
    event_data={
        "debate_id": "debate-123",
        "question": "Should we implement feature X?",
        "status": "initiated"
    },
    partition_key="debate-123"
)

# Through event bridge (automatic routing)
from src.events.domain_event import DomainEvent

class DebateInitiated(DomainEvent):
    # ... implementation

event = DebateInitiated(debate_id="debate-123")
await event_bus.publish(event)  # Automatically routed to Kafka
```

### Consuming Events

```python
# Add event handler
async def handle_debate_event(event_data):
    print(f"Received debate event: {event_data}")

kafka_service.add_event_handler("debate_initiated", handle_debate_event)

# Or use processors directly
from src.events.kafka.processors import DebateEventProcessor

processor = DebateEventProcessor(kafka_service.kafka_client)
await processor.start()
```

### Health Checking

```python
health = await kafka_service.health_check()
print(f"Service running: {health['service_running']}")
print(f"Kafka available: {health['kafka_available']}")
```

## API Endpoints

### Kafka Health Check
```
GET /kafka/health
```

### List Topics
```
GET /kafka/topics
```

### Get Topic Metadata
```
GET /kafka/topics/{topic_name}
```

### Publish Event
```
POST /kafka/events
{
    "event_type": "debate-events",
    "event_data": {"key": "value"},
    "partition_key": "optional-key"
}
```

### Create Topic
```
POST /kafka/topics
{
    "event_type": "my-custom-events",
    "num_partitions": 5,
    "replication_factor": 2
}
```

## Event Serialization

### JSON Serialization (Default)

```python
from src.events.kafka.serializers import JSONEventSerializer

serializer = JSONEventSerializer()
data = {"key": "value", "timestamp": datetime.now()}
serialized = serializer.serialize(data)
deserialized = serializer.deserialize(serialized)
```

### Avro Serialization

```python
from src.events.kafka.serializers import AvroEventSerializer

schema = """
{
    "type": "record",
    "name": "DebateEvent",
    "fields": [
        {"name": "debate_id", "type": "string"},
        {"name": "timestamp", "type": "long"}
    ]
}
"""

serializer = AvroEventSerializer(schema)
data = {"debate_id": "debate-123", "timestamp": 1672531200000}
serialized = serializer.serialize(data)
```

## Event Processing

### Custom Event Processor

```python
from src.events.kafka.processors import EventProcessor

class CustomEventProcessor(EventProcessor):
    def get_event_types(self):
        return ["custom-events"]
    
    async def process_event(self, event_data):
        # Process custom event
        print(f"Processing: {event_data}")
        return True

# Use processor
processor = CustomEventProcessor(kafka_client, "custom-processor")
await processor.start()
```

### Processor Manager

```python
from src.events.kafka.processors import ProcessorManager

manager = ProcessorManager(kafka_client)
await manager.start()  # Starts all default processors

# Add custom processor
manager.add_processor(CustomEventProcessor(kafka_client))
```

## Monitoring and Metrics

### Service Statistics

```python
stats = kafka_service.get_stats()
print(f"Messages produced: {stats['kafka_client']['messages_produced']}")
print(f"Messages consumed: {stats['kafka_client']['messages_consumed']}")
print(f"Active consumers: {stats['kafka_client']['active_consumers']}")
```

### Health Monitoring

```python
health = await kafka_service.health_check()
if not health['components_healthy']:
    print("Some components are unhealthy")
    print(f"Last error: {health['last_error']}")
```

## Error Handling

### Dead Letter Queues

Failed messages are automatically sent to dead letter topics:

```python
# Messages that fail processing go to:
# zamaz-debate.debate-events.dead-letter

# You can consume from dead letter topics for analysis
await kafka_client.create_consumer(
    "dead-letter-consumer",
    ["debate-events.dead-letter"],
    handle_dead_letter_message
)
```

### Retry Logic

The system includes automatic retry with exponential backoff:

```python
# Configuration
config = KafkaConfig(
    retries=3,
    retry_delay_seconds=5
)

# Consumers automatically retry failed messages
# Producers retry failed deliveries
```

## Testing

### Unit Tests

```python
import pytest
from src.events.kafka.client import KafkaClient
from src.events.kafka.config import KafkaConfig

@pytest.mark.asyncio
async def test_kafka_client():
    config = KafkaConfig(bootstrap_servers="localhost:9092")
    client = KafkaClient(config)
    
    await client.start()
    success = await client.produce_event("test-topic", {"key": "value"})
    assert success
    await client.stop()
```

### Integration Tests

```python
# Run integration tests with real Kafka
pytest tests/test_kafka_integration.py -v

# Run with mocks for CI/CD
pytest tests/test_kafka_integration.py -v --mock-kafka
```

## Performance Considerations

### Batching

```python
# Batch publishing for better throughput
events = [{"key": f"value{i}"} for i in range(100)]
await producer.produce_batch("test-topic", events)
```

### Partitioning

```python
# Use partition keys for ordered processing
await kafka_service.publish_event(
    "debate-events",
    event_data,
    partition_key=debate_id  # Events for same debate go to same partition
)
```

### Compression

```python
config = KafkaConfig(compression_type="snappy")  # Or "gzip", "lz4"
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   ```
   Error: Failed to connect to Kafka
   Solution: Check KAFKA_BOOTSTRAP_SERVERS and network connectivity
   ```

2. **Topic Not Found**
   ```
   Error: Topic does not exist
   Solution: Ensure topic auto-creation is enabled or create manually
   ```

3. **Consumer Group Rebalancing**
   ```
   Error: Consumer group rebalancing
   Solution: Increase session timeout or reduce processing time
   ```

### Debug Mode

```python
import logging
logging.getLogger("src.events.kafka").setLevel(logging.DEBUG)

# Enable Kafka client debug logging
config = KafkaConfig()
config.debug = "broker,topic,msg"
```

### Health Check Endpoint

```bash
curl http://localhost:8000/kafka/health
```

## Migration Guide

### From Pure Event Bus

1. **Install Dependencies**
   ```bash
   pip install kafka-python confluent-kafka avro
   ```

2. **Update Configuration**
   ```python
   # Add Kafka config to your app startup
   from src.events.kafka.service import initialize_kafka_service
   await initialize_kafka_service(event_bus)
   ```

3. **Gradual Migration**
   - Start with event bridge (automatic routing)
   - Gradually add custom processors
   - Monitor performance and adjust configuration

### Best Practices

1. **Topic Design**
   - Use meaningful topic names
   - Consider partition count based on throughput
   - Set appropriate retention policies

2. **Event Design**
   - Include correlation IDs for tracing
   - Use versioned schemas for compatibility
   - Keep events immutable

3. **Error Handling**
   - Implement dead letter queues
   - Add proper logging and monitoring
   - Use circuit breakers for resilience

4. **Performance**
   - Batch messages when possible
   - Use compression for large payloads
   - Monitor consumer lag

## Security

### Authentication

```python
config = KafkaConfig(
    security_protocol="SASL_SSL",
    sasl_mechanism="PLAIN",
    sasl_username="your_username",
    sasl_password="your_password"
)
```

### SSL/TLS

```python
config = KafkaConfig(
    security_protocol="SSL",
    ssl_cafile="/path/to/ca.pem",
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem"
)
```

## Conclusion

The Kafka integration provides a robust, scalable foundation for event-driven architecture in the Zamaz Debate System. It enables:

- High-throughput event processing
- Persistent event storage
- Horizontal scaling
- Fault tolerance
- Real-time analytics

The system is designed to be:
- **Reliable**: Automatic retries and dead letter queues
- **Scalable**: Partitioned topics and consumer groups
- **Maintainable**: Clear separation of concerns
- **Observable**: Comprehensive monitoring and health checks

For questions or issues, refer to the test files and example implementations in the codebase.