"""
Kafka Event Consumer

Consumes domain events from Kafka topics and dispatches to handlers.
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

from confluent_kafka import Consumer, KafkaError, TopicPartition

from src.events import DomainEvent, get_event_bus
from .config import KafkaConfig, TopicMapping
from .serialization import EventDeserializer

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    """Consumes domain events from Kafka"""
    
    def __init__(self, config: KafkaConfig, contexts: List[str]):
        """
        Initialize Kafka consumer.
        
        Args:
            config: Kafka configuration
            contexts: List of contexts to consume events for
        """
        self.config = config
        self.contexts = contexts
        self.consumer = Consumer(config.consumer_config)
        self.deserializer = EventDeserializer()
        self.event_bus = get_event_bus()
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        # Subscribe to topics
        topics = self._get_topics_for_contexts(contexts)
        self.consumer.subscribe(topics)
        
        logger.info(f"Kafka consumer subscribed to topics: {topics}")
    
    def _get_topics_for_contexts(self, contexts: List[str]) -> List[str]:
        """Get Kafka topics for the specified contexts"""
        topics = []
        for context in contexts:
            topic = TopicMapping.CONTEXT_TOPICS.get(context)
            if topic:
                topics.append(f"{self.config.topic_prefix}{topic}")
        return topics
    
    async def start(self) -> None:
        """Start consuming events"""
        self._running = True
        logger.info("Kafka consumer started")
        
        while self._running:
            try:
                # Poll for messages
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    self._handle_error(msg.error())
                    continue
                
                # Process message
                await self._process_message(msg)
                
            except Exception as e:
                logger.error(f"Error in consumer loop: {str(e)}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _process_message(self, msg) -> None:
        """Process a Kafka message"""
        try:
            # Deserialize event
            event = self.deserializer.deserialize(msg.value())
            
            if event is None:
                logger.warning(f"Failed to deserialize message from {msg.topic()}")
                # Commit anyway to avoid getting stuck
                self.consumer.commit(msg)
                return
            
            # Get context from headers
            headers = dict(msg.headers() or [])
            context = headers.get('context', b'').decode('utf-8')
            
            logger.debug(
                f"Processing {event.event_type} from {msg.topic()} "
                f"[partition {msg.partition()}] at offset {msg.offset()}"
            )
            
            # Publish to local event bus
            await self.event_bus.publish(event)
            
            # Commit offset after successful processing
            self.consumer.commit(msg)
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            # TODO: Send to dead letter queue
            # For now, commit to avoid reprocessing
            self.consumer.commit(msg)
    
    def _handle_error(self, error: KafkaError) -> None:
        """Handle Kafka errors"""
        if error.code() == KafkaError._PARTITION_EOF:
            # End of partition, not an error
            logger.debug(f"Reached end of partition: {error}")
        else:
            logger.error(f"Kafka error: {error}")
    
    def stop(self) -> None:
        """Stop consuming events"""
        self._running = False
        self.consumer.close()
        self._executor.shutdown(wait=True)
        logger.info("Kafka consumer stopped")
    
    def pause(self, partitions: List[TopicPartition]) -> None:
        """Pause consumption from specific partitions"""
        self.consumer.pause(partitions)
        logger.info(f"Paused partitions: {partitions}")
    
    def resume(self, partitions: List[TopicPartition]) -> None:
        """Resume consumption from specific partitions"""
        self.consumer.resume(partitions)
        logger.info(f"Resumed partitions: {partitions}")


class MultiContextConsumer:
    """Manages multiple consumers for different contexts"""
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize multi-context consumer.
        
        Args:
            config: Kafka configuration
        """
        self.config = config
        self.consumers: Dict[str, KafkaEventConsumer] = {}
        self._tasks: List[asyncio.Task] = []
    
    def add_context(self, context: str) -> None:
        """
        Add a context to consume events for.
        
        Args:
            context: The bounded context name
        """
        if context not in self.consumers:
            # Create dedicated consumer for context
            consumer_config = self.config.consumer_config.copy()
            consumer_config['group.id'] = f"{self.config.consumer_group_id}-{context}"
            
            config = KafkaConfig(
                bootstrap_servers=self.config.bootstrap_servers,
                consumer_config=consumer_config,
                topic_prefix=self.config.topic_prefix,
            )
            
            consumer = KafkaEventConsumer(config, [context])
            self.consumers[context] = consumer
            
            logger.info(f"Added consumer for context: {context}")
    
    async def start(self) -> None:
        """Start all consumers"""
        for context, consumer in self.consumers.items():
            task = asyncio.create_task(
                consumer.start(),
                name=f"consumer-{context}"
            )
            self._tasks.append(task)
        
        logger.info(f"Started {len(self.consumers)} context consumers")
        
        # Wait for all consumers
        await asyncio.gather(*self._tasks, return_exceptions=True)
    
    def stop(self) -> None:
        """Stop all consumers"""
        for consumer in self.consumers.values():
            consumer.stop()
        
        # Cancel tasks
        for task in self._tasks:
            task.cancel()
        
        logger.info("All consumers stopped")


class EventReplayConsumer:
    """Special consumer for replaying events from specific offsets"""
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize replay consumer.
        
        Args:
            config: Kafka configuration
        """
        # Use unique group ID for replay
        replay_config = config.consumer_config.copy()
        replay_config['group.id'] = f"{config.consumer_group_id}-replay"
        replay_config['enable.auto.commit'] = False
        
        self.config = config
        self.consumer = Consumer(replay_config)
        self.deserializer = EventDeserializer()
    
    async def replay_from_timestamp(
        self,
        topics: List[str],
        timestamp_ms: int,
        event_handler: Callable[[DomainEvent], None],
        max_events: Optional[int] = None,
    ) -> int:
        """
        Replay events from a specific timestamp.
        
        Args:
            topics: Topics to replay from
            timestamp_ms: Start timestamp in milliseconds
            event_handler: Handler for replayed events
            max_events: Maximum number of events to replay
            
        Returns:
            Number of events replayed
        """
        # Get partitions for topics
        partitions = []
        for topic in topics:
            topic_metadata = self.consumer.list_topics(topic)
            if topic in topic_metadata.topics:
                for partition_id in topic_metadata.topics[topic].partitions:
                    partitions.append(
                        TopicPartition(topic, partition_id, timestamp_ms)
                    )
        
        # Seek to timestamp
        offsets = self.consumer.offsets_for_times(partitions)
        self.consumer.assign(offsets)
        
        # Replay events
        count = 0
        while max_events is None or count < max_events:
            msg = self.consumer.poll(timeout=1.0)
            
            if msg is None:
                break
            
            if msg.error():
                continue
            
            # Deserialize and handle event
            event = self.deserializer.deserialize(msg.value())
            if event:
                await event_handler(event)
                count += 1
        
        self.consumer.close()
        return count