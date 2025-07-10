"""
Kafka-DDD Event Bridge

Bridges the in-memory DDD event bus with Kafka for distributed event processing.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Type
from datetime import datetime

from src.events import DomainEvent, EventBus, get_event_bus, subscribe
from .config import KafkaConfig
from .producer import KafkaEventProducer, BatchEventProducer
from .consumer import KafkaEventConsumer, MultiContextConsumer
from .serialization import register_all_events

logger = logging.getLogger(__name__)


class KafkaEventBridge:
    """
    Bridges the DDD event bus with Kafka.
    
    This allows events to flow between:
    - Local in-memory event bus (for same-process communication)
    - Kafka (for distributed, persistent event streaming)
    """
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        """
        Initialize the event bridge.
        
        Args:
            config: Kafka configuration (uses defaults if not provided)
        """
        self.config = config or KafkaConfig.from_env()
        self.event_bus = get_event_bus(record_events=True)
        self.producer = KafkaEventProducer(self.config)
        self.batch_producer = BatchEventProducer(self.config)
        self.consumers: Dict[str, KafkaEventConsumer] = {}
        
        # Track which events to bridge to Kafka
        self._bridged_event_types: Set[Type[DomainEvent]] = set()
        self._context_mapping: Dict[Type[DomainEvent], str] = {}
        
        # Register event serialization
        register_all_events()
        
        logger.info("Kafka event bridge initialized")
    
    def bridge_event_type(
        self,
        event_type: Type[DomainEvent],
        context: str,
        to_kafka: bool = True,
        from_kafka: bool = True,
    ) -> None:
        """
        Configure bridging for a specific event type.
        
        Args:
            event_type: The domain event type to bridge
            context: The bounded context for the event
            to_kafka: Whether to publish these events to Kafka
            from_kafka: Whether to consume these events from Kafka
        """
        if to_kafka:
            self._bridged_event_types.add(event_type)
            self._context_mapping[event_type] = context
            
            # Subscribe to local event bus
            @subscribe(event_type, context=f"kafka-bridge-{context}", priority=5)
            async def bridge_to_kafka(event: DomainEvent):
                await self._publish_to_kafka(event, context)
        
        if from_kafka and context not in self.consumers:
            # Create consumer for this context
            self.consumers[context] = KafkaEventConsumer(self.config, [context])
        
        logger.info(
            f"Bridged {event_type.__name__} for context {context} "
            f"(to_kafka={to_kafka}, from_kafka={from_kafka})"
        )
    
    def bridge_all_events(self) -> None:
        """Bridge all known domain events to/from Kafka"""
        # Import all contexts to get event types
        from src.contexts import debate, testing, performance, implementation, evolution
        
        # Bridge debate events
        self.bridge_event_type(debate.DebateStarted, "debate")
        self.bridge_event_type(debate.DebateCompleted, "debate")
        
        # Bridge testing events
        self.bridge_event_type(testing.TestFailed, "testing")
        self.bridge_event_type(testing.TestSuiteCompleted, "testing")
        self.bridge_event_type(testing.CoverageDecreased, "testing")
        
        # Bridge performance events
        self.bridge_event_type(performance.MetricCollected, "performance")
        self.bridge_event_type(performance.MetricThresholdBreached, "performance")
        self.bridge_event_type(performance.BenchmarkCompleted, "performance")
        
        # Bridge implementation events
        self.bridge_event_type(implementation.TaskCreated, "implementation")
        self.bridge_event_type(implementation.PullRequestCreated, "implementation")
        self.bridge_event_type(implementation.DeploymentCompleted, "implementation")
        
        # Bridge evolution events
        self.bridge_event_type(evolution.EvolutionTriggered, "evolution")
        self.bridge_event_type(evolution.EvolutionCompleted, "evolution")
        
        logger.info("Bridged all domain events to Kafka")
    
    async def _publish_to_kafka(self, event: DomainEvent, context: str) -> None:
        """Publish an event to Kafka"""
        try:
            self.producer.publish(event, context)
            logger.debug(f"Published {event.event_type} to Kafka")
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {str(e)}")
            # Event remains in local bus even if Kafka fails
    
    async def start_consumers(self) -> None:
        """Start all Kafka consumers"""
        tasks = []
        for context, consumer in self.consumers.items():
            task = asyncio.create_task(
                consumer.start(),
                name=f"kafka-consumer-{context}"
            )
            tasks.append(task)
        
        logger.info(f"Started {len(tasks)} Kafka consumers")
        
        # Wait for all consumers
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def stop(self) -> None:
        """Stop the event bridge"""
        # Stop consumers
        for consumer in self.consumers.values():
            consumer.stop()
        
        # Flush producer
        self.producer.flush()
        self.producer.close()
        self.batch_producer.close()
        
        logger.info("Kafka event bridge stopped")
    
    def get_metrics(self) -> Dict[str, any]:
        """Get bridge metrics"""
        return {
            "bridged_event_types": len(self._bridged_event_types),
            "active_consumers": len(self.consumers),
            "event_bus_history_size": len(self.event_bus.get_event_history()),
            "event_bus_metrics": self.event_bus.get_event_metrics(),
        }


class HybridEventBus(EventBus):
    """
    Extended event bus that automatically bridges to Kafka.
    
    This can replace the standard EventBus for transparent Kafka integration.
    """
    
    def __init__(self, kafka_config: Optional[KafkaConfig] = None):
        """
        Initialize hybrid event bus.
        
        Args:
            kafka_config: Kafka configuration
        """
        super().__init__(record_events=True)
        self.kafka_bridge = KafkaEventBridge(kafka_config)
        self._kafka_enabled = kafka_config is not None
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish event to both local bus and Kafka"""
        # Publish locally first
        await super().publish(event)
        
        # Then to Kafka if enabled
        if self._kafka_enabled:
            event_type = type(event)
            context = self.kafka_bridge._context_mapping.get(event_type)
            if context:
                await self.kafka_bridge._publish_to_kafka(event, context)
    
    def enable_kafka(self, config: KafkaConfig) -> None:
        """Enable Kafka integration"""
        self.kafka_bridge = KafkaEventBridge(config)
        self._kafka_enabled = True
        self.kafka_bridge.bridge_all_events()
    
    def disable_kafka(self) -> None:
        """Disable Kafka integration"""
        if self._kafka_enabled:
            self.kafka_bridge.stop()
            self._kafka_enabled = False


# Global hybrid event bus instance
_hybrid_event_bus: Optional[HybridEventBus] = None


def get_hybrid_event_bus(kafka_config: Optional[KafkaConfig] = None) -> HybridEventBus:
    """
    Get the global hybrid event bus instance.
    
    Args:
        kafka_config: Optional Kafka configuration
        
    Returns:
        The global HybridEventBus instance
    """
    global _hybrid_event_bus
    
    if _hybrid_event_bus is None:
        _hybrid_event_bus = HybridEventBus(kafka_config)
        
        # Auto-bridge all events if Kafka is configured
        if kafka_config:
            _hybrid_event_bus.kafka_bridge.bridge_all_events()
    
    return _hybrid_event_bus