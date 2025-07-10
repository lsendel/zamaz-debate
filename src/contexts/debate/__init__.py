"""
Debate Context - Core Domain

This bounded context handles the core business logic of debates between AI agents.
It manages the debate lifecycle, consensus building, and decision making.

Key Aggregates:
- DebateSession: Manages the entire debate process
- Decision: Represents decisions made through debate
- Round: Represents individual debate rounds

Key Domain Services:
- ComplexityAssessment: Determines if a decision requires debate
- ConsensusEvaluation: Evaluates when consensus is reached
- ArgumentValidation: Validates arguments presented in debates
"""

from .aggregates import DebateSession, Decision, Round
from .domain_services import (
    ArgumentValidation,
    ComplexityAssessment,
    ConsensusEvaluation,
)
from .events import (
    ConsensusReached, 
    DebateInitiated, 
    DecisionMade, 
    RoundCompleted,
    DebateRequested,
    DebateStarted,
    DebateCompleted,
)
from .repositories import DebateRepository, DecisionRepository
from .value_objects import Argument, Consensus, Topic


class DebateContext:
    """Main context class for Debate"""
    pass


__all__ = [
    "DebateContext",
    # Aggregates
    "DebateSession",
    "Decision",
    "Round",
    # Domain Services
    "ComplexityAssessment",
    "ConsensusEvaluation",
    "ArgumentValidation",
    # Value Objects
    "Argument",
    "Topic",
    "Consensus",
    # Repositories
    "DebateRepository",
    "DecisionRepository",
    # Events
    "DebateInitiated",
    "RoundCompleted",
    "ConsensusReached",
    "DecisionMade",
    "DebateRequested",
    "DebateStarted",
    "DebateCompleted",
]
