"""
Kafka Configuration

Provides configuration settings for Kafka integration.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class KafkaConfig:
    """Kafka configuration settings"""
    
    # Connection settings
    bootstrap_servers: str = "localhost:9092"
    client_id: str = "zamaz-debate-system"
    
    # Producer settings
    producer_config: Dict[str, any] = None
    
    # Consumer settings
    consumer_group_id: str = "zamaz-debate-consumers"
    consumer_config: Dict[str, any] = None
    
    # Topic configuration
    topic_prefix: str = "zamaz."
    num_partitions: int = 3
    replication_factor: int = 1
    
    # Serialization
    use_avro: bool = False
    schema_registry_url: Optional[str] = None
    
    # Error handling
    max_retries: int = 3
    retry_backoff_ms: int = 1000
    dead_letter_topic_suffix: str = ".dlq"
    
    # Performance
    batch_size: int = 16384
    linger_ms: int = 10
    compression_type: str = "gzip"
    
    def __post_init__(self):
        """Initialize configuration with defaults"""
        if self.producer_config is None:
            self.producer_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': f"{self.client_id}-producer",
                'acks': 'all',
                'retries': self.max_retries,
                'batch.size': self.batch_size,
                'linger.ms': self.linger_ms,
                'compression.type': self.compression_type,
                'enable.idempotence': True,
            }
        
        if self.consumer_config is None:
            self.consumer_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': self.consumer_group_id,
                'client.id': f"{self.client_id}-consumer",
                'enable.auto.commit': False,
                'auto.offset.reset': 'earliest',
                'max.poll.interval.ms': 300000,
                'session.timeout.ms': 45000,
            }
    
    @classmethod
    def from_env(cls) -> "KafkaConfig":
        """Create configuration from environment variables"""
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            client_id=os.getenv("KAFKA_CLIENT_ID", "zamaz-debate-system"),
            consumer_group_id=os.getenv("KAFKA_CONSUMER_GROUP", "zamaz-debate-consumers"),
            topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "zamaz."),
            num_partitions=int(os.getenv("KAFKA_NUM_PARTITIONS", "3")),
            replication_factor=int(os.getenv("KAFKA_REPLICATION_FACTOR", "1")),
            use_avro=os.getenv("KAFKA_USE_AVRO", "false").lower() == "true",
            schema_registry_url=os.getenv("KAFKA_SCHEMA_REGISTRY_URL"),
            max_retries=int(os.getenv("KAFKA_MAX_RETRIES", "3")),
            retry_backoff_ms=int(os.getenv("KAFKA_RETRY_BACKOFF_MS", "1000")),
        )


class TopicMapping:
    """Maps bounded contexts to Kafka topics"""
    
    # Context to topic mapping
    CONTEXT_TOPICS = {
        "debate": "debate.events",
        "testing": "testing.events",
        "performance": "performance.events",
        "implementation": "implementation.events",
        "evolution": "evolution.events",
        "webhook": "webhook.events",
    }
    
    # Event type to topic mapping (for specific routing)
    EVENT_TOPICS = {
        # High-volume events get their own topics
        "MetricCollected": "performance.metrics",
        "TestExecuted": "testing.executions",
        
        # Critical events
        "EvolutionTriggered": "evolution.triggers",
        "DeploymentCompleted": "implementation.deployments",
    }
    
    # Dead letter topics
    DEAD_LETTER_TOPICS = {
        context: f"{topic}.dlq"
        for context, topic in CONTEXT_TOPICS.items()
    }
    
    @classmethod
    def get_topic_for_event(cls, event_type: str, context: str, config: KafkaConfig) -> str:
        """Get the Kafka topic for an event"""
        # Check if event has specific topic mapping
        if event_type in cls.EVENT_TOPICS:
            topic = cls.EVENT_TOPICS[event_type]
        else:
            # Use context-based topic
            topic = cls.CONTEXT_TOPICS.get(context, "general.events")
        
        # Add prefix
        return f"{config.topic_prefix}{topic}"
    
    @classmethod
    def get_dead_letter_topic(cls, original_topic: str, config: KafkaConfig) -> str:
        """Get the dead letter topic for a given topic"""
        return f"{original_topic}{config.dead_letter_topic_suffix}"
    
    @classmethod
    def get_all_topics(cls, config: KafkaConfig) -> List[str]:
        """Get all topics that need to be created"""
        topics = []
        
        # Add context topics
        for topic in cls.CONTEXT_TOPICS.values():
            topics.append(f"{config.topic_prefix}{topic}")
        
        # Add event-specific topics
        for topic in cls.EVENT_TOPICS.values():
            topics.append(f"{config.topic_prefix}{topic}")
        
        # Add dead letter topics
        for topic in cls.DEAD_LETTER_TOPICS.values():
            topics.append(f"{config.topic_prefix}{topic}")
        
        return list(set(topics))  # Remove duplicates