"""
Event Serialization for Kafka

This module provides serialization and deserialization for events sent through Kafka.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import avro.schema
    import avro.io
    import io
    AVRO_AVAILABLE = True
except ImportError:
    AVRO_AVAILABLE = False

logger = logging.getLogger(__name__)


class EventSerializer(ABC):
    """Base class for event serializers"""
    
    @abstractmethod
    def serialize(self, event_data: Dict[str, Any]) -> bytes:
        """Serialize event data to bytes"""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize bytes to event data"""
        pass


class JSONEventSerializer(EventSerializer):
    """JSON-based event serializer"""
    
    def __init__(self, encoding: str = "utf-8"):
        self.encoding = encoding
    
    def serialize(self, event_data: Dict[str, Any]) -> bytes:
        """Serialize event data to JSON bytes"""
        try:
            # Convert datetime objects to ISO format strings
            normalized_data = self._normalize_data(event_data)
            json_str = json.dumps(normalized_data, ensure_ascii=False, separators=(',', ':'))
            return json_str.encode(self.encoding)
        except Exception as e:
            logger.error(f"Failed to serialize event data: {e}")
            raise EventSerializationError(f"JSON serialization failed: {e}")
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize JSON bytes to event data"""
        try:
            json_str = data.decode(self.encoding)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to deserialize event data: {e}")
            raise EventDeserializationError(f"JSON deserialization failed: {e}")
    
    def _normalize_data(self, data: Any) -> Any:
        """Normalize data for JSON serialization"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self._normalize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._normalize_data(item) for item in data]
        elif hasattr(data, '__dict__'):
            # Handle dataclasses and other objects
            return self._normalize_data(data.__dict__)
        else:
            return data


class AvroEventSerializer(EventSerializer):
    """Avro-based event serializer"""
    
    def __init__(self, schema_str: str):
        if not AVRO_AVAILABLE:
            raise ImportError("Avro library is required for AvroEventSerializer")
        
        self.schema = avro.schema.parse(schema_str)
    
    def serialize(self, event_data: Dict[str, Any]) -> bytes:
        """Serialize event data to Avro bytes"""
        try:
            # Normalize data for Avro
            normalized_data = self._normalize_for_avro(event_data)
            
            # Create Avro writer
            writer = avro.io.DatumWriter(self.schema)
            bytes_writer = io.BytesIO()
            encoder = avro.io.BinaryEncoder(bytes_writer)
            
            # Write data
            writer.write(normalized_data, encoder)
            return bytes_writer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to serialize event data with Avro: {e}")
            raise EventSerializationError(f"Avro serialization failed: {e}")
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize Avro bytes to event data"""
        try:
            # Create Avro reader
            reader = avro.io.DatumReader(self.schema)
            bytes_reader = io.BytesIO(data)
            decoder = avro.io.BinaryDecoder(bytes_reader)
            
            # Read data
            return reader.read(decoder)
            
        except Exception as e:
            logger.error(f"Failed to deserialize event data with Avro: {e}")
            raise EventDeserializationError(f"Avro deserialization failed: {e}")
    
    def _normalize_for_avro(self, data: Any) -> Any:
        """Normalize data for Avro serialization"""
        if isinstance(data, datetime):
            return int(data.timestamp() * 1000)  # Convert to milliseconds
        elif isinstance(data, dict):
            return {k: self._normalize_for_avro(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._normalize_for_avro(item) for item in data]
        elif hasattr(data, '__dict__'):
            return self._normalize_for_avro(data.__dict__)
        else:
            return data


class CompressedEventSerializer(EventSerializer):
    """Compressed event serializer wrapper"""
    
    def __init__(self, base_serializer: EventSerializer, compression_type: str = "gzip"):
        self.base_serializer = base_serializer
        self.compression_type = compression_type
        
        # Import compression library
        if compression_type == "gzip":
            import gzip
            self.compressor = gzip
        elif compression_type == "zlib":
            import zlib
            self.compressor = zlib
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
    
    def serialize(self, event_data: Dict[str, Any]) -> bytes:
        """Serialize and compress event data"""
        try:
            # First serialize with base serializer
            serialized_data = self.base_serializer.serialize(event_data)
            
            # Then compress
            if self.compression_type == "gzip":
                return self.compressor.compress(serialized_data)
            elif self.compression_type == "zlib":
                return self.compressor.compress(serialized_data)
            
        except Exception as e:
            logger.error(f"Failed to compress event data: {e}")
            raise EventSerializationError(f"Compression failed: {e}")
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Decompress and deserialize event data"""
        try:
            # First decompress
            if self.compression_type == "gzip":
                decompressed_data = self.compressor.decompress(data)
            elif self.compression_type == "zlib":
                decompressed_data = self.compressor.decompress(data)
            else:
                decompressed_data = data
            
            # Then deserialize with base serializer
            return self.base_serializer.deserialize(decompressed_data)
            
        except Exception as e:
            logger.error(f"Failed to decompress event data: {e}")
            raise EventDeserializationError(f"Decompression failed: {e}")


# Default serializer (alias for JSONEventSerializer)
EventSerializer = JSONEventSerializer


# Avro schemas for different event types
AVRO_SCHEMAS = {
    "debate_event": """
    {
        "type": "record",
        "name": "DebateEvent",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "event_type", "type": "string"},
            {"name": "aggregate_id", "type": "string"},
            {"name": "aggregate_type", "type": "string"},
            {"name": "occurred_at", "type": "long"},
            {"name": "debate_id", "type": "string"},
            {"name": "question", "type": "string"},
            {"name": "context", "type": "string"},
            {"name": "round_number", "type": ["null", "int"], "default": null},
            {"name": "participant", "type": ["null", "string"], "default": null},
            {"name": "response", "type": ["null", "string"], "default": null},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    }
    """,
    
    "decision_event": """
    {
        "type": "record",
        "name": "DecisionEvent",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "event_type", "type": "string"},
            {"name": "aggregate_id", "type": "string"},
            {"name": "aggregate_type", "type": "string"},
            {"name": "occurred_at", "type": "long"},
            {"name": "decision_id", "type": "string"},
            {"name": "question", "type": "string"},
            {"name": "context", "type": "string"},
            {"name": "decision_text", "type": "string"},
            {"name": "decision_type", "type": "string"},
            {"name": "method", "type": "string"},
            {"name": "rounds", "type": "int"},
            {"name": "debate_id", "type": ["null", "string"], "default": null},
            {"name": "implementation_assignee", "type": ["null", "string"], "default": null},
            {"name": "implementation_complexity", "type": ["null", "string"], "default": null},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    }
    """,
    
    "evolution_event": """
    {
        "type": "record",
        "name": "EvolutionEvent",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "event_type", "type": "string"},
            {"name": "aggregate_id", "type": "string"},
            {"name": "aggregate_type", "type": "string"},
            {"name": "occurred_at", "type": "long"},
            {"name": "evolution_id", "type": "string"},
            {"name": "improvement_type", "type": "string"},
            {"name": "description", "type": "string"},
            {"name": "impact_assessment", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    }
    """,
    
    "webhook_event": """
    {
        "type": "record",
        "name": "WebhookEvent",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "event_type", "type": "string"},
            {"name": "aggregate_id", "type": "string"},
            {"name": "aggregate_type", "type": "string"},
            {"name": "occurred_at", "type": "long"},
            {"name": "webhook_id", "type": "string"},
            {"name": "endpoint_url", "type": "string"},
            {"name": "payload", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "attempts", "type": "int"},
            {"name": "last_attempt_at", "type": ["null", "long"], "default": null},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    }
    """
}


def get_avro_serializer(event_type: str) -> Optional[AvroEventSerializer]:
    """Get Avro serializer for a specific event type"""
    if not AVRO_AVAILABLE:
        logger.warning("Avro library not available, falling back to JSON serialization")
        return None
    
    schema = AVRO_SCHEMAS.get(event_type)
    if not schema:
        logger.warning(f"No Avro schema defined for event type: {event_type}")
        return None
    
    return AvroEventSerializer(schema)


class EventSerializationError(Exception):
    """Exception raised when event serialization fails"""
    pass


class EventDeserializationError(Exception):
    """Exception raised when event deserialization fails"""
    pass