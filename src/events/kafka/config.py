"""
Kafka Configuration Management

This module handles Kafka client configuration and connection settings.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class KafkaConfig:
    """Configuration for Kafka clients"""
    
    bootstrap_servers: str = field(default="localhost:9092")
    security_protocol: str = field(default="PLAINTEXT")
    sasl_mechanism: Optional[str] = field(default=None)
    sasl_username: Optional[str] = field(default=None)
    sasl_password: Optional[str] = field(default=None)
    ssl_cafile: Optional[str] = field(default=None)
    ssl_certfile: Optional[str] = field(default=None)
    ssl_keyfile: Optional[str] = field(default=None)
    
    # Producer specific
    acks: str = field(default="all")
    retries: int = field(default=3)
    batch_size: int = field(default=16384)
    linger_ms: int = field(default=5)
    compression_type: str = field(default="snappy")
    max_in_flight_requests_per_connection: int = field(default=5)
    
    # Consumer specific
    group_id: str = field(default="zamaz-debate-group")
    auto_offset_reset: str = field(default="latest")
    enable_auto_commit: bool = field(default=True)
    auto_commit_interval_ms: int = field(default=5000)
    session_timeout_ms: int = field(default=30000)
    heartbeat_interval_ms: int = field(default=3000)
    max_poll_records: int = field(default=500)
    
    # Topic configuration
    topic_prefix: str = field(default="zamaz-debate")
    num_partitions: int = field(default=3)
    replication_factor: int = field(default=1)
    
    # Schema registry (for Avro)
    schema_registry_url: Optional[str] = field(default=None)
    
    @classmethod
    def from_env(cls) -> "KafkaConfig":
        """Create configuration from environment variables"""
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
            sasl_username=os.getenv("KAFKA_SASL_USERNAME"),
            sasl_password=os.getenv("KAFKA_SASL_PASSWORD"),
            ssl_cafile=os.getenv("KAFKA_SSL_CAFILE"),
            ssl_certfile=os.getenv("KAFKA_SSL_CERTFILE"),
            ssl_keyfile=os.getenv("KAFKA_SSL_KEYFILE"),
            
            acks=os.getenv("KAFKA_ACKS", "all"),
            retries=int(os.getenv("KAFKA_RETRIES", "3")),
            batch_size=int(os.getenv("KAFKA_BATCH_SIZE", "16384")),
            linger_ms=int(os.getenv("KAFKA_LINGER_MS", "5")),
            compression_type=os.getenv("KAFKA_COMPRESSION_TYPE", "snappy"),
            
            group_id=os.getenv("KAFKA_GROUP_ID", "zamaz-debate-group"),
            auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest"),
            enable_auto_commit=os.getenv("KAFKA_ENABLE_AUTO_COMMIT", "true").lower() == "true",
            auto_commit_interval_ms=int(os.getenv("KAFKA_AUTO_COMMIT_INTERVAL_MS", "5000")),
            session_timeout_ms=int(os.getenv("KAFKA_SESSION_TIMEOUT_MS", "30000")),
            heartbeat_interval_ms=int(os.getenv("KAFKA_HEARTBEAT_INTERVAL_MS", "3000")),
            max_poll_records=int(os.getenv("KAFKA_MAX_POLL_RECORDS", "500")),
            
            topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "zamaz-debate"),
            num_partitions=int(os.getenv("KAFKA_NUM_PARTITIONS", "3")),
            replication_factor=int(os.getenv("KAFKA_REPLICATION_FACTOR", "1")),
            
            schema_registry_url=os.getenv("KAFKA_SCHEMA_REGISTRY_URL"),
        )
    
    def to_producer_config(self) -> Dict:
        """Convert to producer configuration dictionary"""
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "acks": self.acks,
            "retries": self.retries,
            "batch.size": self.batch_size,
            "linger.ms": self.linger_ms,
            "compression.type": self.compression_type,
            "max.in.flight.requests.per.connection": self.max_in_flight_requests_per_connection,
        }
        
        # Add authentication config if provided
        if self.sasl_mechanism:
            config["sasl.mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl.username"] = self.sasl_username
        if self.sasl_password:
            config["sasl.password"] = self.sasl_password
        
        # Add SSL config if provided
        if self.ssl_cafile:
            config["ssl.ca.location"] = self.ssl_cafile
        if self.ssl_certfile:
            config["ssl.certificate.location"] = self.ssl_certfile
        if self.ssl_keyfile:
            config["ssl.key.location"] = self.ssl_keyfile
        
        return config
    
    def to_consumer_config(self) -> Dict:
        """Convert to consumer configuration dictionary"""
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "group.id": self.group_id,
            "auto.offset.reset": self.auto_offset_reset,
            "enable.auto.commit": self.enable_auto_commit,
            "auto.commit.interval.ms": self.auto_commit_interval_ms,
            "session.timeout.ms": self.session_timeout_ms,
            "heartbeat.interval.ms": self.heartbeat_interval_ms,
            "max.poll.records": self.max_poll_records,
        }
        
        # Add authentication config if provided
        if self.sasl_mechanism:
            config["sasl.mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl.username"] = self.sasl_username
        if self.sasl_password:
            config["sasl.password"] = self.sasl_password
        
        # Add SSL config if provided
        if self.ssl_cafile:
            config["ssl.ca.location"] = self.ssl_cafile
        if self.ssl_certfile:
            config["ssl.certificate.location"] = self.ssl_certfile
        if self.ssl_keyfile:
            config["ssl.key.location"] = self.ssl_keyfile
        
        return config
    
    def get_topic_name(self, event_type: str) -> str:
        """Get the full topic name for an event type"""
        return f"{self.topic_prefix}.{event_type}"
    
    def get_dead_letter_topic_name(self, event_type: str) -> str:
        """Get the dead letter topic name for an event type"""
        return f"{self.topic_prefix}.{event_type}.dead-letter"


# Topic configuration mapping
TOPIC_CONFIGS = {
    "debate-events": {
        "cleanup.policy": "delete",
        "retention.ms": 7 * 24 * 60 * 60 * 1000,  # 7 days
        "segment.ms": 24 * 60 * 60 * 1000,  # 1 day
        "max.message.bytes": 1048576,  # 1MB
    },
    "decision-events": {
        "cleanup.policy": "delete",
        "retention.ms": 30 * 24 * 60 * 60 * 1000,  # 30 days
        "segment.ms": 24 * 60 * 60 * 1000,  # 1 day
        "max.message.bytes": 1048576,  # 1MB
    },
    "evolution-events": {
        "cleanup.policy": "delete",
        "retention.ms": 90 * 24 * 60 * 60 * 1000,  # 90 days
        "segment.ms": 7 * 24 * 60 * 60 * 1000,  # 7 days
        "max.message.bytes": 2097152,  # 2MB
    },
    "webhook-events": {
        "cleanup.policy": "delete",
        "retention.ms": 7 * 24 * 60 * 60 * 1000,  # 7 days
        "segment.ms": 24 * 60 * 60 * 1000,  # 1 day
        "max.message.bytes": 524288,  # 512KB
    },
    "metrics-events": {
        "cleanup.policy": "delete",
        "retention.ms": 7 * 24 * 60 * 60 * 1000,  # 7 days
        "segment.ms": 60 * 60 * 1000,  # 1 hour
        "max.message.bytes": 65536,  # 64KB
    },
}