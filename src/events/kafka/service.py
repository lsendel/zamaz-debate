"""
Kafka Service Integration

This module provides a service layer for integrating Kafka with the Zamaz Debate System.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .client import KafkaClient
from .config import KafkaConfig
from .event_bridge import KafkaEventBridge
from .processors import ProcessorManager
from src.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class KafkaService:
    """
    Main service for Kafka integration
    
    This service coordinates all Kafka components and provides a unified interface
    for the Zamaz Debate System.
    """
    
    def __init__(self, event_bus: EventBus, config: Optional[KafkaConfig] = None,
                 data_dir: Optional[Path] = None):
        """
        Initialize the Kafka service
        
        Args:
            event_bus: The existing event bus instance
            config: Kafka configuration (uses default if None)
            data_dir: Data directory for storing Kafka-related data
        """
        self.event_bus = event_bus
        self.config = config or KafkaConfig.from_env()
        self.data_dir = data_dir or Path("data/kafka")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Core components
        self.kafka_client: Optional[KafkaClient] = None
        self.event_bridge: Optional[KafkaEventBridge] = None
        self.processor_manager: Optional[ProcessorManager] = None
        
        # Service state
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            "service_started_at": None,
            "service_uptime_seconds": 0,
            "components_started": 0,
            "components_failed": 0,
            "last_health_check": None,
            "last_error": None,
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
    
    async def start(self):
        """Start the Kafka service"""
        if self._running:
            return
        
        logger.info("Starting Kafka service...")
        
        try:
            # Initialize Kafka client
            self.kafka_client = KafkaClient(self.config)
            await self.kafka_client.start()
            self._stats["components_started"] += 1
            
            # Initialize event bridge
            self.event_bridge = KafkaEventBridge(self.event_bus, self.config)
            await self.event_bridge.start()
            self._stats["components_started"] += 1
            
            # Initialize processor manager
            self.processor_manager = ProcessorManager(self.kafka_client)
            await self.processor_manager.start()
            self._stats["components_started"] += 1
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            # Update stats
            self._stats["service_started_at"] = asyncio.get_event_loop().time()
            self._running = True
            
            logger.info("Kafka service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka service: {e}")
            self._stats["components_failed"] += 1
            self._stats["last_error"] = str(e)
            await self.stop()  # Cleanup on failure
            raise
    
    async def stop(self):
        """Stop the Kafka service"""
        if not self._running:
            return
        
        logger.info("Stopping Kafka service...")
        
        try:
            # Stop health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Stop processor manager
            if self.processor_manager:
                await self.processor_manager.stop()
                self.processor_manager = None
            
            # Stop event bridge
            if self.event_bridge:
                await self.event_bridge.stop()
                self.event_bridge = None
            
            # Stop Kafka client
            if self.kafka_client:
                await self.kafka_client.stop()
                self.kafka_client = None
            
            self._running = False
            logger.info("Kafka service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Kafka service: {e}")
            self._stats["last_error"] = str(e)
    
    async def publish_event(self, event_type: str, event_data: Dict[str, Any], 
                           partition_key: Optional[str] = None) -> bool:
        """
        Publish an event to Kafka
        
        Args:
            event_type: Type of event
            event_data: Event data payload
            partition_key: Optional partition key for message routing
            
        Returns:
            True if event was published successfully
        """
        if not self._running or not self.kafka_client:
            logger.warning("Kafka service not running, cannot publish event")
            return False
        
        try:
            return await self.kafka_client.produce_event(event_type, event_data, partition_key)
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            self._stats["last_error"] = str(e)
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
        if not self._running or not self.kafka_client:
            logger.warning("Kafka service not running, cannot create topic")
            return False
        
        try:
            return await self.kafka_client.create_topic(event_type, num_partitions, replication_factor)
        except Exception as e:
            logger.error(f"Error creating topic: {e}")
            self._stats["last_error"] = str(e)
            return False
    
    async def list_topics(self) -> List[str]:
        """
        List all topics
        
        Returns:
            List of topic names
        """
        if not self._running or not self.kafka_client:
            return []
        
        try:
            return await self.kafka_client.list_topics()
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            self._stats["last_error"] = str(e)
            return []
    
    async def get_topic_metadata(self, topic_name: str) -> Optional[Dict]:
        """
        Get metadata for a topic
        
        Args:
            topic_name: Name of the topic
            
        Returns:
            Topic metadata dictionary or None if not found
        """
        if not self._running or not self.kafka_client:
            return None
        
        try:
            return await self.kafka_client.get_topic_metadata(topic_name)
        except Exception as e:
            logger.error(f"Error getting topic metadata: {e}")
            self._stats["last_error"] = str(e)
            return None
    
    def add_event_handler(self, event_type: str, handler_callback):
        """
        Add a handler for consuming events from Kafka
        
        Args:
            event_type: Event type to handle
            handler_callback: Async function to handle events
        """
        if not self._running or not self.event_bridge:
            logger.warning("Kafka service not running, cannot add event handler")
            return
        
        self.event_bridge.add_consumer_handler(event_type, handler_callback)
    
    def remove_event_handler(self, event_type: str, handler_callback):
        """
        Remove a handler for consuming events from Kafka
        
        Args:
            event_type: Event type to stop handling
            handler_callback: Handler function to remove
        """
        if not self._running or not self.event_bridge:
            return
        
        self.event_bridge.remove_consumer_handler(event_type, handler_callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        stats = {
            **self._stats,
            "is_running": self._running,
            "config": {
                "bootstrap_servers": self.config.bootstrap_servers,
                "group_id": self.config.group_id,
                "topic_prefix": self.config.topic_prefix,
            }
        }
        
        # Add component stats
        if self.kafka_client:
            stats["kafka_client"] = self.kafka_client.get_stats()
        
        if self.event_bridge:
            stats["event_bridge"] = self.event_bridge.get_stats()
        
        if self.processor_manager:
            stats["processor_manager"] = self.processor_manager.get_stats()
        
        # Calculate uptime
        if self._stats["service_started_at"]:
            current_time = asyncio.get_event_loop().time()
            stats["service_uptime_seconds"] = current_time - self._stats["service_started_at"]
        
        return stats
    
    def clear_stats(self):
        """Clear service statistics"""
        self._stats = {
            "service_started_at": self._stats["service_started_at"],  # Keep start time
            "service_uptime_seconds": 0,
            "components_started": 0,
            "components_failed": 0,
            "last_health_check": None,
            "last_error": None,
        }
        
        # Clear component stats
        if self.kafka_client:
            self.kafka_client.clear_stats()
        
        if self.event_bridge:
            self.event_bridge.clear_stats()
        
        if self.processor_manager:
            self.processor_manager.clear_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Health check results
        """
        health = {
            "service_running": self._running,
            "kafka_available": False,
            "components_healthy": True,
            "last_error": self._stats["last_error"],
            "uptime_seconds": 0,
        }
        
        if self._stats["service_started_at"]:
            current_time = asyncio.get_event_loop().time()
            health["uptime_seconds"] = current_time - self._stats["service_started_at"]
        
        # Check Kafka client
        if self.kafka_client:
            kafka_health = await self.kafka_client.health_check()
            health["kafka_client"] = kafka_health
            health["kafka_available"] = kafka_health.get("kafka_client_running", False)
        
        # Check event bridge
        if self.event_bridge:
            bridge_health = await self.event_bridge.health_check()
            health["event_bridge"] = bridge_health
            if not bridge_health.get("bridge_running", False):
                health["components_healthy"] = False
        
        # Check processor manager
        if self.processor_manager:
            processor_health = self.processor_manager.get_stats()
            health["processor_manager"] = processor_health
            if not processor_health.get("is_running", False):
                health["components_healthy"] = False
        
        self._stats["last_health_check"] = asyncio.get_event_loop().time()
        return health
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while self._running:
            try:
                await self.health_check()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                self._stats["last_error"] = str(e)
                await asyncio.sleep(60)  # Wait longer on error
    
    async def restart(self):
        """Restart the Kafka service"""
        logger.info("Restarting Kafka service...")
        await self.stop()
        await self.start()
    
    def is_running(self) -> bool:
        """Check if the service is running"""
        return self._running
    
    def get_config(self) -> KafkaConfig:
        """Get the current configuration"""
        return self.config
    
    async def update_config(self, new_config: KafkaConfig):
        """Update configuration and restart service"""
        logger.info("Updating Kafka configuration...")
        self.config = new_config
        
        if self._running:
            await self.restart()


# Global service instance
_kafka_service: Optional[KafkaService] = None


async def get_kafka_service() -> Optional[KafkaService]:
    """Get the global Kafka service instance"""
    global _kafka_service
    return _kafka_service


async def initialize_kafka_service(event_bus: EventBus, config: Optional[KafkaConfig] = None) -> KafkaService:
    """Initialize the global Kafka service"""
    global _kafka_service
    
    if _kafka_service is not None:
        logger.warning("Kafka service already initialized")
        return _kafka_service
    
    _kafka_service = KafkaService(event_bus, config)
    await _kafka_service.start()
    return _kafka_service


async def shutdown_kafka_service():
    """Shutdown the global Kafka service"""
    global _kafka_service
    
    if _kafka_service is not None:
        await _kafka_service.stop()
        _kafka_service = None


class KafkaServiceError(Exception):
    """Exception raised by Kafka service operations"""
    pass