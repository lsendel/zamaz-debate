# Kafka-DDD Integration Testing Guide

## Overview

This guide explains how to test the integration between the DDD event system and Apache Kafka in the Zamaz Debate System.

## Architecture Overview

### Event Flow
```
DDD Event Bus (In-Memory) <---> Kafka Event Bridge <---> Apache Kafka
      |                                                         |
      v                                                         v
Local Handlers                                         Distributed Consumers
```

### Key Components

1. **DDD Event Bus**: In-memory event publishing and subscription
2. **Kafka Event Bridge**: Bridges local events to/from Kafka
3. **Event Serialization**: JSON-based serialization with metadata
4. **Topic Mapping**: Context-based topic organization
5. **Hybrid Event Bus**: Transparent Kafka integration

## What We're Testing

### 1. Integration Points
- **Event Serialization**: Domain events ↔ Kafka messages
- **Topic Routing**: Events routed to correct Kafka topics
- **Bidirectional Flow**: Local → Kafka and Kafka → Local
- **Cross-Context Communication**: Events flow between bounded contexts via Kafka
- **Hybrid Operation**: System works with or without Kafka

### 2. Resilience
- **Kafka Unavailability**: Local events continue to work
- **Serialization Errors**: Graceful handling of malformed events
- **Consumer Failures**: Other consumers continue processing
- **Backpressure**: System handles high event volume
- **Ordering Guarantees**: Events maintain order within partitions

### 3. Performance
- **Throughput**: Millions of events per day
- **Latency**: Sub-second event propagation
- **Batch Processing**: Efficient bulk operations
- **Resource Usage**: Memory and CPU efficiency

## Test Setup

### Prerequisites
```bash
# Install dependencies
pip install kafka-python confluent-kafka avro-python3 testcontainers pytest-docker

# For local testing, start Kafka
docker run -d --name kafka \
  -p 9092:9092 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  confluentinc/cp-kafka:latest
```

### Environment Configuration
```bash
# .env file
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CLIENT_ID=zamaz-debate-test
KAFKA_CONSUMER_GROUP=zamaz-test-group
KAFKA_TOPIC_PREFIX=test.
KAFKA_USE_AVRO=false
```

## Running Tests

### All Kafka Integration Tests
```bash
pytest tests/integration/test_kafka_integration.py -v
```

### Specific Test Categories
```bash
# Serialization tests only
pytest tests/integration/test_kafka_integration.py::TestKafkaSerialization -v

# Producer/Consumer tests
pytest tests/integration/test_kafka_integration.py::TestKafkaProducerConsumer -v

# Event bridge tests
pytest tests/integration/test_kafka_integration.py::TestKafkaEventBridge -v

# End-to-end flows
pytest tests/integration/test_kafka_integration.py::TestEndToEndKafkaFlow -v
```

### With Docker Compose
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
  
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
  
  tests:
    build: .
    depends_on:
      - kafka
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    command: pytest tests/integration/test_kafka_integration.py
```

## Test Scenarios

### 1. Basic Integration Test
```python
# Verify event flows through Kafka
async def test_event_through_kafka():
    # Create hybrid bus with Kafka
    bus = HybridEventBus(kafka_config)
    
    # Publish event
    event = DebateCompleted(...)
    await bus.publish(event)
    
    # Event goes to both local handlers and Kafka
    assert local_handler_called
    assert kafka_message_produced
```

### 2. Cross-Context Flow Test
```python
# Test debate → implementation flow via Kafka
async def test_cross_context_via_kafka():
    # Setup bridge
    bridge = KafkaEventBridge(config)
    bridge.bridge_all_events()
    
    # Publish debate completed
    await bus.publish(DebateCompleted(...))
    
    # Verify task created event flows back
    assert TaskCreated in received_events
```

### 3. Resilience Test
```python
# Test system continues without Kafka
async def test_kafka_failure_resilience():
    # Create bus with bad Kafka config
    bus = HybridEventBus(bad_config)
    
    # Local events still work
    await bus.publish(event)
    assert local_handlers_executed
```

### 4. Performance Test
```python
# Test high-volume event processing
async def test_high_volume_events():
    batch_producer = BatchEventProducer(config)
    
    # Send 10,000 events
    for i in range(10000):
        batch_producer.add_event(event, context)
    
    # Verify throughput
    assert time_elapsed < 5.0  # seconds
```

## Debugging Kafka Integration

### 1. Check Topic Creation
```bash
# List topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Expected topics:
# test.debate.events
# test.testing.events
# test.performance.events
# test.implementation.events
# test.evolution.events
```

### 2. Monitor Event Flow
```bash
# Consume from a topic
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic test.debate.events \
  --from-beginning
```

### 3. Check Consumer Groups
```bash
# List consumer groups
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --list

# Check group lag
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group zamaz-test-group \
  --describe
```

### 4. Debug Serialization
```python
# Test event serialization
serializer = EventSerializer()
data = serializer.serialize(event)
print(json.loads(data))  # Inspect serialized format

# Test deserialization
deserializer = EventDeserializer()
register_all_events()
event = deserializer.deserialize(data)
```

## Common Issues and Solutions

### Issue: Events Not Appearing in Kafka
**Check**:
1. Producer flush: `producer.flush()`
2. Topic exists: `kafka-topics --list`
3. Correct bootstrap servers
4. Network connectivity

**Solution**:
```python
# Ensure flush after publish
producer.publish(event, context)
producer.flush(timeout=5.0)
```

### Issue: Consumer Not Receiving Events
**Check**:
1. Consumer group ID
2. Topic subscription
3. Offset position
4. Consumer poll timeout

**Solution**:
```python
# Reset consumer offset
consumer.seek_to_beginning()
# Or use auto.offset.reset=earliest
```

### Issue: Serialization Failures
**Check**:
1. Event class registered
2. All fields serializable
3. UUID and datetime handling

**Solution**:
```python
# Register event class
EventDeserializer.register_event_class(YourEvent)

# Ensure all fields are serializable
@dataclass(frozen=True)
class YourEvent(DomainEvent):
    # Use basic types or implement to_dict()
```

### Issue: High Latency
**Check**:
1. Batch settings
2. Network latency
3. Consumer poll interval
4. Partition count

**Solution**:
```python
# Optimize batch settings
config.batch_size = 32768
config.linger_ms = 50

# Increase partitions for parallelism
config.num_partitions = 10
```

## Performance Optimization

### 1. Batch Processing
```python
# Use batch producer for bulk events
batch_producer = BatchEventProducer(config)
for event in events:
    batch_producer.add_event(event, context)
batch_producer.flush_batch()
```

### 2. Compression
```python
# Enable compression
config.compression_type = "gzip"  # or "lz4", "snappy"
```

### 3. Parallel Consumers
```python
# Use MultiContextConsumer for parallel processing
multi_consumer = MultiContextConsumer(config)
multi_consumer.add_context("debate")
multi_consumer.add_context("testing")
await multi_consumer.start()
```

### 4. Partition Strategy
```python
# Use aggregate_id for partition key
producer.publish(event, context, key=str(event.aggregate_id))
# Ensures order within aggregate
```

## Monitoring and Metrics

### 1. Bridge Metrics
```python
metrics = bridge.get_metrics()
print(f"Bridged events: {metrics['bridged_event_types']}")
print(f"Active consumers: {metrics['active_consumers']}")
print(f"Event counts: {metrics['event_bus_metrics']}")
```

### 2. Kafka Metrics
```bash
# JMX metrics (if enabled)
kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec
kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec
kafka.consumer:type=consumer-fetch-manager-metrics
```

### 3. Application Metrics
```python
# Track in your monitoring system
statsd.gauge('kafka.events.published', count)
statsd.gauge('kafka.events.consumed', count)
statsd.gauge('kafka.consumer.lag', lag)
```

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Start Kafka
  run: docker-compose -f docker-compose.test.yml up -d kafka

- name: Wait for Kafka
  run: |
    timeout 60 bash -c 'until nc -z localhost 9092; do sleep 1; done'

- name: Run Kafka Integration Tests
  run: pytest tests/integration/test_kafka_integration.py

- name: Stop Kafka
  run: docker-compose -f docker-compose.test.yml down
```

### Test Coverage
```bash
# Run with coverage
pytest tests/integration/test_kafka_integration.py \
  --cov=src/infrastructure/kafka \
  --cov=src/events \
  --cov-report=html
```

## Best Practices

1. **Always Bridge Both Ways**: Enable both to_kafka and from_kafka for complete flow
2. **Use Testcontainers**: For reliable, isolated Kafka instances in tests
3. **Test Serialization First**: Ensure events serialize correctly before integration
4. **Monitor Consumer Lag**: Keep track of processing delays
5. **Handle Failures Gracefully**: Local events should work even if Kafka is down
6. **Use Proper Partitioning**: Partition by aggregate_id for ordering guarantees
7. **Implement Idempotency**: Handle duplicate events gracefully
8. **Version Your Events**: Plan for schema evolution

## Conclusion

The Kafka integration provides:
- ✅ Distributed event streaming across services
- ✅ Event persistence and replay capability
- ✅ Horizontal scaling through partitions
- ✅ Resilience with local fallback
- ✅ High throughput for millions of events
- ✅ Loose coupling between contexts

Testing ensures these benefits are realized while maintaining system reliability.