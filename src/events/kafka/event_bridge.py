"""
Kafka Event Bridge

This module bridges the existing domain event system with Kafka,
enabling seamless integration between in-memory event bus and Kafka streaming.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4

from src.events.domain_event import DomainEvent
from src.events.event_bus import EventBus
from .client import KafkaClient
from .config import KafkaConfig

logger = logging.getLogger(__name__)


class KafkaEventBridge:
    """
    Bridges domain events between EventBus and Kafka
    
    This bridge allows the existing domain event system to seamlessly
    integrate with Kafka for high-throughput, persistent event processing.
    """
    
    def __init__(self, event_bus: EventBus, kafka_config: Optional[KafkaConfig] = None):
        """
        Initialize the Kafka event bridge
        
        Args:
            event_bus: The existing event bus instance
            kafka_config: Kafka configuration (uses default if None)
        """
        self.event_bus = event_bus
        self.kafka_config = kafka_config or KafkaConfig.from_env()
        self.kafka_client: Optional[KafkaClient] = None
        
        # Event routing configuration
        self._event_routing: Dict[str, str] = {
            "debate_initiated": "debate-events",
            "debate_round_started": "debate-events", 
            "debate_round_completed": "debate-events",
            "debate_consensus_reached": "debate-events",
            "debate_completed": "debate-events",
            "decision_made": "decision-events",
            "decision_approved": "decision-events",
            "decision_rejected": "decision-events",
            "evolution_triggered": "evolution-events",
            "evolution_completed": "evolution-events",
            "improvement_suggested": "evolution-events",
            "webhook_delivered": "webhook-events",
            "webhook_failed": "webhook-events",
            "metric_recorded": "metrics-events",
        }
        
        # Consumer handlers
        self._consumer_handlers: Dict[str, List[Callable]] = {}
        
        # Statistics
        self._stats = {
            "events_published_to_kafka": 0,
            "events_received_from_kafka": 0,
            "events_forwarded_to_bus": 0,
            "routing_errors": 0,
            "last_error": None,
        }
        
        self._running = False
    
    async def start(self):
        """Start the Kafka event bridge"""
        if self._running:
            return
        
        logger.info("Starting Kafka event bridge...")
        
        try:
            # Initialize Kafka client
            self.kafka_client = KafkaClient(self.kafka_config)
            await self.kafka_client.start()
            
            # Subscribe to domain events from the event bus
            await self._subscribe_to_domain_events()
            
            # Start Kafka consumers for each event type
            await self._start_kafka_consumers()
            
            self._running = True
            logger.info("Kafka event bridge started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka event bridge: {e}")
            self._stats["last_error"] = str(e)
            raise
    
    async def stop(self):
        """Stop the Kafka event bridge"""
        if not self._running:
            return
        
        logger.info("Stopping Kafka event bridge...")
        
        try:
            # Stop Kafka client
            if self.kafka_client:
                await self.kafka_client.stop()
                self.kafka_client = None
            
            self._running = False
            logger.info("Kafka event bridge stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Kafka event bridge: {e}")
            self._stats["last_error"] = str(e)
    
    async def _subscribe_to_domain_events(self):
        """Subscribe to domain events from the event bus"""
        for event_type in self._event_routing.keys():
            await self.event_bus.subscribe(event_type, self._handle_domain_event)
        
        logger.info(f"Subscribed to {len(self._event_routing)} domain event types")
    
    async def _handle_domain_event(self, event: DomainEvent):
        """Handle domain events from the event bus and forward to Kafka"""
        try:
            event_type = event.event_type
            
            # Get Kafka topic for this event type
            kafka_topic = self._event_routing.get(event_type)
            if not kafka_topic:
                logger.warning(f"No Kafka topic mapping for event type: {event_type}")
                self._stats["routing_errors"] += 1
                return
            
            # Convert domain event to Kafka event data
            kafka_event_data = {
                "event_id": str(event.event_id),
                "event_type": event_type,
                "aggregate_id": str(event.aggregate_id),
                "aggregate_type": event.aggregate_type,
                "occurred_at": event.occurred_at.isoformat(),
                "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                "causation_id": str(event.causation_id) if event.causation_id else None,
                "user_id": event.metadata.user_id,
                "source": event.metadata.source,
                "event_data": event.to_dict(),
            }
            
            # Publish to Kafka
            if self.kafka_client:
                partition_key = str(event.aggregate_id)
                success = await self.kafka_client.produce_event(
                    event_type=kafka_topic,
                    event_data=kafka_event_data,
                    partition_key=partition_key
                )
                
                if success:
                    self._stats["events_published_to_kafka"] += 1
                    logger.debug(f"Published event {event_type} to Kafka topic {kafka_topic}")
                else:
                    logger.error(f"Failed to publish event {event_type} to Kafka")
                    self._stats["routing_errors"] += 1
            
        except Exception as e:
            logger.error(f"Error handling domain event {event.event_type}: {e}")
            self._stats["routing_errors"] += 1
            self._stats["last_error"] = str(e)
    
    async def _start_kafka_consumers(self):
        """Start Kafka consumers for each event type"""
        unique_topics = set(self._event_routing.values())
        
        for topic in unique_topics:
            consumer_id = f"bridge-{topic}-consumer"
            await self.kafka_client.create_consumer(
                consumer_id=consumer_id,
                event_types=[topic],
                handler_callback=self._handle_kafka_event
            )
        
        logger.info(f"Started {len(unique_topics)} Kafka consumers")
    
    async def _handle_kafka_event(self, kafka_event_data: Dict[str, Any]):
        """Handle events received from Kafka"""
        try:
            self._stats["events_received_from_kafka"] += 1
            
            # Extract event information
            event_type = kafka_event_data.get("event_type")
            event_data = kafka_event_data.get("event_data", {})
            
            if not event_type:
                logger.warning("Received Kafka event without event_type")
                return
            
            # Forward to registered consumer handlers
            handlers = self._consumer_handlers.get(event_type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(kafka_event_data)
                    else:
                        handler(kafka_event_data)
                except Exception as e:
                    logger.error(f"Error in consumer handler for {event_type}: {e}")
            
            # Also forward to event bus (optional - can be configured)
            if self._should_forward_to_event_bus(event_type):
                # Create a simplified event for the event bus
                await self.event_bus.publish({
                    "type": "kafka_event_received",
                    "original_event_type": event_type,
                    "data": kafka_event_data
                })
                self._stats["events_forwarded_to_bus"] += 1
            
        except Exception as e:
            logger.error(f"Error handling Kafka event: {e}")
            self._stats["last_error"] = str(e)
    
    def _should_forward_to_event_bus(self, event_type: str) -> bool:
        """Determine if event should be forwarded to event bus"""
        # By default, don't forward to avoid circular processing
        # This can be configured based on requirements
        return False
    
    def add_consumer_handler(self, event_type: str, handler: Callable):
        """Add a handler for consuming events from Kafka"""
        if event_type not in self._consumer_handlers:
            self._consumer_handlers[event_type] = []
        
        self._consumer_handlers[event_type].append(handler)
        logger.info(f"Added consumer handler for {event_type}")
    
    def remove_consumer_handler(self, event_type: str, handler: Callable):
        """Remove a handler for consuming events from Kafka"""
        if event_type in self._consumer_handlers:
            self._consumer_handlers[event_type].remove(handler)
            if not self._consumer_handlers[event_type]:
                del self._consumer_handlers[event_type]
        
        logger.info(f"Removed consumer handler for {event_type}")
    
    def add_event_routing(self, event_type: str, kafka_topic: str):
        """Add routing for a domain event type to Kafka topic"""
        self._event_routing[event_type] = kafka_topic
        logger.info(f"Added event routing: {event_type} -> {kafka_topic}")
    
    def remove_event_routing(self, event_type: str):
        """Remove routing for a domain event type"""
        if event_type in self._event_routing:
            del self._event_routing[event_type]
            logger.info(f"Removed event routing for {event_type}")
    
    async def publish_direct_to_kafka(self, event_type: str, event_data: Dict[str, Any], 
                                     partition_key: Optional[str] = None):
        """Publish event directly to Kafka without going through event bus"""
        if not self.kafka_client:
            logger.warning("Kafka client not available")
            return False
        
        # Get Kafka topic
        kafka_topic = self._event_routing.get(event_type)
        if not kafka_topic:
            logger.warning(f"No Kafka topic mapping for event type: {event_type}")
            return False
        
        # Enrich event data
        enriched_data = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "occurred_at": asyncio.get_event_loop().time(),
            "event_data": event_data,
            "source": "direct_kafka_publish"
        }
        
        # Publish to Kafka
        success = await self.kafka_client.produce_event(
            event_type=kafka_topic,
            event_data=enriched_data,
            partition_key=partition_key
        )
        
        if success:
            self._stats["events_published_to_kafka"] += 1
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return {
            **self._stats,
            "is_running": self._running,
            "event_routing_count": len(self._event_routing),
            "consumer_handlers_count": sum(len(handlers) for handlers in self._consumer_handlers.values()),
            "kafka_client_stats": self.kafka_client.get_stats() if self.kafka_client else None,
        }
    
    def clear_stats(self):
        """Clear bridge statistics"""
        self._stats = {
            "events_published_to_kafka": 0,
            "events_received_from_kafka": 0,
            "events_forwarded_to_bus": 0,
            "routing_errors": 0,
            "last_error": None,
        }
        
        if self.kafka_client:
            self.kafka_client.clear_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            "bridge_running": self._running,
            "kafka_client_health": None,
            "last_error": self._stats["last_error"],
        }
        
        if self.kafka_client:
            health["kafka_client_health"] = await self.kafka_client.health_check()
        
        return health


class KafkaEventBridgeError(Exception):
    """Exception raised by Kafka event bridge operations"""
    pass