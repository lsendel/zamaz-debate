"""
Kafka Consumer Implementation

This module implements the Kafka consumer for processing events.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition

from .config import KafkaConfig
from .serializers import EventSerializer

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """
    Kafka consumer for processing events
    
    This consumer handles event deserialization, processing, and error handling.
    """
    
    def __init__(self, config: KafkaConfig, consumer_id: str, topics: List[str], 
                 handler_callback: Callable[[Dict[str, Any]], None], 
                 serializer: Optional[EventSerializer] = None):
        """
        Initialize the Kafka consumer
        
        Args:
            config: Kafka configuration
            consumer_id: Unique identifier for this consumer
            topics: List of topics to consume from
            handler_callback: Async function to handle received events
            serializer: Event serializer (uses default JSON serializer if None)
        """
        self.config = config
        self.consumer_id = consumer_id
        self.topics = topics
        self.handler_callback = handler_callback
        self.serializer = serializer or EventSerializer()
        
        self._consumer: Optional[Consumer] = None
        self._running = False
        self._consume_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            "messages_consumed": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "bytes_consumed": 0,
            "last_error": None,
            "last_consumed_at": None,
            "last_processed_at": None,
        }
    
    async def start(self):
        """Start the consumer"""
        if self._running:
            return
        
        logger.info(f"Starting Kafka consumer {self.consumer_id} for topics: {self.topics}")
        
        try:
            # Create consumer with configuration
            consumer_config = self.config.to_consumer_config()
            consumer_config["group.id"] = f"{self.config.group_id}-{self.consumer_id}"
            
            self._consumer = Consumer(consumer_config)
            
            # Subscribe to topics
            self._consumer.subscribe(self.topics)
            
            # Start consume task
            self._consume_task = asyncio.create_task(self._consume_loop())
            
            self._running = True
            logger.info(f"Kafka consumer {self.consumer_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer {self.consumer_id}: {e}")
            self._stats["last_error"] = str(e)
            raise
    
    async def stop(self):
        """Stop the consumer"""
        if not self._running:
            return
        
        logger.info(f"Stopping Kafka consumer {self.consumer_id}...")
        
        try:
            # Stop consume task
            if self._consume_task:
                self._consume_task.cancel()
                try:
                    await self._consume_task
                except asyncio.CancelledError:
                    pass
            
            # Close consumer
            if self._consumer:
                await self._close_consumer()
                self._consumer = None
            
            self._running = False
            logger.info(f"Kafka consumer {self.consumer_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Kafka consumer {self.consumer_id}: {e}")
            self._stats["last_error"] = str(e)
    
    async def _consume_loop(self):
        """Main consume loop"""
        while self._running:
            try:
                # Poll for messages
                message = await self._poll_message()
                
                if message is None:
                    continue
                
                if message.error():
                    self._handle_kafka_error(message.error())
                    continue
                
                # Process message
                await self._process_message(message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consume loop for {self.consumer_id}: {e}")
                self._stats["last_error"] = str(e)
                # Add delay to prevent tight error loop
                await asyncio.sleep(1.0)
    
    async def _poll_message(self):
        """Poll for a message"""
        if not self._consumer:
            return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._consumer.poll, 1.0)
    
    async def _process_message(self, message):
        """Process a received message"""
        try:
            # Update stats
            self._stats["messages_consumed"] += 1
            self._stats["bytes_consumed"] += len(message.value())
            self._stats["last_consumed_at"] = datetime.now()
            
            # Deserialize message
            try:
                event_data = self.serializer.deserialize(message.value())
            except Exception as e:
                logger.error(f"Failed to deserialize message: {e}")
                self._stats["messages_failed"] += 1
                await self._handle_dead_letter(message, f"Deserialization error: {e}")
                return
            
            # Add message metadata
            event_data["kafka_metadata"] = {
                "topic": message.topic(),
                "partition": message.partition(),
                "offset": message.offset(),
                "timestamp": message.timestamp()[1] if message.timestamp()[1] else None,
                "key": message.key().decode("utf-8") if message.key() else None,
                "headers": {k: v.decode("utf-8") for k, v in message.headers() or []},
                "consumer_id": self.consumer_id,
                "processed_at": datetime.now().isoformat(),
            }
            
            # Call handler
            if asyncio.iscoroutinefunction(self.handler_callback):
                await self.handler_callback(event_data)
            else:
                self.handler_callback(event_data)
            
            # Update stats
            self._stats["messages_processed"] += 1
            self._stats["last_processed_at"] = datetime.now()
            
            # Commit offset
            await self._commit_offset(message)
            
            logger.debug(f"Processed message from {message.topic()} partition {message.partition()} offset {message.offset()}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self._stats["messages_failed"] += 1
            self._stats["last_error"] = str(e)
            await self._handle_processing_error(message, e)
    
    async def _commit_offset(self, message):
        """Commit message offset"""
        if not self._consumer:
            return
        
        try:
            if not self.config.enable_auto_commit:
                # Manual commit
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._consumer.commit, message)
        except Exception as e:
            logger.error(f"Error committing offset: {e}")
    
    async def _handle_processing_error(self, message, error):
        """Handle processing errors"""
        try:
            # Try to send to dead letter queue
            await self._handle_dead_letter(message, f"Processing error: {error}")
        except Exception as e:
            logger.error(f"Error handling processing error: {e}")
    
    async def _handle_dead_letter(self, message, error_reason: str):
        """Handle dead letter messages"""
        try:
            # Create dead letter topic name
            dead_letter_topic = self.config.get_dead_letter_topic_name(message.topic())
            
            # Dead letter payload
            dead_letter_data = {
                "original_topic": message.topic(),
                "original_partition": message.partition(),
                "original_offset": message.offset(),
                "original_timestamp": message.timestamp()[1] if message.timestamp()[1] else None,
                "original_key": message.key().decode("utf-8") if message.key() else None,
                "original_value": message.value().decode("utf-8", errors="ignore"),
                "error_reason": error_reason,
                "consumer_id": self.consumer_id,
                "failed_at": datetime.now().isoformat(),
            }
            
            # Log dead letter
            logger.warning(f"Message sent to dead letter queue: {dead_letter_topic}")
            
            # TODO: Implement dead letter producer
            # For now, just log the dead letter data
            logger.info(f"Dead letter data: {dead_letter_data}")
            
        except Exception as e:
            logger.error(f"Error handling dead letter: {e}")
    
    def _handle_kafka_error(self, error: KafkaError):
        """Handle Kafka errors"""
        if error.code() == KafkaError._PARTITION_EOF:
            logger.debug(f"Reached end of partition: {error}")
        elif error.code() == KafkaError._TIMED_OUT:
            logger.debug(f"Consumer timeout: {error}")
        else:
            logger.error(f"Kafka error: {error}")
            self._stats["last_error"] = str(error)
    
    async def _close_consumer(self):
        """Close the consumer"""
        if self._consumer:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._consumer.close)
    
    async def pause(self, partitions: Optional[List[TopicPartition]] = None):
        """Pause consumption"""
        if not self._consumer:
            return
        
        if partitions is None:
            # Pause all assigned partitions
            assignment = self._consumer.assignment()
            if assignment:
                partitions = assignment
        
        if partitions:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._consumer.pause, partitions)
            logger.info(f"Paused consumption for {len(partitions)} partitions")
    
    async def resume(self, partitions: Optional[List[TopicPartition]] = None):
        """Resume consumption"""
        if not self._consumer:
            return
        
        if partitions is None:
            # Resume all assigned partitions
            assignment = self._consumer.assignment()
            if assignment:
                partitions = assignment
        
        if partitions:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._consumer.resume, partitions)
            logger.info(f"Resumed consumption for {len(partitions)} partitions")
    
    async def seek_to_beginning(self, partitions: Optional[List[TopicPartition]] = None):
        """Seek to beginning of partitions"""
        if not self._consumer:
            return
        
        if partitions is None:
            assignment = self._consumer.assignment()
            if assignment:
                partitions = assignment
        
        if partitions:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._consumer.seek_to_beginning, partitions)
            logger.info(f"Seeked to beginning for {len(partitions)} partitions")
    
    async def seek_to_end(self, partitions: Optional[List[TopicPartition]] = None):
        """Seek to end of partitions"""
        if not self._consumer:
            return
        
        if partitions is None:
            assignment = self._consumer.assignment()
            if assignment:
                partitions = assignment
        
        if partitions:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._consumer.seek_to_end, partitions)
            logger.info(f"Seeked to end for {len(partitions)} partitions")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        return {
            **self._stats,
            "is_running": self._running,
            "consumer_id": self.consumer_id,
            "topics": self.topics,
        }
    
    def clear_stats(self):
        """Clear consumer statistics"""
        self._stats = {
            "messages_consumed": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "bytes_consumed": 0,
            "last_error": None,
            "last_consumed_at": None,
            "last_processed_at": None,
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "consumer_running": self._running,
            "consumer_id": self.consumer_id,
            "topics": self.topics,
            "last_error": self._stats["last_error"],
            "last_consumed_at": self._stats["last_consumed_at"],
            "last_processed_at": self._stats["last_processed_at"],
        }


class KafkaConsumerError(Exception):
    """Exception raised by Kafka consumer operations"""
    pass