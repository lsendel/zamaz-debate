"""
Kafka Producer Implementation

This module implements the Kafka producer for publishing events.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from uuid import uuid4

from confluent_kafka import Producer, KafkaError, KafkaException

from .config import KafkaConfig
from .serializers import EventSerializer

logger = logging.getLogger(__name__)


class KafkaProducer:
    """
    Kafka producer for publishing events
    
    This producer handles event serialization, partitioning, and delivery confirmation.
    """
    
    def __init__(self, config: KafkaConfig, serializer: Optional[EventSerializer] = None):
        """
        Initialize the Kafka producer
        
        Args:
            config: Kafka configuration
            serializer: Event serializer (uses default JSON serializer if None)
        """
        self.config = config
        self.serializer = serializer or EventSerializer()
        self._producer: Optional[Producer] = None
        self._running = False
        
        # Delivery confirmation tracking
        self._delivery_futures: Dict[str, asyncio.Future] = {}
        
        # Statistics
        self._stats = {
            "messages_produced": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "bytes_produced": 0,
            "last_error": None,
            "last_produced_at": None,
        }
    
    async def start(self):
        """Start the producer"""
        if self._running:
            return
        
        logger.info("Starting Kafka producer...")
        
        try:
            # Create producer with configuration
            producer_config = self.config.to_producer_config()
            self._producer = Producer(producer_config)
            
            # Start delivery report polling task
            self._poll_task = asyncio.create_task(self._poll_delivery_reports())
            
            self._running = True
            logger.info("Kafka producer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self._stats["last_error"] = str(e)
            raise
    
    async def stop(self):
        """Stop the producer"""
        if not self._running:
            return
        
        logger.info("Stopping Kafka producer...")
        
        try:
            # Cancel polling task
            if hasattr(self, '_poll_task'):
                self._poll_task.cancel()
                try:
                    await self._poll_task
                except asyncio.CancelledError:
                    pass
            
            # Flush remaining messages
            if self._producer:
                await self._flush_messages()
                self._producer = None
            
            # Cancel any pending delivery futures
            for future in self._delivery_futures.values():
                if not future.done():
                    future.cancel()
            self._delivery_futures.clear()
            
            self._running = False
            logger.info("Kafka producer stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Kafka producer: {e}")
            self._stats["last_error"] = str(e)
    
    async def produce(self, topic: str, event_data: Dict[str, Any], 
                     partition_key: Optional[str] = None, 
                     wait_for_delivery: bool = True) -> bool:
        """
        Produce an event to Kafka
        
        Args:
            topic: Topic to produce to
            event_data: Event data payload
            partition_key: Optional partition key for message routing
            wait_for_delivery: Whether to wait for delivery confirmation
            
        Returns:
            True if message was produced successfully
        """
        if not self._running or not self._producer:
            logger.warning("Producer not running, cannot produce message")
            return False
        
        try:
            # Add metadata to event
            enriched_event = self._enrich_event(event_data)
            
            # Serialize event
            serialized_data = self.serializer.serialize(enriched_event)
            
            # Generate message ID for tracking
            message_id = str(uuid4())
            
            # Create future for delivery confirmation if requested
            delivery_future = None
            if wait_for_delivery:
                delivery_future = asyncio.Future()
                self._delivery_futures[message_id] = delivery_future
            
            # Produce message
            self._producer.produce(
                topic=topic,
                key=partition_key,
                value=serialized_data,
                callback=lambda err, msg: self._delivery_callback(err, msg, message_id),
                headers={"message_id": message_id}
            )
            
            # Update stats
            self._stats["messages_produced"] += 1
            self._stats["bytes_produced"] += len(serialized_data)
            self._stats["last_produced_at"] = datetime.now()
            
            # Wait for delivery if requested
            if wait_for_delivery and delivery_future:
                try:
                    await asyncio.wait_for(delivery_future, timeout=30.0)
                    return True
                except asyncio.TimeoutError:
                    logger.warning(f"Delivery timeout for message {message_id}")
                    self._stats["messages_failed"] += 1
                    return False
                except Exception as e:
                    logger.error(f"Delivery error for message {message_id}: {e}")
                    self._stats["messages_failed"] += 1
                    return False
                finally:
                    # Clean up future
                    self._delivery_futures.pop(message_id, None)
            else:
                # Fire and forget mode
                return True
            
        except Exception as e:
            logger.error(f"Error producing message to {topic}: {e}")
            self._stats["messages_failed"] += 1
            self._stats["last_error"] = str(e)
            return False
    
    async def produce_batch(self, topic: str, events: list[Dict[str, Any]], 
                          partition_key_fn: Optional[Callable[[Dict], str]] = None) -> int:
        """
        Produce a batch of events
        
        Args:
            topic: Topic to produce to
            events: List of event data payloads
            partition_key_fn: Optional function to extract partition key from event
            
        Returns:
            Number of messages successfully produced
        """
        if not self._running or not self._producer:
            logger.warning("Producer not running, cannot produce batch")
            return 0
        
        successful_count = 0
        
        for event_data in events:
            try:
                partition_key = partition_key_fn(event_data) if partition_key_fn else None
                success = await self.produce(topic, event_data, partition_key, wait_for_delivery=False)
                if success:
                    successful_count += 1
            except Exception as e:
                logger.error(f"Error producing event in batch: {e}")
        
        # Flush the batch
        await self._flush_messages()
        
        logger.info(f"Produced {successful_count}/{len(events)} messages in batch to {topic}")
        return successful_count
    
    async def _flush_messages(self):
        """Flush pending messages"""
        if self._producer:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._producer.flush, 10.0)
    
    async def _poll_delivery_reports(self):
        """Poll for delivery reports"""
        while self._running:
            try:
                if self._producer:
                    # Poll for delivery reports
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._producer.poll, 0.1)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling delivery reports: {e}")
                await asyncio.sleep(1.0)
    
    def _delivery_callback(self, err: KafkaError, msg, message_id: str):
        """Handle delivery report callback"""
        try:
            if err is not None:
                logger.error(f"Message delivery failed: {err}")
                self._stats["messages_failed"] += 1
                self._stats["last_error"] = str(err)
                
                # Set error on future if it exists
                if message_id in self._delivery_futures:
                    future = self._delivery_futures[message_id]
                    if not future.done():
                        future.set_exception(KafkaException(err))
            else:
                logger.debug(f"Message delivered to {msg.topic()} partition {msg.partition()} offset {msg.offset()}")
                self._stats["messages_delivered"] += 1
                
                # Set success on future if it exists
                if message_id in self._delivery_futures:
                    future = self._delivery_futures[message_id]
                    if not future.done():
                        future.set_result(True)
                        
        except Exception as e:
            logger.error(f"Error in delivery callback: {e}")
    
    def _enrich_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to event"""
        return {
            **event_data,
            "kafka_metadata": {
                "produced_at": datetime.now().isoformat(),
                "producer_id": id(self),
                "message_id": str(uuid4()),
            }
        }
    
    def is_ready(self) -> bool:
        """Check if producer is ready"""
        return self._running and self._producer is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics"""
        return {
            **self._stats,
            "is_running": self._running,
            "pending_deliveries": len(self._delivery_futures),
        }
    
    def clear_stats(self):
        """Clear producer statistics"""
        self._stats = {
            "messages_produced": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "bytes_produced": 0,
            "last_error": None,
            "last_produced_at": None,
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "producer_running": self._running,
            "producer_ready": self.is_ready(),
            "pending_deliveries": len(self._delivery_futures),
            "last_error": self._stats["last_error"],
            "last_produced_at": self._stats["last_produced_at"],
        }


class KafkaProducerError(Exception):
    """Exception raised by Kafka producer operations"""
    pass