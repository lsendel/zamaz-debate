"""
Kafka Client Management

This module provides a high-level interface for Kafka operations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, ConfigResource, ResourceType

from .config import KafkaConfig
from .producer import KafkaProducer
from .consumer import KafkaConsumer
from .topics import TopicManager

logger = logging.getLogger(__name__)


class KafkaClient:
    """
    High-level Kafka client for the Zamaz Debate System
    
    This client provides a unified interface for producing and consuming events,
    managing topics, and monitoring Kafka operations.
    """
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        """
        Initialize the Kafka client
        
        Args:
            config: Kafka configuration. If None, will load from environment.
        """
        self.config = config or KafkaConfig.from_env()
        self._producer: Optional[KafkaProducer] = None
        self._consumers: Dict[str, KafkaConsumer] = {}
        self._topic_manager: Optional[TopicManager] = None
        self._admin_client: Optional[AdminClient] = None
        self._running = False
        
        # Statistics
        self._stats = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "production_errors": 0,
            "consumption_errors": 0,
            "topics_created": 0,
            "active_consumers": 0,
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
    
    async def start(self):
        """Start the Kafka client"""
        if self._running:
            return
        
        logger.info("Starting Kafka client...")
        
        # Initialize admin client
        self._admin_client = AdminClient(self.config.to_producer_config())
        
        # Initialize topic manager
        self._topic_manager = TopicManager(self.config, self._admin_client)
        
        # Initialize producer
        self._producer = KafkaProducer(self.config)
        await self._producer.start()
        
        # Ensure required topics exist
        await self._ensure_required_topics()
        
        self._running = True
        logger.info("Kafka client started successfully")
    
    async def stop(self):
        """Stop the Kafka client"""
        if not self._running:
            return
        
        logger.info("Stopping Kafka client...")
        
        # Stop all consumers
        for consumer in self._consumers.values():
            await consumer.stop()
        self._consumers.clear()
        
        # Stop producer
        if self._producer:
            await self._producer.stop()
            self._producer = None
        
        # Close admin client
        if self._admin_client:
            # Admin client doesn't have an async close method
            self._admin_client = None
        
        self._running = False
        logger.info("Kafka client stopped")
    
    async def produce_event(self, event_type: str, event_data: Dict[str, Any], 
                          partition_key: Optional[str] = None) -> bool:
        """
        Produce an event to Kafka
        
        Args:
            event_type: Type of event (used for topic routing)
            event_data: Event data payload
            partition_key: Optional partition key for message routing
            
        Returns:
            True if message was produced successfully
        """
        if not self._running or not self._producer:
            logger.warning("Kafka client not running, cannot produce event")
            return False
        
        try:
            topic = self.config.get_topic_name(event_type)
            success = await self._producer.produce(topic, event_data, partition_key)
            
            if success:
                self._stats["messages_produced"] += 1
                logger.debug(f"Produced event to topic {topic}")
            else:
                self._stats["production_errors"] += 1
                logger.error(f"Failed to produce event to topic {topic}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error producing event: {e}")
            self._stats["production_errors"] += 1
            return False
    
    async def create_consumer(self, consumer_id: str, event_types: List[str], 
                            handler_callback) -> bool:
        """
        Create a consumer for specific event types
        
        Args:
            consumer_id: Unique identifier for this consumer
            event_types: List of event types to consume
            handler_callback: Async function to handle received events
            
        Returns:
            True if consumer was created successfully
        """
        if not self._running:
            logger.warning("Kafka client not running, cannot create consumer")
            return False
        
        if consumer_id in self._consumers:
            logger.warning(f"Consumer {consumer_id} already exists")
            return False
        
        try:
            # Convert event types to topic names
            topics = [self.config.get_topic_name(event_type) for event_type in event_types]
            
            # Create consumer
            consumer = KafkaConsumer(
                config=self.config,
                consumer_id=consumer_id,
                topics=topics,
                handler_callback=handler_callback
            )
            
            # Start consumer
            await consumer.start()
            
            self._consumers[consumer_id] = consumer
            self._stats["active_consumers"] = len(self._consumers)
            
            logger.info(f"Created consumer {consumer_id} for topics: {topics}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating consumer {consumer_id}: {e}")
            return False
    
    async def remove_consumer(self, consumer_id: str) -> bool:
        """
        Remove a consumer
        
        Args:
            consumer_id: ID of the consumer to remove
            
        Returns:
            True if consumer was removed successfully
        """
        if consumer_id not in self._consumers:
            logger.warning(f"Consumer {consumer_id} not found")
            return False
        
        try:
            consumer = self._consumers[consumer_id]
            await consumer.stop()
            del self._consumers[consumer_id]
            
            self._stats["active_consumers"] = len(self._consumers)
            logger.info(f"Removed consumer {consumer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing consumer {consumer_id}: {e}")
            return False
    
    async def create_topic(self, event_type: str, num_partitions: Optional[int] = None,
                          replication_factor: Optional[int] = None) -> bool:
        """
        Create a topic for an event type
        
        Args:
            event_type: Event type name
            num_partitions: Number of partitions (uses config default if None)
            replication_factor: Replication factor (uses config default if None)
            
        Returns:
            True if topic was created successfully
        """
        if not self._running or not self._topic_manager:
            logger.warning("Kafka client not running, cannot create topic")
            return False
        
        try:
            topic_name = self.config.get_topic_name(event_type)
            success = await self._topic_manager.create_topic(
                topic_name, 
                num_partitions or self.config.num_partitions,
                replication_factor or self.config.replication_factor
            )
            
            if success:
                self._stats["topics_created"] += 1
                logger.info(f"Created topic {topic_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating topic for {event_type}: {e}")
            return False
    
    async def list_topics(self) -> List[str]:
        """
        List all topics
        
        Returns:
            List of topic names
        """
        if not self._running or not self._topic_manager:
            return []
        
        try:
            return await self._topic_manager.list_topics()
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            return []
    
    async def get_topic_metadata(self, topic_name: str) -> Optional[Dict]:
        """
        Get metadata for a topic
        
        Args:
            topic_name: Name of the topic
            
        Returns:
            Topic metadata dictionary or None if not found
        """
        if not self._running or not self._topic_manager:
            return None
        
        try:
            return await self._topic_manager.get_topic_metadata(topic_name)
        except Exception as e:
            logger.error(f"Error getting topic metadata for {topic_name}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            **self._stats,
            "is_running": self._running,
            "config": {
                "bootstrap_servers": self.config.bootstrap_servers,
                "group_id": self.config.group_id,
                "topic_prefix": self.config.topic_prefix,
            }
        }
    
    def clear_stats(self):
        """Clear client statistics"""
        self._stats = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "production_errors": 0,
            "consumption_errors": 0,
            "topics_created": 0,
            "active_consumers": len(self._consumers),
        }
    
    async def _ensure_required_topics(self):
        """Ensure required topics exist"""
        required_event_types = [
            "debate-events",
            "decision-events", 
            "evolution-events",
            "webhook-events",
            "metrics-events"
        ]
        
        for event_type in required_event_types:
            await self.create_topic(event_type)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check
        
        Returns:
            Health check results
        """
        health = {
            "kafka_client_running": self._running,
            "producer_ready": self._producer is not None and self._producer.is_ready(),
            "active_consumers": len(self._consumers),
            "topics_available": len(await self.list_topics()),
            "last_error": None,
        }
        
        # Check producer health
        if self._producer:
            producer_health = await self._producer.health_check()
            health["producer_health"] = producer_health
        
        # Check consumer health
        consumer_health = {}
        for consumer_id, consumer in self._consumers.items():
            consumer_health[consumer_id] = await consumer.health_check()
        health["consumer_health"] = consumer_health
        
        return health


class KafkaClientError(Exception):
    """Exception raised by Kafka client operations"""
    pass


class KafkaConnectionError(KafkaClientError):
    """Exception raised when Kafka connection fails"""
    pass


class KafkaTopicError(KafkaClientError):
    """Exception raised when topic operations fail"""
    pass