"""
Kafka Infrastructure

Provides Kafka integration for the DDD event system, enabling distributed
event streaming and processing across bounded contexts.
"""

from .event_bridge import KafkaEventBridge, HybridEventBus, get_hybrid_event_bus
from .producer import KafkaEventProducer, BatchEventProducer
from .consumer import KafkaEventConsumer, MultiContextConsumer
from .serialization import EventSerializer, EventDeserializer, register_all_events
from .config import KafkaConfig, TopicMapping

__all__ = [
    "KafkaEventBridge",
    "HybridEventBus",
    "get_hybrid_event_bus",
    "KafkaEventProducer",
    "BatchEventProducer",
    "KafkaEventConsumer",
    "MultiContextConsumer",
    "EventSerializer",
    "EventDeserializer",
    "register_all_events",
    "KafkaConfig",
    "TopicMapping",
]