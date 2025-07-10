"""
Kafka Infrastructure

Provides Kafka integration for the DDD event system, enabling distributed
event streaming and processing across bounded contexts.
"""

from .event_bridge import KafkaEventBridge
from .producer import KafkaEventProducer
from .consumer import KafkaEventConsumer
from .serialization import EventSerializer, EventDeserializer
from .config import KafkaConfig

__all__ = [
    "KafkaEventBridge",
    "KafkaEventProducer",
    "KafkaEventConsumer",
    "EventSerializer",
    "EventDeserializer",
    "KafkaConfig",
]