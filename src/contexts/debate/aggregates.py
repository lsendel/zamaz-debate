"""
Debate Context Aggregates

This module contains the aggregate roots for the debate context.
Aggregates enforce business invariants and manage their own consistency.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .events import (
    ConsensusReached,
    DebateInitiated,
    DecisionMade,
    RoundCompleted,
    RoundStarted,
)
from .value_objects import Argument, Consensus, Topic


class DebateStatus(Enum):
    """Status of a debate session"""

    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DecisionType(Enum):
    """Type of decision being made"""

    SIMPLE = "simple"
    COMPLEX = "complex"
    ARCHITECTURAL = "architectural"
    STRATEGIC = "strategic"


@dataclass
class Round:
    """
    Represents a single debate round

    This is not an aggregate root, but an entity within the DebateSession aggregate.
    """

    id: UUID = field(default_factory=uuid4)
    round_number: int = 0
    arguments: List[Argument] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_argument(self, argument: Argument) -> None:
        """Add an argument to this round"""
        if self.completed_at is not None:
            raise ValueError("Cannot add arguments to completed round")
        self.arguments.append(argument)

    def complete(self) -> None:
        """Mark this round as completed"""
        if self.completed_at is not None:
            raise ValueError("Round is already completed")
        self.completed_at = datetime.now()

    @property
    def is_completed(self) -> bool:
        """Check if this round is completed"""
        return self.completed_at is not None


@dataclass
class DebateSession:
    """
    Debate Session Aggregate Root

    Manages the entire debate lifecycle including rounds, arguments, and consensus.
    Enforces business invariants around debate rules and participant behavior.
    """

    id: UUID = field(default_factory=uuid4)
    topic: Topic = field(default_factory=lambda: Topic(""))
    participants: List[str] = field(default_factory=list)
    rounds: List[Round] = field(default_factory=list)
    status: DebateStatus = DebateStatus.INITIATED
    consensus: Optional[Consensus] = None
    decision: Optional["Decision"] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    max_rounds: int = 5

    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Initialize the debate session and publish domain event"""
        if self.status == DebateStatus.INITIATED and not self._events:
            self._publish_event(
                DebateInitiated(
                    debate_id=self.id,
                    topic=self.topic.value,
                    participants=self.participants,
                    occurred_at=datetime.now(),
                )
            )

    def add_participant(self, participant: str) -> None:
        """Add a participant to the debate"""
        if self.status != DebateStatus.INITIATED:
            raise ValueError("Cannot add participants to debate in progress")
        if participant in self.participants:
            raise ValueError(f"Participant {participant} already in debate")
        self.participants.append(participant)

    def start_round(self) -> Round:
        """Start a new debate round"""
        if self.status == DebateStatus.COMPLETED:
            raise ValueError("Cannot start round in completed debate")

        if len(self.rounds) >= self.max_rounds:
            raise ValueError(f"Maximum rounds ({self.max_rounds}) exceeded")

        # Complete the previous round if it exists and is not completed
        if self.rounds and not self.rounds[-1].is_completed:
            self.rounds[-1].complete()
            self._publish_event(
                RoundCompleted(
                    debate_id=self.id,
                    round_id=self.rounds[-1].id,
                    round_number=self.rounds[-1].round_number,
                    occurred_at=datetime.now(),
                )
            )

        # Create new round
        round_number = len(self.rounds) + 1
        new_round = Round(round_number=round_number)
        self.rounds.append(new_round)

        self.status = DebateStatus.IN_PROGRESS

        self._publish_event(
            RoundStarted(
                debate_id=self.id,
                round_id=new_round.id,
                round_number=round_number,
                occurred_at=datetime.now(),
            )
        )

        return new_round

    def add_argument(self, argument: Argument) -> None:
        """Add an argument to the current round"""
        if not self.rounds:
            raise ValueError("No active round to add argument to")

        current_round = self.rounds[-1]
        if current_round.is_completed:
            raise ValueError("Cannot add argument to completed round")

        current_round.add_argument(argument)

    def reach_consensus(self, consensus: Consensus) -> None:
        """Reach consensus and complete the debate"""
        if self.status == DebateStatus.COMPLETED:
            raise ValueError("Debate is already completed")

        self.consensus = consensus
        self._publish_event(
            ConsensusReached(
                debate_id=self.id, consensus=consensus.value, occurred_at=datetime.now()
            )
        )

    def make_decision(self, decision: "Decision") -> None:
        """Make a final decision and complete the debate"""
        if self.consensus is None:
            raise ValueError("Cannot make decision without consensus")

        self.decision = decision
        self.status = DebateStatus.COMPLETED
        self.completed_at = datetime.now()

        # Complete the current round if it exists
        if self.rounds and not self.rounds[-1].is_completed:
            self.rounds[-1].complete()

        self._publish_event(
            DecisionMade(
                debate_id=self.id,
                decision_id=decision.id,
                decision_type=decision.type.value,
                occurred_at=datetime.now(),
            )
        )

    def cancel(self) -> None:
        """Cancel the debate"""
        if self.status == DebateStatus.COMPLETED:
            raise ValueError("Cannot cancel completed debate")

        self.status = DebateStatus.CANCELLED
        self.completed_at = datetime.now()

    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events

    @property
    def current_round(self) -> Optional[Round]:
        """Get the current active round"""
        if not self.rounds:
            return None
        return self.rounds[-1] if not self.rounds[-1].is_completed else None

    @property
    def is_completed(self) -> bool:
        """Check if the debate is completed"""
        return self.status == DebateStatus.COMPLETED


@dataclass
class Decision:
    """
    Decision Aggregate Root

    Represents a decision made through the debate process.
    Maintains the decision context and rationale.
    """

    id: UUID = field(default_factory=uuid4)
    question: str = ""
    type: DecisionType = DecisionType.SIMPLE
    rationale: str = ""
    recommendation: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    implementation_required: bool = False
    debate_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        """Validate decision invariants"""
        if not self.question.strip():
            raise ValueError("Decision question cannot be empty")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")

        if self.type == DecisionType.COMPLEX and self.debate_id is None:
            raise ValueError("Complex decisions must have an associated debate")

    def update_confidence(self, new_confidence: float) -> None:
        """Update the confidence level of the decision"""
        if not (0.0 <= new_confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        self.confidence = new_confidence

    def mark_for_implementation(self) -> None:
        """Mark this decision as requiring implementation"""
        self.implementation_required = True

    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events

    @property
    def requires_debate(self) -> bool:
        """Check if this decision type requires a debate"""
        return self.type in [
            DecisionType.COMPLEX,
            DecisionType.ARCHITECTURAL,
            DecisionType.STRATEGIC,
        ]
