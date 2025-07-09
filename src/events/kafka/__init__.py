"""
Apache Kafka Integration for Zamaz Debate System

This module provides Apache Kafka integration for high-throughput event processing.
It complements the existing event bus system by providing persistent, scalable
event streaming capabilities.
"""

from .client import KafkaClient
from .config import KafkaConfig
from .consumer import KafkaConsumer
from .producer import KafkaProducer
from .topics import TopicManager
from .serializers import EventSerializer, AvroEventSerializer

__all__ = [
    "KafkaClient",
    "KafkaConfig", 
    "KafkaConsumer",
    "KafkaProducer",
    "TopicManager",
    "EventSerializer",
    "AvroEventSerializer",
]