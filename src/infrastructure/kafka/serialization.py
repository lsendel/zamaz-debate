"""
Event Serialization for Kafka

Handles serialization and deserialization of domain events for Kafka transport.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Type
from uuid import UUID

from src.events import DomainEvent

logger = logging.getLogger(__name__)


class EventSerializer:
    """Serializes domain events for Kafka"""
    
    @staticmethod
    def serialize(event: DomainEvent) -> bytes:
        """
        Serialize a domain event to bytes for Kafka.
        
        Args:
            event: The domain event to serialize
            
        Returns:
            Serialized event as bytes
        """
        try:
            # Convert event to dictionary
            if hasattr(event, 'to_dict'):
                event_dict = event.to_dict()
            else:
                event_dict = EventSerializer._event_to_dict(event)
            
            # Add metadata
            event_dict['_metadata'] = {
                'event_class': f"{event.__class__.__module__}.{event.__class__.__name__}",
                'serialized_at': datetime.now().isoformat(),
                'version': '1.0',
            }
            
            # Serialize to JSON bytes
            return json.dumps(event_dict, default=EventSerializer._json_encoder).encode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to serialize event {event.event_type}: {str(e)}")
            raise
    
    @staticmethod
    def _event_to_dict(event: DomainEvent) -> Dict[str, Any]:
        """Convert event to dictionary"""
        result = {
            'event_id': str(event.event_id),
            'occurred_at': event.occurred_at.isoformat(),
            'event_type': event.event_type,
            'aggregate_id': str(event.aggregate_id),
            'version': event.version,
        }
        
        # Add event-specific fields
        for key, value in event.__dict__.items():
            if key not in result and not key.startswith('_'):
                result[key] = EventSerializer._convert_value(value)
        
        return result
    
    @staticmethod
    def _convert_value(value: Any) -> Any:
        """Convert complex types to serializable format"""
        if isinstance(value, UUID):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif hasattr(value, '__dict__'):
            # Convert nested objects
            return {k: EventSerializer._convert_value(v) 
                   for k, v in value.__dict__.items() 
                   if not k.startswith('_')}
        elif isinstance(value, list):
            return [EventSerializer._convert_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: EventSerializer._convert_value(v) for k, v in value.items()}
        else:
            return value
    
    @staticmethod
    def _json_encoder(obj: Any) -> Any:
        """JSON encoder for special types"""
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class EventDeserializer:
    """Deserializes events from Kafka"""
    
    # Registry of event classes
    _event_registry: Dict[str, Type[DomainEvent]] = {}
    
    @classmethod
    def register_event_class(cls, event_class: Type[DomainEvent]) -> None:
        """Register an event class for deserialization"""
        class_path = f"{event_class.__module__}.{event_class.__name__}"
        cls._event_registry[class_path] = event_class
        # Also register by event type
        if hasattr(event_class, 'event_type'):
            cls._event_registry[event_class.event_type] = event_class
    
    @classmethod
    def deserialize(cls, data: bytes) -> Optional[DomainEvent]:
        """
        Deserialize bytes from Kafka to a domain event.
        
        Args:
            data: Serialized event data
            
        Returns:
            Deserialized domain event or None if failed
        """
        try:
            # Parse JSON
            event_dict = json.loads(data.decode('utf-8'))
            
            # Extract metadata
            metadata = event_dict.pop('_metadata', {})
            event_class_path = metadata.get('event_class')
            
            # Find event class
            event_class = cls._event_registry.get(event_class_path)
            if not event_class:
                # Try by event type
                event_type = event_dict.get('event_type')
                event_class = cls._event_registry.get(event_type)
            
            if not event_class:
                logger.warning(f"Unknown event class: {event_class_path}")
                # Return generic DomainEvent
                return cls._create_generic_event(event_dict)
            
            # Convert string UUIDs back to UUID objects
            if 'event_id' in event_dict and isinstance(event_dict['event_id'], str):
                event_dict['event_id'] = UUID(event_dict['event_id'])
            if 'aggregate_id' in event_dict and isinstance(event_dict['aggregate_id'], str):
                event_dict['aggregate_id'] = UUID(event_dict['aggregate_id'])
            
            # Convert ISO datetime strings back to datetime objects
            if 'occurred_at' in event_dict and isinstance(event_dict['occurred_at'], str):
                event_dict['occurred_at'] = datetime.fromisoformat(event_dict['occurred_at'])
            
            # Create event instance
            return event_class(**event_dict)
            
        except Exception as e:
            logger.error(f"Failed to deserialize event: {str(e)}")
            logger.debug(f"Event data: {data}")
            return None
    
    @classmethod
    def _create_generic_event(cls, event_dict: Dict[str, Any]) -> DomainEvent:
        """Create a generic domain event from dictionary"""
        # Extract base fields
        base_fields = {
            'event_id': UUID(event_dict.get('event_id')) if isinstance(event_dict.get('event_id'), str) else event_dict.get('event_id', UUID()),
            'occurred_at': datetime.fromisoformat(event_dict.get('occurred_at')) if isinstance(event_dict.get('occurred_at'), str) else event_dict.get('occurred_at', datetime.now()),
            'event_type': event_dict.get('event_type', 'UnknownEvent'),
            'aggregate_id': UUID(event_dict.get('aggregate_id')) if isinstance(event_dict.get('aggregate_id'), str) else event_dict.get('aggregate_id', UUID()),
            'version': event_dict.get('version', 1),
        }
        
        # Create generic event
        event = DomainEvent(**base_fields)
        
        # Add additional fields as attributes
        for key, value in event_dict.items():
            if key not in base_fields:
                setattr(event, key, value)
        
        return event


def register_all_events():
    """Register all domain events for deserialization"""
    # Import all event classes
    from src.contexts.debate import (
        DebateStarted, ArgumentPresented, RoundCompleted, DebateCompleted
    )
    from src.contexts.testing import (
        TestSuiteCreated, TestExecuted, TestPassed, TestFailed,
        CoverageReported, TestSuiteCompleted
    )
    from src.contexts.performance import (
        MetricCollected, ThresholdBreached, BenchmarkStarted,
        BenchmarkCompleted, OptimizationApplied
    )
    from src.contexts.implementation import (
        ImplementationRequested, TaskCreated, TaskAssigned,
        PullRequestCreated, DeploymentTriggered, DeploymentCompleted
    )
    from src.contexts.evolution import (
        EvolutionTriggered, ImprovementSuggested, EvolutionPlanCreated,
        EvolutionApplied, EvolutionCompleted
    )
    
    # Register debate events
    for event_class in [DebateStarted, ArgumentPresented, RoundCompleted, DebateCompleted]:
        EventDeserializer.register_event_class(event_class)
    
    # Register testing events
    for event_class in [TestSuiteCreated, TestExecuted, TestPassed, TestFailed,
                       CoverageReported, TestSuiteCompleted]:
        EventDeserializer.register_event_class(event_class)
    
    # Register performance events
    for event_class in [MetricCollected, ThresholdBreached, BenchmarkStarted,
                       BenchmarkCompleted, OptimizationApplied]:
        EventDeserializer.register_event_class(event_class)
    
    # Register implementation events
    for event_class in [ImplementationRequested, TaskCreated, TaskAssigned,
                       PullRequestCreated, DeploymentTriggered, DeploymentCompleted]:
        EventDeserializer.register_event_class(event_class)
    
    # Register evolution events
    for event_class in [EvolutionTriggered, ImprovementSuggested, EvolutionPlanCreated,
                       EvolutionApplied, EvolutionCompleted]:
        EventDeserializer.register_event_class(event_class)
    
    logger.info("Registered all domain events for Kafka deserialization")