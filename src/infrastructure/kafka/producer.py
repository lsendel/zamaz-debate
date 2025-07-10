"""
Kafka Event Producer

Publishes domain events to Kafka topics.
"""

import logging
from typing import Callable, Optional
from uuid import UUID

from confluent_kafka import Producer
from confluent_kafka.error import KafkaError

from src.events import DomainEvent
from .config import KafkaConfig, TopicMapping
from .serialization import EventSerializer

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Publishes domain events to Kafka"""
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize Kafka producer.
        
        Args:
            config: Kafka configuration
        """
        self.config = config
        self.producer = Producer(config.producer_config)
        self.serializer = EventSerializer()
        self._delivery_callbacks = {}
        
        logger.info(f"Kafka producer initialized with servers: {config.bootstrap_servers}")
    
    def publish(
        self,
        event: DomainEvent,
        context: str,
        key: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        """
        Publish an event to Kafka.
        
        Args:
            event: The domain event to publish
            context: The bounded context publishing the event
            key: Optional partition key (defaults to aggregate_id)
            callback: Optional delivery callback
        """
        try:
            # Determine topic
            topic = TopicMapping.get_topic_for_event(
                event.event_type,
                context,
                self.config
            )
            
            # Serialize event
            event_data = self.serializer.serialize(event)
            
            # Use aggregate_id as key if not provided
            if key is None:
                key = str(event.aggregate_id)
            
            # Store callback if provided
            if callback:
                self._delivery_callbacks[str(event.event_id)] = callback
            
            # Produce to Kafka
            self.producer.produce(
                topic=topic,
                key=key.encode('utf-8') if key else None,
                value=event_data,
                on_delivery=self._delivery_callback,
                headers={
                    'event_type': event.event_type,
                    'context': context,
                    'event_id': str(event.event_id),
                }
            )
            
            # Trigger send (non-blocking)
            self.producer.poll(0)
            
            logger.debug(f"Published {event.event_type} to topic {topic}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {str(e)}")
            raise
    
    def _delivery_callback(self, err: Optional[KafkaError], msg) -> None:
        """Handle delivery confirmation"""
        if err:
            logger.error(f"Event delivery failed: {err}")
            # TODO: Implement retry logic or dead letter queue
        else:
            logger.debug(
                f"Event delivered to {msg.topic()} "
                f"[partition {msg.partition()}] "
                f"at offset {msg.offset()}"
            )
            
            # Call custom callback if provided
            event_id = msg.headers().get('event_id')
            if event_id and event_id in self._delivery_callbacks:
                callback = self._delivery_callbacks.pop(event_id)
                callback(err, msg)
    
    def flush(self, timeout: float = 10.0) -> int:
        """
        Flush pending messages.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Number of messages still pending
        """
        return self.producer.flush(timeout)
    
    def close(self) -> None:
        """Close the producer"""
        self.producer.flush(30.0)  # Wait up to 30 seconds for pending messages
        logger.info("Kafka producer closed")


class BatchEventProducer:
    """Publishes events in batches for better performance"""
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize batch producer.
        
        Args:
            config: Kafka configuration
        """
        self.config = config
        self.producer = Producer(config.producer_config)
        self.serializer = EventSerializer()
        self._batch = []
        self._batch_size = 100  # Configurable batch size
        
    def add_event(
        self,
        event: DomainEvent,
        context: str,
        key: Optional[str] = None,
    ) -> None:
        """
        Add event to batch.
        
        Args:
            event: The domain event
            context: The bounded context
            key: Optional partition key
        """
        self._batch.append({
            'event': event,
            'context': context,
            'key': key or str(event.aggregate_id),
        })
        
        # Auto-flush if batch is full
        if len(self._batch) >= self._batch_size:
            self.flush_batch()
    
    def flush_batch(self) -> int:
        """
        Flush the current batch.
        
        Returns:
            Number of events flushed
        """
        if not self._batch:
            return 0
        
        count = 0
        for item in self._batch:
            try:
                event = item['event']
                context = item['context']
                key = item['key']
                
                topic = TopicMapping.get_topic_for_event(
                    event.event_type,
                    context,
                    self.config
                )
                
                event_data = self.serializer.serialize(event)
                
                self.producer.produce(
                    topic=topic,
                    key=key.encode('utf-8'),
                    value=event_data,
                    headers={
                        'event_type': event.event_type,
                        'context': context,
                        'event_id': str(event.event_id),
                    }
                )
                count += 1
                
            except Exception as e:
                logger.error(f"Failed to produce event in batch: {str(e)}")
        
        # Clear batch
        self._batch.clear()
        
        # Trigger sends
        self.producer.poll(0)
        
        return count
    
    def close(self) -> None:
        """Close the batch producer"""
        # Flush any remaining events
        self.flush_batch()
        self.producer.flush(30.0)
        logger.info("Batch producer closed")