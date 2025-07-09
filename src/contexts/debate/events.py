"""
Debate Context Domain Events

Domain events represent significant business events that occur within the debate context.
They are used for communication between bounded contexts and maintaining event history.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""
    event_id: UUID
    occurred_at: datetime
    event_type: str
    aggregate_id: UUID
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'event_id': str(self.event_id),
            'occurred_at': self.occurred_at.isoformat(),
            'event_type': self.event_type,
            'aggregate_id': str(self.aggregate_id),
            'version': self.version
        }


@dataclass(frozen=True)
class DebateInitiated(DomainEvent):
    """Event published when a debate is initiated"""
    debate_id: UUID
    topic: str
    participants: List[str]
    max_rounds: int = 5
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'DebateInitiated')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'topic': self.topic,
            'participants': self.participants,
            'max_rounds': self.max_rounds
        })
        return data


@dataclass(frozen=True)
class RoundStarted(DomainEvent):
    """Event published when a debate round starts"""
    debate_id: UUID
    round_id: UUID
    round_number: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'RoundStarted')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'round_id': str(self.round_id),
            'round_number': self.round_number
        })
        return data


@dataclass(frozen=True)
class ArgumentPresented(DomainEvent):
    """Event published when an argument is presented in a debate"""
    debate_id: UUID
    round_id: UUID
    participant: str
    argument_content: str
    argument_type: str
    confidence: float
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'ArgumentPresented')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'round_id': str(self.round_id),
            'participant': self.participant,
            'argument_content': self.argument_content,
            'argument_type': self.argument_type,
            'confidence': self.confidence
        })
        return data


@dataclass(frozen=True)
class RoundCompleted(DomainEvent):
    """Event published when a debate round is completed"""
    debate_id: UUID
    round_id: UUID
    round_number: int
    arguments_count: int = 0
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'RoundCompleted')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'round_id': str(self.round_id),
            'round_number': self.round_number,
            'arguments_count': self.arguments_count
        })
        return data


@dataclass(frozen=True)
class ConsensusReached(DomainEvent):
    """Event published when consensus is reached in a debate"""
    debate_id: UUID
    consensus: str
    consensus_level: str
    confidence: float
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'ConsensusReached')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'consensus': self.consensus,
            'consensus_level': self.consensus_level,
            'confidence': self.confidence
        })
        return data


@dataclass(frozen=True)
class DebateCompleted(DomainEvent):
    """Event published when a debate is completed"""
    debate_id: UUID
    total_rounds: int
    total_arguments: int
    final_consensus: str
    decision_id: Optional[UUID] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'DebateCompleted')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'total_rounds': self.total_rounds,
            'total_arguments': self.total_arguments,
            'final_consensus': self.final_consensus,
            'decision_id': str(self.decision_id) if self.decision_id else None
        })
        return data


@dataclass(frozen=True)
class DecisionMade(DomainEvent):
    """Event published when a decision is made"""
    decision_id: UUID
    debate_id: Optional[UUID]
    decision_type: str
    question: str
    recommendation: str
    confidence: float
    implementation_required: bool
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'DecisionMade')
        object.__setattr__(self, 'aggregate_id', self.decision_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'decision_id': str(self.decision_id),
            'debate_id': str(self.debate_id) if self.debate_id else None,
            'decision_type': self.decision_type,
            'question': self.question,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'implementation_required': self.implementation_required
        })
        return data


@dataclass(frozen=True)
class ComplexityAssessed(DomainEvent):
    """Event published when decision complexity is assessed"""
    decision_id: UUID
    complexity_score: float
    requires_debate: bool
    criteria: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'ComplexityAssessed')
        object.__setattr__(self, 'aggregate_id', self.decision_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'decision_id': str(self.decision_id),
            'complexity_score': self.complexity_score,
            'requires_debate': self.requires_debate,
            'criteria': self.criteria
        })
        return data


@dataclass(frozen=True)
class DebateCancelled(DomainEvent):
    """Event published when a debate is cancelled"""
    debate_id: UUID
    reason: str
    cancelled_by: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'DebateCancelled')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'reason': self.reason,
            'cancelled_by': self.cancelled_by
        })
        return data


@dataclass(frozen=True)
class DebateTimeoutOccurred(DomainEvent):
    """Event published when a debate times out"""
    debate_id: UUID
    timeout_duration_minutes: int
    current_round: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'DebateTimeoutOccurred')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'timeout_duration_minutes': self.timeout_duration_minutes,
            'current_round': self.current_round
        })
        return data


@dataclass(frozen=True)
class DebateMetricsCalculated(DomainEvent):
    """Event published when debate metrics are calculated"""
    debate_id: UUID
    total_rounds: int
    total_arguments: int
    average_argument_length: float
    debate_duration_minutes: int
    consensus_time_minutes: int
    efficiency_score: float
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'DebateMetricsCalculated')
        object.__setattr__(self, 'aggregate_id', self.debate_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            'debate_id': str(self.debate_id),
            'total_rounds': self.total_rounds,
            'total_arguments': self.total_arguments,
            'average_argument_length': self.average_argument_length,
            'debate_duration_minutes': self.debate_duration_minutes,
            'consensus_time_minutes': self.consensus_time_minutes,
            'efficiency_score': self.efficiency_score
        })
        return data