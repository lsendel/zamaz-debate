"""
Debate Context Value Objects

Value objects are immutable objects that represent concepts with no identity.
They are defined by their attributes and are used to ensure type safety and encapsulation.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ArgumentType(Enum):
    """Type of argument in a debate"""

    SUPPORTING = "supporting"
    OPPOSING = "opposing"
    CLARIFYING = "clarifying"
    EVIDENCE = "evidence"


class ConsensusLevel(Enum):
    """Level of consensus reached"""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


@dataclass(frozen=True)
class Topic:
    """
    Debate Topic Value Object

    Represents the topic or question being debated.
    Immutable to ensure consistency throughout the debate.
    """

    value: str
    description: Optional[str] = None
    category: Optional[str] = None

    def __post_init__(self):
        """Validate topic invariants"""
        if not self.value.strip():
            raise ValueError("Topic value cannot be empty")

        if len(self.value) > 500:
            raise ValueError("Topic value cannot exceed 500 characters")

    @property
    def is_question(self) -> bool:
        """Check if the topic is phrased as a question"""
        return self.value.strip().endswith("?")

    @property
    def word_count(self) -> int:
        """Get the word count of the topic"""
        return len(self.value.split())


@dataclass(frozen=True)
class Argument:
    """
    Argument Value Object

    Represents an argument made by a participant in the debate.
    Immutable to preserve the integrity of the debate record.
    """

    content: str
    participant: str
    type: ArgumentType
    timestamp: datetime
    supporting_evidence: Optional[str] = None
    confidence: float = 0.0

    def __post_init__(self):
        """Validate argument invariants"""
        if not self.content.strip():
            raise ValueError("Argument content cannot be empty")

        if len(self.content) > 5000:
            raise ValueError("Argument content cannot exceed 5000 characters")

        if not self.participant.strip():
            raise ValueError("Argument participant cannot be empty")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")

    @property
    def word_count(self) -> int:
        """Get the word count of the argument"""
        return len(self.content.split())

    @property
    def has_evidence(self) -> bool:
        """Check if the argument has supporting evidence"""
        return self.supporting_evidence is not None and self.supporting_evidence.strip() != ""

    @property
    def strength_score(self) -> float:
        """Calculate a strength score based on confidence and evidence"""
        base_score = self.confidence
        evidence_bonus = 0.1 if self.has_evidence else 0.0
        length_bonus = min(0.1, self.word_count / 1000)  # Bonus for detailed arguments
        return min(1.0, base_score + evidence_bonus + length_bonus)


@dataclass(frozen=True)
class Consensus:
    """
    Consensus Value Object

    Represents the consensus reached at the end of a debate.
    Immutable to preserve the decision record.
    """

    value: str
    level: ConsensusLevel
    rationale: str
    confidence: float
    reached_at: datetime

    def __post_init__(self):
        """Validate consensus invariants"""
        if not self.value.strip():
            raise ValueError("Consensus value cannot be empty")

        if not self.rationale.strip():
            raise ValueError("Consensus rationale cannot be empty")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")

        # Confidence should align with consensus level
        if self.level == ConsensusLevel.STRONG and self.confidence < 0.8:
            raise ValueError("Strong consensus requires confidence >= 0.8")
        elif self.level == ConsensusLevel.MODERATE and self.confidence < 0.6:
            raise ValueError("Moderate consensus requires confidence >= 0.6")
        elif self.level == ConsensusLevel.WEAK and self.confidence < 0.4:
            raise ValueError("Weak consensus requires confidence >= 0.4")

    @property
    def is_actionable(self) -> bool:
        """Check if the consensus is strong enough to be actionable"""
        return self.level in [ConsensusLevel.STRONG, ConsensusLevel.MODERATE]

    @property
    def requires_review(self) -> bool:
        """Check if the consensus requires additional review"""
        return self.level == ConsensusLevel.WEAK or self.confidence < 0.5


@dataclass(frozen=True)
class DecisionCriteria:
    """
    Decision Criteria Value Object

    Represents the criteria used to evaluate decisions.
    Used in complexity assessment and decision evaluation.
    """

    impact: str  # high, medium, low
    complexity: str  # high, medium, low
    reversibility: str  # reversible, semi-reversible, irreversible
    stakeholder_count: int
    time_sensitivity: str  # urgent, moderate, low

    def __post_init__(self):
        """Validate decision criteria invariants"""
        valid_levels = ["high", "medium", "low"]
        valid_reversibility = ["reversible", "semi-reversible", "irreversible"]
        valid_time_sensitivity = ["urgent", "moderate", "low"]

        if self.impact not in valid_levels:
            raise ValueError(f"Impact must be one of {valid_levels}")

        if self.complexity not in valid_levels:
            raise ValueError(f"Complexity must be one of {valid_levels}")

        if self.reversibility not in valid_reversibility:
            raise ValueError(f"Reversibility must be one of {valid_reversibility}")

        if self.time_sensitivity not in valid_time_sensitivity:
            raise ValueError(f"Time sensitivity must be one of {valid_time_sensitivity}")

        if self.stakeholder_count < 0:
            raise ValueError("Stakeholder count cannot be negative")

    @property
    def complexity_score(self) -> float:
        """Calculate a complexity score from 0.0 to 1.0"""
        scores = {"high": 1.0, "medium": 0.6, "low": 0.3}

        impact_score = scores[self.impact]
        complexity_score = scores[self.complexity]
        reversibility_score = {
            "irreversible": 1.0,
            "semi-reversible": 0.6,
            "reversible": 0.3,
        }[self.reversibility]
        stakeholder_score = min(1.0, self.stakeholder_count / 10)  # Normalize to 0-1
        time_score = scores[self.time_sensitivity]

        # Weighted average
        return (
            impact_score * 0.3
            + complexity_score * 0.3
            + reversibility_score * 0.2
            + stakeholder_score * 0.1
            + time_score * 0.1
        )

    @property
    def requires_debate(self) -> bool:
        """Check if these criteria require a debate"""
        return self.complexity_score >= 0.6


@dataclass(frozen=True)
class DebateMetrics:
    """
    Debate Metrics Value Object

    Represents metrics collected during a debate.
    Used for performance analysis and improvement.
    """

    total_rounds: int
    total_arguments: int
    average_argument_length: float
    debate_duration_minutes: int
    consensus_time_minutes: int
    participant_engagement: Dict[str, float]  # participant -> engagement score

    def __post_init__(self):
        """Validate metrics invariants"""
        if self.total_rounds < 0:
            raise ValueError("Total rounds cannot be negative")

        if self.total_arguments < 0:
            raise ValueError("Total arguments cannot be negative")

        if self.average_argument_length < 0:
            raise ValueError("Average argument length cannot be negative")

        if self.debate_duration_minutes < 0:
            raise ValueError("Debate duration cannot be negative")

        if self.consensus_time_minutes < 0:
            raise ValueError("Consensus time cannot be negative")

        # Validate engagement scores
        for participant, score in self.participant_engagement.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"Engagement score for {participant} must be between 0.0 and 1.0")

    @property
    def average_engagement(self) -> float:
        """Calculate average engagement across all participants"""
        if not self.participant_engagement:
            return 0.0
        return sum(self.participant_engagement.values()) / len(self.participant_engagement)

    @property
    def efficiency_score(self) -> float:
        """Calculate debate efficiency score"""
        if self.debate_duration_minutes == 0:
            return 0.0

        # Lower duration with higher argument quality is better
        arguments_per_minute = self.total_arguments / self.debate_duration_minutes
        length_factor = min(1.0, self.average_argument_length / 100)  # Normalize to 0-1
        engagement_factor = self.average_engagement

        return (arguments_per_minute * 0.4 + length_factor * 0.3 + engagement_factor * 0.3) / 3
